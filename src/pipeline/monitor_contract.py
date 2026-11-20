"""Explicit monitoring/review contracts; no approval or training operation exists."""

from pathlib import Path
import re

from src.features.games import _utc_timestamp
from src.pipeline.model_contract import hex_id
from src.pipeline.run_contract import ContractError, digest, encode

POLICY = {'version': 'monitor-policy-v1', 'minimum_distribution_rows': 30, 'minimum_labels': 30,
          'minimum_outcome_coverage': 0.8, 'quarantine_rate': 0.10, 'exclusion_rate': 0.20,
          'missing_history_rate': 0.05, 'maximum_age_seconds': 86400,
          'numeric_psi': 0.20, 'binary_rate_difference': 0.15,
          'brier_increase': 0.05, 'log_loss_increase': 0.10}


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,63}', value):
        raise ContractError('Select a stable lowercase 8–64 character token.')
    return value


def weekly_reference(value):
    if not isinstance(value, dict) or set(value) != {'run_token_sha256', 'summary_sha256'}:
        raise ContractError('Select an explicit weekly run and exact summary hash.')
    for item in value.values(): hex_id(item)


def validate_report(event):
    required = {'operation', 'schema_version', 'run_token', 'weekly_reference', 'model_reference',
                'outcome_sources', 'as_of', 'windows', 'review_reference', 'allow_retrospective_demo', 'evidence_mode'}
    if not isinstance(event, dict) or set(event) != required or event['operation'] != 'report':
        raise ContractError('Expected only explicit monitoring report fields.')
    if type(event['schema_version']) is not int or event['schema_version'] != 1 or event['allow_retrospective_demo'] is not True:
        raise ContractError('Version one and retrospective permission are required.')
    token(event['run_token']); weekly_reference(event['weekly_reference'])
    if event['evidence_mode'] not in ('saved_retrospective', 'synthetic_test'):
        raise ContractError('Select saved_retrospective or explicitly synthetic_test evidence.')
    model = event['model_reference']
    if not isinstance(model, dict) or set(model) != {'model_id', 'training_token_sha256', 'training_receipt_sha256'}:
        raise ContractError('Select the explicit protected model reference.')
    for value in model.values(): hex_id(value)
    sources = event['outcome_sources']
    if not isinstance(sources, list) or len(sources) > 10:
        raise ContractError('Select zero to ten explicit later outcome captures.')
    seen = set()
    for source in sources:
        fields = {'season', 'manifest_name', 'raw_sha256', 'manifest_sha256', 'capture_token_sha256', 'capture_receipt_sha256'}
        if not isinstance(source, dict) or set(source) != fields or type(source['season']) is not int or source['season'] != 2026:
            raise ContractError('Outcome references must identify cloud captures for season 2026.')
        if not re.fullmatch(r'[0-9a-f]{32}\.manifest\.json', source.get('manifest_name', '')):
            raise ContractError('Outcome manifest must be a fixed snapshot filename.')
        for k in fields-{'season', 'manifest_name'}: hex_id(source[k])
        if source['manifest_sha256'] in seen: raise ContractError('Duplicate outcome source.')
        seen.add(source['manifest_sha256'])
    as_of = _utc_timestamp(event['as_of'])
    windows = event['windows']
    if not isinstance(windows, list) or not 1 <= len(windows) <= 12:
        raise ContractError('Select one to twelve chronological nonoverlapping windows.')
    result_windows, previous = [], None
    for window in windows:
        if not isinstance(window, dict) or set(window) != {'start', 'end'}:
            raise ContractError('Each window requires start and end timestamps.')
        start, end = _utc_timestamp(window['start']), _utc_timestamp(window['end'])
        from datetime import datetime
        if not datetime.fromisoformat(start) < datetime.fromisoformat(end) <= datetime.fromisoformat(as_of):
            raise ContractError('Window start must precede end, and end must not follow as_of.')
        if previous is not None and datetime.fromisoformat(start) < datetime.fromisoformat(previous):
            raise ContractError('Performance windows must be ordered and nonoverlapping.')
        result_windows.append({'start': start, 'end': end}); previous = end
    review = event['review_reference']
    if review is not None:
        if not isinstance(review, dict) or set(review) != {'alert_id', 'sequence', 'sha256'}:
            raise ContractError('Review display needs an explicit transition reference.')
        hex_id(review['alert_id']); hex_id(review['sha256'])
        if type(review['sequence']) is not int or not 1 <= review['sequence'] <= 100:
            raise ContractError('Invalid review sequence.')
    return dict(event, as_of=as_of, windows=result_windows, outcome_sources=sorted(sources, key=lambda s:s['manifest_sha256']))


def validate_review(event):
    fields = {'operation', 'schema_version', 'transition_token', 'alert_id', 'alert_sha256', 'previous_sequence',
              'previous_sha256', 'action', 'reviewer', 'timestamp', 'reason', 'evidence_hashes', 'simulation'}
    if not isinstance(event, dict) or set(event) != fields or event['operation'] != 'review' or type(event['schema_version']) is not int or event['schema_version'] != 1:
        raise ContractError('Expected explicit version-one human review fields.')
    token(event['transition_token']); hex_id(event['alert_id']); hex_id(event['alert_sha256'])
    if type(event['simulation']) is not bool:raise ContractError('Review simulation status must be explicit.')
    sequence = event['previous_sequence']
    if type(sequence) is not int or not 0 <= sequence < 100:
        raise ContractError('Review sequence must be 0–99.')
    if sequence == 0:
        if event['previous_sha256'] is not None: raise ContractError('Initial review has no previous hash.')
    else: hex_id(event['previous_sha256'])
    if event['action'] not in ('acknowledged', 'investigating', 'closed'):
        raise ContractError('Unknown review action; no training or forecast approval action exists.')
    if not isinstance(event['reviewer'], str) or not 2 <= len(event['reviewer']) <= 120 or any(ord(c)<32 for c in event['reviewer']):
        raise ContractError('An explicit reviewer identity is required.')
    if event['reason'] not in ('investigation_requested', 'evidence_checked', 'followup_needed', 'expected_withholding', 'confirmed_issue', 'false_positive'):
        raise ContractError('Select a structured investigation/disposition reason.')
    if not isinstance(event['evidence_hashes'], list) or not 1 <= len(event['evidence_hashes']) <= 20:
        raise ContractError('Record one to twenty private evidence hashes.')
    for value in event['evidence_hashes']: hex_id(value)
    return dict(event, timestamp=_utc_timestamp(event['timestamp']))


def implementation_hash():
    root = Path(__file__).resolve().parents[2]
    names = ('monitor_contract', 'monitoring_metrics', 'monitor_storage', 'monitoring_view', 'cloud_monitoring', 'cloud_review')
    return digest(encode({n:digest((root/'src/pipeline'/f'{n}.py').read_bytes()) for n in names}))
