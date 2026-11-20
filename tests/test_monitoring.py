"""Synthetic offline monitoring, delayed labels, immutable alerts and human review."""

import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

from src.pipeline import cloud_monitoring as cloud, cloud_review, monitor_contract as contract, monitoring_metrics as metrics
from src.pipeline.monitor_storage import MonitorStore, alert
from src.pipeline.run_contract import digest,encode,STATUS
from tests import test_cloud_weekly as weekly_fixtures


def features(n=60, shift=0):
    return [{'prior_win_pct_diff':0.1+shift,'prior_avg_margin_diff':i/10+shift*20,'home_field':i%2} for i in range(n)]


def labelled(n=40):
    predictions=[];outcomes=[]
    for i in range(n):
        r={'game_id':str(i),'season':'2026','week':'13','home_id':'10','away_id':'20','cutoff':'2026-11-25T18:00:00Z',
           'home_win_probability':str(.8 if i%2 else .2),'away_win_probability':str(.2 if i%2 else .8)}
        predictions.append(r);outcomes.append({'game_id':str(i),'season':2026,'week':13,'home_id':10,'away_id':20,
            'start_date':r['cutoff'],'observed_at':'2026-11-26T12:00:00Z','completed':True,'home_points':21 if i%2 else 7,'away_points':14})
    return predictions,outcomes


class MonitoringMetricsTests(unittest.TestCase):
    def test_numeric_shift_binary_change_and_constant_reference(self):
        a=features();b=features(shift=.7)
        result=metrics.distributions(a,b)
        self.assertEqual(result['state'],'measured')
        self.assertTrue(result['features']['prior_win_pct_diff']['changed'])
        self.assertTrue(result['features']['prior_avg_margin_diff']['changed'])
        for row in b:row['home_field']=1
        self.assertTrue(metrics.distributions(a,b)['features']['home_field']['changed'])
        self.assertFalse(metrics.distributions(a,a)['features']['prior_win_pct_diff']['changed'])

    def test_small_empty_and_malformed_features_are_not_measured_drift(self):
        self.assertEqual(metrics.distributions(features(),[])['state'],'insufficient_data')
        self.assertEqual(metrics.distributions(features(),features(4,.7))['state'],'insufficient_data')
        invalid=features();invalid[0]['home_field']=.5
        self.assertEqual(metrics.distributions(features(),invalid)['state'],'failed')

    def test_performance_reuses_existing_metrics_and_chronological_coverage(self):
        p,o=labelled();windows=[{'start':'2026-11-25T00:00:00Z','end':'2026-11-27T00:00:00Z'}]
        result=metrics.performance(p,o,windows,'2026-11-27T00:00:00Z',{'context':'synthetic holdout'})
        from src.evaluation.metrics import evaluate_probabilities
        expected,cal=evaluate_probabilities([i%2 for i in range(40)],[float(r['home_win_probability']) for r in p])
        self.assertEqual(result['windows'][0]['metrics'],expected);self.assertEqual(result['windows'][0]['calibration'],cal)
        self.assertEqual(result['matched'],40);self.assertEqual(result['windows'][0]['coverage'],1)

    def test_missing_delayed_and_sparse_labels_are_pending_not_zero_error(self):
        p,o=labelled();windows=[{'start':'2026-11-25T00:00:00Z','end':'2026-11-27T00:00:00Z'}]
        r=metrics.performance(p,[],windows,'2026-11-27T00:00:00Z',{})
        self.assertEqual(r['state'],'pending');self.assertEqual(r['pending'],40);self.assertIsNone(r['windows'][0]['metrics'])
        r=metrics.performance(p,o[:10],windows,'2026-11-27T00:00:00Z',{})
        self.assertEqual(r['state'],'insufficient_data');self.assertIsNone(r['windows'][0]['metrics'])
        p.extend(copy.deepcopy(p[:10]));p[-1]['game_id']='new'
        self.assertEqual(metrics.probability_errors(p),9)
        p,o=labelled(50)
        r=metrics.performance(p,o[:30],windows,'2026-11-27T00:00:00Z',{})
        self.assertEqual(r['windows'][0]['coverage'],.6);self.assertIsNone(r['windows'][0]['metrics'])

    def test_outcome_identity_schedule_revisions_and_future_observations_fail_safely(self):
        p,o=labelled();windows=[{'start':'2026-11-25T00:00:00Z','end':'2026-11-27T00:00:00Z'}]
        o[0]['away_id']=99;o[1]['start_date']='2026-11-25T19:00:00Z'
        r=metrics.performance(p,o,windows,'2026-11-27T00:00:00Z',{})
        self.assertEqual(r['mismatched'],2)
        o[2]['observed_at']='2026-12-01T00:00:00Z'
        with self.assertRaises(ValueError):metrics.performance(p,o,windows,'2026-11-27T00:00:00Z',{})


