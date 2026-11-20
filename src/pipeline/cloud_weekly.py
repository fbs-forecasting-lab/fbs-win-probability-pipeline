"""One bounded cloud workflow; immutable weekly scoring, never training or Athena queries."""

import json
import os
from pathlib import Path
import tempfile

import boto3
from botocore.config import Config

from src.features import dataset, games
from src.ingestion.s3_storage import S3Store
from src.models import baseline
from src.pipeline import cloud_modeling, weekly_contract as contract
from src.pipeline.cloud_ingestion import create_once
from src.pipeline.cloud_preparation import verify_origin
from src.pipeline.run_contract import ContractError, STATUS, digest, encode

CLIENT_CONFIG = Config(connect_timeout=5, read_timeout=250, retries={'mode': 'standard', 'total_max_attempts': 1})


class WeeklyStore(cloud_modeling.ModelingStore):
    def _get(self, key, *, optional=False):
        allowed = tuple(f'{self.prefix}/{p}/' for p in ('weekly', 'cloud-ingestion/runs', 'raw/cfbd/games',
                                                     'cloud-modeling', 'cloud-preparation/runs', 'datasets'))
        if not isinstance(key, str) or not key.startswith(allowed):
            raise ContractError('Weekly read is outside approved project domains.')
        if optional:
            result = self.client.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
            if not any(item.get('Key') == key for item in result.get('Contents', [])): return None
        return S3Store._get(self, key, optional=False)


def checked_stage(store, base):
    content = store._get(base+'/complete.json', optional=True)
    if content is None: return None
    result = baseline.read_json(content)
    baseline.check_status(result)
    for key, expected in result['artifact_sha256'].items():
        if digest(store._get(key)) != expected:
            raise ContractError('Completed weekly stage artifact failed verification; no repair allowed.')
    return result


def publish_stage(store, base, artifacts, facts):
    complete = dict(facts, **STATUS, state='completed', stage=base.rsplit('/', 1)[-1],
                    artifact_sha256={base+'/'+n: digest(b) for n, b in artifacts.items()})
    artifacts = dict(artifacts, **{'complete.json': encode(complete)})
    store._upload(base, artifacts, 'complete.json')
    return complete


def scoring_reference(request, store, base, invoke_capture):
    if request['scoring_source']['mode'] == 'reuse': return request['scoring_source']['source']
    token = request['scoring_source']['capture_token']
    token_hash = digest(token.encode())
    capture_base = store.prefix+'/cloud-ingestion/runs/'+token_hash
    receipt = store._get(capture_base+'/complete.json', optional=True)
    if receipt is None:
        event = {'schema_version': 1, 'season': request['season'], 'week': request['week'], 'idempotency_token': token}
        intent = encode({'event': event})
        owned = create_once(store, base+'/capture-intent.json', intent)
        if store._get(base+'/capture-intent.json') != intent:
            raise ContractError('Weekly capture intent conflicts; no invocation allowed.')
        if owned:
            result = invoke_capture(event) # exclusive owner; ambiguous responses must never be retried
            if result.get('state') == 'failed': raise ContractError('Cloud capture failed; preserve its existing token.')
        failure = store._get(capture_base+'/failure.json', optional=True)
        if failure is not None: raise ContractError('Cloud capture failed; do not refetch.')
        receipt = store._get(capture_base+'/complete.json', optional=True)
        if receipt is None: return None
    completed = baseline.read_json(receipt)
    return {'season': request['season'], 'manifest_name': completed['manifest_key'].rsplit('/', 1)[1],
            'raw_sha256': completed['raw_sha256'], 'manifest_sha256': completed['manifest_sha256'],
            'capture_token_sha256': token_hash, 'capture_receipt_sha256': digest(receipt)}


