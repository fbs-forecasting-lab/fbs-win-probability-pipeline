"""Offline SageMaker lineage verification; external approval is the trust anchor.

Evidence is UTF-8 JSON containing create_request, describe_job, identities and
runtime. The externally approved hash must come from a trusted review channel,
never the artifact supplier. This module compares pinned evidence; it cannot
authenticate an AWS response or prove service execution without that approval.
No Lambda origin, training, SDK calls or legacy publication is performed.
"""

import json
import math
from pathlib import Path
import re

from src.models import baseline, predict
from src.pipeline.managed_archive import FILES, MAX_BYTES, MAX_TAR_BYTES, read_archive
from src.pipeline.managed_contract import validate_request
from src.pipeline.model_contract import PREDICTORS, hex_id
from src.pipeline.run_contract import ContractError, STATUS, digest, encode

PRODUCER = 'sagemaker_training'
MAX_JSON_BYTES = 1024 * 1024
IDENTITY_FIELDS = frozenset(('job_arn', 'image_uri', 'source_sha256',
    'dataset_id', 'dataset_report_sha256', 'dataset_s3_uri',
    'dataset_artifact_sha256', 'preparation_selection_id',
    'preparation_receipt_sha256', 'output_uri'))


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate JSON field.')
            result[key] = value
        return result
    _require(type(content) is bytes and len(content) <= MAX_JSON_BYTES,
             'Invalid or oversized lineage JSON.')
    try:
        result = json.loads(content.decode('utf-8'), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        # Also rejects numeric overflow such as 1e999.
        encode(result)
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError('Invalid lineage JSON.') from None
    _require(isinstance(result, dict), 'Lineage JSON must be an object.')
    return result


def _matches_job(expected, actual, path=''):
    """Allow only explicitly harmless service defaults in approved config fields."""
    defaults = {
        'AlgorithmSpecification.EnableSageMakerMetricsTimeSeries': False,
        'ResourceConfig.KeepAlivePeriodInSeconds': 0,
        'ResourceConfig.VolumeKmsKeyId': '',
        'OutputDataConfig.KmsKeyId': '',
        'OutputDataConfig.CompressionType': 'GZIP',
        'InputDataConfig.0.CompressionType': 'None',
        'InputDataConfig.0.RecordWrapperType': 'None',
    }
    if type(expected) is dict:
        if type(actual) is not dict or not set(expected) <= set(actual):
            return False
        for key in set(actual) - set(expected):
            name = f'{path}.{key}'
            if name not in defaults or encode(actual[key]) != encode(defaults[name]):
                return False
        return all(_matches_job(value, actual[key], f'{path}.{key}' if path else key)
                   for key, value in expected.items())
    if type(expected) is list:
        return (type(actual) is list and len(expected) == len(actual)
                and all(_matches_job(a, b, f'{path}.{i}') for i, (a, b) in enumerate(zip(expected, actual))))
    return encode(expected) == encode(actual)


def _evidence(content, expected_sha256):
    hex_id(expected_sha256)
    _require(type(content) is bytes and digest(content) == expected_sha256,
             'Approved evidence hash mismatch.')
    value = _json(content)
    _require(set(value) == {'schema_version', 'producer_kind', 'create_request',
                            'describe_job', 'identities', 'runtime'}, 'Unexpected evidence fields.')
    _require(type(value['schema_version']) is int and value['schema_version'] == 1
             and value['producer_kind'] == PRODUCER, 'Unsupported managed evidence.')
    request, job, ids = (value[k] for k in ('create_request', 'describe_job', 'identities'))
    _require(all(isinstance(v, dict) for v in (request, job, ids)), 'Invalid job evidence.')
    request = validate_request(request)
    _require(set(ids) == IDENTITY_FIELDS, 'Incomplete managed identity pins.')
    for name in ('source_sha256', 'dataset_id', 'dataset_report_sha256',
                 'preparation_selection_id', 'preparation_receipt_sha256'):
        hex_id(ids[name])
    hashes = ids['dataset_artifact_sha256']
    _require(isinstance(hashes, dict) and set(hashes) == baseline.DATA_FILES,
             'Expected five dataset artifact hashes plus the pinned report.')
    for sha in hashes.values():
        hex_id(sha)
    _require(job.get('TrainingJobStatus') == 'Completed'
             and job.get('SecondaryStatus') == 'Completed'
             and not job.get('FailureReason'), 'Managed job is not successfully completed.')
    _require(all(k in job and _matches_job(v, job[k], k) for k, v in request.items()),
             'Completed job differs from approved training request.')
    _require('RetryStrategy' not in job, 'Managed RetryStrategy must be absent.')
    for field in ('HyperParameters', 'VpcConfig', 'CheckpointConfig', 'DebugHookConfig',
                  'DebugRuleConfigurations', 'ProfilerRuleConfigurations', 'WarmPoolStatus',
                  'RemoteDebugConfig', 'InfraCheckConfig'):
        _require(not job.get(field), 'Unapproved optional job configuration.')
    _require(job.get('EnableInterContainerTrafficEncryption', False) is False,
             'Unapproved inter-container configuration.')
    name = request['TrainingJobName']
    _require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', name),
             'Invalid training job name.')
    arn = ids['job_arn']
    _require(isinstance(arn, str) and re.fullmatch(
        r'arn:aws(?:-us-gov|-cn)?:sagemaker:[a-z0-9-]+:[0-9]{12}:training-job/' + re.escape(name), arn)
        and job.get('TrainingJobArn') == arn, 'Training job identity mismatch.')
    image = ids['image_uri']
    _require(isinstance(image, str) and re.fullmatch(r'[^\s@]+@sha256:[0-9a-f]{64}', image),
             'Training image must be pinned by digest.')
    _require(request['AlgorithmSpecification']['TrainingImage'] == image,
             'Expected the approved immutable image and File input mode.')
    environment = request['Environment']
    expected_environment = {'EXPECTED_DATASET_ID': ids['dataset_id'],
        'EXPECTED_REPORT_SHA256': ids['dataset_report_sha256'], 'ALLOW_RETROSPECTIVE_DEMO': 'true'}
    _require(environment == expected_environment,
        'Training environment differs from approved dataset/consent.')
    _require(request['EnableNetworkIsolation'] is True, 'Isolated managed training is required.')
    channels = request['InputDataConfig']
    _require(isinstance(channels, list) and len(channels) == 1 and isinstance(channels[0], dict),
             'Expected exactly one dataset channel.')
    channel = channels[0]
    _require(set(channel) <= {'ChannelName', 'DataSource', 'InputMode', 'CompressionType'}
             and channel.get('ChannelName') == 'dataset'
             and channel.get('InputMode', 'File') == 'File'
             and channel.get('CompressionType', 'None') == 'None'
             and channel.get('DataSource') == {'S3DataSource': {'S3DataType': 'S3Prefix',
                 'S3Uri': ids['dataset_s3_uri'], 'S3DataDistributionType': 'FullyReplicated'}},
             'Dataset File channel differs from the approved location.')
    output = request['OutputDataConfig']
    _require(isinstance(output, dict) and set(output) <= {'S3OutputPath', 'KmsKeyId'}
             and isinstance(output.get('S3OutputPath'), str), 'Unsupported output configuration.')
    for uri in (ids['dataset_s3_uri'], output['S3OutputPath'], ids['output_uri']):
        _require(isinstance(uri, str) and re.fullmatch(r's3://[a-z0-9][a-z0-9.-]+/[^\s?#]+', uri)
                 and not any(p in ('.', '..', '') for p in uri[5:].rstrip('/').split('/')),
                 'Expected an explicit approved S3 location.')
    _require(ids['output_uri'] == output['S3OutputPath'].rstrip('/') + '/' + name + '/output/model.tar.gz'
             and job.get('ModelArtifacts') == {'S3ModelArtifacts': ids['output_uri']},
             'Managed output object differs from the approved job output.')
    _require(value['runtime'] == baseline.versions(), 'Exact training/inference runtime mismatch.')
    return value


