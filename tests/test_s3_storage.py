"""Offline S3 transfer tests using synthetic fixtures and mocked AWS clients."""

import base64
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError, ReadTimeoutError
from botocore.response import StreamingBody
from botocore.stub import Stubber

from src.features import dataset, games
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.ingestion import s3_storage as s3
from src.models.baseline import load_dataset
from tests.test_dataset import game


def error(code, status=400):
    return ClientError({'Error': {'Code': code, 'Message': 'SECRET service details'},
                        'ResponseMetadata': {'HTTPStatusCode': status}}, 'MockOperation')


class MemoryS3:
    """Deterministic fake with real conditional-write semantics, no network."""
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.flags = dict.fromkeys(s3.PUBLIC_BLOCK_FLAGS, True)
        self.fail_put = None
        self.fail_get = None
        self.race_content = None
        self.race_key = None

    def get_public_access_block(self, **kwargs):
        self.calls.append(('privacy', kwargs))
        return {'PublicAccessBlockConfiguration': self.flags}

    def get_object(self, **kwargs):
        self.calls.append(('get', kwargs))
        key = kwargs['Key']
        if key == self.fail_get:
            raise ReadTimeoutError(endpoint_url='SECRET')
        if key not in self.objects:
            raise error('NoSuchKey', 404)
        content = self.objects[key]
        return {'Body': io.BytesIO(content), 'ContentLength': len(content), 'ETag': 'not-a-sha256'}

    def put_object(self, **kwargs):
        self.calls.append(('put', kwargs))
        key, content = kwargs['Key'], kwargs['Body']
        assert kwargs['IfNoneMatch'] == '*'
        assert kwargs['ChecksumSHA256'] == base64.b64encode(hashlib.sha256(content).digest()).decode()
        assert 'ACL' not in kwargs and 'ServerSideEncryption' not in kwargs
        if key == self.fail_put:
            raise error('AccessDenied', 403)
        if key == self.race_key:
            self.objects[key] = content if self.race_content is None else self.race_content
        if key in self.objects:
            raise error('PreconditionFailed', 412)
        self.objects[key] = content
        return {'ETag': 'not-a-sha256'}


