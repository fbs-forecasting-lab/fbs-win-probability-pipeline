"""Explicit references and immutable training identities; no arbitrary model input."""

import math
from pathlib import Path
import re

from src.pipeline.run_contract import ContractError, digest, encode

MODEL_FILES = ('model.joblib', 'evaluation.json', 'calibration.json', 'holdout_predictions.csv',
               'sample_predictions.csv', 'exclusions.json', 'model_metadata.json',
               'interpretation.json', 'training_provenance.json')
PREDICTORS = ('prior_win_pct_diff', 'prior_avg_margin_diff', 'home_field')


def hex_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ContractError('Expected an explicit lowercase SHA-256 identity, not a URL or path.')
    return value


def validate(event, mode):
    common = {'schema_version', 'allow_retrospective_demo'}
    fields = (common | {'training_token', 'dataset_id', 'preparation_selection_id', 'preparation_receipt_sha256'}
              if mode == 'training' else common | {'model_id', 'training_token_sha256', 'training_receipt_sha256', 'mode'})
    if mode != 'training' and isinstance(event, dict) and event.get('mode') == 'hypothetical':
        fields |= {'features'}
    if not isinstance(event, dict) or set(event) != fields:
        raise ContractError('Expected only the explicit versioned training or inference fields.')
    if type(event['schema_version']) is not int or event['schema_version'] != 1 or event['allow_retrospective_demo'] is not True:
        raise ContractError('Version 1 and explicit retrospective-demo permission are required.')
    if mode == 'training':
        if not isinstance(event['training_token'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,63}', event['training_token']):
            raise ContractError('Training token must contain 8–64 lowercase letters, digits or hyphens.')
        for name in ('dataset_id', 'preparation_selection_id', 'preparation_receipt_sha256'):
            hex_id(event[name])
    else:
        for name in ('model_id', 'training_token_sha256', 'training_receipt_sha256'):
            hex_id(event[name])
        if event['mode'] not in ('saved_sample', 'hypothetical'):
            raise ContractError('Select saved_sample or hypothetical inference.')
        if event['mode'] == 'hypothetical':
            values = event['features']
            if not isinstance(values, dict) or set(values) != set(PREDICTORS):
                raise ContractError('Hypothetical input requires exactly the three predictors.')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in values.values()):
                raise ContractError('Hypothetical predictors must be finite numeric values, not booleans or strings.')
            if not -1 <= values['prior_win_pct_diff'] <= 1 or values['home_field'] not in (0, 1):
                raise ContractError('Hypothetical feature domain is invalid.')
    # Canonical feature order is fixed even when JSON keys arrive sorted/reordered.
    result = dict(event)
    if 'features' in result:
        result['features'] = {name: result['features'][name] for name in PREDICTORS}
    return result


def implementation_hash():
    root = Path(__file__).resolve().parents[2]
    names = ('src/pipeline/model_contract.py', 'src/pipeline/cloud_modeling.py',
             'src/models/baseline.py', 'src/models/predict.py', 'src/evaluation/metrics.py',
             'src/features/dataset.py', 'src/features/games.py', 'src/ingestion/s3_storage.py',
             'src/ingestion/storage.py', 'src/pipeline/run_contract.py')
    return digest(encode({name: digest((root / name).read_bytes()) for name in names}))


def identities(request):
    release = implementation_hash()
    return digest(request['training_token'].encode()), digest(encode({'request': request, 'implementation_sha256': release})), release
