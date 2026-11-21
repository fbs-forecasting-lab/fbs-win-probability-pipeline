"""Timestamp-aware two-way moneylines; benchmark inputs never become predictors/labels."""
from collections import Counter
from datetime import datetime
import math
import re

from src.features.games import _utc_timestamp
from src.pipeline.insights_contract import decode,MAX_MARKET_BYTES
from src.pipeline.run_contract import ContractError,STATUS,digest
from src.pipeline import monitoring_metrics

def instant(value):return datetime.fromisoformat(_utc_timestamp(value))

def implied(price,odds_format):
    if type(price) not in (int,float) or not math.isfinite(price):raise ContractError('Invalid moneyline price.')
    if odds_format=='decimal' and price>1:return 1/price
    if odds_format=='american' and abs(price)>=100:return 100/(price+100) if price>0 else (-price)/((-price)+100)
    raise ContractError('Unsupported moneyline price or format.')

def fair_probabilities(home,away,odds_format):
    h,a=implied(home,odds_format),implied(away,odds_format);total=h+a
    if not all(math.isfinite(v) and 0<v<=1 for v in (h,a)) or not math.isfinite(total) or total<=0:raise ContractError('Invalid implied probabilities.')
    p=h/total
    return {'home_implied':h,'away_implied':a,'overround':total-1,
            'home_probability':p,'away_probability':1-p,'method':'proportional two-way normalization'}

def normalize(raw,manifest):
    if type(manifest.get('schema_version')) is not int or manifest['schema_version']!=1 or manifest.get('provider')!='The Odds API' or manifest.get('sport')!='americanfootball_ncaaf' or manifest.get('endpoint')!='current_odds_v4' or manifest.get('http_status')!=200 or digest(raw)!=manifest.get('raw_sha256') or any(manifest.get(k)!=v for k,v in STATUS.items()):
        raise ContractError('Market manifest/response identity differs.')
    values=decode(raw,MAX_MARKET_BYTES)
    if not isinstance(values,list) or len(values)>1000 or len(values)!=manifest['record_count']:raise ContractError('Market event count differs or exceeds bound.')
    requested,retrieved=instant(manifest['requested_at']),instant(manifest['retrieved_at'])
    if requested>retrieved:raise ContractError('Market capture chronology differs.')
    fmt=manifest['request_parameters']['oddsFormat']
    ids=Counter(v.get('id') for v in values if isinstance(v,dict) and isinstance(v.get('id'),str))
    rows=[];excluded=[]
    for index,event in enumerate(values):
        try:
            if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',event['id']):raise ContractError('missing_event_identity')
            if ids[event['id']]!=1:raise ContractError('ambiguous_event_identity')
            if event.get('sport_key')!='americanfootball_ncaaf':raise ContractError('wrong_sport')
            home,away=event['home_team'],event['away_team']
            if any(not isinstance(v,str) or not 1<=len(v)<=150 or any(ord(c)<32 for c in v) for v in (home,away)) or home==away:raise ContractError('invalid_team_identity')
            kickoff=_utc_timestamp(event['commence_time']);books=event['bookmakers']
            if not isinstance(books,list) or len(books)>100:raise ContractError('invalid_bookmaker_set')
            keys=Counter(v.get('key') for v in books if isinstance(v,dict) and isinstance(v.get('key'),str))
            if not books:excluded.append({'source_row':index,'event_id':event['id'],'reason':'missing_market'})
            for book in books:
                try:
                    if not isinstance(book,dict) or not isinstance(book.get('markets'),list):raise ContractError('malformed_bookmaker')
                    key=book['key']
                    if not isinstance(key,str) or not re.fullmatch(r'[a-z0-9_]{1,50}',key) or keys[key]!=1:raise ContractError('ambiguous_bookmaker')
                    selected=[v for v in book['markets'] if isinstance(v,dict) and v.get('key')=='h2h']
                    if len(selected)!=1:raise ContractError('missing_or_ambiguous_moneyline')
                    market=selected[0]
                    if 'last_update' not in market:raise ContractError('missing_market_timestamp')
                    updated=_utc_timestamp(market['last_update'])
                    if instant(updated)>retrieved:raise ContractError('market_timestamp_after_observation')
                    outcomes=market['outcomes']
                    if not isinstance(outcomes,list) or len(outcomes)!=2 or not all(isinstance(v,dict) and 'name' in v for v in outcomes) or {v['name'] for v in outcomes}!={home,away}:raise ContractError('not_two_way_matching_teams')
                    prices={v['name']:v['price'] for v in outcomes};p=fair_probabilities(prices[home],prices[away],fmt)
                    rows.append(dict(p,provider='The Odds API',market='h2h',event_id=event['id'],home=home,away=away,kickoff=kickoff,bookmaker=key,
                        market_updated_at=updated,bookmaker_updated_at=book.get('last_update'),retrieved_at=manifest['retrieved_at'],
                        raw_sha256=manifest['raw_sha256'],source_row=index,odds_format=fmt,home_price=prices[home],away_price=prices[away]))
                except (KeyError,TypeError,ValueError) as exc:
                    excluded.append({'source_row':index,'event_id':event['id'],'reason':str(exc) if isinstance(exc,ContractError) else 'malformed_market'})
        except (KeyError,TypeError,ValueError) as exc:
            excluded.append({'source_row':index,'reason':str(exc) if isinstance(exc,ContractError) else 'malformed_event'})
    return rows,{'received_events':len(values),'retained_markets':len(rows),'exclusions':excluded}