def prepare_week(request, reference, store, directory):
    """Reuse existing normalization/building; no change to recovery-only preparation."""
    paths, sources, origins, artifacts, source_hashes = [], {}, {}, {}, {}
    for ref in request['history_sources']+[reference]:
        year = ref['season']
        path = store.download_raw(year, ref['manifest_name'], directory/'raw'/str(year))
        snapshot = games.load_snapshot(path); source = snapshot.source
        if any(source[k] != ref[k] for k in ('raw_sha256', 'manifest_sha256')):
            raise ContractError('Weekly source hash mismatch.')
        params = source['request_parameters']
        if year < 2026 and 'week' in params: raise ContractError('Weekly history must be full-season captures.')
        if year == 2026 and params.get('week') != request['week']:
            raise ContractError('Selected scoring capture does not match the explicitly requested week.')
        origins[str(year)] = verify_origin(store, ref, source, (path.parent/source['raw_file']).read_bytes(), path.read_bytes())
        source_base = store.prefix+'/raw/cfbd/games/season='+str(year)
        source_hashes[source_base+'/'+source['raw_file']] = source['raw_sha256']
        source_hashes[source_base+'/'+path.name] = source['manifest_sha256']
        capture_base = store.prefix+'/cloud-ingestion/runs/'+ref['capture_token_sha256']
        source_hashes[capture_base+'/complete.json'] = ref['capture_receipt_sha256']
        source_hashes[capture_base+'/capture.json'] = digest(store._get(capture_base+'/capture.json'))
        paths.append(path); sources[year] = source
        normalized = games.normalize_snapshot(path, directory/'normalized')
        for name in ('games.csv', 'exclusions.json', 'quality_report.json'):
            artifacts[f'normalized/{year}/{name}'] = (normalized/name).read_bytes()
    report = dataset.build_dataset(paths, directory/'dataset', normalized_root=directory/'normalized', allow_retrospective_demo=True)
    inputs = dataset._load_inputs(paths, directory/'normalized')
    data = baseline.load_dataset(directory/'dataset', allow_retrospective_demo=True)
    prior = {}
    if request['previous_run'] is not None:
        r = request['previous_run']; previous_base = store.prefix+'/weekly/runs/'+r['run_token_sha256']
        raw = store._get(previous_base+'/complete.json')
        if digest(raw) != r['summary_sha256']: raise ContractError('Previous schedule summary hash mismatch.')
        previous = checked_stage(store, previous_base)
        if previous['request']['season'] != request['season'] or previous['request']['week'] != request['week']:
            raise ContractError('Previous schedule must refer to this same season/week.')
        source_hashes[previous_base+'/complete.json'] = r['summary_sha256']
        source_hashes.update(previous['artifact_sha256'])
        prior = {r['game_id']: r for r in baseline.read_json(store._get(previous_base+'/preparation/schedule.json'))['rows']}
    rows, rejected = [], []
    aggregates, _ = dataset._aggregate(inputs)
    for row in data['splits']['prediction']['rows']:
        reasons = contract.row_reasons(row, sources[2026], {y: sources[y] for y in range(2021, 2026)},
                                       request['forecast_cutoff'], prior.get(row['game_id']))
        for side in ('home', 'away'):
            history = aggregates.get((2025, int(row[side+'_id'])))
            if history is None or contract.instant(history['latest_scheduled_start']) >= contract.instant(request['forecast_cutoff']):
                reasons.append(side+'_history_not_before_forecast_cutoff')
        if reasons: rejected.append(dict(row, reasons=reasons))
        else: rows.append(row)
    exclusions = baseline.read_json((directory/'dataset/exclusions.json').read_bytes())
    rejected.extend(r for r in exclusions['rows'] if r['split'] == 'prediction')
    for name in ('train.csv', 'holdout.csv', 'prediction.csv', 'team_season_aggregates.csv', 'dataset_report.json', 'exclusions.json'):
        artifacts['dataset/'+name] = (directory/'dataset'/name).read_bytes()
    artifacts['rows.json'] = encode({'rows': rows})
    artifacts['schedule.json'] = encode({'rows': [{'game_id': str(r['id']), 'cutoff': r['start_date'],
        'home_id': str(r['home_id']), 'away_id': str(r['away_id'])} for r in inputs[2026].rows]})
    artifacts['eligibility.json'] = encode(dict(STATUS, eligible=len(rows), rejected=rejected,
        normalization=baseline.read_json(artifacts['normalized/2026/exclusions.json']),
        forecast_cutoff=request['forecast_cutoff'], **contract.publication_status()))
    artifacts['provenance.json'] = encode(dict(STATUS, sources=report['sources'], cloud_origins=origins,
        scoring_dataset_id=report['dataset_id'], forecast_cutoff=request['forecast_cutoff'],
        predictor_columns=baseline.PREDICTORS, model_reference=request['model_reference']))
    return artifacts, {'eligible_rows': len(rows), 'dataset_id': report['dataset_id'], 'reference': reference,
                       'source_artifact_sha256': source_hashes}


