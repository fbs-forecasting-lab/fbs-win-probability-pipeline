"""Monitoring IAM prefix contexts, isolated review writes, disabled delivery and package scope."""

import fnmatch
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class MonitoringPackagingTests(unittest.TestCase):
    def setUp(self):self.resources=json.loads((ROOT/'infra/cloud-monitoring.yaml').read_text())['Resources']

    def policy(self,role):return self.resources[role]['Properties']['Policies'][0]['PolicyDocument']['Statement']

    def test_no_pipeline_start_training_query_capture_or_notification_permissions(self):
        for role in ('MonitorRole','ReviewRole'):
            actions={a for s in self.policy(role) if s['Effect']=='Allow' for a in s['Action']}
            self.assertFalse(any(a.startswith(('lambda:','athena:','secretsmanager:','sns:','scheduler:')) for a in actions))
            self.assertNotIn('states:StartExecution',actions);self.assertNotIn('s3:DeleteObject',actions)
        for role,domain in [('MonitorRole','monitoring/'),('ReviewRole','monitoring/')]:
            writes=[s for s in self.policy(role) if s['Effect']=='Allow' and 's3:PutObject' in s['Action']]
            self.assertTrue(all(domain in str(s['Resource']) for s in writes))
        monitor_writes=str([s['Resource'] for s in self.policy('MonitorRole') if s['Effect']=='Allow' and 's3:PutObject' in s['Action']])
        self.assertNotIn('/reviews/',monitor_writes)
        review_writes=str([s['Resource'] for s in self.policy('ReviewRole') if s['Effect']=='Allow' and 's3:PutObject' in s['Action']])
        self.assertNotIn('/runs/',review_writes);self.assertNotIn('/alert.json',review_writes)

    def test_exact_raw_probe_and_limited_list_contexts(self):
        for role in ('MonitorRole','ReviewRole'):
            listing,=[s for s in self.policy(role) if 's3:ListBucket' in s['Action']]
            self.assertEqual(listing['Resource'],{'Fn::Sub':'arn:${AWS::Partition}:s3:::${ProjectBucket}'})
            self.assertEqual(listing['Condition']['NumericLessThanEquals'],{'s3:max-keys':'1'})
            patterns=[s['Fn::Sub'].replace('${ProjectPrefix}','project') for s in listing['Condition']['StringLike']['s3:prefix']]
            self.assertFalse(any(fnmatch.fnmatchcase('unrelated/path',p) for p in patterns))
            if role=='MonitorRole':self.assertTrue(any(fnmatch.fnmatchcase('project/raw/cfbd/games/season=2026/x.manifest.json',p) for p in patterns))
            else:self.assertFalse(any(fnmatch.fnmatchcase('project/raw/cfbd/games/season=2026/x.manifest.json',p) for p in patterns))

    def test_monitor_actual_helper_list_probes_are_supported(self):
        from tests.test_monitoring import CloudMonitoringTests
        from tests.test_cloud_weekly import WeeklyS3
        from tests.test_s3_storage import error
        listing,=[s for s in self.policy('MonitorRole') if 's3:ListBucket' in s['Action']]
        patterns=[s['Fn::Sub'].replace('${ProjectPrefix}','project') for s in listing['Condition']['StringLike']['s3:prefix']]
        original=WeeklyS3.list_objects_v2
        def guarded(client,**kwargs):
            if kwargs['MaxKeys']>1 or not any(fnmatch.fnmatchcase(kwargs['Prefix'],p) for p in patterns):raise error('AccessDenied',403)
            return original(client,**kwargs)
        fixture=CloudMonitoringTests();fixture.setUp()
        try:
            with patch.object(WeeklyS3,'list_objects_v2',guarded):
                self.assertEqual(fixture.run_report()['state'],'completed')
        finally:fixture.doCleanups()

    def test_disabled_event_rule_and_alarms_have_no_delivery_actions(self):
        rule=self.resources['FailureRule']['Properties'];self.assertEqual(rule['State'],'DISABLED')
        self.assertEqual(set(rule['EventPattern']['detail']['status']),{'FAILED','TIMED_OUT','ABORTED'})
        self.assertEqual(rule['Targets'][0]['RetryPolicy']['MaximumRetryAttempts'],0)
        for resource in self.resources.values():
            if resource['Type']=='AWS::CloudWatch::Alarm':
                self.assertFalse(resource['Properties']['ActionsEnabled']);self.assertEqual(resource['Properties']['AlarmActions'],[])
        spec=importlib.util.spec_from_file_location('monitor_packaging',ROOT/'bin/package_cloud_monitoring.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.validate_template();self.assertEqual(len(module.SOURCE_FILES),30)
        self.assertFalse(any(n.startswith(('data/','tests/')) for n in module.SOURCE_FILES))
