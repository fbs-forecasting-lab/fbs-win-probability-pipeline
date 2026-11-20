"""Offline preparation, recovery, lineage and local SQL semantic checks."""

import csv
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.features import dataset, games
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.pipeline import cloud_preparation as cloud, preparation_contract as contract
from src.pipeline.cloud_ingestion import capture_run, CloudS3Store
from src.pipeline.run_contract import STATUS, digest, encode
from tests.test_cloud_ingestion import AtomicS3
from tests.test_dataset import game
from tests.test_s3_storage import error


class PreparationS3(AtomicS3):
    def list_objects_v2(self, **kwargs):
        self.calls.append(('list', kwargs))
        if kwargs['MaxKeys'] != 1 or not kwargs['Prefix'].startswith(('project/raw/cfbd/games/',
                'project/cloud-ingestion/runs/', 'project/cloud-preparation/', 'project/datasets/')):
            raise error('AccessDenied', 403)
        keys = sorted(k for k in self.objects if k.startswith(kwargs['Prefix']))[:1]
        return {'Contents': [{'Key': key} for key in keys]}


def local_sql(client, sql):
    """Execute the SAME SQL using SQLite; this is not Athena evidence."""
    selection = sql.split("selection_id = '")[1].split("'")[0]
    content = client.objects[f'project/cloud-preparation/queryable/selection_id={selection}/games.jsonl']
    records = [json.loads(line) for line in content.splitlines()]
    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        db.execute("ATTACH DATABASE ':memory:' AS fbs_preparation")
        columns = list(games.COLUMNS) + ['start_epoch_us','selection_id']
        db.execute('CREATE TABLE fbs_preparation.selected_games (' + ','.join(columns) + ')')
        for row in records:
            db.execute('INSERT INTO fbs_preparation.selected_games VALUES (' + ','.join('?' for _ in columns) + ')',
                       [row.get(c) for c in columns[:-1]] + [selection])
        cursor = db.execute(sql)
        names = [item[0] for item in cursor.description]
        rows = [dict(row) for row in cursor]
    return names, rows


class LocalAthena:
    """API shape and stable token simulation, not validation of the AWS runtime."""
    def __init__(self, client):
        self.client, self.starts, self.queries = client, [], {}
        self.state, self.mutate = 'SUCCEEDED', None
        self.ambiguous = False

    def start_query_execution(self, **kwargs):
        token = kwargs['ClientRequestToken']
        self.starts.append(kwargs)
        if token not in self.queries:
            self.queries[token] = kwargs
        elif self.queries[token] != kwargs:
            raise ValueError('Changed idempotent request')
        if self.ambiguous:
            self.ambiguous = False
            raise TimeoutError('sensitive service details')
        return {'QueryExecutionId': token}

    def get_query_execution(self, QueryExecutionId):
        q = self.queries[QueryExecutionId]
        return {'QueryExecution': {'Query':q['QueryString'], 'WorkGroup':q['WorkGroup'],
            'QueryExecutionContext':q['QueryExecutionContext'], 'Status': {'State':self.state}}}

    def get_query_results(self, QueryExecutionId, **kwargs):
        names, rows = local_sql(self.client, self.queries[QueryExecutionId]['QueryString'])
        if self.mutate:
            self.mutate(rows)
        return {'ResultSet': {'ResultSetMetadata': {'ColumnInfo':[{'Name':n} for n in names]},
                'Rows':[{'Data':[{'VarCharValue':n} for n in names]}] + [
                    {'Data':[{} if row[n] is None else {'VarCharValue':str(row[n])} for n in names]} for row in rows]}}


class CloudPreparationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No network')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS')))
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.client = PreparationS3()
        self.store = cloud.PreparationStore(self.client, 'course-project-bucket', 'project')
        self.athena = LocalAthena(self.client)
        self.event = {'schema_version':1,'allow_retrospective_demo':True,'require_cloud_sources':False,'sources':[]}
        self.paths = []

    def fixtures(self, overrides=None, cloud_sources=False):
        for season in dataset.SEASONS:
            rows = (overrides or {}).get(season, [game(season), game(season, 2)])
            params = {'year':season,'seasonType':'regular','classification':'fbs'}
            if season == 2026:
                params['week'] = 4
            response = GamesResponse(json.dumps(rows).encode(), params, '2026-11-20T06:00:00Z', 200)
            if cloud_sources:
                request = {'schema_version':1,'season':season,'idempotency_token':f'synthetic-{season}'}
                if season == 2026:
                    request['week'] = 4
                result = capture_run(request, CloudS3Store(self.client, self.store.bucket, 'project'),
                    lambda:'fictional-key', fetch=lambda *args, **kwargs: response)
                self.assertEqual(result['state'], 'completed', result)
                name = result['manifest_key'].split('/')[-1]
                path = self.store.download_raw(season, name, self.root/'reference'/str(season))
            else:
                path = save_snapshot(response, self.root/'raw'/str(season))[1]
                self.store.upload_raw(path)
            source = games.load_snapshot(path).source
            reference = {'season':season,'manifest_name':path.name,'raw_sha256':source['raw_sha256'],
                         'manifest_sha256':source['manifest_sha256']}
            if cloud_sources:
                reference.update(capture_token_sha256=result['token_sha256'], capture_receipt_sha256=digest(
                    self.client.objects[f"project/cloud-ingestion/runs/{result['token_sha256']}/complete.json"]))
            self.event['sources'].append(reference)
            self.paths.append(path)
        self.client.calls.clear()

    def run_preparation(self, event=None):
        return cloud.prepare_run(self.event if event is None else event, self.store, self.athena)

    def test_sql_parity_splits_labels_zero_scores_and_neutral_site(self):
        self.fixtures()
        result = self.run_preparation()
        self.assertEqual(result['state'], 'completed', result)
        self.assertEqual(result['splits'], {'train':6,'holdout':2,'prediction':2})
        self.assertEqual(result['sql_parity']['verified_target_rows'], 10)
        for k,v in STATUS.items():
            self.assertEqual(result[k], v)
        prefix = result['dataset_prefix']
        for path in self.paths:
            games.normalize_snapshot(path, self.root/'normalized')
        expected = dataset.build_dataset(self.paths, self.root/'expected', normalized_root=self.root/'normalized',
                                         allow_retrospective_demo=True)
        self.assertEqual(expected['dataset_id'],result['dataset_id'])
        for name in contract.DATA_FILES:
            self.assertEqual((self.root/'expected'/name).read_bytes(),self.client.objects[f'{prefix}/{name}'])
        self.assertEqual(len(self.athena.starts),1)
        self.assertTrue(all(v['origin']=='legacy_upload_unverified' for v in result['origins'].values()))

    def test_sql_parity_missing_history_completion_exclusions_quarantine_and_duplicates(self):
        self.fixtures({2022:[game(2022, homeId=99),game(2022,2,completed=False,homePoints=None,awayPoints=None),
                            game(2022,3,awayClassification='fcs'),game(2022,4,startTimeTBD=True)],
                       2026:[game(2026,completed=True,homePoints=14,awayPoints=7),game(2026,2),
                             game(2026,3),game(2026,3)]})
        result = self.run_preparation()
        self.assertEqual(result['state'],'completed',result)
        self.assertEqual(result['splits']['train'],2)
        self.assertEqual(result['splits']['prediction'],1)
        quality = [json.loads(v) for k,v in self.client.objects.items() if k.endswith('quality_report.json')]
        self.assertTrue(any(q['counts']['quarantined'] == 2 for q in quality))

    def test_sql_parity_rejects_equal_cutoff_and_fractional_timestamp_order(self):
        self.fixtures({2021:[game(2021,startDate='2022-09-01T16:00:00.000001Z'),game(2021,2)],
                       2022:[game(2022,startDate='2022-09-01T16:00:00Z'),game(2022,2)]})
        result = self.run_preparation()
        self.assertEqual(result['state'],'completed',result)
        self.assertEqual(result['splits']['train'],5)

    def test_missing_duplicate_seasons_permission_and_graded_lineage_refused_before_io(self):
        self.fixtures()
        for changed in [self.event|{'sources':self.event['sources'][:-1]},
                        self.event|{'sources':[self.event['sources'][0]]*6},
                        self.event|{'allow_retrospective_demo':False}, self.event|{'require_cloud_sources':True},
                        self.event|{'secret':'forbidden'}]:
            with self.subTest(changed=changed.keys()):
                self.client.calls.clear()
                result = self.run_preparation(changed)
                self.assertEqual(result['stage'],'request_validation')
                self.assertEqual(self.client.calls,[])
        self.assertFalse(self.athena.starts)

    def test_hash_corruption_and_week_limited_history_stop_before_query_or_publication(self):
        self.fixtures()
        key = next(k for k in self.client.objects if '/season=2021/' in k and k.endswith('.json') and not k.endswith('manifest.json'))
        self.client.objects[key] += b'changed'
        result = self.run_preparation()
        self.assertEqual(result['stage'],'source_verification')
        self.assertFalse(self.athena.starts)
        self.assertFalse(any('cloud-preparation' in k for k in self.client.objects))

    def test_week_limited_history_missing_source_and_wrong_expected_hash_are_explicit_failures(self):
        self.fixtures()
        reference = self.event['sources'][0]
        bad = json.loads(json.dumps(self.event))
        bad['sources'][0]['manifest_sha256'] = '0'*64
        self.assertEqual(self.run_preparation(bad)['message'],'Selected raw/manifest hash mismatch.')
        params = {'year':2021,'seasonType':'regular','classification':'fbs','week':1}
        response = GamesResponse(json.dumps([game(2021)]).encode(),params,'2026-11-20T06:00:00Z',200)
        path = save_snapshot(response,self.root/'weekly')[1]
        self.store.upload_raw(path)
        source = games.load_snapshot(path).source
        bad['sources'][0] = {'season':2021,'manifest_name':path.name,'raw_sha256':source['raw_sha256'],
                             'manifest_sha256':source['manifest_sha256']}
        self.assertIn('full-season',self.run_preparation(bad)['message'])
        del self.client.objects[f"project/raw/cfbd/games/season=2021/{reference['manifest_name']}"]
        self.assertEqual(self.run_preparation()['stage'],'source_verification')
        self.assertFalse(self.athena.starts)

    def test_verified_cloud_lineage_and_forged_receipt_rejection(self):
        self.fixtures(cloud_sources=True)
        self.event['require_cloud_sources'] = True
        result = self.run_preparation()
        self.assertEqual(result['state'],'completed',result)
        self.assertTrue(all(v['cloud_capture_verified'] for v in result['origins'].values()))
        bad = json.loads(json.dumps(self.event))
        bad['sources'][0]['capture_receipt_sha256'] = '0'*64
        self.assertEqual(self.run_preparation(bad)['stage'],'source_verification')

    def test_pending_query_and_completed_replay_reuse_immutable_objects(self):
        self.fixtures()
        self.athena.state = 'RUNNING'
        pending = self.run_preparation()
        self.assertEqual(pending['state'],'query_pending',pending)
        self.assertFalse(any('/datasets/' in k for k in self.client.objects))
        self.athena.state = 'SUCCEEDED'
        result = self.run_preparation()
        before = dict(self.client.objects)
        self.client.calls.clear()
        self.assertEqual(result,self.run_preparation())
        self.assertEqual(before,self.client.objects)
        self.assertFalse(any(call[0]=='put' for call in self.client.calls))
        self.assertEqual(len(self.athena.starts),1)

    def test_interrupted_publication_and_ambiguous_query_start_recover_without_second_query(self):
        self.fixtures()
        self.client.break_after_put = 'games.csv'
        self.assertEqual(self.run_preparation()['state'],'failed')
        self.athena.ambiguous = True
        self.assertEqual(self.run_preparation()['stage'],'athena_query')
        result = self.run_preparation()
        self.assertEqual(result['state'],'completed',result)
        self.assertEqual(len(self.athena.queries),1)
        self.assertEqual(len(self.athena.starts),2)

    def test_conflict_and_missing_completed_outputs_fail_closed(self):
        self.fixtures()
        result = self.run_preparation()
        key = result['dataset_prefix']+'/train.csv'
        self.client.objects[key] = b'conflicting evidence'
        before = dict(self.client.objects)
        self.assertEqual(self.run_preparation()['state'],'failed')
        self.assertEqual(self.client.objects,before)
        del self.client.objects[key]
        self.assertEqual(self.run_preparation()['state'],'failed')
        self.assertNotIn(key,self.client.objects)

    def test_sql_difference_never_publishes_dataset_or_complete(self):
        self.fixtures()
        self.athena.mutate = lambda rows: rows[0].update(prior_win_pct_diff=123)
        result = self.run_preparation()
        self.assertEqual(result['stage'],'sql_parity',result)
        self.assertFalse(any('/datasets/' in k or k.endswith('/complete.json') for k in self.client.objects))

    def test_sql_failure_duplicate_missing_target_and_nan_never_publish(self):
        self.fixtures()
        self.athena.state = 'FAILED'
        self.assertEqual(self.run_preparation()['stage'],'athena_query')
        self.athena.state = 'SUCCEEDED'
        for mutation in [lambda rows: rows.append(rows[0]),lambda rows: rows.pop(),
                         lambda rows: rows[0].update(prior_avg_margin_diff='nan')]:
            self.athena.mutate = mutation
            self.assertEqual(self.run_preparation()['stage'],'sql_parity')
        self.assertFalse(any('/datasets/' in k for k in self.client.objects))

    def test_unselected_snapshot_is_not_counted_and_source_order_is_canonical(self):
        self.fixtures()
        extra = save_snapshot(GamesResponse(json.dumps([game(2021)]).encode(),
            {'year':2021,'seasonType':'regular','classification':'fbs'},'2026-11-20T07:00:00Z',200),self.root/'extra')[1]
        self.store.upload_raw(extra)
        result = self.run_preparation()
        self.assertEqual(result['state'],'completed',result)
        before = dict(self.client.objects)
        self.assertEqual(result,self.run_preparation(self.event|{'sources':self.event['sources'][::-1]}))
        self.assertEqual(before,self.client.objects)
        self.assertEqual(result['splits'],{'train':6,'holdout':2,'prediction':2})

    def test_missing_prepared_artifact_is_not_silently_repaired(self):
        self.fixtures()
        result = self.run_preparation()
        key = next(k for k in self.client.objects if '/normalized/' in k and k.endswith('games.csv'))
        del self.client.objects[key]
        self.assertEqual(self.run_preparation()['stage'],'publish_normalized')
        self.assertNotIn(key,self.client.objects)

    def test_query_result_pagination_preserves_every_row(self):
        pages = [
            {'ResultSet':{'ResultSetMetadata':{'ColumnInfo':[{'Name':'id'}]},
                          'Rows':[{'Data':[{'VarCharValue':'id'}]},{'Data':[{'VarCharValue':'1'}]}]},'NextToken':'next'},
            {'ResultSet':{'ResultSetMetadata':{'ColumnInfo':[{'Name':'id'}]},'Rows':[{'Data':[{'VarCharValue':'2'}]}]}}]
        from unittest.mock import Mock
        client = Mock()
        client.get_query_results.side_effect = pages
        self.assertEqual(cloud.query_rows(client,'known'),[{'id':'1'},{'id':'2'}])
        self.assertEqual(client.get_query_results.call_args.kwargs['NextToken'],'next')

    def test_operational_cutoff_refuses_post_cutoff_and_unknown_availability(self):
        self.fixtures()
        for cutoff, message in [('2026-09-01T00:00:00Z','at/after'),('2027-01-01T00:00:00Z','unverified')]:
            result = self.run_preparation(self.event|{'forecast_cutoff':cutoff})
            self.assertEqual(result['stage'],'source_verification')
            self.assertIn(message,result['message'])
        self.assertFalse(self.athena.starts)

    def test_private_bucket_access_denied_and_unexpected_errors_are_sanitized(self):
        self.fixtures()
        self.client.flags['BlockPublicAcls'] = False
        self.assertEqual(self.run_preparation()['stage'],'aws_preflight')
        self.client.flags['BlockPublicAcls'] = True
        with patch.object(self.client,'get_object',side_effect=error('AccessDenied',403)):
            self.assertEqual(self.run_preparation()['stage'],'source_verification')
        with patch.object(self.store,'download_raw',side_effect=RuntimeError('private contents')):
            result = self.run_preparation()
            self.assertEqual(result['error_type'],'RuntimeError')
            self.assertNotIn('private contents',json.dumps(result))
        self.assertFalse(self.athena.starts)

    def test_no_api_secret_model_or_local_history_dependency(self):
        self.fixtures()
        with patch('src.ingestion.cfbd.fetch_games',side_effect=AssertionError('No fetch')), \
             patch('src.pipeline.week_refresh.discover_history',side_effect=AssertionError('No local history')):
            self.assertEqual(self.run_preparation()['state'],'completed')

    def seed_successful_query(self):
        """Leave the original immutable query ledger, without publishing a dataset."""
        self.athena.state = 'RUNNING'
        pending = self.run_preparation()
        self.assertEqual(pending['state'], 'query_pending', pending)
        self.athena.state = 'SUCCEEDED'
        return pending

    def test_query_verification_tolerates_only_boundary_whitespace(self):
        self.fixtures()
        self.seed_successful_query()
        original = self.athena.get_query_execution
        for transform in (lambda sql: sql.removesuffix('\n'), lambda sql: '\n \t'+sql+'\t\n '):
            def response(**kwargs):
                result = original(**kwargs)
                result['QueryExecution']['Query'] = transform(result['QueryExecution']['Query'])
                return result
            with patch.object(self.athena, 'get_query_execution', side_effect=response), \
                 patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
                result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
                self.assertEqual(result['state'], 'completed', result)
        self.assertEqual(len(self.athena.starts), 1)

    def test_material_sql_body_and_database_workgroup_changes_fail_verification(self):
        self.fixtures()
        self.seed_successful_query()
        original = self.athena.get_query_execution
        changes = (
            lambda q: q.update(Query=q['Query'].replace('SELECT *', 'SELECT  *', 1)),
            lambda q: q.update(Query=q['Query'].replace("'prediction'", "'holdout'")),
            lambda q: q.update(Query=q['Query'].split('\n', 1)[1]),
            lambda q: q.update(Query=q['Query']+'-- changed comment'),
            lambda q: q.update(Query=q['Query'].replace("selection_id = '", "selection_id = '0", 1)),
            lambda q: q.update(WorkGroup='different-workgroup'),
            lambda q: q.update(QueryExecutionContext={'Database':'different_database'}),
        )
        for change in changes:
            def response(**kwargs):
                result = original(**kwargs)
                change(result['QueryExecution'])
                return result
            with patch.object(self.athena, 'get_query_execution', side_effect=response), \
                 patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
                result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
                self.assertEqual(result['stage'], 'athena_query', result)
                self.assertIn('identity', result['message'])
        self.assertFalse(any('/datasets/' in key or key.endswith('/complete.json') for key in self.client.objects))

    def test_recovery_preserves_selection_arguments_receipt_and_query_id_without_start(self):
        self.fixtures(cloud_sources=True)
        self.event['require_cloud_sources'] = True
        request = contract.validate(self.event)
        legacy_selection = digest(encode({'request':request,
            'implementation_sha256':'e583b79e8bef1e2c1d13adf25a6c595eb67ae569bd9a190a86b9c48f46d18725',
            'database':'fbs_preparation','table':'selected_games','workgroup':'fbs-data-preparation'}))
        pending = self.seed_successful_query()
        self.assertEqual(pending['selection_id'], legacy_selection)
        key = f"project/cloud-preparation/runs/{legacy_selection}/query.json"
        before = self.client.objects[key]
        sources = {k:v for k,v in self.client.objects.items() if '/raw/' in k or '/cloud-ingestion/' in k}
        original = self.athena.get_query_execution
        def trimmed(**kwargs):
            response = original(**kwargs)
            response['QueryExecution']['Query'] = response['QueryExecution']['Query'].rstrip('\n')
            return response
        with patch.object(self.athena, 'get_query_execution', side_effect=trimmed), \
             patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
            result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
            self.assertEqual(result['state'], 'completed', result)
            self.assertEqual(result['query_id'], pending['query_id'])
            self.assertEqual(result, cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True))
        self.assertEqual(self.client.objects[key], before)
        self.assertEqual(sources, {k:v for k,v in self.client.objects.items() if k in sources})
        self.assertEqual(len(self.athena.starts), 1)

    def test_recovery_refuses_missing_or_unsuccessful_query_without_start(self):
        self.fixtures()
        with patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
            result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
            self.assertEqual(result['stage'], 'athena_query', result)
            self.assertIn('original query receipt', result['message'])
        self.seed_successful_query()
        for state in ('RUNNING', 'FAILED', 'CANCELLED'):
            self.athena.state = state
            with patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
                result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
                self.assertEqual(result['state'], 'failed', result)
                self.assertIn('original successful query', result['message'])
        self.assertEqual(len(self.athena.starts), 1)

    def test_recovery_still_requires_sql_parity_before_dataset_publication(self):
        self.fixtures()
        self.seed_successful_query()
        self.athena.mutate = lambda rows: rows[0].update(prior_avg_margin_diff=999)
        with patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
            result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
        self.assertEqual(result['stage'], 'sql_parity', result)
        self.assertFalse(any('/datasets/' in k or k.endswith('/complete.json') for k in self.client.objects))

    def test_recovery_resumes_partial_dataset_and_preserves_completed_replay(self):
        self.fixtures()
        self.seed_successful_query()
        self.client.break_after_put = 'train.csv'
        with patch.object(self.athena, 'start_query_execution', side_effect=AssertionError('No replacement query')):
            failed = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
            self.assertEqual(failed['stage'], 'publish_dataset', failed)
            partial = {k:v for k,v in self.client.objects.items() if '/datasets/' in k}
            result = cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True)
            self.assertEqual(result['state'], 'completed', result)
            self.assertEqual(partial, {k:v for k,v in self.client.objects.items() if k in partial})
            before = dict(self.client.objects)
            self.client.calls.clear()
            self.assertEqual(result, cloud.prepare_run(self.event, self.store, self.athena, recovery_only=True))
            self.assertEqual(before, self.client.objects)
            self.assertFalse(any(call[0]=='put' for call in self.client.calls))

    def test_identity_bridge_refuses_unreviewed_source_hash_or_legacy_identity_changes(self):
        self.fixtures()
        record = json.loads(contract.COMPATIBILITY_PATH.read_bytes())
        for section in ('runtime_source_sha256', 'identity_source_sha256'):
            altered = json.loads(json.dumps(record))
            altered[section]['cloud_preparation.py'] = '0'*64
            path = self.root/(section+'.json')
            path.write_text(json.dumps(altered))
            with patch.object(contract, 'COMPATIBILITY_PATH', path):
                result = self.run_preparation()
                self.assertEqual(result['stage'], 'request_validation', result)
                self.assertIn('compatibility', result['message'])
        self.assertFalse(self.athena.starts)


if __name__ == '__main__':
    unittest.main()
