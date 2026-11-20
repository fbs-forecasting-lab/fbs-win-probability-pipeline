"""Explicit weekly identities and technical eligibility, separate from publication approval."""

from datetime import datetime
from pathlib import Path
import re

from src.features import games
from src.pipeline import model_contract, preparation_contract
from src.pipeline.run_contract import ContractError, digest, encode

MAX_SCHEDULE_AGE_SECONDS = 86400


def instant(value):
    return datetime.fromisoformat(games._utc_timestamp(value).replace('Z', '+00:00'))


def validate(event):
    fields = {'schema_version', 'season', 'week', 'forecast_cutoff', 'run_token',
              'history_sources', 'model_reference', 'scoring_source', 'previous_run', 'allow_retrospective_demo'}
    if not isinstance(event, dict) or set(event) != fields:
        raise ContractError('Select the explicit weekly contract fields; no latest references.')
    if type(event['schema_version']) is not int or event['schema_version'] != 1 or event['allow_retrospective_demo'] is not True:
        raise ContractError('Weekly version 1 and retrospective-demo permission are required.')
    if type(event['season']) is not int or event['season'] != 2026:
        raise ContractError('The current fixed model and feature builder support scoring season 2026 only.')
    if type(event['week']) is not int or not 1 <= event['week'] <= 99:
        raise ContractError('Select a positive explicit week from 1 through 99.')
    if not isinstance(event['run_token'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,63}', event['run_token']):
        raise ContractError('Select a stable 8–64 character lowercase run token.')
    cutoff = games._utc_timestamp(event['forecast_cutoff'])
    model = event['model_reference']
    if not isinstance(model, dict) or set(model) != {'model_id', 'training_token_sha256', 'training_receipt_sha256'}:
        raise ContractError('Select the explicit trusted model and receipt identities.')
    model_contract.validate(dict(model, schema_version=1, allow_retrospective_demo=True, mode='saved_sample'), 'inference')
    scoring = event['scoring_source']
    if not isinstance(scoring, dict):
        raise ContractError('Select capture or reuse with explicit source identity.')
    dummy = {'season': 2026, 'manifest_name': '0'*32+'.manifest.json', 'raw_sha256': '0'*64,
             'manifest_sha256': '0'*64, 'capture_token_sha256': '0'*64, 'capture_receipt_sha256': '0'*64}
    if scoring.get('mode') == 'reuse' and set(scoring) == {'mode', 'source'}:
        dummy = scoring['source']
        if not isinstance(dummy, dict) or dummy.get('season') != 2026:
            raise ContractError('Reused scoring capture must belong to the requested season.')
    elif scoring.get('mode') == 'capture' and set(scoring) == {'mode', 'capture_token'}:
        from src.pipeline.run_contract import validate as capture_validate
        capture_validate({'schema_version': 1, 'season': 2026, 'week': event['week'], 'idempotency_token': scoring['capture_token']})
    else:
        raise ContractError('Capture requires a stable token; reuse requires an exact cloud source.')
    if not isinstance(event['history_sources'], list) or len(event['history_sources']) != 5:
        raise ContractError('Select exactly five full-season historical cloud captures, 2021–2025.')
    selection = preparation_contract.validate({'schema_version': 1, 'allow_retrospective_demo': True,
        'require_cloud_sources': True, 'sources': event['history_sources']+[dummy]})
    previous = event['previous_run']
    if previous is not None:
        if not isinstance(previous, dict) or set(previous) != {'run_token_sha256', 'summary_sha256'}:
            raise ContractError('A prior schedule comparison requires an explicit previous run and summary hash.')
        for value in previous.values(): model_contract.hex_id(value)
    return dict(event, forecast_cutoff=cutoff, history_sources=selection['sources'][:5])


def implementation_hash():
    root = Path(__file__).resolve().parents[2]
    names = ('src/pipeline/weekly_contract.py', 'src/pipeline/cloud_weekly.py',
             'src/pipeline/cloud_ingestion.py', 'src/pipeline/cloud_preparation.py',
             'src/pipeline/preparation_contract.py', 'src/ingestion/cfbd.py')
    return digest(encode({'model_implementation': model_contract.implementation_hash(),
        'source_sha256': {n: digest((root/n).read_bytes()) for n in names}}))


def identity(request):
    return digest(request['run_token'].encode()), digest(encode({'request': request, 'implementation': implementation_hash()}))


def row_reasons(row, source, history, cutoff, previous=None):
    """Scheduled chronology is technical evidence only, never historical availability proof."""
    deadline = instant(cutoff)
    reasons = []
    if row['completed'] is True or row['completed'] == 'true': reasons.append('completed')
    if row.get('start_time_tbd'): reasons.append('kickoff_tbd')
    if instant(row['cutoff']) <= deadline: reasons.append('scheduled_start_not_after_cutoff')
    for label, metadata in [('schedule', source), *[(str(y), s) for y, s in history.items()]]:
        observed = instant(metadata['retrieved_at'])
        if observed >= deadline: reasons.append(label+'_observed_at_or_after_cutoff')
        published = metadata.get('source_availability', {}).get('available_at')
        if published is not None and instant(published) >= deadline:
            reasons.append(label+'_published_at_or_after_cutoff')
        if label == 'schedule' and (deadline-observed).total_seconds() > MAX_SCHEDULE_AGE_SECONDS:
            reasons.append('stale_schedule_observation')
    if previous is not None:
        if instant(previous['cutoff']) <= deadline: reasons.append('previous_schedule_started_before_cutoff')
        if any(row[k] != previous[k] for k in ('home_id', 'away_id')): reasons.append('revised_matchup_identity')
    return reasons


def publication_status():
    # Capture time is never substituted for a verified historical publication time.
    return {'operational_forecast_approved': False, 'publication_status': 'withheld',
            'withheld_reasons': ['historical_publication_and_schedule_revision_evidence_unverified',
                                 'saved_model_is_retrospective_and_unapproved']}
