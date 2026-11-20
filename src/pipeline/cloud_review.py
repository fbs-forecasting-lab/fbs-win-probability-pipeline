"""Private append-only human-review records; no forecast/training approval actions."""

import json
import os

import boto3
from botocore.config import Config

from src.pipeline.monitor_contract import validate_review
from src.pipeline.monitor_storage import MonitorStore, verified_object
from src.pipeline.cloud_ingestion import create_once
from src.pipeline.run_contract import ContractError, STATUS, digest, encode


def review_run(event, store, approved_reviewer):
    try:
        request = validate_review(event)
        if request['reviewer'] != approved_reviewer: raise ContractError('Reviewer differs from configured authorized review identity.')
        store._private_bucket()
        base = store.prefix+'/monitoring/alerts/'+request['alert_id']
        alert = json.loads(verified_object(store,base+'/alert.json',request['alert_sha256']))
        if alert['alert_id'] != request['alert_id']: raise ContractError('Alert identity differs.')
        if alert['simulated'] != request['simulation']:raise ContractError('Simulated reviews cannot dispose of genuine alerts.')
        previous = None
        if request['previous_sequence']:
            previous = json.loads(verified_object(store,base+'/reviews/'+str(request['previous_sequence']).zfill(3)+'.json',request['previous_sha256']))
            if previous['alert_id'] != request['alert_id'] or previous['sequence'] != request['previous_sequence']:
                raise ContractError('Review predecessor identity differs.')
        old = previous['action'] if previous else None
        allowed = {None:('acknowledged',),'acknowledged':('investigating',),'investigating':('closed',),'closed':()}
        if request['action'] not in allowed[old]: raise ContractError('Invalid review transition; acknowledgment is not disposition or approval.')
        if request['action']=='closed' and request['reason'] not in ('confirmed_issue','false_positive','expected_withholding','followup_needed'):
            raise ContractError('Closing a review requires an explicit disposition reason.')
        from datetime import datetime
        instant = datetime.fromisoformat
        if previous and instant(request['timestamp']) <= instant(previous['timestamp']): raise ContractError('Review timestamps must increase.')
        if alert['evidence'].get('as_of') and instant(request['timestamp']) < instant(alert['evidence']['as_of']):
            raise ContractError('Review timestamp precedes the selected alert observation.')
        claim_key = store.prefix+'/monitoring/review-tokens/'+digest(request['transition_token'].encode())+'/claim.json'
        claim = encode(request);existing = store._get(claim_key,optional=True)
        if existing is None: create_once(store,claim_key,claim)
        if store._get(claim_key) != claim: raise ContractError('Review token conflicts with another transition.')
        result = dict(STATUS, schema_version=1,sequence=request['previous_sequence']+1,alert_id=request['alert_id'],
            action=request['action'],reviewer=request['reviewer'],timestamp=request['timestamp'],reason=request['reason'],
            simulation=request['simulation'],
            evidence_hashes=request['evidence_hashes'],previous_sha256=request['previous_sha256'],request_sha256=digest(claim),
            identity_attestation='Asserted by the private IAM invoker; handler does not authenticate a human identity.',
            evidence_verification='Hashes recorded; external investigation evidence must be retained privately.',
            retraining_authorized=False,operational_publication_authorized=False)
        key = base+'/reviews/'+str(result['sequence']).zfill(3)+'.json';data = encode(result)
        existing = store._get(key,optional=True)
        if existing is None: store._put(key,data)
        elif existing != data: raise ContractError('Concurrent review transition conflict; no history overwritten.')
        return dict(result,state='completed',sha256=digest(data))
    except Exception as exc:
        return dict(STATUS,state='failed',stage='human_review',error_type=type(exc).__name__,
                    message=str(exc) if isinstance(exc,ContractError) else 'Review stopped; existing records preserved.')


def handler(event,context):
    try:
        validate_review(event)
        config=Config(connect_timeout=5,read_timeout=30,retries={'total_max_attempts':1})
        store=MonitorStore(boto3.client('s3',config=config),os.environ['FBS_S3_BUCKET'],os.environ['FBS_S3_PREFIX'])
        result=review_run(event,store,os.environ['APPROVED_REVIEWER'])
        if result['state']=='failed':raise ContractError('Review failed; no review history overwritten.')
        return result
    except Exception as exc:
        raise RuntimeError('Human review failed or request/configuration rejected; no approval granted.') from None
