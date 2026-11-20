"""Private cloud adapters around the existing baseline, evaluation and saved-model inference."""

import base64
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import platform
import tempfile

import boto3

from src.features import dataset
from src.ingestion.s3_storage import S3Store
from src.models import baseline, predict
from src.pipeline.cloud_ingestion import CLIENT_CONFIG, create_once
from src.pipeline import model_contract as contract
from src.pipeline.run_contract import ContractError, STATUS, digest, encode

MAX_BUNDLE_BYTES = 32 * 1024 * 1024
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class ModelingStore(S3Store):
    """Use exact-key absence probes; a 403 always stays a failure."""
    def __init__(self, client, bucket, prefix, approved_reference=None):
        super().__init__(client, bucket, prefix)
        self.approved_reference = approved_reference

    def _get(self, key, *, optional=False):
        if not isinstance(key, str) or not key.startswith(tuple(f'{self.prefix}/{part}/' for part in
                ('cloud-modeling', 'cloud-preparation/runs', 'datasets'))):
            raise ContractError('Modeling read is outside the approved prefixes.')
        if optional:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
            if not any(item.get('Key') == key for item in response.get('Contents', [])):
                return None
        return super()._get(key, optional=False)


def verify_dataset(store, reference, directory):
    """Verify trusted preparation completion and every byte BEFORE fitting."""
    check_reference(store, reference)
    key = f"{store.prefix}/cloud-preparation/runs/{reference['preparation_selection_id']}/complete.json"
    content = store._get(key)
    if digest(content) != reference['preparation_receipt_sha256']:
        raise ContractError('Preparation completion receipt hash mismatch.')
    completed = baseline.read_json(content)
    baseline.check_status(completed)
    if (completed.get('state') != 'completed' or completed.get('dataset_id') != reference['dataset_id']
            or completed.get('selection_id') != reference['preparation_selection_id']
            or not completed.get('sql_parity', {}).get('verified_target_rows')
            or len(completed.get('origins', {})) != 6
            or not all(v.get('cloud_capture_verified') is True for v in completed['origins'].values())):
        raise ContractError('Preparation receipt does not establish the selected verified cloud dataset.')
    names = baseline.DATA_FILES | {'dataset_report.json'}
    hashes = completed.get('dataset_artifact_sha256')
    if not isinstance(hashes, dict) or set(hashes) != names:
        raise ContractError('Preparation receipt must bind all six dataset files.')
    for value in hashes.values():
        contract.hex_id(value)
    store.download_dataset(reference['dataset_id'], directory, allow_retrospective_demo=True)
    files = {name: (directory / name).read_bytes() for name in names}
    if sum(map(len, files.values())) > MAX_BUNDLE_BYTES or any(digest(data) != hashes[name] for name, data in files.items()):
        raise ContractError('Downloaded dataset differs from preparation completion or exceeds the size bound.')
    return completed


def check_reference(store, reference):
    if store.approved_reference is not None and any(reference.get(k) != v for k, v in store.approved_reference.items()):
        raise ContractError('Dataset reference is outside this deployment approved preparation identity.')


def interpretation(model):
    """Describe fitted associations in original and standardized feature units, never causation."""
    scaler, logistic = model.named_steps['scaler'], model.named_steps['logistic']
    weights = logistic.coef_[0]
    rows = []
    for index, name in enumerate(baseline.PREDICTORS):
        beta = float(weights[index])
        scale = float(scaler.scale_[index])
        rows.append({'feature': name, 'training_mean': float(scaler.mean_[index]), 'training_scale': scale,
                     'coefficient_per_training_standard_deviation': beta,
                     'log_odds_change_per_original_unit': beta / scale,
                     'odds_ratio_per_training_standard_deviation': math.exp(beta),
                     'association': 'higher home-win odds' if beta > 0 else 'lower home-win odds' if beta < 0 else 'no fitted association'})
    return {**STATUS, 'predictor_columns': baseline.PREDICTORS, 'features': rows,
            'intercept_at_training_means': float(logistic.intercept_[0]),
            'original_unit_intercept': float(logistic.intercept_[0] - sum(weights * scaler.mean_ / scaler.scale_)),
            'scaler_fitted_rows': int(scaler.n_samples_seen_),
            'context': 'Coefficients describe conditional associations with home-win log odds, not causal effects. '
                       'Win percentage is a fraction; margin is points/game; home_field is 0 or 1. '
                       'Scaling uses training rows only; coefficients are not feature-importance or causal rankings.'}


