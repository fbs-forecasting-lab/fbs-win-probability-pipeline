"""Synthetic provider stubs verify behavior only, never genuine model integration."""
import copy
import json
import os
import unittest
from unittest.mock import Mock,patch

from src.pipeline import cloud_explanation as cloud,explanation_facts,insights_contract as contract
from src.pipeline.insights_storage import InsightsStore
from src.pipeline.run_contract import digest,encode,STATUS
from tests import test_monitoring as fixtures

def provider_response(ids=None):
    return {'output':{'message':{'role':'assistant','content':[{'text':json.dumps({'fact_ids':ids or ['status','performance','limits','quality','holdout']})}]}},
            'stopReason':'end_turn','usage':{'inputTokens':120,'outputTokens':25,'totalTokens':145},'metrics':{'latencyMs':12},'ResponseMetadata':{'RequestId':'synthetic-request-only'}}

class ExplanationTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.CloudMonitoringTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;result=fixture.run_report();assert result['state']=='completed'
        self.client=fixture.client;self.store=InsightsStore(self.client,fixture.store.bucket,'project')
        self.provider=Mock();self.provider.converse.return_value=provider_response()
        self.event={'operation':'explain','schema_version':1,'run_token':'synthetic-explain-01','allow_retrospective_demo':True,
            'monitor_reference':{'run_token_sha256':digest(fixture.event['run_token'].encode()),'completion_sha256':digest(encode(result)),'report_sha256':result['report_sha256']}}
        self.source=dict(self.client.objects);self.base='project/stakeholder/explanations/'+digest(self.event['run_token'].encode())
    def run_adapter(self,event=None):return cloud.run(self.event if event is None else event,self.store,self.provider)
    def test_verified_facts_only_reach_real_adapter_call_and_summary_has_no_provider_prose(self):
        r=self.run_adapter();self.assertEqual(r['explanation_state'],'available',r)
        kwargs=self.provider.converse.call_args.kwargs;payload=json.dumps(kwargs)
        for private in (self.store.bucket,'project/','game_id','model_id','Fictional Reviewer'):self.assertNotIn(private,payload)
        self.assertEqual(kwargs['modelId'],contract.MODEL_ID);self.assertEqual(kwargs['inferenceConfig']['maxTokens'],128)
        self.assertLessEqual(sum(len(x['text'].encode()) for x in kwargs['system'])+len(kwargs['messages'][0]['content'][0]['text'].encode()),6144)
        for k,v in STATUS.items():self.assertEqual(r[k],v)
        for key,raw in self.source.items():self.assertEqual(self.client.objects[key],raw)
        self.assertIn(b'not yet measurable',self.client.objects[self.base+'/display.html'])
    def test_exact_replay_has_no_second_provider_call_or_writes(self):
        r=self.run_adapter();before=dict(self.client.objects);self.client.calls.clear()
        self.assertEqual(self.run_adapter(),r);self.assertEqual(self.provider.converse.call_count,1)
        self.assertEqual(before,self.client.objects);self.assertFalse(any(v[0]=='put' for v in self.client.calls))
    def test_provider_failure_preserves_facts_and_records_unavailable_without_template_fallback(self):
        self.provider.converse.side_effect=RuntimeError('PRIVATE_PROVIDER_DETAILS')
        r=self.run_adapter();self.assertEqual(r['explanation_state'],'unavailable',r)
        self.assertIn(self.base+'/facts.json',self.client.objects)
        self.assertNotIn(b'PRIVATE_PROVIDER_DETAILS',b''.join(self.client.objects.values()))
        self.assertIsNone(json.loads(self.client.objects[self.base+'/explanation.json'])['selection'])
        self.assertEqual(self.run_adapter(),r);self.assertEqual(self.provider.converse.call_count,1)
    def test_unsupported_numbers_or_claims_cannot_reach_display(self):
        response=provider_response();response['output']['message']['content'][0]['text']=json.dumps({'fact_ids':['status','performance','limits'],'summary':'LIVE APPROVED 9999.9%'})
        self.provider.converse.return_value=response
        r=self.run_adapter();self.assertEqual(r['explanation_state'],'unavailable')
        self.assertNotIn(b'9999.9%',self.client.objects[self.base+'/display.html'])
    def test_missing_limits_duplicate_or_unknown_facts_are_refused(self):
        facts=explanation_facts.catalog(self.fixture.report(self.fixture.run_report()))
        for ids in (['status','performance','quality'],['status','performance','limits','limits'],['status','performance','limits','approved_forecast']):
            with self.subTest(ids=ids),self.assertRaises(ValueError):explanation_facts.validate_selection(json.dumps({'fact_ids':ids}),facts)
    def test_truncated_response_or_invalid_usage_is_unavailable(self):
        for response in (dict(provider_response(),stopReason='max_tokens'),dict(provider_response(),usage={'inputTokens':1,'outputTokens':2,'totalTokens':100})):
            with self.subTest(response=response['stopReason']):
                event=dict(self.event,run_token='synthetic-invalid-'+str(response['usage']['totalTokens']))
                self.provider.converse.return_value=response
                self.assertEqual(self.run_adapter(event)['explanation_state'],'unavailable')
    def test_tampered_source_and_unsafe_inputs_refuse_before_provider(self):
        bad=dict(self.event,monitor_reference=dict(self.event['monitor_reference'],report_sha256='0'*64))
        self.assertEqual(self.run_adapter(bad)['state'],'failed');self.provider.converse.assert_not_called()
        self.assertEqual(self.run_adapter(dict(self.event,prompt='unrestricted text'))['state'],'failed')
        self.assertEqual(self.run_adapter(dict(self.event,allow_retrospective_demo=False))['state'],'failed')
        self.provider.converse.assert_not_called()
    def test_conflicting_token_and_damaged_completed_output_do_not_call_provider_again(self):
        r=self.run_adapter();self.assertEqual(r['state'],'completed')
        changed=dict(self.event,monitor_reference=dict(self.event['monitor_reference'],completion_sha256='a'*64))
        self.assertEqual(self.run_adapter(changed)['state'],'failed')
        self.client.objects[self.base+'/facts.json']=b'changed'
        self.assertEqual(self.run_adapter()['state'],'failed');self.assertEqual(self.provider.converse.call_count,1)
    def test_interrupted_capture_never_repeats_external_attempt(self):
        self.client.fail_put=self.base+'/response.json'
        self.assertEqual(self.run_adapter()['state'],'failed');self.assertEqual(self.provider.converse.call_count,1)
        self.client.fail_put=None
        self.assertEqual(self.run_adapter()['state'],'attempt_unresolved');self.assertEqual(self.provider.converse.call_count,1)
    def test_interrupted_publication_recovers_exact_checkpoint_without_provider_call(self):
        self.client.fail_put=self.base+'/explanation.json'
        self.assertEqual(self.run_adapter()['state'],'failed')
        self.client.fail_put=None
        self.assertEqual(self.run_adapter()['state'],'completed');self.assertEqual(self.provider.converse.call_count,1)
    def test_failed_privacy_check_cannot_publish_or_call_provider(self):
        self.client.flags={};before=dict(self.client.objects)
        self.assertEqual(self.run_adapter()['state'],'failed');self.provider.converse.assert_not_called();self.assertEqual(before,self.client.objects)
    def test_source_unknown_text_never_enters_fact_catalog_and_missing_labels_are_not_zero(self):
        report=self.fixture.report(self.fixture.run_report());report['arbitrary']='PRIVATE_UNTRUSTED_TEXT'
        text=json.dumps(explanation_facts.catalog(report));self.assertNotIn('PRIVATE_UNTRUSTED_TEXT',text)
        del report['performance']['pending']
        with self.assertRaises(KeyError):explanation_facts.catalog(report)
    def test_handler_refuses_invalid_config_before_sdk_clients(self):
        with patch.dict(os.environ,{'AWS_REGION':'us-east-1','PROVIDER_MODEL_ID':'wrong'}),patch.object(cloud.boto3,'client') as client:
            with self.assertRaises(RuntimeError):cloud.handler(self.event,None)
            client.assert_not_called()
    def test_insufficient_or_failed_distribution_does_not_invent_zero_change(self):
        report=self.fixture.report(self.fixture.run_report())
        for state in ('failed','insufficient_data'):
            report['distributions']={'state':state,'features':{}}
            text=explanation_facts.catalog(report)['distributions']
            self.assertIn('unavailable',text);self.assertNotIn('0 feature',text)
    def test_measured_distribution_preserves_sample_sizes_and_refuses_disagreement(self):
        report=self.fixture.report(self.fixture.run_report())
        report['distributions']={'state':'measured','features':{n:{'changed':False,'reference_n':60,'scoring_n':40} for n in ('prior_win_pct_diff','prior_avg_margin_diff','home_field')}}
        text=explanation_facts.catalog(report)['distributions'];self.assertIn('60 training rows',text);self.assertIn('40 scoring rows',text)
        report['distributions']['features']['home_field']['scoring_n']=41
        with self.assertRaises(ValueError):explanation_facts.catalog(report)
