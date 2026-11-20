"""Offline cloud-capture contract, realistic atomic races and interruption tests."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ReadTimeoutError
from botocore.stub import Stubber
import boto3

from src.ingestion import cfbd
from src.ingestion.s3_storage import S3Store
from src.pipeline import cloud_ingestion as cloud
from src.pipeline.run_contract import STATUS, encode, validate
from tests.test_s3_storage import MemoryS3, error
from tests.test_dataset import game


class AtomicS3(MemoryS3):
    """Serialize individual operations, not whole runs: IfNoneMatch races are real."""
    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()
        self.break_after_put = None
        self.corrupt_reads = None
        self.conflict_once = False
        self.stopped_once = False

    def put_object(self, **kwargs):
        with self.lock:
            if self.conflict_once:
                self.conflict_once = False
                raise error('ConditionalRequestConflict', 409)
            result = super().put_object(**kwargs)
            if self.break_after_put and kwargs['Key'].endswith(self.break_after_put) and not self.stopped_once:
                self.stopped_once = True
                raise ReadTimeoutError(endpoint_url='secret-url')
            return result

    def list_objects_v2(self, **kwargs):
        # Emulate the exact IAM prefix and max-keys conditions used by the role.
        with self.lock:
            self.calls.append(('list', kwargs))
            prefix=kwargs['Prefix']
            if (not prefix.startswith(('project/raw/cfbd/games/', 'project/cloud-ingestion/runs/'))
                    or kwargs['MaxKeys'] != 1):
                raise error('AccessDenied',403)
            keys=sorted(k for k in self.objects if k.startswith(prefix))[:1]
            return {'Contents':[{'Key':key} for key in keys], 'IsTruncated':False}

    def get_object(self, **kwargs):
        with self.lock:
            if self.corrupt_reads and kwargs['Key'].endswith(self.corrupt_reads):
                self.calls.append(('get', kwargs))
                return {'Body': io.BytesIO(b'corrupt'), 'ContentLength': 7}
            return super().get_object(**kwargs)


class CloudIngestionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No network')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS')))
        self.client = AtomicS3()
        self.store = cloud.CloudS3Store(self.client, 'course-project-bucket', 'project')
        self.event = {'schema_version': 1, 'season': 2026, 'week': 5, 'idempotency_token': 'take-0001'}
        self.raw = json.dumps([game(2026, week=5)]).encode()
        self.response = cfbd.GamesResponse(self.raw, {'year': 2026, 'week': 5, 'seasonType': 'regular', 'classification': 'fbs'}, '2026-11-20T15:00:00Z', 200)
        self.fetch = Mock(return_value=self.response)
        self.secret = Mock(return_value='synthetic-secret-value')

    def run_capture(self, event=None, **kwargs):
        return cloud.capture_run(self.event if event is None else event, self.store, self.secret,
                                 fetch=kwargs.pop('fetch', self.fetch), **kwargs)

    def key(self, name):
        return f'project/cloud-ingestion/runs/{validate(self.event)[1]}/{name}.json'

    def test_request_validation_before_external_calls(self):
        for event in [{}, self.event | {'api_key': 'private'}, self.event | {'season': True},
                      self.event | {'week': -1}, self.event | {'week': None},
                      self.event | {'idempotency_token': '../bad-token'}, self.event | {'schema_version': True}]:
            with self.subTest(event=event):
                result = self.run_capture(event)
                self.assertEqual(result['state'], 'failed')
                self.assertEqual(self.client.calls, [])
                self.secret.assert_not_called(); self.fetch.assert_not_called()
        for key in ['week']:
            request, _, _ = validate({k:v for k,v in self.event.items() if k != key})
            self.assertIsNone(request['week'])
        self.assertEqual(validate(self.event | {'week': 0})[0]['week'], 0)

    def test_success_raw_bytes_hashes_flags_and_completion_last(self):
        result = self.run_capture()
        self.assertEqual(result['state'], 'completed')
        self.fetch.assert_called_once_with(2026, 5, api_key='synthetic-secret-value', max_attempts=1)
        self.assertEqual(self.client.objects[result['raw_key']], self.raw)
        manifest = json.loads(self.client.objects[result['manifest_key']])
        self.assertEqual(result['raw_sha256'], manifest['sha256'])
        self.assertEqual(manifest['source_availability']['status'], 'unknown')
        self.assertIsNone(manifest['source_availability']['available_at'])
        self.assertFalse(manifest['approved_for_predictor_use'])
        self.assertEqual(result['retrieved_at'], self.response.retrieved_at)
        self.assertIn('started_at', result); self.assertIn('completed_at', result)
        for k,v in STATUS.items(): self.assertEqual(result[k],v)
        puts = [v['Key'] for k,v in self.client.calls if k=='put']
        self.assertEqual(puts[-1], self.key('complete'))
        self.assertLess(puts.index(self.key('capture')), puts.index(result['raw_key']))
        self.assertNotIn('synthetic-secret-value', json.dumps(result))
        self.assertTrue(all(b'synthetic-secret-value' not in v for v in self.client.objects.values()))

    def test_completed_replay_returns_verified_receipt_without_secret_or_fetch(self):
        first = self.run_capture()
        self.fetch.reset_mock(); self.secret.reset_mock()
        second = self.run_capture()
        self.assertEqual(first,second)
        self.fetch.assert_not_called(); self.secret.assert_not_called()
        self.client.objects[first['raw_key']] = b'tampered'
        self.assertEqual(self.run_capture()['state'], 'failed')
        self.fetch.assert_not_called()

    def test_fetch_log_is_safe_and_replay_does_not_emit_second_fetch(self):
        with self.assertLogs(cloud.LOGGER,level='INFO') as logs:
            first=self.run_capture()
            self.assertEqual(self.run_capture(),first)
        self.assertEqual(len(logs.output),1)
        self.assertIn('cfbd_fetch_start',logs.output[0])
        self.assertNotIn('synthetic-secret-value',logs.output[0])
        self.assertNotIn(self.raw.decode(),logs.output[0])

    def test_conflicting_token_request_refused(self):
        self.run_capture()
        result=self.run_capture(self.event | {'week':6})
        self.assertEqual(result['state'],'failed'); self.assertEqual(result['stage'],'claim')
        self.assertEqual(self.fetch.call_count,1)

    def test_concurrent_claims_only_one_fetch(self):
        started, release=threading.Event(),threading.Event()
        def fetch(*args,**kwargs):
            started.set(); self.assertTrue(release.wait(5)); return self.response
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(self.run_capture,fetch=fetch)
            self.assertTrue(started.wait(5))
            b=pool.submit(self.run_capture)
            loser=b.result(timeout=5)
            self.assertEqual(loser['state'],'in_progress')
            self.fetch.assert_not_called();release.set()
            self.assertEqual(a.result(timeout=5)['state'],'completed')
        self.assertEqual(self.secret.call_count,1)

    def test_partial_publication_resumes_exact_capture_no_refetch(self):
        # The raw PUT commits server-side, then its response is lost.
        self.client.break_after_put='.json'
        # Arm only for final raw publication, not the claim/checkpoint.
        original = self.store.upload_raw
        def upload(path):
            self.client.break_after_put=Path(path).name.replace('.manifest.json','.json')
            return original(path)
        self.client.break_after_put=None
        with patch.object(self.store,'upload_raw',side_effect=upload):
            self.assertEqual(self.run_capture()['state'],'failed')
        self.assertNotIn(self.key('complete'),self.client.objects)
        capture=self.client.objects[self.key('capture')]
        self.assertEqual(self.run_capture()['state'],'completed')
        self.assertEqual(self.client.objects[self.key('capture')],capture)
        self.assertEqual(self.fetch.call_count,1)

    def test_ambiguous_claim_never_refetches(self):
        self.client.break_after_put='claim.json'
        self.assertEqual(self.run_capture()['state'],'failed')
        result=self.run_capture()
        self.assertEqual(result['state'],'in_progress')
        self.secret.assert_not_called();self.fetch.assert_not_called()

    def test_expired_claim_is_interrupted_without_lease_takeover(self):
        self.client.break_after_put='claim.json'
        self.run_capture(clock=lambda:'2026-11-20T00:00:00Z')
        self.assertEqual(self.run_capture(clock=lambda:'2026-11-20T00:04:00Z')['state'],'interrupted')
        self.fetch.assert_not_called();self.secret.assert_not_called()

    def test_capture_put_response_loss_recovers_original(self):
        self.client.break_after_put='capture.json'
        self.assertEqual(self.run_capture()['state'],'failed')
        self.assertEqual(self.run_capture()['state'],'completed')
        self.assertEqual(self.fetch.call_count,1)

    def test_concurrent_recovery_yields_same_completion(self):
        self.client.break_after_put='capture.json'
        self.run_capture()
        barrier=threading.Barrier(2)
        original=self.store.upload_raw
        def upload(path):
            barrier.wait(timeout=5); return original(path)
        with patch.object(self.store,'upload_raw',side_effect=upload):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:self.run_capture(),range(2)))
        self.assertEqual(results[0]['state'],'completed')
        self.assertEqual(results[0],results[1]); self.assertEqual(self.fetch.call_count,1)

    def test_failed_verification_no_completion(self):
        with patch.object(self.store,'upload_raw',return_value={}):
            result=self.run_capture()
        self.assertEqual(result['stage'],'verify_publication')
        self.assertNotIn(self.key('complete'),self.client.objects)
        self.assertEqual(self.run_capture()['state'],'completed')
        self.assertEqual(self.fetch.call_count,1)

    def test_secret_and_auth_failures_are_safe_no_refetch(self):
        for stage in ['secret_retrieval','cfbd_fetch']:
            self.setUp_fresh_token(stage)
            if stage=='secret_retrieval':self.secret.side_effect=RuntimeError('Bearer PRIVATEKEY https://private')
            else:self.fetch.side_effect=cfbd.CFBDError('PRIVATEKEY')
            out=io.StringIO()
            with redirect_stdout(out),redirect_stderr(out): result=self.run_capture()
            self.assertEqual(result['stage'],stage)
            self.assertNotIn('PRIVATEKEY',json.dumps(result)+out.getvalue())
            count=self.fetch.call_count
            self.assertEqual(self.run_capture()['state'],'failed')
            self.assertEqual(self.fetch.call_count,count)
            self.assertNotIn(self.key('complete'),self.client.objects)

    def setUp_fresh_token(self, suffix):
        self.event['idempotency_token']='test-'+suffix.replace('_','-')
        self.fetch=Mock(return_value=self.response); self.secret=Mock(return_value='synthetic-key')

    def test_missing_secret_never_falls_back_to_local_key(self):
        self.secret.return_value=None
        with patch('src.ingestion.cfbd._api_key',side_effect=AssertionError('No local lookup')):
            result=self.run_capture()
        self.assertEqual(result['stage'],'secret_retrieval');self.fetch.assert_not_called()

    def test_structured_secret_rejected_before_http(self):
        self.secret.return_value='{"api_key":"synthetic-key"}'
        result=self.run_capture()
        self.assertEqual(result['stage'],'secret_retrieval');self.fetch.assert_not_called()

    def test_completion_response_loss_returns_same_receipt_on_replay(self):
        self.client.break_after_put='complete.json'
        self.assertEqual(self.run_capture()['state'],'failed')
        completed=self.client.objects[self.key('complete')]
        self.assertEqual(self.run_capture(),json.loads(completed))
        self.assertEqual(self.fetch.call_count,1)

    def test_conditional_409_does_not_claim_or_fetch(self):
        self.client.conflict_once=True
        self.assertEqual(self.run_capture()['state'],'failed')
        self.fetch.assert_not_called();self.secret.assert_not_called()

    def test_corrupt_capture_and_manifest_conflict_never_complete(self):
        self.client.break_after_put='capture.json';self.run_capture()
        original=self.client.objects[self.key('capture')]
        self.client.objects[self.key('capture')]=b'corrupt'
        self.assertEqual(self.run_capture()['state'],'failed')
        self.client.objects[self.key('capture')]=original
        capture=json.loads(original); manifest=json.loads(__import__('base64').b64decode(capture['manifest']))
        key=f"project/raw/cfbd/games/season=2026/{manifest['snapshot_id']}.manifest.json"
        self.client.objects[key]=b'conflict'
        self.assertEqual(self.run_capture()['state'],'failed')
        self.assertNotIn(self.key('complete'),self.client.objects)
        self.assertEqual(self.fetch.call_count,1)

    def test_private_bucket_failure_before_secret_fetch_or_claim(self):
        self.client.flags['BlockPublicAcls']=False
        self.assertEqual(self.run_capture()['stage'],'aws_preflight')
        self.secret.assert_not_called();self.fetch.assert_not_called()
        self.assertFalse(self.client.objects)

    def test_handler_uses_execution_role_secret_and_real_fetch_function(self):
        import os
        config={'FBS_S3_BUCKET':'course-project-bucket','FBS_S3_PREFIX':'project',
                'CFBD_SECRET_ARN':'arn:aws:secretsmanager:us-east-1:000000000000:secret:synthetic-cfbd-abcdef'}
        secrets=Mock();secrets.get_secret_value.return_value={'SecretString':'synthetic-key'}
        def factory(service, **kwargs):
            return self.client if service=='s3' else secrets
        response=Mock(status_code=200,content=self.raw)
        with patch.dict(os.environ,config),patch.object(cloud.boto3,'client',side_effect=factory),patch.object(cfbd.requests,'get',return_value=response) as http,patch.object(cfbd,'_api_key',side_effect=AssertionError('No local key lookup')):
            result=cloud.handler(self.event,None)
        self.assertEqual(result['state'],'completed');http.assert_called_once()
        secrets.get_secret_value.assert_called_once_with(SecretId=config['CFBD_SECRET_ARN'])

    def test_both_atomic_claim_puts_race(self):
        barrier=threading.Barrier(2)
        original=self.client.put_object
        def put(**kwargs):
            if kwargs['Key'].endswith('/claim.json'):barrier.wait(timeout=5)
            return original(**kwargs)
        with patch.object(self.client,'put_object',side_effect=put):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:self.run_capture(),range(2)))
        self.assertEqual(self.fetch.call_count,1)
        self.assertTrue(any(r['state']=='completed' for r in results))
        self.assertEqual(len([k for k in self.client.objects if k.endswith('/complete.json')]),1)

    def test_handler_rejects_event_before_client_creation(self):
        with patch.object(cloud.boto3,'client') as factory:
            self.assertEqual(cloud.handler(self.event | {'key':'secret'},None)['state'],'failed')
            factory.assert_not_called()

    def test_explicit_key_one_http_attempt_and_cli_key_lookup_unchanged(self):
        response=Mock(status_code=200,content=self.raw)
        with patch.object(cfbd,'_api_key',side_effect=AssertionError('Must not read .env')),patch.object(cfbd.requests,'get',return_value=response) as get:
            result=cfbd.fetch_games(2026,5,api_key='synthetic-key',max_attempts=1)
        self.assertEqual(result.raw_response,self.raw);get.assert_called_once()
        with patch.object(cfbd.requests,'get',return_value=Mock(status_code=503)) as get:
            with self.assertRaises(cfbd.CFBDError):cfbd.fetch_games(2026,5,api_key='synthetic-key',max_attempts=1)
            get.assert_called_once()

    def test_lightweight_handler_import_does_not_import_training(self):
        script="import sys; import src.pipeline.cloud_ingestion; assert not any(x in sys.modules for x in ('numpy','pandas','sklearn','src.models.baseline','src.features.dataset'))"
        subprocess.run([sys.executable,'-B','-c',script],check=True,capture_output=True)

    def test_optional_absence_uses_authorized_list_not_get_error(self):
        key=self.key('capture')
        self.assertIsNone(self.store._get(key,optional=True))
        self.assertFalse(any(op=='get' for op,_ in self.client.calls))
        # A different key sharing the prefix does not masquerade as the exact key.
        self.client.objects[key+'.backup']=b'other'
        self.assertIsNone(self.store._get(key,optional=True))
        self.client.objects[key]=b'exact'
        self.assertEqual(self.store._get(key,optional=True),b'exact')

    def test_list_and_get_denials_never_mean_absent(self):
        key=self.key('capture')
        with patch.object(self.client,'list_objects_v2',side_effect=error('AccessDenied',403)):
            with self.assertRaises(Exception):self.store._get(key,optional=True)
            self.assertEqual(self.run_capture()['state'],'failed')
        self.fetch.assert_not_called()
        self.client.objects[key]=b'present'
        with patch.object(self.client,'get_object',side_effect=error('AccessDenied',403)):
            with self.assertRaises(Exception):self.store._get(key,optional=True)
        with self.assertRaises(Exception):self.store._get('unrelated/key',optional=True)

    def test_optional_probe_real_sdk_prefix_and_denied_get(self):
        client=boto3.client('s3',region_name='us-east-1',aws_access_key_id='synthetic',aws_secret_access_key='synthetic')
        store=cloud.CloudS3Store(client,'course-project-bucket','project')
        key=self.key('capture')
        with Stubber(client) as stub:
            stub.add_response('list_objects_v2',{'Contents':[]},
                              {'Bucket':store.bucket,'Prefix':key,'MaxKeys':1})
            self.assertIsNone(store._get(key,optional=True))
            stub.add_response('list_objects_v2',{'Contents':[{'Key':key}]},
                              {'Bucket':store.bucket,'Prefix':key,'MaxKeys':1})
            stub.add_client_error('get_object',service_error_code='AccessDenied',http_status_code=403,
                                  expected_params={'Bucket':store.bucket,'Key':key})
            with self.assertRaises(Exception):store._get(key,optional=True)

    def test_conditional_put_uses_real_sdk_shape(self):
        client=boto3.client('s3',region_name='us-east-1',aws_access_key_id='synthetic',aws_secret_access_key='synthetic')
        store=S3Store(client,'course-project-bucket','project')
        with Stubber(client) as stub:
            stub.add_client_error('put_object',service_error_code='PreconditionFailed',http_status_code=412,
                                  expected_params={'Bucket':store.bucket,'Key':'claim.json','Body':b'{}','IfNoneMatch':'*',
                                                   'ChecksumSHA256':__import__('base64').b64encode(__import__('hashlib').sha256(b'{}').digest()).decode(),'ContentType':'application/json'})
            self.assertFalse(cloud.create_once(store,'claim.json',b'{}'))