def verify_bundle(artifacts, model_id, request, release):
    if set(artifacts) != set(contract.MODEL_FILES) or sum(map(len, artifacts.values())) > MAX_BUNDLE_BYTES:
        raise ContractError('Model bundle filenames or size are invalid.')
    provenance = baseline.read_json(artifacts['training_provenance.json'])
    baseline.check_status(provenance)
    metadata = baseline.read_json(artifacts['model_metadata.json'])
    baseline.check_status(metadata)
    if (provenance.get('model_id') != model_id or provenance.get('request') != request
            or provenance.get('implementation_sha256') != release
            or metadata.get('dataset_id') != request['dataset_id']
            or metadata.get('versions') != baseline.versions()
            or provenance.get('artifact_sha256') != {n: digest(b) for n, b in artifacts.items() if n != 'training_provenance.json'}):
        raise ContractError('Model provenance, dataset, runtime versions or artifact hashes differ.')
    if metadata.get('artifact_sha256') != {n: digest(artifacts[n]) for n in contract.MODEL_FILES[:6]}:
        raise ContractError('Model companion hashes differ; nothing deserialized.')
    return metadata


def model_completion(request, model_id, token, release, claim_bytes, metadata, artifacts, model_base):
    """Bind every reported result to the immutable bundle, including completed replay."""
    return {**STATUS, 'state': 'completed', 'model_id': model_id, 'model_prefix': model_base,
            'training_token_sha256': token, 'request': request, 'implementation_sha256': release,
            'claim_sha256': digest(claim_bytes), 'versions': metadata['versions'],
            'counts': metadata['counts'], 'evaluation': baseline.read_json(artifacts['evaluation.json']),
            'artifact_sha256': {n: digest(b) for n, b in artifacts.items()}}