def _archive(content):
    """Use the shared strict USTAR/timestamp-only PAX reader without extraction."""
    try:
        return read_archive(content, max_bytes=MAX_BYTES, max_tar_bytes=MAX_TAR_BYTES)
    except ValueError:
        raise ContractError('Invalid or unsafe managed archive.') from None


def _metadata(artifacts, evidence):
    metadata = _json(artifacts['model_metadata.json'])
    baseline.check_status(metadata)
    ids = evidence['identities']
    _require(type(metadata.get('model_schema_version')) is int and metadata['model_schema_version'] == 1
             and metadata.get('predictor_columns') == list(PREDICTORS)
             and metadata.get('class_order') == [0, 1]
             and metadata.get('versions') == evidence['runtime']
             and metadata.get('dataset_id') == ids['dataset_id']
             and metadata.get('dataset_report_sha256') == ids['dataset_report_sha256']
             and metadata.get('dataset_artifact_sha256') == ids['dataset_artifact_sha256']
             and metadata.get('artifact_sha256') == {n: digest(b) for n, b in artifacts.items()
                                                     if n != 'model_metadata.json'},
             'Managed metadata, runtime, dataset or companion hashes differ.')
    return metadata


def build_verified_receipt(evidence_bytes, expected_evidence_sha256, archive_bytes):
    """Return receipt bytes after verifying externally approved exact evidence."""
    evidence = _evidence(evidence_bytes, expected_evidence_sha256)
    artifacts = _archive(archive_bytes)
    _metadata(artifacts, evidence)
    identity = {'producer_kind': PRODUCER, 'evidence_sha256': expected_evidence_sha256,
                'archive_sha256': digest(archive_bytes)}
    receipt = dict(identity, schema_version=1, **STATUS,
        managed_model_id=digest(encode(identity)), evidence_json=evidence_bytes.decode('utf-8'),
        artifact_sha256={n: digest(b) for n, b in artifacts.items()})
    content = encode(receipt)
    _require(len(content) <= MAX_JSON_BYTES, 'Managed receipt exceeds bounds.')
    return content


