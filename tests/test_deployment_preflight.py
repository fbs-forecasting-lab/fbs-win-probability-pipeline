"""Offline checks for deployment-only bucket, policy and archive validation."""

import copy
import io
import json
import tarfile
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from src.pipeline.deployment_preflight import (
    BLOCK_FLAGS, ecr_repository_policy_request, inspect_managed_archive, inspect_private_bucket)


class ManagedArchiveInspectionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No network')))
        self.files = {name: ('fictional ' + name).encode() for name in (
            'model.joblib', 'evaluation.json', 'calibration.json',
            'holdout_predictions.csv', 'sample_predictions.csv',
            'exclusions.json', 'model_metadata.json')}

    def archive(self, *, pax=None, duplicate=False, omit=False, extra=False, link=False):
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode='w:gz', format=tarfile.PAX_FORMAT) as archive:
            files = list(self.files.items())
            if omit:
                files.pop()
            if duplicate:
                files.append(('./model.joblib', self.files['model.joblib']))
            if extra:
                files.append(('unapproved.txt', b'fictional'))
            for name, value in files:
                member = tarfile.TarInfo(name)
                member.size = len(value)
                member.pax_headers = dict(pax or {})
                if link and name == 'model.joblib':
                    member.type = tarfile.LNKTYPE if link == 'hard' else tarfile.SYMTYPE
                    member.linkname, member.size = 'elsewhere', 0
                archive.addfile(member, io.BytesIO(value))
        return result.getvalue()

    def test_timestamp_only_pax_keeps_exact_payload_bytes_without_deserializing(self):
        with patch('joblib.load', side_effect=AssertionError('Must not deserialize')) as load:
            value = self.archive(pax={'atime': '123.4', 'ctime': '123.5',
                                      'mtime': '123.6', 'LIBARCHIVE.creationtime': '123.7'})
            self.assertEqual(inspect_managed_archive(value), self.files)
            load.assert_not_called()

    def test_plain_archive_remains_supported(self):
        self.assertEqual(inspect_managed_archive(self.archive()), self.files)

    def test_path_link_size_and_unknown_pax_overrides_are_refused(self):
        for field, value in (('path', 'model.joblib'), ('linkpath', 'model.joblib'),
                             ('size', '1'), ('unknown', '123')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                inspect_managed_archive(self.archive(pax={field: value}))

    def test_malformed_timestamp_metadata_is_refused(self):
        for value in ('nan', 'inf', '../elsewhere', '1e100', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspect_managed_archive(self.archive(pax={'atime': value}))

    def test_duplicate_alias_missing_extra_and_link_members_are_refused(self):
        for option in ('duplicate', 'omit', 'extra', 'link', 'hard link'):
            with self.subTest(option=option), self.assertRaises(ValueError):
                kwargs = {'link': 'hard'} if option == 'hard link' else {option: True}
                inspect_managed_archive(self.archive(**kwargs))

    def test_truncation_and_trailing_content_are_refused(self):
        value = self.archive()
        with self.assertRaises(ValueError):
            inspect_managed_archive(value[:len(value)//2])
        import gzip
        expanded = gzip.decompress(value)
        with self.assertRaises(ValueError):
            inspect_managed_archive(expanded + b'x' * 512)

    def test_invalid_type_and_compressed_size_bound_are_refused(self):
        for value in ('not bytes', b'', b'x' * (32 * 1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                inspect_managed_archive(value)

    def test_small_compressed_archive_cannot_exceed_expanded_size_bound(self):
        import gzip
        value = gzip.compress(b'\0' * (32 * 1024 * 1024 + 512))
        self.assertLess(len(value), 32 * 1024 * 1024)
        with self.assertRaises(ValueError):
            inspect_managed_archive(value)


class ECRRepositoryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No network')))
        self.account = '1' * 12
        self.repository = f'arn:aws:ecr:us-east-1:{self.account}:repository/fictional-training'
        self.function = f'arn:aws:lambda:us-east-1:{self.account}:function:fictional-inference'
        self.policy = {'Version': '2012-10-17', 'Statement': [{
            'Sid': 'ReviewedImageRetrieval', 'Effect': 'Allow',
            'Principal': {'Service': 'lambda.amazonaws.com'},
            'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
            'Resource': self.repository,
            'Condition': {'ArnEquals': {'aws:SourceArn': self.function},
                          'StringEquals': {'aws:SourceAccount': self.account}}}]}

    def build(self, policy=None, repository=None, function=None):
        return ecr_repository_policy_request(
            self.policy if policy is None else policy,
            self.repository if repository is None else repository,
            self.function if function is None else function)

    def test_attachment_removes_only_resource_and_pins_exact_registry_repository(self):
        result = self.build()
        self.assertEqual(result['registryId'], self.account)
        self.assertEqual(result['repositoryName'], 'fictional-training')
        candidate = json.loads(result['policyText'])
        self.assertNotIn('Resource', candidate['Statement'][0])
        candidate['Statement'][0]['Resource'] = self.repository
        self.assertEqual(candidate, self.policy)

    def test_original_policy_is_unchanged_and_result_is_detached(self):
        before = copy.deepcopy(self.policy)
        candidate = json.loads(self.build()['policyText'])
        candidate['Statement'][0]['Action'].append('ecr:PutImage')
        self.assertEqual(self.policy, before)

    def test_broader_principal_actions_or_writes_are_refused(self):
        for field, value in (
                ('Principal', '*'), ('Principal', {'Service': 'sagemaker.amazonaws.com'}),
                ('Action', ['ecr:*']),
                ('Action', ['ecr:BatchGetImage', 'ecr:PutImage']),
                ('Resource', '*'), ('Resource', self.repository + '-other')):
            policy = copy.deepcopy(self.policy)
            policy['Statement'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.build(policy)

    def test_missing_or_wildcard_source_restrictions_are_refused(self):
        conditions = self.policy['Statement'][0]['Condition']
        for value in ({}, {'ArnEquals': conditions['ArnEquals']},
                      {'ArnEquals': {'aws:SourceArn': '*'},
                       'StringEquals': conditions['StringEquals']},
                      {'ArnEquals': conditions['ArnEquals'],
                       'StringEquals': {'aws:SourceAccount': '2' * 12}}):
            policy = copy.deepcopy(self.policy)
            policy['Statement'][0]['Condition'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build(policy)

    def test_other_attachment_function_account_region_and_extra_statements_are_refused(self):
        for kwargs in ({'repository': self.repository + '-other'},
                       {'function': self.function + '-other'},
                       {'function': self.function.replace(self.account, '2' * 12)},
                       {'function': self.function.replace('us-east-1', 'us-west-2')}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.build(**kwargs)
        policy = copy.deepcopy(self.policy)
        policy['Statement'].append(copy.deepcopy(policy['Statement'][0]))
        with self.assertRaises(ValueError):
            self.build(policy)

    def test_generated_request_matches_installed_set_repository_policy_shape(self):
        from botocore.session import Session
        from botocore.validate import validate_parameters
        shape = Session().get_service_model('ecr').operation_model('SetRepositoryPolicy').input_shape
        validate_parameters(self.build(), shape)


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
