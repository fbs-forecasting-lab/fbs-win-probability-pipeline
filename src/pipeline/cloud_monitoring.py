"""Private immutable monitoring and failure alerts; no training, inference or source capture."""

import csv
import io
import json
import os
from pathlib import Path
import tempfile

import boto3
from botocore.config import Config

from src.features import games
from src.models import baseline
from src.pipeline import cloud_modeling, model_contract, weekly_contract
from src.pipeline.cloud_preparation import verify_origin
from src.pipeline.cloud_weekly import checked_stage
from src.pipeline import monitor_contract as contract, monitoring_metrics as metrics, monitoring_view
from src.pipeline.monitor_storage import MonitorStore, alert, completion, publish, verified_object
from src.pipeline.cloud_ingestion import create_once
from src.pipeline.run_contract import ContractError, STATUS, digest, encode

CONFIG = Config(connect_timeout=5,read_timeout=60,retries={'total_max_attempts':1})


def csv_rows(content): return list(csv.DictReader(io.StringIO(content.decode())))


def model_evidence(store, reference):
    """Verify the protected producer bundle without ever deserializing model bytes."""
    ledger = store.prefix+'/cloud-modeling/training/'+reference['training_token_sha256']
    raw = verified_object(store,ledger+'/complete.json',reference['training_receipt_sha256']);receipt = baseline.read_json(raw)
    baseline.check_status(receipt)
    request = model_contract.validate(receipt['request'],'training');token,model_id,release = model_contract.identities(request)
    if token != reference['training_token_sha256'] or model_id != reference['model_id'] or receipt['state'] != 'completed':
        raise ContractError('Protected model identity differs.')
    claim = verified_object(store,ledger+'/claim.json',receipt['claim_sha256'])
    if baseline.read_json(claim) != {'schema_version':1,'model_id':model_id,'request':request,'implementation_sha256':release,'versions':baseline.versions()}:
        raise ContractError('Protected model claim differs.')
    base = store.prefix+'/cloud-modeling/models/'+model_id
    artifacts = {n:verified_object(store,base+'/'+n,receipt['artifact_sha256'][n]) for n in model_contract.MODEL_FILES}
    metadata = cloud_modeling.verify_bundle(artifacts,model_id,request,release)
    if receipt != cloud_modeling.model_completion(request,model_id,token,release,claim,metadata,artifacts,base):
        raise ContractError('Protected model receipt does not match its bundle.')
    return metadata,baseline.read_json(artifacts['evaluation.json'])


def inputs(store, request):
    ref = request['weekly_reference'];base = store.prefix+'/weekly/runs/'+ref['run_token_sha256']
    verified_object(store,base+'/complete.json',ref['summary_sha256']);weekly = checked_stage(store,base)
    selected = weekly_contract.validate(weekly['request']);token,run_id = weekly_contract.identity(selected)
    if token != ref['run_token_sha256'] or weekly['run_id'] != run_id or weekly.get('workflow_completed') is not True or weekly['state'] not in ('withheld','completed'):
        raise ContractError('Monitoring requires a verified completed weekly processing result.')
    if weekly['model_reference'] != request['model_reference'] or selected['model_reference'] != request['model_reference']:
        raise ContractError('Weekly input and selected protected model differ.')
    metadata,evaluation = model_evidence(store,request['model_reference'])
    def read(name):
        key=base+'/'+name
        if key not in weekly['artifact_sha256']: raise ContractError('Required monitoring input is not bound by the weekly summary.')
        return verified_object(store,key,weekly['artifact_sha256'][key])
    training = read('preparation/dataset/train.csv')
    if digest(training) != metadata['dataset_artifact_sha256']['train.csv']: raise ContractError('Training reference differs from the protected model.')
    rows=baseline.read_json(read('preparation/rows.json'))['rows'];predictions=csv_rows(read('inference/predictions.csv'))
    if len(rows)!=len(predictions) or any(any(str(a[k])!=str(b[k]) for k in ('game_id','season','week','home_id','away_id','cutoff')) for a,b in zip(rows,predictions)):
        raise ContractError('Feature and prediction row identities differ.')
    provenance=baseline.read_json(read('preparation/provenance.json'))
    return {'weekly':weekly,'metadata':metadata,'evaluation':evaluation,'training':csv_rows(training),'rows':rows,
            'predictions':predictions,'eligibility':baseline.read_json(read('preparation/eligibility.json')),
            'quality':baseline.read_json(read('preparation/normalized/2026/quality_report.json')),
            'source':provenance['sources']['2026']['source']}


