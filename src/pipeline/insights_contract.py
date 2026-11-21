"""Strict explanation/market requests; no free-text prompt or approval operation."""
import json
from pathlib import Path
import re

from src.features.games import _utc_timestamp
from src.pipeline import monitor_contract
from src.pipeline.model_contract import hex_id
from src.pipeline.run_contract import ContractError,digest,encode

MODEL_ID='amazon.nova-micro-v1:0'
REGION='us-east-1'
MAX_INPUT_BYTES=6144
MAX_OUTPUT_TOKENS=128
MAX_PROVIDER_BYTES=8192
MAX_MARKET_BYTES=4*1024*1024
BOOKMAKER='draftkings'

def decode(raw,limit):
    if not isinstance(raw,bytes) or len(raw)>limit:raise ContractError('Response exceeds its byte limit.')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ContractError('Duplicate response field.')
            result[key]=value
        return result
    def invalid(_):raise ContractError('Nonfinite JSON constant.')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    except (ValueError,UnicodeError):raise ContractError('Malformed JSON.') from None

def reference(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):raise ContractError('Select exact artifact references.')
    for item in value.values():hex_id(item)

def validate(event):
    common={'operation','schema_version','run_token','allow_retrospective_demo'}
    if not isinstance(event,dict) or type(event.get('schema_version')) is not int or event['schema_version']!=1 or event.get('allow_retrospective_demo') is not True:
        raise ContractError('Version one and retrospective permission required.')
    monitor_contract.token(event.get('run_token'));op=event.get('operation')
    if op=='explain':
        if set(event)!=common|{'monitor_reference'}:raise ContractError('Only an explicit verified report may be explained.')
        reference(event['monitor_reference'],('run_token_sha256','completion_sha256','report_sha256'))
        return dict(event)
    if op=='capture_market':
        if set(event)!=common|{'window_start','window_end','odds_format'}:raise ContractError('Select a bounded moneyline capture window.')
        from datetime import datetime
        start,end=map(_utc_timestamp,(event['window_start'],event['window_end']))
        seconds=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).total_seconds()
        if not 0<seconds<=14*86400 or event['odds_format'] not in ('american','decimal'):raise ContractError('Invalid market window or odds format.')
        return dict(event,window_start=start,window_end=end)
    if op!='benchmark' or set(event)!=common|{'weekly_reference','model_reference','market_reference','bookmaker','event_map','outcome_sources','as_of','windows'}:
        raise ContractError('Expected the explicit benchmark contract.')
    reference(event['market_reference'],('run_token_sha256','completion_sha256'))
    if event['bookmaker']!=BOOKMAKER:raise ContractError('The benchmark bookmaker is fixed before comparison.')
    canonical=monitor_contract.validate_report({k:event[k] for k in ('schema_version','run_token','allow_retrospective_demo','weekly_reference','model_reference','outcome_sources','as_of','windows')}|
        {'operation':'report','review_reference':None,'evidence_mode':'saved_retrospective'})
    mapping=event['event_map']
    if not isinstance(mapping,list) or len(mapping)>200:raise ContractError('Select at most 200 explicit event mappings.')
    games,events=set(),set()
    for row in mapping:
        if not isinstance(row,dict) or set(row)!={'game_id','home_id','away_id','market_event_id','market_home','market_away'}:raise ContractError('Each event needs explicit game, team and provider identities.')
        if any(not isinstance(row[k],str) or not re.fullmatch(r'[1-9][0-9]{0,15}',row[k]) for k in ('game_id','home_id','away_id')):raise ContractError('Invalid game/team identifier.')
        if not isinstance(row['market_event_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',row['market_event_id']):raise ContractError('Invalid market event identifier.')
        if any(not isinstance(row[k],str) or not 1<=len(row[k])<=150 or any(ord(c)<32 for c in row[k]) for k in ('market_home','market_away')):raise ContractError('Invalid explicit provider team name.')
        if row['game_id'] in games or row['market_event_id'] in events or row['home_id']==row['away_id'] or row['market_home']==row['market_away']:raise ContractError('Ambiguous event mapping.')
        games.add(row['game_id']);events.add(row['market_event_id'])
    return dict(event,as_of=canonical['as_of'],windows=canonical['windows'],outcome_sources=canonical['outcome_sources'],event_map=sorted(mapping,key=lambda r:r['game_id']))

def implementation_hash():
    root=Path(__file__).resolve().parents[2]
    names=('src/pipeline/insights_contract.py','src/pipeline/insights_storage.py','src/pipeline/explanation_facts.py',
           'src/pipeline/cloud_explanation.py','src/ingestion/odds.py','src/features/markets.py','src/pipeline/cloud_benchmark.py')
    return digest(encode({'monitor_implementation':monitor_contract.implementation_hash(),'sources':{n:digest((root/n).read_bytes()) for n in names}}))
