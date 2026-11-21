"""Offline scope checks for provider isolation, conditional writes and actual helper probes."""
import importlib.util
import json
import fnmatch
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class StakeholderPackagingTests(unittest.TestCase):
    def setUp(self):self.t=json.loads((ROOT/'infra/cloud-stakeholder.yaml').read_text())
    def statements(self,role):return [s for s in self.t['Resources'][role]['Properties']['Policies'][0]['PolicyDocument']['Statement'] if 'Effect' in s]
    def test_roles_cannot_start_predecessors_write_source_or_send_notifications(self):
        for role in ('ExplanationRole','BenchmarkRole'):
            statements=self.statements(role);actions={a for s in statements if s['Effect']=='Allow' for a in s['Action']}
            self.assertFalse(any(a.startswith(('lambda:','states:','athena:','sns:','scheduler:')) for a in actions))
            writes=[str(s['Resource']) for s in statements if s['Effect']=='Allow' and 's3:PutObject' in s['Action']]
            self.assertTrue(all('/stakeholder/' in v for v in writes))
            self.assertFalse(any('/weekly/' in v or '/raw/' in v or '/monitoring/' in v for v in writes))
        actions={a for s in self.statements('BenchmarkRole') if s['Effect']=='Allow' for a in s['Action']};self.assertNotIn('bedrock:InvokeModel',actions)
    def test_only_exact_first_party_regional_model_and_optional_exact_secret(self):
        calls=[s for s in self.statements('ExplanationRole') if 'bedrock:InvokeModel' in s['Action']]
        self.assertEqual(calls[0]['Resource'],{'Fn::Sub':'arn:${AWS::Partition}:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0'})
        self.assertEqual(self.t['Parameters']['MarketSecretArn']['Default'],'')
        optional=self.t['Resources']['BenchmarkRole']['Properties']['Policies'][0]['PolicyDocument']['Statement'][-1]['Fn::If']
        self.assertEqual(optional[1]['Resource'],{'Ref':'MarketSecretArn'});self.assertEqual(optional[1]['Action'],['secretsmanager:GetSecretValue'])
    def test_actual_explanation_optional_probes_match_max_one_policy(self):
        from tests.test_explanations import ExplanationTests
        from tests.test_cloud_weekly import WeeklyS3
        listing=next(s for s in self.statements('ExplanationRole') if 's3:ListBucket' in s['Action'])
        self.assertEqual(listing['Condition']['NumericLessThanEquals'],{'s3:max-keys':'1'})
        patterns=[s['Fn::Sub'].replace('${ProjectPrefix}','project') for s in listing['Condition']['StringLike']['s3:prefix']]
        f=ExplanationTests();f.setUp()
        try:
            original=WeeklyS3.list_objects_v2
            def guarded(client,**kwargs):
                if kwargs['MaxKeys']>1 or not any(fnmatch.fnmatchcase(kwargs['Prefix'],p) for p in patterns):raise AssertionError('Unsupported optional probe')
                return original(client,**kwargs)
            with patch.object(WeeklyS3,'list_objects_v2',guarded):self.assertEqual(f.run_adapter()['state'],'completed')
        finally:f.doCleanups()
    def test_packager_source_scope_and_no_delivery_or_schedules(self):
        spec=importlib.util.spec_from_file_location('stakeholder_package',ROOT/'bin/package_cloud_stakeholder.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
        p.validate_template();self.assertEqual(len(p.SOURCE_FILES),37)
        self.assertTrue(all(not n.startswith(('data/','tests/')) for n in p.SOURCE_FILES))
