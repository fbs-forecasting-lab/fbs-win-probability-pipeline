"""Entirely fictional odds, events and outcomes; no market data or provider access."""
import copy
import json
import math
import unittest
from unittest.mock import Mock,patch

from src.ingestion import odds
from src.features import markets
from src.pipeline.run_contract import encode
from src.evaluation.metrics import evaluate_probabilities

OBS='2026-11-20T12:00:00Z';CUTOFF='2026-11-20T18:00:00Z';KICKOFF='2026-11-25T18:00:00Z';ASOF='2026-11-27T00:00:00Z'
WINDOWS=[{'start':'2026-11-25T00:00:00Z','end':ASOF}]

def capture_request():return {'operation':'capture_market','schema_version':1,'run_token':'synthetic-market-01','allow_retrospective_demo':True,'window_start':'2026-11-21T00:00:00Z','window_end':'2026-11-28T00:00:00Z','odds_format':'decimal'}
def event(i=1):
    return {'id':f'fictional-event-{i}','sport_key':'americanfootball_ncaaf','home_team':f'Fictional Home {i}','away_team':f'Fictional Away {i}','commence_time':KICKOFF,
            'bookmakers':[{'key':'draftkings','last_update':OBS,'markets':[{'key':'h2h','last_update':OBS,'outcomes':[{'name':f'Fictional Home {i}','price':2.0},{'name':f'Fictional Away {i}','price':2.0}]}]}]}
def snapshot(events,observed=OBS):
    raw=encode(events);r=odds.OddsResponse(raw,observed,observed,odds.parameters(capture_request()),{'x-requests-last':1})
    return raw,odds.manifest(r)
def fixtures(n=1):
    events=[event(i) for i in range(1,n+1)];pred=[];mapping=[];outcomes=[]
    for i,e in enumerate(events,1):
        home=bool(i%2);p=.8 if home else .2
        pred.append({'game_id':str(i),'season':'2026','week':'13','home_id':str(100+i),'away_id':str(200+i),'cutoff':KICKOFF,'home_win_probability':p,'away_win_probability':1-p})
        mapping.append({'game_id':str(i),'home_id':str(100+i),'away_id':str(200+i),'market_event_id':e['id'],'market_home':e['home_team'],'market_away':e['away_team']})
        outcomes.append({'game_id':str(i),'season':2026,'week':13,'home_id':100+i,'away_id':200+i,'start_date':KICKOFF,'observed_at':'2026-11-26T12:00:00Z','completed':True,'home_points':21 if home else 7,'away_points':14})
    raw,m=snapshot(events);rows,q=markets.normalize(raw,m)
    return pred,mapping,outcomes,rows