def train_run(event, store):
    stage, model_id = 'request_validation', None
    try:
        request = contract.validate(event, 'training')
        token, model_id, release = contract.identities(request)
        base = f'{store.prefix}/cloud-modeling/training/{token}'
        model_base = f'{store.prefix}/cloud-modeling/models/{model_id}'
        stage = 'aws_preflight'
        store._private_bucket()
        with tempfile.TemporaryDirectory(prefix='fbs-model-train-') as tmp:
            root = Path(tmp)
            stage = 'dataset_verification'
            prepared = verify_dataset(store, request, root / 'dataset')
            claim_bytes = encode({'schema_version': 1, 'model_id': model_id, 'request': request,
                                  'implementation_sha256': release, 'versions': baseline.versions()})
            stage = 'training_claim'
            present = store._get(base + '/claim.json', optional=True)
            owned = create_once(store, base + '/claim.json', claim_bytes) if present is None else False
            if store._get(base + '/claim.json') != claim_bytes:
                raise ContractError('Training token conflicts with its existing request, code or runtime; no fit started.')
            stage = 'completed_replay'
            completed_bytes = store._get(base + '/complete.json', optional=True)
            if completed_bytes is not None:
                completed = baseline.read_json(completed_bytes)
                baseline.check_status(completed)
                expected = {'model_id': model_id, 'request': request, 'implementation_sha256': release,
                            'claim_sha256': digest(claim_bytes), 'state': 'completed'}
                if any(completed.get(k) != v for k, v in expected.items()):
                    raise ContractError('Training completion identity differs.')
                hashes = completed.get('artifact_sha256', {})
                if set(hashes) != set(contract.MODEL_FILES):
                    raise ContractError('Training completion bundle is incomplete.')
                artifacts = {n: store._get(model_base + '/' + n) for n in contract.MODEL_FILES}
                if any(digest(b) != hashes[n] for n, b in artifacts.items()):
                    raise ContractError('Completed model failed integrity replay; no repair or retraining allowed.')
                metadata = verify_bundle(artifacts, model_id, request, release)
                if completed != model_completion(request, model_id, token, release, claim_bytes, metadata, artifacts, model_base):
                    raise ContractError('Completed training receipt differs from its verified metrics, counts or bundle.')
                return completed
            stage = 'model_checkpoint'
            saved = store._get(base + '/checkpoint.json', optional=True)
            model_dir = root / 'model'
            if saved is None:
                if not owned:
                    raise ContractError('Training claim has no durable model checkpoint; do not retrain this token.')
                stage = 'training_evaluation'
                LOGGER.info('model_fit_start training_token_sha256=%s model_id=%s', token, model_id)
                metadata, evaluation = baseline.train_baseline(root / 'dataset', model_dir, allow_retrospective_demo=True)
                model, reloaded_metadata = baseline.load_trusted_model(model_dir, allow_retrospective_demo=True)
                if metadata != reloaded_metadata:
                    raise ContractError('Reloaded model metadata differs.')
                artifacts = {name: (model_dir / name).read_bytes() for name in contract.MODEL_FILES[:7]}
                artifacts['interpretation.json'] = dataset._json(interpretation(model))
                artifacts['training_provenance.json'] = encode({**STATUS, 'model_id': model_id, 'request': request,
                    'implementation_sha256': release, 'versions': baseline.versions(),
                    'runtime': {'system': platform.system(), 'machine': platform.machine(), 'release': platform.release(),
                                'aws_execution_env': os.environ.get('AWS_EXECUTION_ENV', 'offline_synthetic_test')},
                    'libraries': {name: importlib.metadata.version(name) for name in
                                  ('numpy', 'pandas', 'scipy', 'scikit-learn', 'joblib', 'threadpoolctl', 'boto3')},
                    'preparation_receipt_sha256': request['preparation_receipt_sha256'],
                    'artifact_sha256': {name: digest(content) for name, content in artifacts.items()}})
                stage = 'model_checkpoint'
                saved = encode({'model_id': model_id, 'claim_sha256': digest(claim_bytes),
                                'artifacts': {n: base64.b64encode(b).decode() for n, b in artifacts.items()}})
                if len(saved) > 48 * 1024 * 1024:
                    raise ContractError('Model checkpoint exceeds the bounded transfer size.')
                store._put(base + '/checkpoint.json', saved)
            checkpoint = baseline.read_json(saved)
            if checkpoint.get('model_id') != model_id or checkpoint.get('claim_sha256') != digest(claim_bytes):
                raise ContractError('Model checkpoint conflicts with training claim.')
            artifacts = {n: base64.b64decode(v, validate=True) for n, v in checkpoint['artifacts'].items()}
            metadata = verify_bundle(artifacts, model_id, request, release)
            stage = 'publish_model'
            store._upload(model_base, artifacts, 'training_provenance.json')
            completed = model_completion(request, model_id, token, release, claim_bytes, metadata, artifacts, model_base)
            store._put(base + '/complete.json', encode(completed))
            return completed
    except Exception as exc:
        return failure(stage, exc, model_id)


def trusted_model(store, request, root):
    """Establish producer origin + immutable receipt hashes BEFORE pickle-based loading."""
    ledger = f"{store.prefix}/cloud-modeling/training/{request['training_token_sha256']}"
    receipt_bytes = store._get(ledger + '/complete.json')
    if digest(receipt_bytes) != request['training_receipt_sha256']:
        raise ContractError('Trusted training receipt hash mismatch; nothing deserialized.')
    receipt = baseline.read_json(receipt_bytes)
    baseline.check_status(receipt)
    training = contract.validate(receipt['request'], 'training')
    check_reference(store, training)
    token, model_id, release = contract.identities(training)
    if (receipt.get('state') != 'completed' or model_id != request['model_id'] or receipt.get('model_id') != model_id
            or token != request['training_token_sha256'] or receipt.get('implementation_sha256') != release):
        raise ContractError('Model reference is not a completed result from the trusted training implementation.')
    claim = store._get(ledger + '/claim.json')
    if digest(claim) != receipt['claim_sha256']:
        raise ContractError('Training origin claim hash mismatch; nothing deserialized.')
    parsed_claim = baseline.read_json(claim)
    if parsed_claim != {'schema_version': 1, 'model_id': model_id, 'request': training,
                        'implementation_sha256': release, 'versions': baseline.versions()}:
        raise ContractError('Training origin claim differs; nothing deserialized.')
    hashes = receipt.get('artifact_sha256', {})
    if set(hashes) != set(contract.MODEL_FILES):
        raise ContractError('Trusted completion has an incomplete model bundle.')
    base = f'{store.prefix}/cloud-modeling/models/{model_id}'
    artifacts = {name: store._get(base + '/' + name) for name in contract.MODEL_FILES}
    if any(digest(b) != hashes[name] for name, b in artifacts.items()):
        raise ContractError('Published model hash mismatch; nothing deserialized.')
    metadata = verify_bundle(artifacts, model_id, training, release)
    if receipt != model_completion(training, model_id, token, release, claim, metadata, artifacts, base):
        raise ContractError('Trusted training receipt differs from the verified bundle; nothing deserialized.')
    model_dir = root / 'model'
    # Only allowlisted bytes, verified against a receipt in the trainer-only write domain.
    baseline.publish(model_dir, {n: artifacts[n] for n in contract.MODEL_FILES[:7]})
    model, metadata = baseline.load_trusted_model(model_dir, allow_retrospective_demo=True)
    return model, metadata, receipt, model_dir


