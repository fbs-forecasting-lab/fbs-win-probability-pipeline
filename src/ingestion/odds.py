"""One current-moneyline request; no historical endpoint, retries, dotenv or key logging."""
from dataclasses import dataclass
import re
import time
import requests

from src.features.games import _utc_timestamp
from src.pipeline.insights_contract import MAX_MARKET_BYTES,decode
from src.pipeline.run_contract import ContractError,STATUS,now,digest

ENDPOINT='https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds'

@dataclass(frozen=True)
class OddsResponse:
    """Carry one observed odds response with its exact bytes, request timing and quota metadata."""
    raw:bytes
    requested_at:str
    retrieved_at:str
    parameters:dict
    quota:dict
    http_status:int=200

def parameters(request):
    return {'regions':'us','markets':'h2h','oddsFormat':request['odds_format'],'dateFormat':'iso',
            'commenceTimeFrom':request['window_start'],'commenceTimeTo':request['window_end']}

def validate_key(api_key):
    if not isinstance(api_key,str) or not 8<=len(api_key)<=512 or any(c.isspace() for c in api_key):raise ContractError('Market credential is not configured.')

def fetch_moneylines(request,api_key,*,session=None,clock=now):
    validate_key(api_key)
    params=parameters(request);started=_utc_timestamp(clock())
    deadline=time.monotonic()+25
    client=session or requests.Session()
    try:
        # Explicitly zero redirects; the credential is never forwarded to another host.
        with client.get(ENDPOINT,params=dict(params,apiKey=api_key),timeout=(5,15),allow_redirects=False,stream=True) as response:
            if response.status_code!=200:raise ContractError('Market provider did not return a successful capture.')
            chunks=[];size=0
            for chunk in response.iter_content(65536):
                if time.monotonic()>deadline:raise ContractError('Market response exceeded its time bound.')
                size+=len(chunk)
                if size>MAX_MARKET_BYTES:raise ContractError('Market response exceeds capture bound.')
                chunks.append(chunk)
            raw=b''.join(chunks)
            if api_key.encode() in raw:raise ContractError('Market response cannot be retained safely.')
            if not isinstance(decode(raw,MAX_MARKET_BYTES),list):raise ContractError('Market provider returned an unexpected document.')
            quota={}
            for name in ('x-requests-used','x-requests-remaining','x-requests-last'):
                value=response.headers.get(name)
                if value is not None:
                    if not re.fullmatch(r'\d{1,12}',value):raise ContractError('Invalid market quota metadata.')
                    quota[name]=int(value)
            return OddsResponse(raw,started,_utc_timestamp(clock()),params,quota)
    except requests.RequestException:raise ContractError('Market request failed; no retry authorized.') from None
    finally:
        if session is None:client.close()

def manifest(response):
    rows=decode(response.raw,MAX_MARKET_BYTES)
    return {'schema_version':1,'provider':'The Odds API','sport':'americanfootball_ncaaf','endpoint':'current_odds_v4',
            'request_parameters':response.parameters,'requested_at':response.requested_at,'retrieved_at':response.retrieved_at,
            'http_status':response.http_status,'record_count':len(rows),'raw_sha256':digest(response.raw),'quota':response.quota,
            **STATUS}
