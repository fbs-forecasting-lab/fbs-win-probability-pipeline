"""Descriptive monitoring only: fixed heuristics, delayed-label coverage and no model fitting."""

from collections import Counter
from datetime import datetime
import math

import numpy as np

from src.evaluation.metrics import evaluate_probabilities
from src.pipeline.monitor_contract import POLICY
from src.pipeline.run_contract import ContractError

FEATURES = ('prior_win_pct_diff', 'prior_avg_margin_diff', 'home_field')


def instant(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))


def feature_values(rows):
    values, invalid = [], 0
    for row in rows:
        try:
            x = [float(row[k]) for k in FEATURES]
            if not all(math.isfinite(v) for v in x) or not -1 <= x[0] <= 1 or x[2] not in (0, 1): raise ValueError()
            values.append(x)
        except (KeyError, ValueError, TypeError): invalid += 1
    return np.asarray(values, dtype=float).reshape((-1, 3)), invalid


def probability_errors(rows):
    count, ids = 0, set()
    for row in rows:
        try:
            h,a = float(row['home_win_probability']),float(row['away_win_probability'])
            if row['game_id'] in ids: raise ValueError()
            ids.add(row['game_id'])
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in (h,a)) or not math.isclose(h+a, 1, abs_tol=1e-12): raise ValueError()
        except (KeyError, ValueError, TypeError): count += 1
    return count


def quality(quality_report, eligibility, rows, predictions, source_observed, as_of):
    c = quality_report['counts']
    if any(type(c.get(k)) is not int or c[k] < 0 for k in ('input','retained','excluded','quarantined')) or c['input'] != c['retained']+c['excluded']+c['quarantined']:
        raise ContractError('Invalid normalization accounting.')
    if eligibility['eligible'] != len(rows) or len(rows)+len(eligibility['rejected']) != c['retained'] or len(predictions) != len(rows):
        raise ContractError('Prediction/eligibility accounting differs.')
    reasons = Counter(reason for row in eligibility['rejected'] for reason in row['reasons'])
    missing = sum(any('missing_' in reason and '_history' in reason for reason in row['reasons']) for row in eligibility['rejected'])
    _, invalid_features = feature_values(rows)
    invalid_probabilities = probability_errors(predictions)
    age = (instant(as_of)-instant(source_observed)).total_seconds()
    if age < 0: raise ContractError('Selected source observation follows monitoring as_of.')
    rates = {'quarantine_rate': c['quarantined']/c['input'] if c['input'] else None,
             'exclusion_rate': (c['excluded']+len(eligibility['rejected']))/c['input'] if c['input'] else None,
             'missing_history_rate': missing/c['retained'] if c['retained'] else None}
    issues = []
    for name, number in rates.items():
        if number is not None and number > POLICY[name]: issues.append({'code': name, 'severity': 'warning', 'count': number})
    if age > POLICY['maximum_age_seconds'] or reasons.get('stale_schedule_observation'): issues.append({'code':'stale_observation','severity':'warning','count':age})
    if any('cutoff' in r or 'previous_schedule_started' in r for r in reasons): issues.append({'code':'cutoff_exclusions','severity':'info','count':sum(v for r,v in reasons.items() if 'cutoff' in r or 'previous_schedule_started' in r)})
    if not rows: issues.append({'code':'zero_eligible_rows','severity':'info','count':0})
    if invalid_features: issues.append({'code':'invalid_features','severity':'critical','count':invalid_features})
    if invalid_probabilities: issues.append({'code':'invalid_probabilities','severity':'critical','count':invalid_probabilities})
    return {'state':'measured','counts':c,'eligible':len(rows),'feature_rejected':len(eligibility['rejected']),
            'reasons':dict(reasons),'rates':rates,'source_age_seconds':age,'invalid_features':invalid_features,
            'invalid_probabilities':invalid_probabilities,'issues':issues}