def infer_run(event, store):
    stage, model_id = 'request_validation', None
    try:
        request = contract.validate(event, 'inference')
        model_id = request['model_id']
        stage = 'aws_preflight'
        store._private_bucket()
        with tempfile.TemporaryDirectory(prefix='fbs-model-infer-') as tmp:
            root = Path(tmp)
            stage = 'trusted_model_reload'
            model, metadata, receipt, model_dir = trusted_model(store, request, root)
            stage = 'inference'
            if request['mode'] == 'hypothetical':
                return predict.predict_vector(model, request['features']) | {'state': 'completed', 'model_id': model_id,
                    'training_receipt_sha256': request['training_receipt_sha256'], 'dataset_id': metadata['dataset_id']}
            stage = 'dataset_verification'
            verify_dataset(store, receipt['request'], root / 'dataset')
            stage = 'saved_sample_inference'
            output = root / 'predictions'
            report = predict.predict_saved_sample(model_dir, root / 'dataset', output, allow_retrospective_demo=True)
            if (output / 'predictions.csv').read_bytes() != (model_dir / 'sample_predictions.csv').read_bytes():
                raise ContractError('Reloaded saved predictions differ from the trained model sample.')
            artifacts = {n: (output / n).read_bytes() for n in ('predictions.csv', 'exclusions.json', 'prediction_report.json')}
            inference_id = digest(encode(request))
            base = f'{store.prefix}/cloud-modeling/inference/{inference_id}'
            result = {**STATUS, 'state': 'completed', 'inference_id': inference_id, 'model_id': model_id,
                      'dataset_id': metadata['dataset_id'], 'inference_prefix': base,
                      'request': request, 'count': report['count'], 'prediction_context': report['prediction_context'],
                      'artifact_sha256': {n: digest(b) for n, b in artifacts.items()}}
            complete = store._get(base + '/complete.json', optional=True)
            if complete is not None:
                if complete != encode(result) or any(store._get(base + '/' + n) != b for n, b in artifacts.items()):
                    raise ContractError('Completed inference output conflict; no repair allowed.')
                return result
            artifacts['complete.json'] = encode(result)
            store._upload(base, artifacts, 'complete.json')
            return result
    except Exception as exc:
        return failure(stage, exc, model_id)


def failure(stage, exc, model_id=None):
    return {**STATUS, 'state': 'failed', 'stage': stage, 'model_id': model_id,
            'error_type': type(exc).__name__,
            'message': str(exc) if isinstance(exc, ContractError) else 'Model operation stopped; details suppressed and existing evidence preserved.'}


def handler(event, context, mode):
    try:
        contract.validate(event, mode)
        approved = {field: contract.hex_id(os.environ.get(env)) for field, env in (
            ('dataset_id', 'APPROVED_DATASET_ID'), ('preparation_selection_id', 'APPROVED_PREPARATION_ID'),
            ('preparation_receipt_sha256', 'APPROVED_PREPARATION_SHA256'))}
        if mode == 'training' and any(event[k] != v for k, v in approved.items()):
            raise ContractError('Training request differs from this deployment approved preparation identity.')
        store = ModelingStore(None, os.environ.get('FBS_S3_BUCKET'), os.environ.get('FBS_S3_PREFIX'), approved)
        store.client = boto3.client('s3', config=CLIENT_CONFIG)
        return train_run(event, store) if mode == 'training' else infer_run(event, store)
    except Exception as exc:
        return failure('request_or_configuration', exc)


def training_handler(event, context):
    return handler(event, context, 'training')


def inference_handler(event, context):
    return handler(event, context, 'inference')