def compare(predictions,markets,event_map,bookmaker,forecast_cutoff,model_observed_at,market_observed_at,as_of,windows,outcomes):
    deadline,observed,bound=map(instant,(forecast_cutoff,model_observed_at,as_of))
    if observed>bound or monitoring_metrics.probability_errors(predictions):raise ContractError('Invalid model observation/probabilities.')
    ids={str(r['game_id']):r for r in predictions}
    if len(ids)!=len(predictions):raise ContractError('Duplicate model game identity.')
    mapping={r['game_id']:r for r in event_map}
    if len(mapping)!=len(event_map) or len({r['market_event_id'] for r in event_map})!=len(event_map):raise ContractError('Ambiguous explicit mapping.')
    if any(k not in ids for k in mapping):raise ContractError('Mapping refers to an unrelated model game.')
    selected=[r for r in markets if r['bookmaker']==bookmaker]
    events={}
    for row in selected:events.setdefault(row['event_id'],[]).append(row)
    shared=[];rejected=[]
    for game_id,pred in ids.items():
        reasons=[];m=mapping.get(game_id);quote=None
        if instant(market_observed_at)>bound:raise ContractError('Market observed after benchmark as_of.')
        if instant(market_observed_at)>=deadline:reasons.append('market_observed_at_or_after_cutoff')
        if observed>=deadline:reasons.append('model_observed_at_or_after_cutoff')
        if deadline>=instant(pred['cutoff']):reasons.append('forecast_cutoff_not_before_kickoff')
        if m is None:reasons.append('missing_explicit_event_mapping')
        else:
            if any(str(pred[k])!=m[k] for k in ('home_id','away_id')):raise ContractError('Mapped team IDs differ from model input.')
            candidates=events.get(m['market_event_id'],[])
            if len(candidates)!=1:reasons.append('missing_or_ambiguous_bookmaker_market')
            else:
                quote=candidates[0]
                if instant(quote['retrieved_at'])!=instant(market_observed_at):raise ContractError('Quote observation differs from selected capture.')
                if quote['home']!=m['market_home'] or quote['away']!=m['market_away']:reasons.append('market_team_identity_mismatch')
                if instant(quote['kickoff'])!=instant(pred['cutoff']):reasons.append('kickoff_identity_mismatch')
                if instant(quote['retrieved_at'])>bound:raise ContractError('Market observed after benchmark as_of.')
                if instant(quote['market_updated_at'])>=deadline:reasons.append('market_updated_at_or_after_cutoff')
        if reasons:rejected.append({'game_id':game_id,'reasons':reasons});continue
        home=float(pred['home_win_probability']);q=quote['home_probability']
        shared.append({'model':pred,'market':quote,'home_probability_difference':home-q})
    cohort_model=[r['model'] for r in shared]
    cohort_market=[dict(r['model'],home_win_probability=r['market']['home_probability'],away_win_probability=r['market']['away_probability']) for r in shared]
    if shared:
        model_perf=monitoring_metrics.performance(cohort_model,outcomes,windows,as_of,{})
        market_perf=monitoring_metrics.performance(cohort_market,outcomes,windows,as_of,{})
        paired=[]
        for a,b in zip(model_perf['windows'],market_perf['windows'],strict=True):
            if (a['matched'],a['eligible'],a['coverage'],a['state'])!=(b['matched'],b['eligible'],b['coverage'],b['state']):raise ContractError('Paired cohort differs.')
            paired.append({'start':a['start'],'end':a['end'],'matched':a['matched'],'eligible':a['eligible'],'coverage':a['coverage'],'state':a['state'],
                           'model':a['metrics'],'market':b['metrics'],
                           'market_minus_model':{k:b['metrics'][k]-a['metrics'][k] for k in ('brier_score','log_loss')} if a['metrics'] else None})
        state=model_perf['state'];matched=model_perf['matched'];pending=model_perf['pending']
    else:paired=[];state='unavailable';matched=pending=0
    return {'state':'compared' if shared else 'no_aligned_market_data','model_games':len(predictions),'shared_games':len(shared),
            'market_coverage':len(shared)/len(predictions) if predictions else None,'rejections':rejected,
            'differences':[{'game_id':r['model']['game_id'],'market_event_id':r['market']['event_id'],'model_home_probability':float(r['model']['home_win_probability']),
                            'market_home_probability':r['market']['home_probability'],'model_minus_market':r['home_probability_difference']} for r in shared],
            'paired_performance':{'state':state,'matched':matched,'pending':pending,'windows':paired},
            'interpretation':'Same eligible bookmaker/game cohort only. Market observations are benchmarks, never predictors or labels. Technical timing checks do not verify historical publication or operational approval.'}
