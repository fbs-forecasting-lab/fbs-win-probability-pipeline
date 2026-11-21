"""Allowlisted facts and constrained extractive summaries; provider prose is never displayed."""
import math
from src.pipeline.insights_contract import decode,MAX_PROVIDER_BYTES
from src.pipeline.run_contract import ContractError,STATUS,encode

REQUIRED={'status','performance','limits'}

def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ContractError('Invalid factual number.')
    return value

def count(value):
    if type(value) is not int or not 0<=value<=1000000:raise ContractError('Invalid factual count.')
    return value

def catalog(report):
    for k,v in STATUS.items():
        if report.get(k)!=v:raise ContractError('Report safeguards differ.')
    if report.get('operational_forecast_approved') is not False:raise ContractError('Publication must remain withheld.')
    q,d,p=report['quality'],report['distributions'],report['performance']
    raw,kept,quarantined=[count(q['counts'][k]) for k in ('input','retained','quarantined')]
    eligible=count(q['eligible'])
    if p['state'] not in ('pending','insufficient_data','measured','failed'):raise ContractError('Unknown performance state.')
    if p['state']=='failed':perf='Performance verification failed; outcome coverage and rolling metrics are unavailable.'
    else:
        pending,matched=count(p['pending']),count(p['matched'])
        perf=(f'{pending} outcomes are pending and {matched} are matched. Rolling performance is not yet measurable.' if p['state']=='pending' else
              f'Rolling performance state is {p["state"]}, with {matched} matched and {pending} pending outcomes.')
    facts={'status':'This is a retrospective demonstration. Historical availability is unverified and operational publication is withheld.',
           'performance':perf,
           'limits':'Distribution changes alone do not establish concept drift. No retraining, forecast approval or alert closure is authorized.',
           'quality':f'The selected report contains {raw} raw games, {kept} retained, {quarantined} quarantined and {eligible} technical scoring rows.'}
    if d['state'] not in ('measured','insufficient_data','failed'):raise ContractError('Unknown distribution state.')
    if d['state']=='measured':
        features=d['features']
        if set(features)!={'prior_win_pct_diff','prior_avg_margin_diff','home_field'} or any(type(v['changed']) is not bool for v in features.values()):raise ContractError('Invalid measured distribution facts.')
        sizes={(count(v['reference_n']),count(v['scoring_n'])) for v in features.values()}
        if len(sizes)!=1:raise ContractError('Distribution sample sizes differ.')
        reference_n,scoring_n=next(iter(sizes))
        if min(reference_n,scoring_n)<30:raise ContractError('Measured distribution sample is insufficient.')
        changed=sum(v['changed'] for v in features.values())
        facts['distributions']=f'Distribution checks compare {reference_n} training rows with {scoring_n} scoring rows; {changed} feature indicators request investigation.'
    else:
        facts['distributions']=f'Distribution checks are {d["state"]}; a measured change count is unavailable.'
    holdout=p.get('retrospective_holdout_reference',{})
    if 'model' in holdout:
        m=holdout['model'];b=holdout.get('constant_baseline',holdout.get('baseline'))
        values=[number(m[k]) for k in ('brier_score','log_loss','accuracy')]
        if not 0<=values[0]<=1 or values[1]<0 or not 0<=values[2]<=1:raise ContractError('Invalid holdout metrics.')
        facts['holdout']=f'Historical holdout model Brier score is {values[0]:.4f}, log loss {values[1]:.4f} and accuracy {values[2]:.4f}. These are reference results, not newly measured rolling performance.'
        if b is not None:
            values=[number(b[k]) for k in ('brier_score','log_loss','accuracy')]
            if not 0<=values[0]<=1 or values[1]<0 or not 0<=values[2]<=1:raise ContractError('Invalid baseline metrics.')
            facts['baseline']=f'The historical constant baseline Brier score is {values[0]:.4f}, log loss {values[1]:.4f} and accuracy {values[2]:.4f}.'
    return facts

def validate_selection(text,facts):
    if not isinstance(text,str):raise ContractError('Provider response must be a bounded JSON string.')
    value=decode(text.encode(),MAX_PROVIDER_BYTES)
    if not isinstance(value,dict) or set(value)!={'fact_ids'}:raise ContractError('Provider output must select verified facts only.')
    ids=value['fact_ids']
    if not isinstance(ids,list) or not 3<=len(ids)<=7 or any(not isinstance(v,str) for v in ids) or len(set(ids))!=len(ids) or not REQUIRED<=set(ids) or not set(ids)<=set(facts):
        raise ContractError('Unsupported or incomplete explanation claims.')
    return {'fact_ids':ids,'paragraphs':[facts[v] for v in ids],'validation':'Exact source-fact selection; no provider prose, numbers or approval claims displayed.'}
