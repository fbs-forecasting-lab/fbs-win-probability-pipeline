"""Offline trust-pin, read-scope and error-boundary tests for the new wrapper."""
import io
import unittest
from unittest.mock import patch, Mock

from src.pipeline import managed_inference as managed


class ManagedInferenceTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('offline')))
        self.event = dict(schema_version=1, producer_kind='sagemaker_training',
            managed_model_id='a'*64, receipt_sha256='b'*64, allow_retrospective_demo=True,
            mode='hypothetical', features=dict(prior_win_pct_diff=.2, prior_avg_margin_diff=7, home_field=1))

    def test_bad_receipt_or_vector_refused_before_client_creation(self):
        with patch.dict('os.environ', {'APPROVED_MANAGED_RECEIPT_SHA256':'b'*64}), patch.object(managed.boto3, 'client') as client:
            for event in (dict(self.event, receipt_sha256='c'*64), dict(self.event, features={}),
                          dict(self.event, archive_url='https://untrusted.invalid')):
                result = managed.handler(event, None)
                self.assertEqual(result['state'], 'failed')
            client.assert_not_called()

    def test_reads_only_configured_receipt_archive_and_checks_private_bucket(self):
        client = Mock()
        client.get_public_access_block.return_value = {'PublicAccessBlockConfiguration':{
            'BlockPublicAcls':True, 'IgnorePublicAcls':True, 'BlockPublicPolicy':True, 'RestrictPublicBuckets':True}}
        client.get_object.side_effect = lambda **kw: {'ContentLength':2, 'Body':io.BytesIO(b'{}')}
        with patch.object(managed.managed_lineage, 'infer', return_value={'state':'completed'}) as infer:
            result = managed.run(self.event, client, 'synthetic-bucket', 'project', 'synthetic-managed-job', 'd'*64, 'b'*64)
        self.assertEqual(result['state'], 'completed')
        client.get_public_access_block.assert_called_once()
        self.assertEqual([c.kwargs['Key'] for c in client.get_object.call_args_list], [
            'project/final-readiness/managed-training/synthetic-managed-job/verified/receipt.json',
            'project/final-readiness/managed-training/synthetic-managed-job/output/model.tar.gz'])
        self.assertEqual(infer.call_args.args[2], 'b'*64)
        client.put_object.assert_not_called()

    def test_oversized_object_and_private_bucket_failure_do_not_deserialize(self):
        client = Mock()
        client.get_public_access_block.return_value = {'PublicAccessBlockConfiguration':{
            'BlockPublicAcls':True, 'IgnorePublicAcls':True, 'BlockPublicPolicy':True, 'RestrictPublicBuckets':True}}
        client.get_object.return_value = {'ContentLength':managed.managed_lineage.MAX_JSON_BYTES+1, 'Body':io.BytesIO(b'{}')}
        with patch.object(managed.managed_lineage, 'infer') as infer:
            with self.assertRaises(ValueError):
                managed.run(self.event, client, 'synthetic-bucket', 'project', 'synthetic-managed-job', 'd'*64, 'b'*64)
            client.get_object.return_value['Body'].close()
            client.get_public_access_block.return_value = {'PublicAccessBlockConfiguration':{}}
            with self.assertRaises(ValueError):
                managed.run(self.event, client, 'synthetic-bucket', 'project', 'synthetic-managed-job', 'd'*64, 'b'*64)
            infer.assert_not_called()
