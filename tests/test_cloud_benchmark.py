"""Offline synthetic market capture/comparison, immutable evidence and request refusals."""
from datetime import datetime,timezone
import copy
import json
import os
import unittest
from unittest.mock import Mock,patch

from src.ingestion import odds
from src.pipeline import cloud_benchmark as cloud,insights_contract as contract
from src.pipeline.insights_storage import InsightsStore
from src.pipeline.run_contract import digest,encode,STATUS
from tests import test_monitoring as fixtures
from tests.test_markets import capture_request,snapshot,event,OBS

class BenchmarkAdapterTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.CloudMonitoringTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;self.client=fixture.client;self.store=InsightsStore(self.client,fixture.store.bucket,'project')
        self.capture=capture_request();raw,m=snapshot([event()])
        self.fetch=Mock(return_value=odds.OddsResponse(raw,OBS,OBS,odds.parameters(self.capture),{'x-requests-last':1}))
        self.key=Mock(return_value='synthetic-key-only');self.base='project/stakeholder/market-captures/'+digest(self.capture['run_token'].encode())
    def capture_run(self,event=None,get_key=True):
        return cloud.run(self.capture if event is None else event,self.store,get_key=self.key if get_key else None,fetch=self.fetch)
    def test_capture_raw_manifest_normalization_and_replay_without_second_fetch(self):
        r=self.capture_run();self.assertEqual(r['market_state'],'captured',r);self.assertEqual(r['http_attempts'],1)
        self.assertEqual(r['retained_markets'],1)
        before=dict(self.client.objects);self.client.calls.clear();self.assertEqual(self.capture_run(),r)
        self.assertEqual(self.fetch.call_count,1);self.assertEqual(self.key.call_count,1);self.assertEqual(before,self.client.objects)
        self.assertFalse(any(v[0]=='put' for v in self.client.calls))
        ref={'run_token_sha256':digest(self.capture['run_token'].encode()),'completion_sha256':digest(encode(r))}
        rows,manifest,quality=cloud.market_input(self.store,ref);self.assertEqual(rows[0]['home_probability'],.5)
        for k,v in STATUS.items():self.assertEqual(manifest[k],v)
    def test_missing_secret_refuses_without_fetch_or_s3_write(self):
        before=dict(self.client.objects);r=self.capture_run(get_key=False)
        self.assertEqual(r['provider_attempts'],0);self.fetch.assert_not_called();self.key.assert_not_called();self.assertEqual(before,self.client.objects)
    def test_secret_failure_is_zero_http_and_never_retried(self):
        self.key.side_effect=RuntimeError('PRIVATE_KEY_DETAILS');r=self.capture_run()
        self.assertEqual(r['market_state'],'unavailable');self.assertEqual(r['http_attempts'],0);self.fetch.assert_not_called()
        self.assertEqual(self.capture_run(),r);self.assertEqual(self.key.call_count,1)
        self.assertNotIn(b'PRIVATE_KEY_DETAILS',b''.join(self.client.objects.values()))
    def test_http_failure_preserves_unavailable_checkpoint_no_retry(self):
        self.fetch.side_effect=RuntimeError('PRIVATE_HTTP_DETAILS');r=self.capture_run()
        self.assertEqual(r['market_state'],'unavailable');self.assertEqual(r['http_attempts'],1)
        self.assertEqual(self.capture_run(),r);self.assertEqual(self.fetch.call_count,1)
    def test_interrupted_capture_does_not_refetch(self):
        self.client.fail_put=self.base+'/response.json';self.assertEqual(self.capture_run()['state'],'failed')
        self.client.fail_put=None;self.assertEqual(self.capture_run()['state'],'attempt_unresolved');self.assertEqual(self.fetch.call_count,1)
    def test_partial_publication_recovers_and_conflict_preserves_objects(self):
        self.client.fail_put=self.base+'/manifest.json';self.assertEqual(self.capture_run()['state'],'failed')
        self.client.fail_put=None;r=self.capture_run();self.assertEqual(r['market_state'],'captured');self.assertEqual(self.fetch.call_count,1)
        before=dict(self.client.objects);self.assertEqual(self.capture_run(dict(self.capture,odds_format='american'))['state'],'failed');self.assertEqual(before,self.client.objects)
    def test_tampered_market_raw_fails_verification(self):
        r=self.capture_run();self.client.objects[self.base+'/raw.json']=b'[]'
        with self.assertRaises(ValueError):cloud.market_input(self.store,{'run_token_sha256':digest(self.capture['run_token'].encode()),'completion_sha256':digest(encode(r))})
    def test_benchmark_verifies_frozen_model_observation_and_outputs_zero_for_late_market(self):
        captured=self.capture_run();source=self.fixture.run_report();weekly=self.fixture.event
        request={'operation':'benchmark','schema_version':1,'run_token':'synthetic-benchmark-01','allow_retrospective_demo':True,
             'weekly_reference':weekly['weekly_reference'],'model_reference':weekly['model_reference'],
             'market_reference':{'run_token_sha256':digest(self.capture['run_token'].encode()),'completion_sha256':digest(encode(captured))},
             'bookmaker':'draftkings','event_map':[],'outcome_sources':[],'as_of':'2026-11-27T00:00:00Z',
             'windows':[{'start':'2026-08-30T00:00:00Z','end':'2026-11-27T00:00:00Z'}]}
        # The synthetic weekly cutoff is August; November odds must remain ineligible.
        with patch.object(self.client,'head_object',create=True,return_value={'LastModified':datetime(2026,8,31,17,tzinfo=timezone.utc)}):
            r=cloud.run(request,self.store);self.assertEqual(r['shared_games'],0,r);self.assertEqual(r['benchmark_state'],'no_aligned_market_data')
            base='project/stakeholder/benchmarks/'+digest(request['run_token'].encode());report=json.loads(self.client.objects[base+'/benchmark.json'])
            self.assertTrue(all('market_observed_at_or_after_cutoff' in v['reasons'] for v in report['rejections']))
            before=dict(self.client.objects);self.client.calls.clear();self.assertEqual(cloud.run(request,self.store),r)
            self.assertFalse(any(v[0]=='put' for v in self.client.calls));self.assertEqual(before,self.client.objects)
        self.assertEqual(self.fetch.call_count,1)
    def test_partial_vector_style_extra_text_unknown_operations_and_bad_windows_refuse(self):
        for bad in (dict(self.capture,comment='unrestricted'),dict(self.capture,allow_retrospective_demo=False),dict(self.capture,window_end=self.capture['window_start']),dict(self.capture,operation='approve')):
            self.assertEqual(self.capture_run(bad)['state'],'failed')
        self.fetch.assert_not_called();self.key.assert_not_called()
    def test_handler_missing_secret_and_wrong_model_refuse_before_clients(self):
        with patch.dict(os.environ,{'MARKET_SECRET_ARN':''}),patch.object(cloud.boto3,'client') as client:
            self.assertEqual(cloud.handler(self.capture,None)['provider_attempts'],0);client.assert_not_called()
