"""One bounded Bedrock explanation attempt over verified sanitized monitoring facts."""
import html
import json
import os
import boto3
from botocore.config import Config

from src.pipeline import insights_contract as contract,explanation_facts
from src.pipeline.insights_storage import InsightsStore,claim,external_once,replay,publish,verified_object
from src.pipeline import monitor_contract
from src.pipeline.run_contract import ContractError,STATUS,digest,encode

CONFIG=Config(connect_timeout=5,read_timeout=20,retries={'total_max_attempts':1})
SYSTEM='Select and order verified statements for a concise stakeholder summary. Return only JSON with fact_ids, an array of unique supplied identifiers. Include status, performance and limits. Do not invent text, numbers, conclusions or actions. Select at most seven facts.'

def verified_facts(store,ref):
    base=store.prefix+'/monitoring/runs/'+ref['run_token_sha256']
    receipt=json.loads(verified_object(store,base+'/complete.json',ref['completion_sha256']))
    for k,v in STATUS.items():
        if receipt.get(k)!=v:raise ContractError('Monitoring receipt flags differ.')
    if receipt['state']!='completed' or receipt['implementation_sha256']!=monitor_contract.implementation_hash():raise ContractError('Monitoring producer differs.')
    expected_names={base+'/'+n for n in ('report.json','stakeholder.json','display.html')}
    if set(receipt['artifact_sha256'])!=expected_names:raise ContractError('Unexpected monitor artifact set.')
    raw=None
    for key,sha in receipt['artifact_sha256'].items():
        content=verified_object(store,key,sha)
        if key.endswith('/report.json'):raw=content
    if digest(raw)!=ref['report_sha256'] or receipt['report_sha256']!=ref['report_sha256']:raise ContractError('Report identity differs.')
    if digest(receipt['request']['run_token'].encode())!=ref['run_token_sha256']:raise ContractError('Producer token differs.')
    expected={'request':receipt['request'],'implementation_sha256':receipt['implementation_sha256'],'policy':monitor_contract.POLICY}
    if store._get(base+'/claim.json')!=encode(expected):raise ContractError('Producer claim differs.')
    return explanation_facts.catalog(json.loads(raw))

def provider_call(client,facts):
    prompt=encode({'facts':facts}).decode()
    if len(prompt.encode())+len(SYSTEM.encode())>contract.MAX_INPUT_BYTES:raise ContractError('Explanation input exceeds bound.')
    try:
        response=client.converse(modelId=contract.MODEL_ID,system=[{'text':SYSTEM}],messages=[{'role':'user','content':[{'text':prompt}]}],
                                 inferenceConfig={'maxTokens':contract.MAX_OUTPUT_TOKENS,'temperature':0})
        # Keep actual bounded response/usage and request provenance; no fabricated defaults.
        record={'response':{k:response[k] for k in ('output','stopReason','usage','metrics') if k in response},
                'request_id':response.get('ResponseMetadata',{}).get('RequestId')}
        if len(encode(record))>contract.MAX_PROVIDER_BYTES:return {'state':'unavailable','reason':'response_too_large'}
        return dict(record,state='received')
    except Exception as exc:return {'state':'unavailable','reason':'provider_failure','error_type':type(exc).__name__}

def run(event,store,client):
    stage='request_validation'
    try:
        request=contract.validate(event)
        if request['operation']!='explain':raise ContractError('Wrong operation.')
        store._private_bucket();base=store.prefix+'/stakeholder/explanations/'+digest(request['run_token'].encode())
        identity={'request':request,'implementation_sha256':contract.implementation_hash(),'provider':'Amazon Bedrock','model_id':contract.MODEL_ID,'region':contract.REGION,
                  'max_output_tokens':contract.MAX_OUTPUT_TOKENS,'max_input_bytes':contract.MAX_INPUT_BYTES,'attempts':1,'timeout_seconds':20,'prompt_sha256':digest(SYSTEM.encode())}
        claim_sha=claim(store,base,identity);old=replay(store,base,request)
        stage='verified_facts';facts=verified_facts(store,request['monitor_reference'])
        if old is not None:
            key=base+'/facts.json'
            if old['artifact_sha256'].get(key)!=digest(encode(facts)):raise ContractError('Completed factual input differs.')
            return old
        if len(encode({'facts':facts}))+len(SYSTEM.encode())>contract.MAX_INPUT_BYTES:raise ContractError('Fact input exceeds bound.')
        stage='provider_attempt';response=external_once(store,base,claim_sha,lambda:provider_call(client,facts))
        if response is None:return dict(STATUS,state='attempt_unresolved',explanation_state='unavailable',provider_attempts=1,message='Original provider attempt may have occurred; no retry.')
        selection=None;reason=response.get('reason');usage=None
        if response['state']=='received':
            try:
                output=response['response'];usage=output['usage']
                if any(type(usage[k]) is not int or usage[k]<0 for k in ('inputTokens','outputTokens','totalTokens')) or usage['totalTokens']!=usage['inputTokens']+usage['outputTokens'] or usage['outputTokens']>contract.MAX_OUTPUT_TOKENS:raise ContractError('Invalid provider usage.')
                if output['stopReason']!='end_turn' or output['output']['message']['role']!='assistant' or len(output['output']['message']['content'])!=1 or set(output['output']['message']['content'][0])!={'text'}:raise ContractError('Incomplete provider response.')
                text=output['output']['message']['content'][0]['text'];selection=explanation_facts.validate_selection(text,facts)
            except (KeyError,TypeError,ValueError):reason='invalid_provider_output';selection=None
        explanation={'state':'available' if selection else 'unavailable','selection':selection,'reason':None if selection else reason,
                     'authoritative_metrics_changed':False,'operational_forecast_approved':False}
        paragraphs=selection['paragraphs'] if selection else []
        display=('<!doctype html><html lang="en"><meta charset="utf-8"><title>Stakeholder explanation draft</title>'
                 '<h1>Private retrospective summary</h1><p>Explanation: '+explanation['state']+'</p>'+
                 ''.join('<p>'+html.escape(v)+'</p>' for v in paragraphs)+'<h2>Verified factual report</h2>'+
                 ''.join('<p>'+html.escape(v)+'</p>' for v in facts.values())+'</html>').encode()
        stage='publication'
        artifacts={'facts.json':encode(facts),'explanation.json':encode(explanation),'display.html':display,
                   'provenance.json':encode(dict(identity,input_sha256=digest(encode(facts)),response_sha256=digest(encode(response)),usage=usage,provider_response=response))}
        return publish(store,base,artifacts,dict(STATUS,state='completed',request=request,explanation_state=explanation['state'],provider_attempts=1,operational_forecast_approved=False))
    except Exception as exc:return dict(STATUS,state='failed',stage=stage,error_type=type(exc).__name__,message='Explanation stopped; original factual report preserved.')

def handler(event,context):
    request=contract.validate(event)
    if request['operation']!='explain' or os.environ.get('PROVIDER_MODEL_ID')!=contract.MODEL_ID or os.environ.get('AWS_REGION')!=contract.REGION:raise RuntimeError('Explanation configuration refused.')
    store=InsightsStore(boto3.client('s3',config=CONFIG),os.environ['FBS_S3_BUCKET'],os.environ['FBS_S3_PREFIX'])
    return run(request,store,boto3.client('bedrock-runtime',region_name=contract.REGION,config=CONFIG))