class CloudMonitoringTests(unittest.TestCase):
    def setUp(self):
        fixture=weekly_fixtures.WeeklyTests();fixture.setUp();self.addCleanup(fixture.doCleanups);self.fixture=fixture
        result=fixture.finish();self.assertEqual(result['state'],'withheld')
        self.store=MonitorStore(fixture.client,fixture.store.bucket,'project');self.client=fixture.client
        token=digest(fixture.event['run_token'].encode());base='project/weekly/runs/'+token
        fixture.metadata.update(training_seasons=[2022,2023,2024],counts={'train':6,'holdout':2,'prediction':2})
        self.model=self.enterContext(patch.object(cloud,'model_evidence',return_value=(fixture.metadata,{'model':{'brier_score':.2,'log_loss':.6,'accuracy':.7}})))
        self.event={'operation':'report','schema_version':1,'run_token':'synthetic-monitor-01','weekly_reference':{'run_token_sha256':token,'summary_sha256':digest(self.client.objects[base+'/complete.json'])},
            'model_reference':fixture.model_ref,'outcome_sources':[],'as_of':'2026-08-31T20:00:00Z',
            'windows':[{'start':'2026-08-30T00:00:00Z','end':'2026-08-31T20:00:00Z'}],
            'review_reference':None,'allow_retrospective_demo':True,'evidence_mode':'synthetic_test'}
        self.client.calls.clear()

    def run_report(self,event=None):return cloud.report_run(self.event if event is None else event,self.store)

    def report(self,result):
        key=next(k for k in result['artifact_sha256'] if k.endswith('/report.json'))
        return json.loads(self.client.objects[key])

    def test_verified_report_pending_labels_withheld_not_failure_and_safe_display(self):
        r=self.run_report();self.assertEqual(r['state'],'completed',r);report=self.report(r)
        self.assertEqual(report['pipeline_state'],'withheld');self.assertEqual(report['performance']['state'],'pending')
        self.assertEqual(report['performance']['pending'],2);self.assertEqual(report['distributions']['state'],'insufficient_data')
        view=json.loads(next(self.client.objects[k] for k in r['artifact_sha256'] if k.endswith('/stakeholder.json')))
        self.assertEqual(view['technical_rows'],2)
        public=json.dumps(view)
        for private in ('project/','model_id','game_id','Home','Away','reviewer','fictional-course-bucket'):self.assertNotIn(private,public)
        for k,v in STATUS.items():self.assertEqual(report[k],v)

    def test_completed_replay_does_not_write_duplicate_reports_or_alerts(self):
        r=self.run_report();before=dict(self.client.objects);self.client.calls.clear()
        self.assertEqual(self.run_report(),r);self.assertEqual(self.client.objects,before)
        self.assertFalse(any(c[0]=='put' for c in self.client.calls))

    def test_failed_privacy_preflight_cannot_publish_failure_alert_or_direct_alert(self):
        before=dict(self.client.objects)
        with patch.object(self.client,'get_public_access_block',return_value={'PublicAccessBlockConfiguration':{}}):
            result=self.run_report()
            self.assertEqual(result['state'],'failed')
            self.assertNotIn('alert_reference',result)
            with self.assertRaises(ValueError):
                alert(self.store,{'synthetic':True},'privacy_check','critical','Investigate.',simulated=True)
        self.assertEqual(self.client.objects,before)
        self.assertFalse(any(c[0]=='put' for c in self.client.calls))

    def test_partial_publication_recovery_and_completed_missing_artifact_fail(self):
        self.client.break_after_put='report.json';self.assertEqual(self.run_report()['state'],'failed')
        r=self.run_report();self.assertEqual(r['state'],'completed',r)
        key=next(k for k in r['artifact_sha256'] if k.endswith('/display.html'));del self.client.objects[key]
        self.assertEqual(self.run_report()['state'],'failed');self.assertNotIn(key,self.client.objects)

    def test_corrupt_input_creates_durable_simulated_failure_alert_without_model_load(self):
        token=self.event['weekly_reference']['run_token_sha256'];key='project/weekly/runs/'+token+'/preparation/rows.json'
        self.client.objects[key]+=b'bad'
        with patch.object(cloud.baseline.joblib,'load',side_effect=AssertionError('Never deserialize')) as load:
            r=self.run_report();self.assertEqual(r['state'],'failed');load.assert_not_called()
        a=json.loads(self.client.objects[r['alert_reference']['key']]);self.assertTrue(a['simulated'])
        self.assertFalse(a['retraining_authorized'])

    def test_conflicting_monitor_token_and_invalid_window_are_refused(self):
        self.run_report()
        self.assertEqual(self.run_report(dict(self.event,as_of='2026-08-31T21:00:00Z'))['stage'],'report_claim')
        self.assertEqual(self.run_report(dict(self.event,windows=[{'start':'2026-08-31','end':'2026-09-01'}]))['stage'],'request_validation')

    def test_execution_failure_object_detected_even_when_lambda_succeeded(self):
        machine='arn:aws:states:region:account:stateMachine:weekly';arn=machine.replace(':stateMachine:',':execution:')+':failed'
        states=Mock();states.describe_execution.return_value={'stateMachineArn':machine,'status':'FAILED'}
        states.get_execution_history.return_value={'events':[{'id':1,'timestamp':datetime(2026,11,20,tzinfo=timezone.utc),'type':'LambdaFunctionSucceeded','lambdaFunctionSucceededEventDetails':{'output':json.dumps({'state':'failed','stage':'preparation'})}}]}
        event={'operation':'execution','schema_version':1,'execution_arn':arn}
        r=cloud.execution_run(event,self.store,states,machine,simulated=True)
        self.assertEqual(r['state'],'completed',r);self.assertEqual(r['application_failure_count'],1)
        a=json.loads(self.client.objects[r['alerts'][0]['key']]);self.assertTrue(a['simulated']);self.assertEqual(a['code'],'application_failure')
        before=dict(self.client.objects);self.client.calls.clear()
        self.assertEqual(cloud.execution_run(event,self.store,states,machine,simulated=True),r)
        self.assertEqual(before,self.client.objects);self.assertFalse(any(c[0]=='put' for c in self.client.calls))

    def test_timeout_and_successful_withheld_execution_are_distinct(self):
        machine='arn:aws:states:region:account:stateMachine:weekly';states=Mock();states.get_execution_history.return_value={'events':[]}
        for status in ('TIMED_OUT','SUCCEEDED','RUNNING'):
            states.describe_execution.return_value={'stateMachineArn':machine,'status':status}
            event={'operation':'execution','schema_version':1,'execution_arn':machine.replace(':stateMachine:',':execution:')+':'+status}
            r=cloud.execution_run(event,self.store,states,machine,simulated=True)
            self.assertEqual(len(r['alerts']),1 if status=='TIMED_OUT' else 0)
            self.assertEqual(r['state'],'pending' if status=='RUNNING' else 'completed')

    def review_event(self,a):
        return {'operation':'review','schema_version':1,'transition_token':'review-token-01','alert_id':a['alert_id'],'alert_sha256':a['sha256'],
            'previous_sequence':0,'previous_sha256':None,'action':'acknowledged','reviewer':'Fictional Reviewer',
            'timestamp':'2026-11-20T22:00:00Z','reason':'investigation_requested','evidence_hashes':[a['sha256']],'simulation':True}

    def test_human_review_chain_replay_conflict_and_no_approval(self):
        a=alert(self.store,{'synthetic':True},'test_quality','warning','Investigate only.',simulated=True)
        event=self.review_event(a);r=cloud_review.review_run(event,self.store,'Fictional Reviewer')
        self.assertEqual(r['state'],'completed',r);self.assertFalse(r['retraining_authorized']);self.assertFalse(r['operational_publication_authorized'])
        before=dict(self.client.objects);self.client.calls.clear();self.assertEqual(cloud_review.review_run(event,self.store,'Fictional Reviewer'),r)
        self.assertEqual(before,self.client.objects);self.assertFalse(any(c[0]=='put' for c in self.client.calls))
        next_event=dict(event,transition_token='review-token-02',previous_sequence=1,previous_sha256=r['sha256'],action='investigating',timestamp='2026-11-20T22:01:00Z',reason='evidence_checked')
        investigated=cloud_review.review_run(next_event,self.store,'Fictional Reviewer');self.assertEqual(investigated['state'],'completed',investigated)
        conflict=dict(next_event,transition_token='review-token-03',reason='followup_needed')
        self.assertEqual(cloud_review.review_run(conflict,self.store,'Fictional Reviewer')['state'],'failed')
        closed=cloud_review.review_run(dict(next_event,transition_token='review-token-04',previous_sequence=2,previous_sha256=investigated['sha256'],action='closed',timestamp='2026-11-20T22:02:00Z',reason='expected_withholding'),self.store,'Fictional Reviewer')
        self.assertEqual(closed['state'],'completed',closed)

    def test_review_identity_invalid_transition_and_handler_errors(self):
        a=alert(self.store,{},'synthetic','warning','Review.',simulated=True);event=self.review_event(a)
        self.assertEqual(cloud_review.review_run(event,self.store,'Another Reviewer')['state'],'failed')
        self.assertEqual(cloud_review.review_run(dict(event,action='closed'),self.store,'Fictional Reviewer')['state'],'failed')
        with patch.object(cloud.boto3,'client') as client:
            with self.assertRaises(RuntimeError):cloud.handler({},None)
            client.assert_not_called()
        with self.assertRaises(RuntimeError):cloud_review.handler({},None)

    def test_selected_review_is_bound_to_analysis_and_display_does_not_expose_identity(self):
        analysis=digest(encode({k:v for k,v in self.event.items() if k not in ('run_token','review_reference')}|{'policy':contract.POLICY}))
        a=alert(self.store,{'analysis_sha256':analysis},'synthetic_quality','warning','Inspect only.',simulated=True)
        reviewed=cloud_review.review_run(self.review_event(a),self.store,'Fictional Reviewer')
        event=dict(self.event,run_token='reviewed-monitor-01',review_reference={'alert_id':a['alert_id'],'sequence':1,'sha256':reviewed['sha256']})
        result=self.run_report(event);self.assertEqual(result['state'],'completed',result)
        report=self.report(result);self.assertEqual(report['review_state'],'selected_alert_acknowledged')
        view=next(self.client.objects[k] for k in result['artifact_sha256'] if k.endswith('/display.html'))
        self.assertNotIn(b'Fictional Reviewer',view);self.assertNotIn(a['alert_id'].encode(),view)

    def test_quality_invalid_probabilities_cutoff_and_staleness_are_observable(self):
        rows=[{'prior_win_pct_diff':.2,'prior_avg_margin_diff':7,'home_field':1}]
        predictions=[{'game_id':'1','home_win_probability':'NaN','away_win_probability':.2}]
        r=metrics.quality({'counts':{'input':3,'retained':2,'excluded':0,'quarantined':1}},
            {'eligible':1,'rejected':[{'reasons':['missing_home_history','schedule_observed_at_or_after_cutoff']}]},
            rows,predictions,'2026-11-18T00:00:00Z','2026-11-20T00:00:00Z')
        codes={i['code'] for i in r['issues']}
        self.assertTrue({'quarantine_rate','missing_history_rate','invalid_probabilities','stale_observation','cutoff_exclusions'}<=codes)

    def test_model_reference_integrity_failure_precedes_any_deserialization(self):
        self.model.stop()
        with patch.object(cloud.baseline.joblib,'load') as load:
            result=self.run_report(dict(self.event,model_reference=dict(self.event['model_reference'],training_receipt_sha256='0'*64)))
            self.assertEqual(result['state'],'failed');load.assert_not_called()

    def test_explicit_simulated_alert_replays_and_cannot_dispose_genuine_alert(self):
        event={'operation':'simulate_alert','schema_version':1,'simulation_token':'monitor-simulation-01','as_of':'2026-11-20T22:30:00Z'}
        env={'WEEKLY_STATE_MACHINE_ARN':'arn:aws:states:region:account:stateMachine:weekly','FBS_S3_BUCKET':self.store.bucket,'FBS_S3_PREFIX':'project','ALLOW_ALERT_SIMULATION':'true'}
        with patch.dict(cloud.os.environ,env),patch.object(cloud.boto3,'client',return_value=self.client):
            result=cloud.handler(event,None);self.assertTrue(result['simulated'])
            before=dict(self.client.objects);self.client.calls.clear();self.assertEqual(cloud.handler(event,None),result)
            self.assertEqual(before,self.client.objects);self.assertFalse(any(c[0]=='put' for c in self.client.calls))
        genuine=alert(self.store,{},'genuine_quality','warning','Review actual evidence.',simulated=False)
        self.assertEqual(cloud_review.review_run(self.review_event(genuine),self.store,'Fictional Reviewer')['state'],'failed')
