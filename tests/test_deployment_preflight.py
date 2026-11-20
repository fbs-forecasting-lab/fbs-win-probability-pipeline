"""Offline regression checks for deployment-only bucket inspection."""

import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from src.pipeline.deployment_preflight import BLOCK_FLAGS, inspect_private_bucket


class DeploymentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No network')))
        self.client = Mock()
        self.client.get_public_access_block.return_value = {'PublicAccessBlockConfiguration': dict.fromkeys(BLOCK_FLAGS, True)}
        self.client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {'Rules': [
            {'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]}}
        self.client.get_bucket_versioning.return_value = {}
        self.client.get_bucket_policy_status.return_value = {'PolicyStatus': {'IsPublic': False}}

    def inspect(self):
        return inspect_private_bucket(self.client, 'fictional-project-bucket', 'expected-owner')

    def test_absent_policy_with_all_blocks_records_absence_without_fabrication(self):
        self.client.get_bucket_policy_status.side_effect = ClientError({'Error': {'Code': 'NoSuchBucketPolicy'}}, 'GetBucketPolicyStatus')
        result = self.inspect()
        self.assertEqual(result['bucket_policy'], {'state': 'absent', 'aws_error_code': 'NoSuchBucketPolicy'})
        self.assertNotIn('PolicyStatus', str(result['bucket_policy']))
        for call in self.client.method_calls:
            self.assertTrue(call[0].startswith('get_'))
            self.assertEqual(call.kwargs, {'Bucket': 'fictional-project-bucket', 'ExpectedBucketOwner': 'expected-owner'})

    def test_nonpublic_policy_retains_real_status(self):
        self.assertEqual(self.inspect()['bucket_policy'], {'state': 'present', 'response': {'PolicyStatus': {'IsPublic': False}}})

    def test_public_policy_is_refused(self):
        self.client.get_bucket_policy_status.return_value = {'PolicyStatus': {'IsPublic': True}}
        with self.assertRaises(ValueError): self.inspect()

    def test_access_denied_and_other_errors_are_never_policy_absence(self):
        for code in ('AccessDenied', 'NoSuchBucket', 'InternalError'):
            with self.subTest(code=code):
                failure = ClientError({'Error': {'Code': code}}, 'GetBucketPolicyStatus')
                self.client.get_bucket_policy_status.side_effect = failure
                with self.assertRaises(ClientError) as caught: self.inspect()
                self.assertIs(caught.exception, failure)

    def test_missing_disabled_and_malformed_blocks_are_refused_before_policy_lookup(self):
        for flags in (None, {}, dict.fromkeys(BLOCK_FLAGS, False), dict.fromkeys(BLOCK_FLAGS, 1),
                      {k: True for k in BLOCK_FLAGS if k != 'BlockPublicAcls'}):
            with self.subTest(flags=flags):
                self.client.get_public_access_block.return_value = {'PublicAccessBlockConfiguration': flags}
                with self.assertRaises(ValueError): self.inspect()
        self.client.get_bucket_policy_status.assert_not_called()

    def test_malformed_policy_and_missing_encryption_are_refused(self):
        for response in ({}, {'PolicyStatus': {}}, {'PolicyStatus': {'IsPublic': 0}}, None):
            self.client.get_bucket_policy_status.return_value = response
            with self.assertRaises(ValueError): self.inspect()
        self.client.get_bucket_encryption.return_value = {}
        with self.assertRaises(ValueError): self.inspect()
