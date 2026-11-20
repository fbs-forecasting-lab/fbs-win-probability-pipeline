"""Offline workflow budget, schedule identity, package scope and IAM boundaries."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeeklyPackagingTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads((ROOT/'infra/cloud-weekly.yaml').read_text())
        self.resources = self.template['Resources']

    def test_bounded_workflow_uses_explicit_request_without_automatic_retries(self):
        definition = self.resources['Workflow']['Properties']['Definition']
        states = definition['States']
        self.assertEqual(self.resources['Workflow']['Properties']['StateMachineType'], 'STANDARD')
        self.assertEqual(states['Advance']['InputPath'], '$.request')
        self.assertNotIn('Retry', states['Advance'])
        # Interpret the budget for a perpetually pending stage: exactly eight advances.
        polls, calls = 0, 0
        while True:
            calls += 1
            if polls >= states['Budget']['Choices'][0]['NumericGreaterThanEquals']: break
            polls += 1
        self.assertEqual(calls, 8)
        self.assertEqual(states['Wait']['Seconds'], 15)
        self.assertEqual(states['Outcome']['Default'], 'Failed')
        self.assertEqual(states['Failed']['Type'], 'Fail')

    def test_disabled_schedule_has_fixed_run_identity_and_no_retry_or_week_rollover(self):
        props = self.resources['Schedule']['Properties']
        self.assertEqual(props['State'], 'DISABLED')
        self.assertEqual(props['ScheduleExpressionTimezone'], 'UTC')
        self.assertEqual(props['Target']['RetryPolicy']['MaximumRetryAttempts'], 0)
        text, bindings = props['Target']['Input']['Fn::Sub']
        rendered = text.replace('${Workflow}', 'arn:example:workflow').replace('${RunName}', 'fixed-week-token')
        rendered = rendered.replace('${EncodedInput}', json.dumps(json.dumps({'season': 2026, 'week': 12, 'run_token': 'fixed-week-token'})))
        payload = json.loads(rendered)
        self.assertEqual(payload['Name'], 'fixed-week-token')
        self.assertEqual(json.loads(payload['Input'])['week'], 12)
        self.assertIn('ScheduleInput', str(bindings))

    def test_worker_cannot_train_query_change_bucket_or_write_existing_data(self):
        policy = self.resources['WeeklyRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        allows = [s for s in policy if s['Effect'] == 'Allow']
        actions = {a for s in allows for a in s['Action']}
        self.assertFalse(any(a.startswith(('athena:', 'secretsmanager:', 'glue:')) for a in actions))
        self.assertNotIn('s3:DeleteObject', actions)
        self.assertNotIn('s3:PutBucketPolicy', actions)
        writes = [s for s in allows if 's3:PutObject' in s['Action']]
        self.assertTrue(all('/weekly/runs/' in str(s['Resource']) for s in writes))
        invokes = [s for s in allows if 'lambda:InvokeFunction' in s['Action']]
        self.assertEqual([s['Resource'] for s in invokes], [{'Ref': 'IngestionFunctionArn'}])

    def test_packager_retains_original_dependencies_and_allowlists_only_sources(self):
        spec = importlib.util.spec_from_file_location('weekly_packager', ROOT/'bin/package_cloud_weekly.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.validate_template()
        self.assertEqual(len(module.SOURCE_FILES), 24)
        self.assertTrue(all(n.startswith('src/') for n in module.SOURCE_FILES))
        self.assertIn('src/pipeline/preparation_identity_v1.json', module.SOURCE_FILES)
        self.assertNotIn('src/pipeline/deployment_preflight.py', module.SOURCE_FILES)