def score_week(request, prepared, store, root, base):
    """New scoring contract, leaving predict_saved_sample's exact-dataset contract intact."""
    model_request = dict(request['model_reference'], schema_version=1, allow_retrospective_demo=True, mode='saved_sample')
    model, metadata, receipt, _ = cloud_modeling.trusted_model(store, model_request, root)
    for name in ('train.csv', 'holdout.csv', 'team_season_aggregates.csv'):
        if digest(store._get(base+'/preparation/dataset/'+name)) != metadata['dataset_artifact_sha256'][name]:
            raise ContractError('Weekly scoring changed the model training/holdout/history evidence.')
    rows = baseline.read_json(store._get(base+'/preparation/rows.json'))['rows']
    x = baseline.feature_frame(rows)
    probabilities = baseline.home_probabilities(model, x)
    context = 'weekly_retrospective_scoring_operational_publication_withheld'
    artifacts = {'predictions.csv': baseline.prediction_csv(rows, probabilities, context)}
    artifacts['provenance.json'] = encode(dict(STATUS, model_reference=request['model_reference'],
        model_training_dataset_id=metadata['dataset_id'], scoring_dataset_id=prepared['dataset_id'],
        preparation_receipt_sha256=digest(store._get(base+'/preparation/complete.json')),
        forecast_cutoff=request['forecast_cutoff'], predictor_columns=baseline.PREDICTORS,
        prediction_context=context, **contract.publication_status()))
    model_hashes = {receipt['model_prefix']+'/'+n: h for n, h in receipt['artifact_sha256'].items()}
    ledger = store.prefix+'/cloud-modeling/training/'+request['model_reference']['training_token_sha256']
    model_hashes[ledger+'/complete.json'] = request['model_reference']['training_receipt_sha256']
    model_hashes[ledger+'/claim.json'] = receipt['claim_sha256']
    return artifacts, {'count': len(rows), 'model_training_dataset_id': metadata['dataset_id'],
                       'scoring_dataset_id': prepared['dataset_id'], 'model_artifact_sha256': model_hashes}