def later_outcomes(store, request, scoring_source, cutoff):
    rows,lineage=[],[]
    with tempfile.TemporaryDirectory(prefix='monitor-labels-') as temporary:
        for index,ref in enumerate(request['outcome_sources']):
            path=store.download_raw(2026,ref['manifest_name'],Path(temporary)/str(index));snapshot=games.load_snapshot(path);source=snapshot.source
            if any(source[k]!=ref[k] for k in ('raw_sha256','manifest_sha256')): raise ContractError('Outcome snapshot hash mismatch.')
            observed=source['retrieved_at']
            if not metrics.instant(scoring_source['retrieved_at']) < metrics.instant(observed) <= metrics.instant(request['as_of']) or metrics.instant(observed) <= metrics.instant(cutoff):
                raise ContractError('Outcomes must be later observations after scoring input/cutoff and no later than as_of.')
            origin=verify_origin(store,ref,source,(path.parent/source['raw_file']).read_bytes(),path.read_bytes())
            normalized,exclusions,quality=games._normalize(snapshot)
            for row in normalized:
                rows.append(dict(row,game_id=str(row['id']),observed_at=observed))
            lineage.append({'reference':ref,'source':source,'origin':origin,'counts':quality['counts']})
    return rows,lineage


def selected_review(store, reference, analysis_sha256):
    if reference is None:return 'not_selected'
    key=store.prefix+'/monitoring/alerts/'+reference['alert_id']+'/reviews/'+str(reference['sequence']).zfill(3)+'.json'
    result=baseline.read_json(verified_object(store,key,reference['sha256']))
    if result['alert_id']!=reference['alert_id'] or result['sequence']!=reference['sequence']:raise ContractError('Review reference differs.')
    original=baseline.read_json(store._get(store.prefix+'/monitoring/alerts/'+reference['alert_id']+'/alert.json'))
    if original['evidence'].get('analysis_sha256')!=analysis_sha256:raise ContractError('Selected review belongs to another analysis.')
    return 'selected_alert_'+result['action']