def _receipt(receipt_bytes, expected_receipt_sha256, archive_bytes):
    hex_id(expected_receipt_sha256)
    _require(type(receipt_bytes) is bytes and digest(receipt_bytes) == expected_receipt_sha256,
             'Externally approved receipt hash mismatch.')
    receipt = _json(receipt_bytes)
    _require(set(receipt) == {'schema_version', 'producer_kind', 'evidence_sha256',
        'archive_sha256', 'managed_model_id', 'evidence_json', 'artifact_sha256'} | set(STATUS),
        'Unexpected managed receipt fields.')
    baseline.check_status(receipt)
    _require(type(receipt['schema_version']) is int and receipt['schema_version'] == 1
             and receipt['producer_kind'] == PRODUCER and isinstance(receipt['evidence_json'], str),
             'Unsupported managed receipt.')
    evidence = _evidence(receipt['evidence_json'].encode('utf-8'), receipt['evidence_sha256'])
    identity = {k: receipt[k] for k in ('producer_kind', 'evidence_sha256', 'archive_sha256')}
    _require(type(archive_bytes) is bytes and digest(archive_bytes) == receipt['archive_sha256']
             and receipt['managed_model_id'] == digest(encode(identity)), 'Managed archive identity mismatch.')
    artifacts = _archive(archive_bytes)
    _require(receipt['artifact_sha256'] == {n: digest(b) for n, b in artifacts.items()},
             'Managed receipt artifact hashes differ.')
    _metadata(artifacts, evidence)
    return receipt, evidence, artifacts


def load_verified_model(receipt_bytes, expected_receipt_sha256, archive_bytes, root):
    """Verify all lineage/bytes before publishing locally and deserializing once.

    root must be a fresh or empty private directory with no symlink ancestors.
    Returns (model, metadata, native_receipt, model_directory).
    """
    receipt, _, artifacts = _receipt(receipt_bytes, expected_receipt_sha256, archive_bytes)
    root = Path(root).absolute()
    _require('..' not in root.parts and not any(p.is_symlink() for p in (root, *root.parents))
             and (not root.exists() or (root.is_dir() and not any(root.iterdir()))),
             'Select a fresh private model root without symbolic links.')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require(root.stat().st_mode & 0o077 == 0, 'Model root must have private permissions.')
    model_dir = root / 'model'
    baseline.publish(model_dir, artifacts)
    model, metadata = baseline.load_trusted_model(model_dir, allow_retrospective_demo=True)
    return model, metadata, receipt, model_dir