def advance(event, store, invoke_capture):
    stage, base = 'request_validation', None
    try:
        request = contract.validate(event)
        token, run_id = contract.identity(request)
        base = store.prefix+'/weekly/runs/'+token
        stage = 'aws_preflight'; store._private_bucket()
        stage = 'run_claim'
        claim = encode({'request': request, 'run_id': run_id, 'implementation_sha256': contract.implementation_hash()})
        if store._get(base+'/claim.json', optional=True) is None:
            create_once(store, base+'/claim.json', claim)
        if store._get(base+'/claim.json') != claim: raise ContractError('Weekly token conflicts with existing request or implementation.')
        stage = 'completed_replay'
        completed = checked_stage(store, base)
        if completed is not None:
            if completed['request'] != request or completed['run_id'] != run_id: raise ContractError('Weekly completion identity conflict.')
            return completed
        stage = 'ingestion'
        ingested = checked_stage(store, base+'/ingestion')
        if ingested is None:
            reference = scoring_reference(request, store, base, invoke_capture)
            if reference is None: return dict(STATUS, state='pending', pending_stage='ingestion', run_id=run_id)
            publish_stage(store, base+'/ingestion', {'reference.json': encode(reference)}, {'reference': reference})
            return dict(STATUS, state='pending', pending_stage='preparation', run_id=run_id)
        stage = 'preparation'
        prepared = checked_stage(store, base+'/preparation')
        if prepared is None:
            with tempfile.TemporaryDirectory(prefix='weekly-prepare-') as temp:
                artifacts, facts = prepare_week(request, ingested['reference'], store, Path(temp))
            publish_stage(store, base+'/preparation', artifacts, facts)
            return dict(STATUS, state='pending', pending_stage='inference', run_id=run_id)
        stage = 'inference'
        inferred = checked_stage(store, base+'/inference')
        if inferred is None:
            with tempfile.TemporaryDirectory(prefix='weekly-infer-') as temp:
                artifacts, facts = score_week(request, prepared, store, Path(temp), base)
            publish_stage(store, base+'/inference', artifacts, facts)
            return dict(STATUS, state='pending', pending_stage='summary', run_id=run_id)
        stage = 'verified_summary'
        if inferred['count'] != prepared['eligible_rows']:
            raise ContractError('Weekly prediction count differs from technical eligibility.')
        hashes = {}
        for part in ('ingestion', 'preparation', 'inference'):
            receipt = checked_stage(store, base+'/'+part)
            hashes.update(receipt['artifact_sha256']); hashes[base+'/'+part+'/complete.json'] = digest(store._get(base+'/'+part+'/complete.json'))
        hashes.update(prepared['source_artifact_sha256']); hashes.update(inferred['model_artifact_sha256'])
        for key, expected in hashes.items():
            if digest(store._get(key)) != expected: raise ContractError('Weekly summary provenance hash mismatch.')
        result = dict(STATUS, state='withheld', workflow_completed=True, request=request, run_id=run_id,
            technical_eligible_rows=prepared['eligible_rows'], prediction_count=inferred['count'],
            model_reference=request['model_reference'], scoring_dataset_id=prepared['dataset_id'],
            artifact_sha256=hashes, **contract.publication_status())
        store._put(base+'/complete.json', encode(result))
        return result
    except Exception as exc:
        result = dict(STATUS, state='failed', stage=stage, error_type=type(exc).__name__,
            message=str(exc) if isinstance(exc, ContractError) else 'Weekly workflow stopped; existing evidence preserved.')
        if base is not None:
            try: store._put(base+'/failures/'+digest(encode(result))+'.json', encode(result))
            except Exception: pass
        return result


def handler(event, context):
    try:
        request = contract.validate(event)
        approved_model = json.loads(os.environ['APPROVED_MODEL_REFERENCE'])
        if request['model_reference'] != approved_model: raise ContractError('Model reference differs from the approved weekly deployment.')
        approved_training = json.loads(os.environ['APPROVED_TRAINING_REFERENCE'])
        if not isinstance(approved_training, dict) or set(approved_training) != {'dataset_id', 'preparation_selection_id', 'preparation_receipt_sha256'}:
            raise ContractError('Configure the exact original model preparation binding.')
        from src.pipeline.model_contract import hex_id
        for value in approved_training.values(): hex_id(value)
        store = WeeklyStore(boto3.client('s3', config=CLIENT_CONFIG), os.environ['FBS_S3_BUCKET'], os.environ['FBS_S3_PREFIX'], approved_training)
        def invoke_capture(payload):
            client = boto3.client('lambda', config=CLIENT_CONFIG)
            result = client.invoke(FunctionName=os.environ['INGESTION_FUNCTION_ARN'], InvocationType='RequestResponse', Payload=encode(payload))
            try: body = result['Payload'].read()
            finally: result['Payload'].close()
            if result.get('FunctionError') or result.get('StatusCode') != 200: raise ContractError('Capture invocation failed or is ambiguous; do not retry it.')
            return baseline.read_json(body)
        return advance(request, store, invoke_capture)
    except Exception as exc:
        return dict(STATUS, state='failed', stage='request_or_configuration', error_type=type(exc).__name__, message='Invalid weekly request/configuration; no stage started.')