def report_run(event, store):
    stage,base,request='request_validation',None,None
    try:
        request=contract.validate_report(event);store._private_bucket()
        base=store.prefix+'/monitoring/runs/'+digest(request['run_token'].encode())
        identity={'request':request,'implementation_sha256':contract.implementation_hash(),'policy':contract.POLICY}
        claim=encode(identity);stage='report_claim'
        if store._get(base+'/claim.json',optional=True) is None:create_once(store,base+'/claim.json',claim)
        if store._get(base+'/claim.json')!=claim:raise ContractError('Monitoring token conflicts with request, policy or implementation.')
        stage='verified_inputs';data=inputs(store,request)
        stage='outcome_verification';outcomes,lineage=later_outcomes(store,request,data['source'],data['weekly']['request']['forecast_cutoff'])
        stage='monitor_analysis'
        quality=metrics.quality(data['quality'],data['eligibility'],data['rows'],data['predictions'],data['source']['retrieved_at'],request['as_of'])
        drift=metrics.distributions(data['training'],data['rows'])
        performance=metrics.performance(data['predictions'],outcomes,request['windows'],request['as_of'],data['evaluation'])
        issues=list(quality['issues'])
        for name,feature in drift.get('features',{}).items():
            if feature['changed']:issues.append({'code':'distribution_change_'+name,'severity':'warning','count':feature['scoring_n']})
        for index,window in enumerate(performance.get('windows',[])):
            if window['state']=='measured' and (window['metrics']['brier_score']-data['evaluation']['model']['brier_score']>contract.POLICY['brier_increase'] or window['metrics']['log_loss']-data['evaluation']['model']['log_loss']>contract.POLICY['log_loss_increase']):
                issues.append({'code':'performance_change_window_'+str(index),'severity':'warning','count':window['matched']})
        records=[]
        analysis_sha256=digest(encode({k:v for k,v in request.items() if k not in ('run_token','review_reference')}|{'policy':contract.POLICY}))
        for issue in issues:
            records.append(alert(store,{'analysis_sha256':analysis_sha256,'weekly_reference':request['weekly_reference'],
                'as_of':request['as_of'],'measure':issue},issue['code'],issue['severity'],
                'Inspect source versions, sample sizes and evidence. Human review required; do not retrain or approve forecasts automatically.',simulated=request['evidence_mode']=='synthetic_test'))
        report=dict(STATUS,request=request,policy=contract.POLICY,source_identities=data['weekly']['artifact_sha256'],
            training_seasons=data['metadata']['training_seasons'],training_n=data['metadata']['counts']['train'],
            model_reference=request['model_reference'],outcome_lineage=lineage,pipeline_state=data['weekly']['state'],
            quality=quality,distributions=drift,performance=performance,alerts=records,
            review_state=selected_review(store,request['review_reference'],analysis_sha256),operational_forecast_approved=False,
            limitations=['Distribution changes are not concept drift.','Missing labels are not zero error.',
                         'Historical publication and operational approval remain unverified.'])
        view=monitoring_view.stakeholder(report)
        stage='report_publication'
        artifacts={'report.json':encode(report),'stakeholder.json':encode(view),'display.html':monitoring_view.render(view)}
        result=dict(STATUS,state='completed',request=request,implementation_sha256=identity['implementation_sha256'],
            report_sha256=digest(artifacts['report.json']),alert_references=records,operational_forecast_approved=False)
        old=completion(store,base)
        if old is not None:
            expected=dict(result,artifact_sha256={base+'/'+n:digest(v) for n,v in artifacts.items()})
            if old!=expected:raise ContractError('Completed monitoring result conflicts; no repair allowed.')
            return old
        return publish(store,base,artifacts,result)
    except Exception as exc:
        result=dict(STATUS,state='failed',stage=stage,error_type=type(exc).__name__,message='Monitoring stopped; evidence preserved; no forecasts or models changed.')
        if request is not None:
            try:result['alert_reference']=alert(store,{'request_sha256':digest(encode(request)),'stage':stage,'error_type':type(exc).__name__},'monitoring_processing_failure','critical','Inspect verified inputs and private execution evidence; never bypass integrity checks.',simulated=request['evidence_mode']=='synthetic_test')
            except Exception:pass
        return result