class S3StorageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS network')))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No CFBD network')))
        manifests = []
        self.normalized = self.root / 'normalized'
        for year in dataset.SEASONS:
            params = {'year': year, 'seasonType': 'regular', 'classification': 'fbs'}
            if year == 2026:
                params['week'] = 4
            response = GamesResponse(json.dumps([game(year), game(year, 2)]).encode(), params,
                                     '2026-09-23T04:00:00Z', 200)
            path = save_snapshot(response, self.root / 'raw')[1]
            games.normalize_snapshot(path, self.normalized)
            manifests.append(path)
        self.manifest = manifests[4]
        self.data = self.root / 'features'
        report = dataset.build_dataset(manifests, self.data, normalized_root=self.normalized, allow_retrospective_demo=True)
        self.identifier = report['dataset_id']
        self.client = MemoryS3()
        self.store = s3.S3Store(self.client, 'course-project-bucket', 'fbs-demo')
        self.base = f'fbs-demo/datasets/{self.identifier}'

    def upload(self):
        return self.store.upload_dataset(self.data, allow_retrospective_demo=True)

    def download(self, target=None):
        return self.store.download_dataset(self.identifier, target or self.root / 'download', allow_retrospective_demo=True)

    def test_raw_pair_verified_exact_keys_and_manifest_last(self):
        manifest = json.loads(self.manifest.read_bytes())
        sid = manifest['snapshot_id']
        base = 'fbs-demo/raw/cfbd/games/season=2025'
        result = self.store.upload_raw(self.manifest)
        self.assertEqual(list(result), [f's3://course-project-bucket/{base}/{sid}.json',
                                       f's3://course-project-bucket/{base}/{sid}.manifest.json'])
        self.assertEqual(len(self.client.objects), 2)
        self.assertEqual(self.client.objects[f'{base}/{sid}.manifest.json'], self.manifest.read_bytes())
        puts = [params['Key'] for op, params in self.client.calls if op == 'put']
        self.assertTrue(puts[-1].endswith('.manifest.json'))
        # Every data object was read back before the marker's conditional write.
        marker_index = next(i for i, (op, params) in enumerate(self.client.calls)
                            if op == 'put' and params['Key'].endswith('.manifest.json'))
        self.assertIn(('get', {'Bucket': self.store.bucket, 'Key': puts[0]}), self.client.calls[marker_index-1:marker_index])

    def test_dataset_exact_six_keys_and_report_last(self):
        (self.data / 'unrelated.txt').write_text('must not upload')
        result = self.upload()
        expected = set(s3.DATA_FILES) | {'dataset_report.json'}
        self.assertEqual(set(self.client.objects), {f'{self.base}/{name}' for name in expected})
        puts = [params for op, params in self.client.calls if op == 'put']
        self.assertEqual(len(puts), 6)
        self.assertEqual(puts[-1]['Key'], f'{self.base}/dataset_report.json')
        self.assertTrue(all(value == 'uploaded' for value in result.values()))
        for name in expected:
            self.assertEqual(self.client.objects[f'{self.base}/{name}'], (self.data / name).read_bytes())

    def test_invalid_local_raw_or_dataset_fails_before_any_aws_call(self):
        raw = self.manifest.with_name(self.manifest.name.replace('.manifest.json', '.json'))
        raw.write_bytes(b'[]')
        with self.assertRaisesRegex(s3.S3StorageError, 'Local raw'):
            self.store.upload_raw(self.manifest)
        (self.data / 'train.csv').write_bytes(b'corrupt')
        with self.assertRaisesRegex(s3.S3StorageError, 'Local dataset'):
            self.upload()
        self.assertEqual(self.client.calls, [])

    def test_demo_permission_required_for_dataset_transfers(self):
        with self.assertRaises(s3.S3StorageError):
            self.store.upload_dataset(self.data)
        with self.assertRaises(s3.S3StorageError):
            self.store.download_dataset(self.identifier, self.root / 'missing')
        self.assertEqual(self.client.calls, [])

    def test_identical_remote_rerun_does_not_write(self):
        self.upload()
        original = dict(self.client.objects)
        self.client.calls.clear()
        result = self.upload()
        self.assertTrue(all(status == 'reused' for status in result.values()))
        self.assertFalse(any(op == 'put' for op, _ in self.client.calls))
        self.assertEqual(self.client.objects, original)

    def test_conflicting_remote_data_or_marker_preserved_before_writes(self):
        for name in ('train.csv', 'dataset_report.json'):
            with self.subTest(name=name):
                self.client.objects = {f'{self.base}/{name}': b'keep-existing'}
                self.client.calls.clear()
                with self.assertRaisesRegex(s3.S3StorageError, 'Conflicting remote'):
                    self.upload()
                self.assertFalse(any(op == 'put' for op, _ in self.client.calls))
                self.assertEqual(self.client.objects, {f'{self.base}/{name}': b'keep-existing'})

    def test_concurrent_conditional_write_only_reuses_identical_bytes(self):
        self.client.race_key = f'{self.base}/train.csv'
        self.upload()
        self.assertEqual(self.client.objects[self.client.race_key], (self.data / 'train.csv').read_bytes())
        self.client.objects.clear()
        self.client.race_content = b'conflicting'
        with self.assertRaisesRegex(s3.S3StorageError, 'Conflicting remote'):
            self.upload()
        self.assertNotIn(f'{self.base}/dataset_report.json', self.client.objects)
        self.assertEqual(self.client.objects[self.client.race_key], b'conflicting')

    def test_partial_upload_has_no_marker_and_can_resume(self):
        self.client.fail_put = f'{self.base}/train.csv'
        with self.assertRaisesRegex(s3.S3StorageError, 'access denied'):
            self.upload()
        self.assertGreater(len(self.client.objects), 0)
        self.assertNotIn(f'{self.base}/dataset_report.json', self.client.objects)
        before = dict(self.client.objects)
        self.client.fail_put = None
        self.upload()
        self.assertEqual(len(self.client.objects), 6)
        self.assertTrue(all(self.client.objects[key] == content for key, content in before.items()))

    def test_missing_data_behind_existing_marker_not_silently_repaired(self):
        self.client.objects[f'{self.base}/dataset_report.json'] = (self.data / 'dataset_report.json').read_bytes()
        with self.assertRaisesRegex(s3.S3StorageError, 'missing objects'):
            self.upload()
        self.assertFalse(any(op == 'put' for op, _ in self.client.calls))

    def test_download_byte_identity_hashes_and_existing_loader(self):
        self.upload()
        result = self.download()
        target = self.root / 'download'
        self.assertEqual(result['verified_files'], 6)
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()},
                         {p.name: p.read_bytes() for p in self.data.iterdir()})
        self.assertEqual(load_dataset(target, allow_retrospective_demo=True)['report']['dataset_id'], self.identifier)
        self.assertFalse(result['approved_for_point_in_time_forecasting'])
        self.assertFalse(result['historical_availability_verified'])

    def test_download_missing_marker_or_partial_network_failure_publishes_nothing(self):
        with self.assertRaisesRegex(s3.S3StorageError, 'missing'):
            self.download()
        self.assertFalse((self.root / 'download').exists())
        self.upload()
        self.client.fail_get = f'{self.base}/train.csv'
        with self.assertRaisesRegex(s3.S3StorageError, 'connection or read'):
            self.download()
        self.assertFalse((self.root / 'download').exists())

    def test_download_actual_bytes_tampering_rejected_not_etag(self):
        self.upload()
        self.client.objects[f'{self.base}/train.csv'] += b'bad'
        with self.assertRaisesRegex(s3.S3StorageError, 'SHA-256 mismatch'):
            self.download()
        self.assertFalse((self.root / 'download').exists())

    def test_unsafe_remote_paths_rejected_before_artifact_gets_or_local_writes(self):
        for unsafe in ('../escape', '/tmp/escape', 'subdir/train.csv', r'..\escape'):
            report = json.loads((self.data / 'dataset_report.json').read_bytes())
            report['artifact_sha256'][unsafe] = report['artifact_sha256'].pop('train.csv')
            self.client.objects = {f'{self.base}/dataset_report.json': json.dumps(report).encode()}
            self.client.calls.clear()
            with self.subTest(path=unsafe), self.assertRaisesRegex(s3.S3StorageError, 'unsafe/invalid'):
                self.download()
            self.assertEqual(sum(op == 'get' for op, _ in self.client.calls), 1)
            self.assertFalse((self.root / 'download').exists())
        with self.assertRaisesRegex(s3.S3StorageError, 'not a path'):
            self.store.download_dataset('../bad', self.root / 'download', allow_retrospective_demo=True)

    def test_remote_semantic_validation_after_valid_hashes(self):
        self.upload()
        report = json.loads(self.client.objects[f'{self.base}/dataset_report.json'])
        report['splits']['train']['output'] += 1
        self.client.objects[f'{self.base}/dataset_report.json'] = json.dumps(report).encode()
        with self.assertRaisesRegex(s3.S3StorageError, 'validation'):
            self.download()
        self.assertFalse((self.root / 'download').exists())

    def test_existing_local_outputs_and_symlinks_preserved(self):
        self.upload()
        self.download()
        target = self.root / 'download'
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
        self.download()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()})
        (target / 'train.csv').write_bytes(b'keep-local')
        with self.assertRaisesRegex(s3.S3StorageError, 'existing files preserved'):
            self.download()
        self.assertEqual((target / 'train.csv').read_bytes(), b'keep-local')
        link = self.root / 'link'
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(s3.S3StorageError):
            self.download(link)

    def test_failed_local_publish_has_no_completion_marker_and_resumes(self):
        self.upload()
        original = dataset._atomic_create
        def fail(path, content):
            if path.name == 'train.csv':
                raise OSError('SECRET disk error')
            return original(path, content)
        with patch.object(dataset, '_atomic_create', side_effect=fail):
            with self.assertRaises(s3.S3StorageError):
                self.download()
        self.assertFalse((self.root / 'download/dataset_report.json').exists())
        self.download()
        self.assertEqual(len(list((self.root / 'download').iterdir())), 6)

    def test_private_bucket_check_never_alters_security(self):
        self.client.flags['BlockPublicPolicy'] = False
        with self.assertRaisesRegex(s3.S3StorageError, 'Block Public Access'):
            self.upload()
        self.assertEqual([op for op, _ in self.client.calls], ['privacy'])
        self.client.get_public_access_block = Mock(side_effect=error('NoSuchPublicAccessBlockConfiguration', 404))
        with self.assertRaisesRegex(s3.S3StorageError, 'absent'):
            self.upload()

    def test_sanitized_missing_expired_access_and_concurrent_errors(self):
        cases = [(NoCredentialsError(), 'missing'), (PartialCredentialsError(provider='SECRET', cred_var='SECRET'), 'missing'),
                 (error('ExpiredToken'), 'expired'), (error('AccessDenied', 403), 'access denied'),
                 (error('ConditionalRequestConflict', 409), 'Concurrent'), (error('Unexpected'), 'Details suppressed')]
        for exc, expected in cases:
            with self.subTest(error=type(exc).__name__):
                message = str(s3._aws_error(exc))
                self.assertIn(expected, message)
                self.assertNotIn('SECRET', message)
                self.client.get_public_access_block = Mock(side_effect=exc)
                with self.assertRaises(s3.S3StorageError) as caught:
                    self.upload()
                self.assertNotIn('SECRET', str(caught.exception))

    def test_sdk_client_profile_region_retries_and_temporary_credential_chain(self):
        session = Mock(region_name='us-east-1')
        with patch.object(s3.boto3, 'Session', return_value=session) as factory:
            s3.make_client('us-east-1', 'course')
        factory.assert_called_once_with(profile_name='course', region_name='us-east-1')
        _, kwargs = session.client.call_args
        self.assertEqual(kwargs['config'].retries, {'mode': 'standard', 'total_max_attempts': 3})
        self.assertEqual(kwargs['config'].connect_timeout, 5)
        self.assertEqual(kwargs['config'].read_timeout, 30)
        with patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'synthetic-key', 'AWS_SECRET_ACCESS_KEY': 'synthetic-secret',
                                      'AWS_SESSION_TOKEN': 'synthetic-token', 'AWS_DEFAULT_REGION': 'us-east-1'}, clear=True):
            client = s3.make_client()
            self.assertEqual(client._request_signer._credentials.token, 'synthetic-token')
            client.close()

    def test_installed_sdk_supports_conditional_put_with_stubber(self):
        client = boto3.client('s3', region_name='us-east-1', aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
        store = s3.S3Store(client, 'course-project-bucket', 'fbs-demo')
        content = b'[]'
        expected = {'Bucket': store.bucket, 'Key': 'fbs-demo/test.json', 'Body': content, 'IfNoneMatch': '*',
                    'ChecksumSHA256': base64.b64encode(hashlib.sha256(content).digest()).decode(),
                    'ContentType': 'application/json'}
        with Stubber(client) as stub:
            stub.add_response('put_object', {}, expected)
            stub.add_response('get_object', {'Body': StreamingBody(io.BytesIO(content), len(content)), 'ContentLength': 2},
                              {'Bucket': store.bucket, 'Key': 'fbs-demo/test.json'})
            self.assertEqual(store._put('fbs-demo/test.json', content), 'uploaded')
            stub.assert_no_pending_responses()
        client.close()

    def test_configuration_precedence_and_missing_bucket_fail_without_client(self):
        with patch.object(s3, 'dotenv_values', return_value={'FBS_S3_BUCKET': 'file-bucket', 'FBS_S3_PREFIX': 'file-prefix'}):
            with patch.dict('os.environ', {'FBS_S3_BUCKET': 'env-bucket'}, clear=True):
                self.assertEqual(s3.configuration()['FBS_S3_BUCKET'], 'env-bucket')
                self.assertEqual(s3.configuration()['FBS_S3_PREFIX'], 'file-prefix')
            with patch.dict('os.environ', {'FBS_S3_BUCKET': ''}, clear=True):
                self.assertIsNone(s3.configuration()['FBS_S3_BUCKET'])
        defaults = dict.fromkeys(('FBS_S3_BUCKET', 'FBS_S3_REGION', 'FBS_S3_PREFIX', 'FBS_AWS_PROFILE'))
        with patch.object(s3, 'configuration', return_value=defaults), patch.object(s3, 'make_client') as factory:
            with redirect_stderr(io.StringIO()):
                self.assertEqual(s3.main(['upload-raw', '--manifest', str(self.manifest)]), 1)
            factory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
