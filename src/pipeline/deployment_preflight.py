"""Validation helpers for deployment controllers, separate from Lambda code."""

import copy
import json
import re

from botocore.exceptions import ClientError

from src.pipeline.managed_archive import read_archive

BLOCK_FLAGS = frozenset(('BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets'))


def inspect_managed_archive(content):
    """Use the native reader for inspection only; no extraction or deserialization.

    Keep the controller's original 32 MiB expanded bound. Native receipt trust
    and runtime checks remain separate from this payload-only inspection.
    """
    return read_archive(content, max_tar_bytes=32 * 1024 * 1024)


def ecr_repository_policy_request(policy, repository_arn, function_arn):
    """Bind the reviewed retrieval policy to one ECR repository without Resource.

    ECR repository policies apply only to their attachment repository. Require the
    original explicit ARN and exact Lambda/account conditions before omitting
    Resource; return the exact registry/name attachment along with the policy.
    No AWS call, mutation of the original policy, or expansion of access occurs.
    Service acceptance must still be verified through Set/GetRepositoryPolicy.
    """
    repository = re.fullmatch(
        r'arn:aws:ecr:([a-z0-9-]+):([0-9]{12}):repository/([a-z0-9._/-]+)',
        repository_arn) if isinstance(repository_arn, str) else None
    function = re.fullmatch(
        r'arn:aws:lambda:([a-z0-9-]+):([0-9]{12}):function:([A-Za-z0-9_-]+)',
        function_arn) if isinstance(function_arn, str) else None
    if not repository or not function or repository.group(1, 2) != function.group(1, 2):
        raise ValueError('Select one exact same-account, same-region repository and function.')
    if (not isinstance(policy, dict) or set(policy) != {'Version', 'Statement'}
            or policy['Version'] != '2012-10-17'
            or not isinstance(policy['Statement'], list) or len(policy['Statement']) != 1):
        raise ValueError('Expected the single reviewed repository-policy statement.')
    statement = policy['Statement'][0]
    required = {'Effect', 'Principal', 'Action', 'Resource', 'Condition'}
    conditions = {'ArnEquals': {'aws:SourceArn': function_arn},
                  'StringEquals': {'aws:SourceAccount': repository[2]}}
    actions = {'ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'}
    if (not isinstance(statement, dict)
            or set(statement) not in (required, required | {'Sid'})
            or statement['Effect'] != 'Allow'
            or statement['Principal'] != {'Service': 'lambda.amazonaws.com'}
            or not isinstance(statement['Action'], list) or len(statement['Action']) != 2
            or any(not isinstance(action, str) for action in statement['Action'])
            or set(statement['Action']) != actions
            or statement['Resource'] != repository_arn
            or statement['Condition'] != conditions):
        raise ValueError('Reviewed repository, retrieval actions or source restrictions differ.')
    candidate = copy.deepcopy(policy)
    del candidate['Statement'][0]['Resource']
    return {'registryId': repository[2], 'repositoryName': repository[3],
            'policyText': json.dumps(candidate, sort_keys=True, separators=(',', ':'))}


def inspect_private_bucket(client, bucket, expected_owner):
    """Require owner-scoped reads, encryption and all four public-access blocks.

    An absent policy is recorded as absence, never as a fabricated PolicyStatus.
    Every other service error propagates. Existing policies must be nonpublic.
    This helper never writes or changes permissions.
    """
    arguments = {'Bucket': bucket, 'ExpectedBucketOwner': expected_owner}

    def read(method):
        response = getattr(client, method)(**arguments)
        if not isinstance(response, dict):
            raise ValueError('Malformed bucket metadata response.')
        return {k: v for k, v in response.items() if k != 'ResponseMetadata'}

    blocks = read('get_public_access_block')
    flags = blocks.get('PublicAccessBlockConfiguration')
    if not isinstance(flags, dict) or set(flags) != BLOCK_FLAGS or any(v is not True for v in flags.values()):
        raise ValueError('All four bucket-level public-access blocks must be enabled.')
    encryption = read('get_bucket_encryption')
    configuration = encryption.get('ServerSideEncryptionConfiguration')
    rules = configuration.get('Rules') if isinstance(configuration, dict) else None
    if not isinstance(rules, list) or not rules:
        raise ValueError('Required bucket encryption configuration is missing.')
    for rule in rules:
        default = rule.get('ApplyServerSideEncryptionByDefault') if isinstance(rule, dict) else None
        if not isinstance(default, dict) or default.get('SSEAlgorithm') not in ('AES256', 'aws:kms', 'aws:kms:dsse'):
            raise ValueError('Bucket encryption configuration is malformed.')
    versioning = read('get_bucket_versioning')
    if ('Status' in versioning and versioning['Status'] not in ('Enabled', 'Suspended')):
        raise ValueError('Bucket versioning metadata is malformed.')
    try:
        policy = read('get_bucket_policy_status')
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') != 'NoSuchBucketPolicy':
            raise
        policy_record = {'state': 'absent', 'aws_error_code': 'NoSuchBucketPolicy'}
    else:
        status = policy.get('PolicyStatus')
        if not isinstance(status, dict) or status.get('IsPublic') is not False:
            raise ValueError('Existing bucket policy is public or its status is malformed.')
        policy_record = {'state': 'present', 'response': policy}
    return {'get_public_access_block': blocks, 'get_bucket_encryption': encryption,
            'get_bucket_versioning': versioning, 'bucket_policy': policy_record}