def infer(request, receipt_bytes, expected_receipt_sha256, archive_bytes, root, dataset_dir=None):
    """Native inference with a separately injected, externally approved receipt pin.

    A separately pinned consumer image must retain the producer runtime, with
    ImageConfig.EntryPoint overridden to /lambda-entrypoint.sh and a new handler
    as Command. Its digest is distinct from the immutable producer image in the
    evidence; never rewrite that producer identity. The wrapper obtains its pin from protected
    configuration, read only approved receipt/archive/dataset locations, and
    pass a fresh private root here. This function creates no SDK clients and
    changes no legacy function. Linux image/runtime execution remains separate
    evidence; host tests do not establish it.
    """
    fields = {'schema_version', 'producer_kind', 'managed_model_id', 'receipt_sha256',
              'allow_retrospective_demo', 'mode'}
    if isinstance(request, dict) and request.get('mode') == 'hypothetical':
        fields |= {'features'}
    _require(isinstance(request, dict) and set(request) == fields, 'Unexpected managed inference fields.')
    _require(type(request['schema_version']) is int and request['schema_version'] == 1
             and request['producer_kind'] == PRODUCER and request['allow_retrospective_demo'] is True
             and request['mode'] in ('hypothetical', 'saved_sample'), 'Invalid managed inference request.')
    for key in ('managed_model_id', 'receipt_sha256'):
        hex_id(request[key])
    hex_id(expected_receipt_sha256)
    _require(request['receipt_sha256'] == expected_receipt_sha256,
             'Request differs from the independently approved receipt pin.')
    if request['mode'] == 'hypothetical':
        values = request['features']
        # Match model_contract.validate's feature rules without inventing Lambda identities.
        _require(isinstance(values, dict) and set(values) == set(PREDICTORS)
                 and all(type(v) in (int, float) and math.isfinite(v) for v in values.values()),
                 'Expected exactly three finite numeric predictors.')
        _require(-1 <= values['prior_win_pct_diff'] <= 1 and values['home_field'] in (0, 1),
                 'Hypothetical feature domain is invalid.')
        values = {name: values[name] for name in PREDICTORS}
    receipt, evidence, _ = _receipt(receipt_bytes, request['receipt_sha256'], archive_bytes)
    _require(receipt['managed_model_id'] == request['managed_model_id'], 'Managed model reference mismatch.')
    if request['mode'] == 'saved_sample':
        _require(dataset_dir is not None, 'Saved-sample inference requires the pinned dataset.')
        data = baseline.load_dataset(dataset_dir, allow_retrospective_demo=True)
        ids = evidence['identities']
        _require(data['report_sha256'] == ids['dataset_report_sha256']
                 and data['report']['dataset_id'] == ids['dataset_id']
                 and data['report']['artifact_sha256'] == ids['dataset_artifact_sha256'],
                 'Saved inference dataset differs from the approved managed input.')
    model, metadata, _, model_dir = load_verified_model(
        receipt_bytes, request['receipt_sha256'], archive_bytes, root)
    if request['mode'] == 'hypothetical':
        result = predict.predict_vector(model, values)
    else:
        output = Path(root) / 'predictions'
        result = predict.predict_saved_sample(model_dir, dataset_dir, output, allow_retrospective_demo=True)
        _require((output / 'predictions.csv').read_bytes() == (model_dir / 'sample_predictions.csv').read_bytes(),
                 'Independent saved predictions differ from the managed artifact.')
    return dict(result, state='completed', producer_kind=PRODUCER,
                managed_model_id=receipt['managed_model_id'], receipt_sha256=request['receipt_sha256'],
                dataset_id=metadata['dataset_id'])