def distributions(training, scoring):
    reference, bad_ref = feature_values(training); selected, bad_score = feature_values(scoring)
    if bad_ref or bad_score: return {'state':'failed','invalid_rows':bad_ref+bad_score,'features':{}}
    sufficient = min(len(reference),len(selected)) >= POLICY['minimum_distribution_rows']
    results = {}
    for i,name in enumerate(FEATURES):
        x,y = reference[:,i], selected[:,i]
        result = {'reference_n':len(x),'scoring_n':len(y),'reference_mean':float(x.mean()) if len(x) else None,
                  'scoring_mean':float(y.mean()) if len(y) else None,'state':'measured' if sufficient else 'insufficient_data','changed':False}
        if len(x) and len(y):
            if name == 'home_field':
                difference = abs(float(y.mean()-x.mean()))
                result.update(kind='binary',rate_difference=difference,reference_counts=[int((x==v).sum()) for v in (0,1)],scoring_counts=[int((y==v).sum()) for v in (0,1)])
                result['changed'] = sufficient and difference > POLICY['binary_rate_difference']
            elif np.ptp(x) <= 1e-12:
                outside = float((~np.isclose(y,x[0],rtol=0,atol=1e-12)).mean())
                result.update(kind='constant_reference',reference_value=float(x[0]),outside_reference_rate=outside)
                result['changed'] = sufficient and outside > 0.10
            else:
                cuts = np.unique(np.quantile(x,np.arange(0.1,1,0.1)))
                bins = np.r_[-np.inf,cuts,np.inf]
                a,b = np.histogram(x,bins)[0],np.histogram(y,bins)[0]
                p,q = (a+0.5)/(len(x)+0.5*len(a)),(b+0.5)/(len(y)+0.5*len(b))
                psi = float(((q-p)*np.log(q/p)).sum())
                result.update(kind='numeric',training_cutpoints=cuts.tolist(),psi=psi,smoothing=0.5)
                result['changed'] = sufficient and psi > POLICY['numeric_psi']
        results[name] = result
    return {'state':'measured' if sufficient else 'insufficient_data','minimum_rows':POLICY['minimum_distribution_rows'],'features':results,
            'interpretation':'Distribution indicators are investigation heuristics, not concept-drift or retraining evidence.'}


def performance(predictions, outcomes, windows, as_of, holdout):
    """Outcome dictionaries are observation records; they are never passed to feature construction."""
    if probability_errors(predictions): return {'state':'failed','metrics':None,'reason':'invalid_probabilities','windows':[]}
    if len({r['game_id'] for r in predictions}) != len(predictions): raise ContractError('Duplicate prediction identity.')
    latest = {}
    for row in outcomes:
        key = str(row['game_id'])
        if instant(row['observed_at']) > instant(as_of): raise ContractError('Outcome observed after monitoring as_of.')
        if key in latest:
            previous = latest[key]
            if row['observed_at'] == previous['observed_at'] and row != previous: raise ContractError('Conflicting same-time outcomes.')
        if key not in latest or instant(row['observed_at']) > instant(latest[key]['observed_at']): latest[key] = row
    joined, pending, mismatched = [], 0, 0
    for row in predictions:
        outcome = latest.get(str(row['game_id']))
        if outcome is None or not outcome['completed']: pending += 1; continue
        if any(str(outcome[k]) != str(row[k]) for k in ('season','week','home_id','away_id')):
            mismatched += 1; continue
        if instant(outcome['observed_at']) <= instant(row['cutoff']) or instant(outcome['start_date']) != instant(row['cutoff']):
            mismatched += 1; continue
        if outcome['home_points'] == outcome['away_points']: mismatched += 1; continue
        joined.append((row,int(outcome['home_points']>outcome['away_points'])))
    reports = []
    for window in windows:
        eligible = [r for r in predictions if instant(window['start']) <= instant(r['cutoff']) < instant(window['end'])]
        matched = [(r,y) for r,y in joined if instant(window['start']) <= instant(r['cutoff']) < instant(window['end'])]
        coverage = len(matched)/len(eligible) if eligible else None
        state = 'pending' if not matched else 'insufficient_data'
        scores, calibration = None, None
        if len(matched) >= POLICY['minimum_labels'] and coverage >= POLICY['minimum_outcome_coverage']:
            scores,calibration = evaluate_probabilities([y for r,y in matched],[float(r['home_win_probability']) for r,y in matched]);state='measured'
        reports.append(dict(window,state=state,eligible=len(eligible),matched=len(matched),coverage=coverage,metrics=scores,calibration=calibration))
    return {'state':'measured' if any(w['state']=='measured' for w in reports) else 'pending' if not joined else 'insufficient_data',
            'total_predictions':len(predictions),'matched':len(joined),'pending':pending,'mismatched':mismatched,
            'unmatched_outcome_games':len(set(latest)-{str(r['game_id']) for r in predictions}),
            'windows':reports,'retrospective_holdout_reference':holdout,
            'context':'Immutable predictions joined to later observations; retrospective/unapproved, not verified prospective performance.'}
