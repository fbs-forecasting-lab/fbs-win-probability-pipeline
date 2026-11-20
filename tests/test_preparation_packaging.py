"""Offline infrastructure and package boundaries for the preparation slice."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PreparationPackagingTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('preparation_packaging',ROOT/'bin/package_cloud_preparation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_template_runtime_scan_limit_projection_and_source_allowlist(self):
        module = self.load()
        template = module.validate_template()
        resources = template['Resources']
        self.assertEqual(resources['Preparation']['Properties']['Handler'],'src.pipeline.cloud_preparation.handler')
        self.assertEqual(resources['SelectedGames']['Properties']['TableInput']['Parameters']['projection.selection_id.type'],'injected')
        columns = resources['SelectedGames']['Properties']['TableInput']['StorageDescriptor']['Columns']
        self.assertIn({'Name':'start_epoch_us','Type':'bigint'},columns)
        self.assertTrue(set(('src/features/dataset.py','src/pipeline/prior_season_features.sql')) <= set(module.SOURCE_FILES))
        self.assertFalse(any(p.startswith(('data/','tests/','src/models/')) for p in module.SOURCE_FILES))

    def test_role_has_no_capture_secret_delete_or_catalog_mutation_permissions(self):
        resources = self.load().validate_template()['Resources']
        statements = resources['ExecutionRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        actions = {a for s in statements for a in (s['Action'] if isinstance(s['Action'],list) else [s['Action']])}
        self.assertFalse(any(a.startswith(('secretsmanager:','lambda:','glue:Create','glue:Update','glue:Delete')) for a in actions))
        self.assertNotIn('s3:DeleteObject',actions)
        self.assertNotIn('s3:*',actions)
        self.assertNotIn('athena:*',actions)
        denies = [s for s in statements if s['Effect']=='Deny']
        self.assertEqual(denies[0]['Condition'],{'StringNotEquals':{'s3:if-none-match':'*'}})
        variables = resources['Preparation']['Properties']['Environment']['Variables']
        self.assertNotIn('CFBD_SECRET_ARN',variables)

    def test_recovery_template_denies_start_and_keeps_runtime_limits(self):
        resources = self.load().validate_template()['Resources']
        function = resources['Preparation']['Properties']
        self.assertEqual(function['Environment']['Variables']['PREPARATION_RECOVERY_ONLY'], 'true')
        self.assertEqual(function['ReservedConcurrentExecutions'], 1)
        statements = resources['ExecutionRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        self.assertFalse(any(s['Effect']=='Allow' and 'athena:StartQueryExecution' in s['Action'] for s in statements))
        self.assertTrue(any(s['Effect']=='Deny' and 'athena:StartQueryExecution' in s['Action'] for s in statements))
