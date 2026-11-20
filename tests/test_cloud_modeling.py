"""Synthetic offline training/inference adapters; no project data or network."""

from contextlib import contextmanager
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.models import baseline, predict
from src.pipeline import cloud_modeling as cloud, model_contract as contract
from src.pipeline.run_contract import STATUS, digest, encode
from tests import test_baseline as baseline_fixtures
from tests.test_cloud_ingestion import AtomicS3
from tests.test_s3_storage import error


class ModelS3(AtomicS3):
    def list_objects_v2(self, **kwargs):
        self.calls.append(('list', kwargs))
        if kwargs['MaxKeys'] != 1 or not kwargs['Prefix'].startswith(('project/datasets/', 'project/cloud-modeling/', 'project/cloud-preparation/runs/')):
            raise error('AccessDenied', 403)
        keys = sorted(k for k in self.objects if k.startswith(kwargs['Prefix']))[:1]
        return {'Contents': [{'Key': k} for k in keys]}


class CloudModelingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No network')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS')))
        fixture = baseline_fixtures.BaselineTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.root = fixture, fixture.root
        self.client = ModelS3()
        self.store = cloud.ModelingStore(self.client, 'course-project-bucket', 'project')
        data = baseline.load_dataset(fixture.data, allow_retrospective_demo=True)
        self.store.upload_dataset(fixture.data, allow_retrospective_demo=True)
        self.selection = 'a' * 64
        files = baseline.DATA_FILES | {'dataset_report.json'}
        prep = {**STATUS, 'state': 'completed', 'selection_id': self.selection, 'dataset_id': data['report']['dataset_id'],
                'sql_parity': {'verified_target_rows': 20},
                'origins': {str(y): {'cloud_capture_verified': True} for y in range(2021, 2027)},
                'dataset_artifact_sha256': {n: digest((fixture.data / n).read_bytes()) for n in files}}
        content = encode(prep)
        self.prep_key = f'project/cloud-preparation/runs/{self.selection}/complete.json'
        self.client.objects[self.prep_key] = content
        self.request = {'schema_version': 1, 'allow_retrospective_demo': True, 'training_token': 'synthetic-train-01',
                        'dataset_id': data['report']['dataset_id'], 'preparation_selection_id': self.selection,
                        'preparation_receipt_sha256': digest(content)}
        self.store.approved_reference = {k:self.request[k] for k in ('dataset_id','preparation_selection_id','preparation_receipt_sha256')}
        self.client.calls.clear()

    def train(self, request=None):
        return cloud.train_run(self.request if request is None else request, self.store)

    def reference(self, result, mode='saved_sample'):
        token = result['training_token_sha256']
        receipt = self.client.objects[f'project/cloud-modeling/training/{token}/complete.json']
        request = {'schema_version': 1, 'allow_retrospective_demo': True, 'model_id': result['model_id'],
                   'training_token_sha256': token, 'training_receipt_sha256': digest(receipt), 'mode': mode}
        if mode == 'hypothetical': request['features'] = dict(zip(baseline.PREDICTORS, (.2, 7, 1)))
        return request

    def test_train_equivalent_metrics_calibration_settings_and_saved_reload(self):
        result = self.train()
        self.assertEqual(result['state'], 'completed', result)
        expected_metadata, expected_eval = self.fixture.train()
        self.assertEqual(result['evaluation'], expected_eval)
        self.assertEqual(result['counts'], {'train':12,'holdout':4,'prediction':4})
        base = result['model_prefix']
        for name in contract.MODEL_FILES[:7]:
            self.assertEqual(self.client.objects[base+'/'+name], (self.fixture.output/name).read_bytes())
        interpretation = json.loads(self.client.objects[base+'/interpretation.json'])
        self.assertEqual(interpretation['scaler_fitted_rows'], 12)
        self.assertEqual([r['feature'] for r in interpretation['features']], baseline.PREDICTORS)
        self.assertIn('not causal', interpretation['context'])
        inferred = cloud.infer_run(self.reference(result), self.store)
        self.assertEqual(inferred['state'], 'completed', inferred)
        self.assertEqual(inferred['count'], 4)
        key = f"project/cloud-modeling/inference/{inferred['inference_id']}/predictions.csv"
        self.assertEqual(self.client.objects[key], self.client.objects[base+'/sample_predictions.csv'])
        for row in csv.DictReader(io.StringIO(self.client.objects[key].decode())):
            self.assertAlmostEqual(float(row['home_win_probability'])+float(row['away_win_probability']),1)
        hypothetical = cloud.infer_run(self.reference(result, 'hypothetical'), self.store)
        model = self.fixture.restore()
        expected = predict.predict_vector(model, dict(zip(baseline.PREDICTORS, (.2,7,1))))
        self.assertEqual(hypothetical['home_win_probability'], expected['home_win_probability'])
        self.assertEqual(hypothetical['away_win_probability'], expected['away_win_probability'])
        for field, value in STATUS.items(): self.assertEqual(hypothetical[field], value)

    def test_completed_replay_never_retrains_and_preserves_all_objects(self):
        result = self.train()
        before = dict(self.client.objects)
        self.client.calls.clear()
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('Never retrain')):
            self.assertEqual(self.train(), result)
        self.assertEqual(self.client.objects, before)
        self.assertFalse(any(c[0]=='put' for c in self.client.calls))

    def test_partial_model_publication_recovers_original_checkpoint_without_fit(self):
        self.client.break_after_put = 'model.joblib'
        failure = self.train()
        self.assertEqual(failure['stage'],'publish_model',failure)
        before = {k:v for k,v in self.client.objects.items() if '/models/' in k}
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('Never refit')):
            result = self.train()
        self.assertEqual(result['state'],'completed',result)
        self.assertEqual(before,{k:v for k,v in self.client.objects.items() if k in before})

    def test_ambiguous_checkpoint_write_reuses_bytes_without_refetch_or_refit(self):
        self.client.break_after_put = 'checkpoint.json'
        self.assertEqual(self.train()['stage'],'model_checkpoint')
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('Never refit')):
            self.assertEqual(self.train()['state'],'completed')

    def test_interrupted_claim_without_checkpoint_does_not_train_again(self):
        with patch.object(baseline,'train_baseline',side_effect=RuntimeError('private details')):
            self.assertEqual(self.train()['stage'],'training_evaluation')
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('Never refit')):
            result = self.train()
        self.assertIn('no durable model checkpoint',result['message'])
        self.assertNotIn('private details',json.dumps(result))

    def test_preparation_receipt_or_dataset_corruption_stops_before_fit(self):
        with patch.object(baseline,'train_baseline') as train:
            bad = self.request|{'preparation_receipt_sha256':'0'*64}
            self.assertEqual(self.train(bad)['stage'],'dataset_verification')
            key = next(k for k in self.client.objects if k.endswith('/train.csv'))
            self.client.objects[key] += b'corrupt'
            self.assertEqual(self.train()['stage'],'dataset_verification')
            train.assert_not_called()

    def test_corrupt_model_or_receipt_is_never_deserialized(self):
        result = self.train()
        request = self.reference(result,'hypothetical')
        key = result['model_prefix']+'/model.joblib'
        self.client.objects[key] += b'corrupt'
        with patch.object(baseline.joblib,'load',side_effect=AssertionError('No untrusted load')) as load:
            value = cloud.infer_run(request,self.store)
            self.assertEqual(value['stage'],'trusted_model_reload')
            load.assert_not_called()
            value = cloud.infer_run(request|{'training_receipt_sha256':'0'*64},self.store)
            self.assertEqual(value['stage'],'trusted_model_reload')
            load.assert_not_called()

    def test_completed_missing_or_conflicting_model_cannot_be_repaired_or_retrained(self):
        result = self.train()
        key = result['model_prefix']+'/evaluation.json'
        self.client.objects[key] = b'conflict'
        before = dict(self.client.objects)
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('No fit')):
            self.assertEqual(self.train()['state'],'failed')
        self.assertEqual(before,self.client.objects)
        del self.client.objects[key]
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('No fit')):
            self.assertEqual(self.train()['state'],'failed')
        self.assertNotIn(key,self.client.objects)

    def test_invalid_requests_vectors_and_arbitrary_urls_refused_before_io(self):
        invalid = [self.request|{'allow_retrospective_demo':False},self.request|{'model_url':'https://invalid'},
                   self.request|{'dataset_id':'../../unsafe'}]
        for request in invalid:
            self.client.calls.clear()
            self.assertEqual(self.train(request)['stage'],'request_validation')
            self.assertFalse(self.client.calls)
        result = self.train()
        request = self.reference(result,'hypothetical')
        for features in ({'score':1}, {'prior_win_pct_diff':True,'prior_avg_margin_diff':7,'home_field':1},
                         {'prior_win_pct_diff':float('nan'),'prior_avg_margin_diff':7,'home_field':1},
                         {'prior_win_pct_diff':.2,'prior_avg_margin_diff':7,'home_field':.5}):
            self.client.calls.clear()
            self.assertEqual(cloud.infer_run(request|{'features':features},self.store)['stage'],'request_validation')
            self.assertFalse(self.client.calls)

    def test_cloud_adapter_preserves_train_only_fitting_under_changed_holdout_labels(self):
        a = self.train()
        metadata = json.loads(self.client.objects[a['model_prefix']+'/model_metadata.json'])
        with tempfile.TemporaryDirectory() as tmp:
            model_dir = Path(tmp)
            for name in contract.MODEL_FILES[:7]: (model_dir/name).write_bytes(self.client.objects[a['model_prefix']+'/'+name])
            model,_ = baseline.load_trusted_model(model_dir,allow_retrospective_demo=True)
            data = self.fixture.load()
            np.testing.assert_allclose(model.named_steps['scaler'].mean_, data['splits']['train']['x'].mean())
            self.assertEqual(metadata['constant_training_home_win_rate'],float(data['splits']['train']['y'].mean()))
            self.assertEqual(metadata['training_seasons'],[2022,2023,2024])
            self.assertEqual(metadata['holdout_seasons'],[2025])
            self.fixture.change_rows('holdout.csv',lambda rows:[row.update(home_win=str(1-int(row['home_win']))) for row in rows])
            other_client=ModelS3()
            other=cloud.ModelingStore(other_client,'course-project-bucket','project')
            other.upload_dataset(self.fixture.data,allow_retrospective_demo=True)
            prepared=json.loads(self.client.objects[self.prep_key])
            prepared['dataset_artifact_sha256']={n:digest((self.fixture.data/n).read_bytes()) for n in baseline.DATA_FILES|{'dataset_report.json'}}
            other_client.objects[self.prep_key]=encode(prepared)
            other_request=self.request|{'preparation_receipt_sha256':digest(encode(prepared))}
            second=cloud.train_run(other_request,other)
            self.assertEqual(second['state'],'completed',second)
            second_dir=self.root/'second-reloaded'
            second_dir.mkdir()
            for name in contract.MODEL_FILES[:7]: (second_dir/name).write_bytes(other_client.objects[second['model_prefix']+'/'+name])
            changed,_=baseline.load_trusted_model(second_dir,allow_retrospective_demo=True)
            np.testing.assert_array_equal(model.named_steps['scaler'].mean_,changed.named_steps['scaler'].mean_)
            np.testing.assert_array_equal(model.named_steps['logistic'].coef_,changed.named_steps['logistic'].coef_)
            np.testing.assert_array_equal(baseline.home_probabilities(model,data['splits']['holdout']['x']),
                                          baseline.home_probabilities(changed,data['splits']['holdout']['x']))
            self.assertNotEqual(a['evaluation']['model'],second['evaluation']['model'])

    def test_versions_and_origin_claim_tampering_fail_before_deserialization(self):
        result = self.train()
        request = self.reference(result,'hypothetical')
        with patch.object(baseline,'versions',return_value=baseline.versions()|{'numpy':'unreviewed'}), \
             patch.object(baseline.joblib,'load') as load:
            self.assertEqual(cloud.infer_run(request,self.store)['state'],'failed')
            load.assert_not_called()
        key = f"project/cloud-modeling/training/{result['training_token_sha256']}/claim.json"
        self.client.objects[key] = b'forged origin'
        with patch.object(baseline.joblib,'load') as load:
            self.assertEqual(cloud.infer_run(request,self.store)['state'],'failed')
            load.assert_not_called()

    def test_batch_replay_and_partial_or_conflicting_outputs_are_safe(self):
        trained=self.train()
        request=self.reference(trained)
        self.client.break_after_put='predictions.csv'
        self.assertEqual(cloud.infer_run(request,self.store)['state'],'failed')
        partial={k:v for k,v in self.client.objects.items() if '/inference/' in k}
        completed=cloud.infer_run(request,self.store)
        self.assertEqual(completed['state'],'completed',completed)
        self.assertEqual(partial,{k:v for k,v in self.client.objects.items() if k in partial})
        before=dict(self.client.objects)
        self.client.calls.clear()
        self.assertEqual(completed,cloud.infer_run(request,self.store))
        self.assertEqual(before,self.client.objects)
        self.assertFalse(any(c[0]=='put' for c in self.client.calls))
        key=completed['inference_prefix']+'/predictions.csv'
        self.client.objects[key]=b'conflicting prediction evidence'
        conflict=dict(self.client.objects)
        self.assertEqual(cloud.infer_run(request,self.store)['state'],'failed')
        self.assertEqual(conflict,self.client.objects)

    def test_same_training_token_cannot_change_verified_request(self):
        self.train()
        alternate='b'*64
        prepared=json.loads(self.client.objects[self.prep_key])
        prepared['selection_id']=alternate
        self.client.objects[f'project/cloud-preparation/runs/{alternate}/complete.json']=encode(prepared)
        request=self.request|{'preparation_selection_id':alternate,'preparation_receipt_sha256':digest(encode(prepared))}
        self.store.approved_reference=None
        before=dict(self.client.objects)
        with patch.object(baseline,'train_baseline',side_effect=AssertionError('No changed-request fit')):
            result=self.train(request)
        self.assertEqual(result['stage'],'training_claim',result)
        self.assertIn('conflicts',result['message'])
        self.assertEqual(before,self.client.objects)

    def test_handler_refuses_bad_configuration_or_vector_before_client_creation(self):
        with patch.object(cloud.boto3,'client') as client:
            self.assertEqual(cloud.training_handler({},None)['state'],'failed')
            client.assert_not_called()
            fields={'FBS_S3_BUCKET':'course-project-bucket','FBS_S3_PREFIX':'project',
                    'APPROVED_DATASET_ID':self.request['dataset_id'],'APPROVED_PREPARATION_ID':self.selection,
                    'APPROVED_PREPARATION_SHA256':self.request['preparation_receipt_sha256']}
            with patch.dict(cloud.os.environ,fields):
                invalid=self.request|{'dataset_id':'f'*64}
                self.assertEqual(cloud.training_handler(invalid,None)['state'],'failed')
                client.assert_not_called()

    def test_completed_receipt_cannot_report_altered_metrics_or_counts(self):
        result=self.train()
        key=f"project/cloud-modeling/training/{result['training_token_sha256']}/complete.json"
        original=self.client.objects[key]
        for change in (lambda r:r['counts'].update(train=999),
                       lambda r:r['evaluation']['model'].update(accuracy=r['evaluation']['model']['accuracy']+0.01)):
            receipt=json.loads(original)
            change(receipt)
            self.client.objects[key]=encode(receipt)
            with patch.object(baseline,'train_baseline',side_effect=AssertionError('No refit')):
                self.assertEqual(self.train()['state'],'failed')
            request=self.reference(result,'hypothetical')
            with patch.object(baseline.joblib,'load') as load:
                self.assertEqual(cloud.infer_run(request,self.store)['state'],'failed')
                load.assert_not_called()