def execution_run(event, store, states, approved_machine, *, simulated=False):
    """Detect application failure objects even when the Lambda task succeeded."""
    try:
        fields={'operation','schema_version','execution_arn'}
        if not isinstance(event,dict) or set(event)!=fields or event['operation']!='execution' or type(event['schema_version']) is not int or event['schema_version']!=1:raise ContractError('Invalid execution-monitor request.')
        expected=approved_machine.replace(':stateMachine:',':execution:')+':'
        if not isinstance(event['execution_arn'],str) or not event['execution_arn'].startswith(expected) or ':' in event['execution_arn'][len(expected):]:raise ContractError('Execution is outside approved workflow.')
        state=states.describe_execution(executionArn=event['execution_arn'])
        if state['stateMachineArn']!=approved_machine:raise ContractError('Execution machine identity differs.')
        events=[];page={}
        while True:
            response=states.get_execution_history(executionArn=event['execution_arn'],maxResults=1000,includeExecutionData=True,**page);events+=response['events']
            if len(events)>10000:raise ContractError('Execution history exceeds the bounded limit.')
            if not response.get('nextToken'):break
            page={'nextToken':response['nextToken']}
        failures=[]
        for row in events:
            if row['type']=='LambdaFunctionSucceeded':
                output=json.loads(row['lambdaFunctionSucceededEventDetails']['output'])
                if isinstance(output,dict) and output.get('state')=='failed':failures.append({'event_id':row['id'],'application_failed':True})
        terminal=state['status'] in ('FAILED','TIMED_OUT','ABORTED')
        events=json.loads(json.dumps(events,default=lambda value:value.isoformat()))
        evidence={'execution_arn':event['execution_arn'],'execution_status':state['status'],'history_sha256':digest(encode(events)),'application_failures':failures}
        records=[]
        if state['status']=='RUNNING':return dict(STATUS,state='pending',pipeline_status='RUNNING',application_failure_count=len(failures),alerts=[])
        if terminal or failures:records.append(alert(store,evidence,'application_failure' if failures else 'orchestration_failure','critical','Inspect immutable stage receipts and execution history; acknowledge and investigate; do not restart capture or retrain automatically.',simulated=simulated))
        result=dict(STATUS,state='pending' if state['status']=='RUNNING' else 'completed',pipeline_status=state['status'],application_failure_count=len(failures),alerts=records,operational_forecast_approved=False)
        if result['state']=='pending':return result
        # A deliberate later redrive is a new observation, not permission to overwrite old evidence.
        base=store.prefix+'/monitoring/executions/'+digest(encode({'execution_arn':event['execution_arn'],'history_sha256':evidence['history_sha256']}))
        old=completion(store,base)
        artifacts={'evidence.json':encode(evidence),'result.json':encode(result)}
        if old is not None:
            if old!=dict(result,artifact_sha256={base+'/'+n:digest(v) for n,v in artifacts.items()}):raise ContractError('Completed execution monitoring conflict.')
            return old
        return publish(store,base,artifacts,result)
    except Exception as exc:
        return dict(STATUS,state='failed',stage='execution_monitoring',error_type=type(exc).__name__,message='Execution monitoring stopped; private evidence preserved.')


def handler(event,context):
    try:
        machine=os.environ['WEEKLY_STATE_MACHINE_ARN']
        if isinstance(event,dict) and event.get('source')=='aws.states':
            detail=event['detail']
            if event.get('detail-type')!='Step Functions Execution Status Change' or detail['stateMachineArn']!=machine:raise ContractError('Unexpected workflow event.')
            event={'operation':'execution','schema_version':1,'execution_arn':detail['executionArn']}
        if event.get('operation')=='simulate_alert':
            if os.environ.get('ALLOW_ALERT_SIMULATION','false')!='true' or set(event)!={'operation','schema_version','simulation_token','as_of'} or type(event['schema_version']) is not int or event['schema_version']!=1:
                raise ContractError('Alert simulation is disabled or malformed.')
            contract.token(event['simulation_token']);games._utc_timestamp(event['as_of'])
        elif event.get('operation')=='report':
            request=contract.validate_report(event)
            if request['evidence_mode']=='synthetic_test' and os.environ.get('ALLOW_SYNTHETIC_MONITORING','false')!='true':raise ContractError('Synthetic evidence is disabled in this deployment.')
            if request['model_reference']!=json.loads(os.environ['APPROVED_MODEL_REFERENCE']):raise ContractError('Monitoring model differs from deployment approval.')
        elif event.get('operation')!='execution':raise ContractError('Unknown monitoring operation.')
        store=MonitorStore(boto3.client('s3',config=CONFIG),os.environ['FBS_S3_BUCKET'],os.environ['FBS_S3_PREFIX'])
        if event['operation']=='simulate_alert':
            store._private_bucket()
            reference=alert(store,{'simulation_token_sha256':digest(event['simulation_token'].encode()),'as_of':games._utc_timestamp(event['as_of'])},
                'simulated_monitoring_check','info','Explicit smoke-test alert; not a genuine incident disposition.',simulated=True)
            return dict(STATUS,state='completed',alert_reference=reference,simulated=True)
        result=report_run(event,store) if event['operation']=='report' else execution_run(event,store,boto3.client('stepfunctions',config=CONFIG),machine)
        if result['state']=='failed':raise ContractError('Monitoring failed; inspect immutable alert/evidence records.')
        return result
    except Exception as exc:
        raise RuntimeError('Monitoring failed or request/configuration rejected; inspect private evidence.') from None
