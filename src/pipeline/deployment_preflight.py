"""Read-only bucket checks for deployment controllers, separate from Lambda code."""

from botocore.exceptions import ClientError

BLOCK_FLAGS = frozenset(('BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets'))


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