def compare(pred,mapping,rows,labels=None,**kwargs):
    values={'forecast_cutoff':CUTOFF,'model_observed_at':OBS,'market_observed_at':OBS,'as_of':ASOF,'windows':WINDOWS,'outcomes':[] if labels is None else labels};values.update(kwargs)
    return markets.compare(pred,rows,mapping,'draftkings',**values)

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP network')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send',side_effect=AssertionError('No AWS network')))
    def test_american_decimal_and_proportional_overround(self):
        self.assertAlmostEqual(markets.implied(-110,'american'),110/210)
        self.assertAlmostEqual(markets.implied(150,'american'),.4)
        r=markets.fair_probabilities(1.91,1.91,'decimal');self.assertEqual(r['home_probability'],.5);self.assertAlmostEqual(r['overround'],2/1.91-1)
        self.assertEqual(r['home_probability']+r['away_probability'],1)
        self.assertLess(markets.fair_probabilities(2.1,2.1,'decimal')['overround'],0)
    def test_invalid_prices_are_rejected(self):
        for value,fmt in [(0,'american'),(-99,'american'),(99,'american'),(True,'decimal'),(1,'decimal'),(float('nan'),'decimal'),(float('inf'),'american')]:
            with self.subTest(value=value),self.assertRaises(ValueError):markets.implied(value,fmt)
    def test_manifest_hash_and_all_timestamps_are_preserved(self):
        raw,m=snapshot([event()]);rows,q=markets.normalize(raw,m)
        self.assertEqual(q['retained_markets'],1);self.assertEqual(rows[0]['raw_sha256'],m['raw_sha256'])
        self.assertEqual(rows[0]['market_updated_at'],OBS);self.assertEqual(rows[0]['bookmaker_updated_at'],OBS)
        with self.assertRaises(ValueError):markets.normalize(raw+b' ',m)
    def test_missing_market_timestamp_never_uses_bookmaker_or_retrieval_time(self):
        e=event();del e['bookmakers'][0]['markets'][0]['last_update'];raw,m=snapshot([e]);rows,q=markets.normalize(raw,m)
        self.assertEqual(rows,[]);self.assertEqual(q['exclusions'][0]['reason'],'missing_market_timestamp')
    def test_duplicate_events_or_bookmakers_are_ambiguous(self):
        e=event();raw,m=snapshot([e,e]);rows,q=markets.normalize(raw,m);self.assertEqual(rows,[])
        e=event();e['bookmakers'].append(copy.deepcopy(e['bookmakers'][0]));raw,m=snapshot([e]);self.assertEqual(markets.normalize(raw,m)[0],[])
    def test_three_way_wrong_names_and_future_updates_are_excluded(self):
        for change in ('draw','name','future'):
            e=event();market=e['bookmakers'][0]['markets'][0]
            if change=='draw':market['outcomes'].append({'name':'Draw','price':3})
            if change=='name':market['outcomes'][0]['name']='Unrelated Team'
            if change=='future':market['last_update']='2026-11-21T12:00:00Z'
            raw,m=snapshot([e]);self.assertEqual(markets.normalize(raw,m)[0],[])
    def test_probability_differences_without_labels_are_not_performance(self):
        p,m,o,q=fixtures(2);r=compare(p,m,q)
        self.assertEqual(r['shared_games'],2);self.assertEqual(r['paired_performance']['state'],'pending')
        self.assertIsNone(r['paired_performance']['windows'][0]['model']);self.assertAlmostEqual(r['differences'][0]['model_minus_market'],.3)
    def test_current_odds_do_not_recreate_old_cutoff_even_with_old_quote_timestamp(self):
        p,m,o,q=fixtures();q[0]['retrieved_at']='2026-11-21T12:00:00Z'
        r=compare(p,m,q,market_observed_at=q[0]['retrieved_at'])
        self.assertEqual(r['shared_games'],0);self.assertIn('market_observed_at_or_after_cutoff',r['rejections'][0]['reasons'])
    def test_cutoff_equality_and_late_model_are_rejected(self):
        p,m,o,q=fixtures();q[0]['retrieved_at']=CUTOFF
        self.assertEqual(compare(p,m,q,market_observed_at=CUTOFF)['shared_games'],0)
        p,m,o,q=fixtures();self.assertEqual(compare(p,m,q,model_observed_at=CUTOFF)['shared_games'],0)
        self.assertEqual(compare(p,m,q,forecast_cutoff=KICKOFF)['shared_games'],0)
    def test_identity_schedule_and_explicit_mapping_mismatches(self):
        p,m,o,q=fixtures();q[0]['home']='Wrong Home';self.assertEqual(compare(p,m,q)['shared_games'],0)
        p,m,o,q=fixtures();q[0]['kickoff']='2026-11-25T19:00:00Z';self.assertEqual(compare(p,m,q)['shared_games'],0)
        p,m,o,q=fixtures();m[0]['away_id']='999'
        with self.assertRaises(ValueError):compare(p,m,q)
    def test_missing_mapping_bookmaker_and_duplicate_mapping_remain_gaps(self):
        p,m,o,q=fixtures();self.assertEqual(compare(p,[],q)['market_coverage'],0)
        q[0]['bookmaker']='otherbook';self.assertEqual(compare(p,m,q)['shared_games'],0)
        with self.assertRaises(ValueError):compare(p,m+m,q)
    def test_paired_metrics_use_exact_shared_labelled_cohort(self):
        p,m,o,q=fixtures(40);r=compare(p,m[:30],q,o)
        self.assertEqual(r['shared_games'],30);self.assertEqual(r['market_coverage'],.75)
        window=r['paired_performance']['windows'][0];self.assertEqual(window['matched'],30)
        expected,_=evaluate_probabilities([int(v['home_points']>v['away_points']) for v in o[:30]],[v['home_win_probability'] for v in p[:30]])
        self.assertEqual(window['model'],expected);self.assertAlmostEqual(window['market']['brier_score'],.25)
        self.assertAlmostEqual(window['market_minus_model']['brier_score'],.21)
    def test_sparse_or_mismatched_outcomes_do_not_produce_paired_metrics(self):
        p,m,o,q=fixtures(40);o[0]['away_id']=999;r=compare(p,m,q,o[:30])
        self.assertEqual(r['paired_performance']['state'],'insufficient_data');self.assertIsNone(r['paired_performance']['windows'][0]['model'])
    def test_observations_after_asof_are_refused(self):
        p,m,o,q=fixtures()
        with self.assertRaises(ValueError):compare(p,m,q,market_observed_at='2026-12-01T12:00:00Z')
    def test_http_request_is_one_attempt_no_redirects_and_redacts_failures(self):
        raw,_=snapshot([event()]);response=Mock(status_code=200,headers={'x-requests-last':'1','x-requests-remaining':'499'})
        response.iter_content.return_value=[raw];session=Mock();session.get.return_value.__enter__=Mock(return_value=response);session.get.return_value.__exit__=Mock(return_value=False)
        r=odds.fetch_moneylines(capture_request(),'synthetic-key-only',session=session,clock=lambda:OBS)
        self.assertEqual(r.raw,raw);session.get.assert_called_once();self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
        self.assertNotIn('apiKey',r.parameters);self.assertEqual(r.quota['x-requests-last'],1)
