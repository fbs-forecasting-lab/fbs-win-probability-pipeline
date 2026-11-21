"""Bounded moneyline capture and verified saved-probability benchmarking; never score/train."""
import base64
import json
import os
from datetime import datetime
import boto3
from botocore.config import Config

from src.ingestion import odds
from src.features import markets
from src.pipeline import insights_contract as contract,cloud_monitoring
from src.pipeline.insights_storage import InsightsStore,claim,external_once,replay,publish,verified_object
from src.pipeline.run_contract import ContractError,STATUS,digest,encode

CONFIG=Config(connect_timeout=5,read_timeout=20,retries={'total_max_attempts':1})

def capture(request,store,get_key,fetch=odds.fetch_moneylines):
    base=store.prefix+'/stakeholder/market-captures/'+digest(request['run_token'].encode())
    identity={'request':request,'implementation_sha256':contract.implementation_hash(),'provider':'The Odds API','endpoint':odds.ENDPOINT,'request_parameters':odds.parameters(request),'attempts':1}
    claimed=claim(store,base,identity);old=replay(store,base,request)
    if old is not None:return old
    def call():
        try:
            key=get_key();odds.validate_key(key)
        except Exception as exc:return {'state':'unavailable','reason':'market_access_failed','http_attempts':0,'error_type':type(exc).__name__}
        try:
            response=fetch(request,key)
            return {'state':'received','http_attempts':1,'raw_base64':base64.b64encode(response.raw).decode(),'manifest':odds.manifest(response)}
        except Exception as exc:return {'state':'unavailable','reason':'market_capture_failed','http_attempts':1,'error_type':type(exc).__name__}
    response=external_once(store,base,claimed,call)
    if response is None:return dict(STATUS,state='attempt_unresolved',market_state='unavailable',message='Original market attempt may have occurred; no retry.')
    if response['state']!='received':
        return publish(store,base,{'capture_status.json':encode(response)},dict(STATUS,state='completed',request=request,market_state='unavailable',attempt_slots_consumed=1,http_attempts=response['http_attempts']))
    raw=base64.b64decode(response['raw_base64'],validate=True);manifest=response['manifest']
    rows,quality=markets.normalize(raw,manifest)
    artifacts={'raw.json':raw,'manifest.json':encode(manifest),'markets.json':encode(rows),'quality.json':encode(quality)}
    return publish(store,base,artifacts,dict(STATUS,state='completed',request=request,market_state='captured',attempt_slots_consumed=1,http_attempts=1,
        raw_sha256=digest(raw),record_count=manifest['record_count'],retained_markets=len(rows),operational_forecast_approved=False))

def market_input(store,reference):
    base=store.prefix+'/stakeholder/market-captures/'+reference['run_token_sha256']
    raw=verified_object(store,base+'/complete.json',reference['completion_sha256']);receipt=json.loads(raw)
    for k,v in STATUS.items():
        if receipt.get(k)!=v:raise ContractError('Market receipt flags differ.')
    if receipt['state']!='completed' or receipt['market_state']!='captured' or digest(receipt['request']['run_token'].encode())!=reference['run_token_sha256']:raise ContractError('Market capture is not a verified completed source.')
    expected={base+'/'+n for n in ('raw.json','manifest.json','markets.json','quality.json')}
    if set(receipt['artifact_sha256'])!=expected:raise ContractError('Market capture artifact set differs.')
    artifacts={k.rsplit('/',1)[-1]:verified_object(store,k,h) for k,h in receipt['artifact_sha256'].items()}
    request=contract.validate(receipt['request'])
    claim_value={'request':request,'implementation_sha256':contract.implementation_hash(),'provider':'The Odds API','endpoint':odds.ENDPOINT,'request_parameters':odds.parameters(request),'attempts':1}
    if store._get(base+'/claim.json')!=encode(claim_value):raise ContractError('Market producer claim differs.')
    manifest=json.loads(artifacts['manifest.json'])
    if manifest['request_parameters']!=odds.parameters(request):raise ContractError('Market request parameters differ.')
    rows,quality=markets.normalize(artifacts['raw.json'],manifest)
    if artifacts['markets.json']!=encode(rows) or artifacts['quality.json']!=encode(quality) or receipt['raw_sha256']!=digest(artifacts['raw.json']):raise ContractError('Market normalization verification failed.')
    return rows,manifest,quality

