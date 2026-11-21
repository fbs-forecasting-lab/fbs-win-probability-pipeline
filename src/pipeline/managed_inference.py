"""Candidate private inference wrapper for the independently approved managed origin.

Deploy only as a NEW function using the exact training image/runtime. The legacy
Lambda model/receipts and all predecessor functions remain untouched. Configuration
pins the receipt and storage keys; callers cannot select arbitrary artifacts.
"""
import os
from pathlib import Path
import re
import tempfile

import boto3

from src.ingestion.s3_storage import S3Store
from src.pipeline import managed_lineage
from src.pipeline.managed_contract import sdk_config
from src.pipeline.model_contract import hex_id, validate
from src.pipeline.run_contract import ContractError, STATUS


def check_request(event, receipt_sha256):
    """Validate native identity/feature domains before any AWS call or model load."""
    fields = {'schema_version', 'producer_kind', 'managed_model_id', 'receipt_sha256',
              'allow_retrospective_demo', 'mode'}
    if isinstance(event, dict) and event.get('mode') == 'hypothetical':
        fields |= {'features'}
    if not isinstance(event, dict) or set(event) != fields or event.get('producer_kind') != managed_lineage.PRODUCER:
        raise ContractError('Expected only the explicit managed inference fields.')
    if event['receipt_sha256'] != hex_id(receipt_sha256):
        raise ContractError('Request differs from the protected managed receipt pin.')
    # Reuse the tested vector/consent contract, without making a Lambda-origin claim.
    legacy_shape = {k: event[k] for k in ('schema_version', 'allow_retrospective_demo', 'mode')}
    legacy_shape.update(model_id=hex_id(event['managed_model_id']),
                        training_token_sha256='0'*64, training_receipt_sha256=receipt_sha256)
    if 'features' in event:
        legacy_shape['features'] = event['features']
    validate(legacy_shape, 'inference')
    return dict(event)


def _read(client, bucket, key, limit):
    """Read a fixed configured object with a hard byte bound, never an arbitrary URL."""
    response = client.get_object(Bucket=bucket, Key=key)
    body = response['Body']
    try:
        if response.get('ContentLength', limit + 1) > limit:
            raise ContractError('Managed evidence exceeds its byte bound.')
        value = body.read(limit + 1)
        if len(value) > limit:
            raise ContractError('Managed evidence exceeds its byte bound.')
        return value
    finally:
        body.close()


def run(event, client, bucket, prefix, job_name, dataset_id, receipt_sha256):
    """Load only approved S3 evidence, then use the native trusted reload contract.

    This dependency-injected wrapper is offline-testable. No objects are written;
    saved-sample results are verified against the training sample before returning.
    """
    event = check_request(event, receipt_sha256)
    if not isinstance(job_name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,62}', job_name):
        raise ContractError('Expected one configured managed job.')
    hex_id(dataset_id)
    store = S3Store(client, bucket, prefix)
    store._private_bucket()
    base = f'{store.prefix}/final-readiness/managed-training/{job_name}'
    receipt = _read(client, bucket, base+'/verified/receipt.json', managed_lineage.MAX_JSON_BYTES)
    archive = _read(client, bucket, base+'/output/model.tar.gz', managed_lineage.MAX_BYTES)
    with tempfile.TemporaryDirectory(prefix='fbs-managed-inference-') as tmp:
        root = Path(tmp)
        data = None
        if event['mode'] == 'saved_sample':
            data = root/'dataset'
            store.download_dataset(dataset_id, data, allow_retrospective_demo=True)
        return managed_lineage.infer(event, receipt, receipt_sha256, archive, root/'reload', dataset_dir=data)


def handler(event, context):
    """Future Lambda entrypoint; protected configuration is the independent trust pin."""
    try:
        sha = os.environ['APPROVED_MANAGED_RECEIPT_SHA256']
        check_request(event, sha)
        return run(event, boto3.client('s3', config=sdk_config()), os.environ['FBS_S3_BUCKET'],
                   os.environ['FBS_S3_PREFIX'], os.environ['APPROVED_MANAGED_JOB_NAME'],
                   os.environ['APPROVED_MANAGED_DATASET_ID'], sha)
    except Exception as exc:
        return dict(STATUS, state='failed', stage='managed_inference', error_type=type(exc).__name__,
                    message='Managed inference stopped; protected evidence preserved.')
