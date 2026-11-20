"""Offline weekly integration with real synthetic normalization/features and a mocked saved model."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.features import dataset, games
from src.ingestion.cfbd import GamesResponse
from src.pipeline import cloud_weekly as cloud, weekly_contract as contract
from src.pipeline.cloud_ingestion import capture_run, CloudS3Store
from src.pipeline.run_contract import STATUS, digest, encode
from tests.test_cloud_ingestion import AtomicS3
from tests.test_dataset import game


class WeeklyS3(AtomicS3):
    def list_objects_v2(self, **kwargs):
        self.calls.append(('list', kwargs))
        assert kwargs['MaxKeys'] == 1
        keys = sorted(k for k in self.objects if k.startswith(kwargs['Prefix']))[:1]
        return {'Contents': [{'Key': k} for k in keys]}


class SavedModel:
    classes_ = [0, 1]

    def predict_proba(self, frame):
        p = np.clip(0.5+frame['home_field'].to_numpy()*0.1+frame['prior_win_pct_diff'].to_numpy()*0.05, 0, 1)
        return np.column_stack((1-p, p))


class WeeklyTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No HTTP')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS')))
        self.enterContext(patch('src.models.baseline.train_baseline', side_effect=AssertionError('Weekly must never train')))
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.client = WeeklyS3(); self.store = cloud.WeeklyStore(self.client, 'fictional-course-bucket', 'project')
        self.refs = [self.capture(y, 4, [game(y), game(y, 2)], f'fixture-{y}') for y in range(2021, 2027)]
        paths = []
        for ref in self.refs:
            path = self.store.download_raw(ref['season'], ref['manifest_name'], self.root/'raw'/str(ref['season']))
            games.normalize_snapshot(path, self.root/'normalized'); paths.append(path)
        original = dataset.build_dataset(paths, self.root/'dataset', normalized_root=self.root/'normalized', allow_retrospective_demo=True)
        self.metadata = {'dataset_id': original['dataset_id'], 'dataset_artifact_sha256': original['artifact_sha256']}
        self.model_base = 'project/cloud-modeling/models/'+'a'*64
        ledger = 'project/cloud-modeling/training/'+'b'*64
        self.client.objects[self.model_base+'/model.joblib'] = b'synthetic saved-model boundary'
        self.client.objects[ledger+'/claim.json'] = b'claim'
        self.client.objects[ledger+'/complete.json'] = b'original completed receipt'
        self.model_ref = {'model_id': 'a'*64, 'training_token_sha256': 'b'*64,
                          'training_receipt_sha256': digest(self.client.objects[ledger+'/complete.json'])}
        receipt = {'model_prefix': self.model_base, 'artifact_sha256': {'model.joblib': digest(self.client.objects[self.model_base+'/model.joblib'])}, 'claim_sha256': digest(b'claim')}
        self.load = self.enterContext(patch.object(cloud.cloud_modeling, 'trusted_model', return_value=(SavedModel(), self.metadata, receipt, self.root)))
        self.event = {'schema_version': 1, 'season': 2026, 'week': 4, 'forecast_cutoff': '2026-08-31T18:00:00Z',
            'run_token': 'weekly-test-01', 'history_sources': self.refs[:5], 'model_reference': self.model_ref,
            'scoring_source': {'mode': 'reuse', 'source': self.refs[-1]}, 'previous_run': None, 'allow_retrospective_demo': True}
        self.invoke = Mock(side_effect=AssertionError('Reuse must never invoke capture'))
        self.client.calls.clear()

    def capture(self, year, week, rows, token, observed='2026-08-31T06:00:00Z'):
        params = {'year': year, 'seasonType': 'regular', 'classification': 'fbs'}
        event = {'schema_version': 1, 'season': year, 'idempotency_token': token}
        if year == 2026: params['week'] = week; event['week'] = week
        response = GamesResponse(json.dumps(rows).encode(), params, observed, 200)
        result = capture_run(event, CloudS3Store(self.client, self.store.bucket, 'project'), lambda: 'synthetic-key', fetch=lambda *a, **k: response)
        self.assertEqual(result['state'], 'completed', result)
        raw = self.client.objects['project/cloud-ingestion/runs/'+result['token_sha256']+'/complete.json']
        return {'season': year, 'manifest_name': result['manifest_key'].rsplit('/', 1)[1],
            'raw_sha256': result['raw_sha256'], 'manifest_sha256': result['manifest_sha256'],
            'capture_token_sha256': result['token_sha256'], 'capture_receipt_sha256': digest(raw)}

    def step(self, event=None): return cloud.advance(self.event if event is None else event, self.store, self.invoke)

    def finish(self, event=None):
        for _ in range(8):
            result = self.step(event)
            if result['state'] != 'pending': return result
        self.fail('Unbounded preparation progress')

    def test_full_weekly_chain_withheld_summary_and_completed_replay_without_external_work(self):
        self.assertEqual(self.step()['pending_stage'], 'preparation')
        self.assertEqual(self.step()['pending_stage'], 'inference')
        self.assertEqual(self.step()['pending_stage'], 'summary')
        result = self.step(); self.assertEqual(result['state'], 'withheld', result)
        self.assertTrue(result['workflow_completed']); self.assertEqual(result['prediction_count'], 2)
        self.assertFalse(result['operational_forecast_approved'])
        for key, value in STATUS.items(): self.assertEqual(result[key], value)
        before = dict(self.client.objects); self.client.calls.clear(); self.load.reset_mock()
        self.assertEqual(self.step(), result); self.assertEqual(before, self.client.objects)
        self.assertFalse(any(c[0] == 'put' for c in self.client.calls)); self.load.assert_not_called(); self.invoke.assert_not_called()

    def test_changed_week_reuses_original_model_and_training_bytes(self):
        first = self.finish()
        rows = [game(2026, week=5, neutralSite=True, startDate='2026-09-08T16:00:00Z')]
        ref = self.capture(2026, 5, rows, 'fixture-week-five', '2026-09-07T06:00:00Z')
        second = self.finish(dict(self.event, run_token='weekly-test-02', week=5, forecast_cutoff='2026-09-07T18:00:00Z', scoring_source={'mode': 'reuse', 'source': ref}))
        self.assertEqual(second['state'], 'withheld', second)
        self.assertEqual(second['prediction_count'], 1)
        self.assertNotEqual(first['scoring_dataset_id'], second['scoring_dataset_id'])
        self.assertEqual(first['model_reference'], second['model_reference'])
        self.assertEqual(self.load.call_count, 2)

    def test_utc_boundaries_offsets_completed_and_staleness(self):
        source = {'retrieved_at': '2026-08-31T06:00:00Z'}
        row = {'completed': False, 'cutoff': '2026-08-31T14:00:00-04:00'}
        reasons = contract.row_reasons(row, source, {}, '2026-08-31T18:00:00Z')
        self.assertIn('scheduled_start_not_after_cutoff', reasons)
        row['cutoff'] = '2026-08-31T14:00:00.000001-04:00'
        self.assertEqual(contract.row_reasons(row, source, {}, '2026-08-31T18:00:00Z'), [])
        self.assertIn('completed', contract.row_reasons(dict(row, completed=True), source, {}, self.event['forecast_cutoff']))
        self.assertIn('schedule_observed_at_or_after_cutoff', contract.row_reasons(row, {'retrieved_at': self.event['forecast_cutoff']}, {}, self.event['forecast_cutoff']))
        self.assertIn('stale_schedule_observation', contract.row_reasons(row, {'retrieved_at': '2026-08-29T06:00:00Z'}, {}, self.event['forecast_cutoff']))
        self.assertIn('2025_observed_at_or_after_cutoff', contract.row_reasons(row, source, {2025: {'retrieved_at': self.event['forecast_cutoff']}}, self.event['forecast_cutoff']))
        self.assertIn('schedule_published_at_or_after_cutoff', contract.row_reasons(row,
            dict(source, source_availability={'available_at': self.event['forecast_cutoff']}), {}, self.event['forecast_cutoff']))

    def test_tbd_completed_missing_history_and_started_games_do_not_get_predictions(self):
        rows = [game(2026, startTimeTBD=True), game(2026, 2, completed=True, homePoints=21, awayPoints=7),
                game(2026, 3, homeId=99), game(2026, 4, startDate='2026-08-31T18:00:00Z')]
        ref = self.capture(2026, 4, rows, 'fixture-exclusions')
        result = self.finish(dict(self.event, scoring_source={'mode': 'reuse', 'source': ref}))
        self.assertEqual(result['state'], 'withheld', result); self.assertEqual(result['prediction_count'], 0)
        eligibility = json.loads(next(v for k, v in self.client.objects.items() if k.endswith('/preparation/eligibility.json')))
        self.assertEqual(len(eligibility['rejected']), 3)
        self.assertEqual(len(eligibility['normalization']['quarantined']), 1)

    def test_missing_history_conflicting_token_wrong_week_and_corruption_fail(self):
        self.assertEqual(self.step(dict(self.event, history_sources=[]))['stage'], 'request_validation')
        self.step()
        self.assertEqual(self.step(dict(self.event, week=5))['stage'], 'run_claim')
        result = self.finish(dict(self.event, run_token='wrong-week-test', week=5))
        self.assertEqual(result['stage'], 'preparation')
        key = 'project/raw/cfbd/games/season=2025/'+self.refs[4]['manifest_name']
        self.client.objects[key] += b'corrupt'
        self.assertEqual(self.step()['stage'], 'preparation')

    def test_partial_publication_and_failed_inference_preserve_recoverable_evidence(self):
        self.step(); self.client.break_after_put = 'rows.json'
        self.assertEqual(self.step()['stage'], 'preparation')
        partial = dict(self.client.objects)
        self.assertEqual(self.step()['pending_stage'], 'inference')
        self.assertTrue(all(self.client.objects[k] == v for k, v in partial.items()))
        with patch.object(cloud.cloud_modeling, 'trusted_model', side_effect=RuntimeError('private detail')):
            failure = self.step(); self.assertEqual(failure['stage'], 'inference'); self.assertNotIn('private detail', str(failure))
        self.assertEqual(self.finish()['state'], 'withheld')

    def test_completed_corrupt_predictions_or_source_never_repairs_or_reports_completion(self):
        result = self.finish()
        key = next(k for k in result['artifact_sha256'] if k.endswith('/predictions.csv'))
        self.client.objects[key] += b'changed'; before = dict(self.client.objects)
        self.assertEqual(self.step()['stage'], 'completed_replay')
        self.assertTrue(all(self.client.objects[k] == v for k, v in before.items()))

    def test_ambiguous_capture_invocation_only_polls_existing_receipt_never_invokes_again(self):
        event = dict(self.event, scoring_source={'mode': 'capture', 'capture_token': 'fresh-weekly-token'})
        self.invoke.side_effect = TimeoutError('private detail')
        self.assertEqual(self.step(event)['state'], 'failed')
        for _ in range(3): self.assertEqual(self.step(event)['state'], 'pending')
        self.assertEqual(self.invoke.call_count, 1)

    def test_fresh_capture_owner_and_duplicate_call_reuse_one_ingestion_request(self):
        event = dict(self.event, scoring_source={'mode': 'capture', 'capture_token': 'fresh-weekly-token'})
        def capture(payload):
            self.capture(2026, 4, [game(2026)], payload['idempotency_token']); return {'state': 'completed'}
        self.invoke.side_effect = capture
        result = self.finish(event)
        self.assertEqual(result['state'], 'withheld', result); self.assertEqual(self.invoke.call_count, 1)
        self.finish(event); self.assertEqual(self.invoke.call_count, 1)

    def test_prior_schedule_revision_preserves_old_run_and_withholds_earlier_start(self):
        first = self.finish(); old = dict(self.client.objects)
        token = digest(self.event['run_token'].encode())
        previous = {'run_token_sha256': token, 'summary_sha256': digest(self.client.objects['project/weekly/runs/'+token+'/complete.json'])}
        ref = self.capture(2026, 4, [game(2026, startDate='2026-09-04T16:00:00Z')], 'schedule-revision', '2026-09-02T06:00:00Z')
        second = self.finish(dict(self.event, run_token='revision-test-01', forecast_cutoff='2026-09-02T18:00:00Z', previous_run=previous, scoring_source={'mode': 'reuse', 'source': ref}))
        self.assertEqual(second['state'], 'withheld', second); self.assertEqual(second['prediction_count'], 0)
        self.assertTrue(all(self.client.objects[k] == v for k, v in old.items()))

    def test_changed_training_evidence_is_rejected_without_model_fit(self):
        self.step(); self.step()
        self.metadata['dataset_artifact_sha256']['train.csv'] = '0'*64
        self.assertEqual(self.step()['stage'], 'inference')

    def test_invalid_contract_and_handler_configuration_are_refused_before_clients(self):
        for event in (dict(self.event, forecast_cutoff='2026-08-31'), dict(self.event, allow_retrospective_demo=False), dict(self.event, season=2027)):
            self.client.calls.clear(); self.assertEqual(self.step(event)['stage'], 'request_validation'); self.assertEqual(self.client.calls, [])
        with patch.object(cloud.boto3, 'client') as client:
            self.assertEqual(cloud.handler({}, None)['state'], 'failed'); client.assert_not_called()