def benchmark(request,store):
    base=store.prefix+'/stakeholder/benchmarks/'+digest(request['run_token'].encode())
    identity={'request':request,'implementation_sha256':contract.implementation_hash(),'bookmaker':contract.BOOKMAKER}
    claim(store,base,identity);old=replay(store,base,request)
    data=cloud_monitoring.inputs(store,request)
    rows,manifest,quality=market_input(store,request['market_reference'])
    key=store.prefix+'/weekly/runs/'+request['weekly_reference']['run_token_sha256']+'/inference/predictions.csv'
    metadata=store.client.head_object(Bucket=store.bucket,Key=key)
    observed=metadata.get('LastModified')
    if not isinstance(observed,datetime) or observed.tzinfo is None:raise ContractError('Trusted model observation time is unavailable.')
    cutoff=data['weekly']['request']['forecast_cutoff']
    outcomes,lineage=cloud_monitoring.later_outcomes(store,request,data['source'],cutoff)
    report=markets.compare(data['predictions'],rows,request['event_map'],request['bookmaker'],cutoff,observed.isoformat(),manifest['retrieved_at'],request['as_of'],request['windows'],outcomes)
    report=dict(STATUS,**report,request=request,model_observed_at=observed.isoformat(),market_manifest=manifest,market_quality=quality,outcome_lineage=lineage,operational_forecast_approved=False)
    public={'state':report['state'],'model_games':report['model_games'],'shared_games':report['shared_games'],'coverage':report['market_coverage'],
            'performance_state':report['paired_performance']['state'],'operational_forecast_approved':False,
            'limitation':'Retrospective/unapproved; missing markets or outcomes are gaps, not model superiority.'}
    artifacts={'benchmark.json':encode(report),'stakeholder.json':encode(public)}
    facts=dict(STATUS,state='completed',request=request,benchmark_state=report['state'],shared_games=report['shared_games'],operational_forecast_approved=False)
    if old is not None:
        if old!=dict(facts,artifact_sha256={base+'/'+n:digest(v) for n,v in artifacts.items()}):raise ContractError('Completed benchmark differs; no repair.')
        return old
    return publish(store,base,artifacts,facts)

def run(event,store,*,get_key=None,fetch=odds.fetch_moneylines):
    stage='request_validation'
    try:
        request=contract.validate(event)
        if request['operation']=='capture_market':
            if get_key is None:return dict(STATUS,state='unavailable',stage='access_refusal',provider_attempts=0,message='Market credential is not configured; no request made.')
            stage='market_capture';return capture(request,store,get_key,fetch)
        if request['operation']!='benchmark':raise ContractError('Wrong benchmark operation.')
        stage='benchmark_verification';return benchmark(request,store)
    except Exception as exc:return dict(STATUS,state='failed',stage=stage,error_type=type(exc).__name__,message='Benchmark stopped; source/model evidence unchanged.')

def handler(event,context):
    request=contract.validate(event)
    if request['operation'] not in ('capture_market','benchmark'):raise RuntimeError('Benchmark operation refused.')
    if request['operation']=='benchmark' and request['model_reference']!=json.loads(os.environ['APPROVED_MODEL_REFERENCE']):raise RuntimeError('Benchmark model reference refused.')
    secret=os.environ.get('MARKET_SECRET_ARN','')
    if request['operation']=='capture_market' and not secret:return dict(STATUS,state='unavailable',stage='access_refusal',provider_attempts=0,message='Market access is not configured.')
    store=InsightsStore(boto3.client('s3',config=CONFIG),os.environ['FBS_S3_BUCKET'],os.environ['FBS_S3_PREFIX'])
    def key():
        response=boto3.client('secretsmanager',config=CONFIG).get_secret_value(SecretId=secret)
        value=response.get('SecretString')
        if not isinstance(value,str):raise ContractError('Market credential is not a string.')
        return value
    return run(request,store,get_key=key if secret else None)
