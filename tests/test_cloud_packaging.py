"""Local deployment boundaries; never invoke CloudFormation or install packages."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('package_cloud_ingestion',ROOT/'bin/package_cloud_ingestion.py')
package=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


class CloudPackagingTests(unittest.TestCase):
    def test_template_resources_limits_no_schedule_bucket_or_secret_creation(self):
        template=package.validate_template()
        resources=template['Resources']
        self.assertEqual(len(resources),4)
        self.assertEqual(resources['Logs']['Properties']['RetentionInDays'],14)
        self.assertEqual(resources['Logs']['DeletionPolicy'],'Retain')
        self.assertNotIn('Events',resources['Ingestion']['Properties'])
        env=resources['Ingestion']['Properties']['Environment']['Variables']
        self.assertEqual(set(env),{'FBS_S3_BUCKET','FBS_S3_PREFIX','CFBD_SECRET_ARN'})
        self.assertEqual(resources['Ingestion']['Properties']['Handler'],'src.pipeline.cloud_ingestion.handler')

    def test_permissions_scoped_no_delete_invoke_or_policy_mutation(self):
        t=package.validate_template()
        statements=t['Resources']['ExecutionRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        actions=[]
        for s in statements:
            if 'Fn::If' in s:s=s['Fn::If'][1]
            action=s['Action'];actions.extend([action] if isinstance(action,str) else action)
            self.assertNotEqual(s['Resource'],'*')
        self.assertEqual(set(actions),{'s3:GetBucketPublicAccessBlock','s3:GetObject','s3:PutObject','s3:ListBucket',
            'secretsmanager:GetSecretValue','logs:CreateLogStream','logs:PutLogEvents','kms:Decrypt','kms:GenerateDataKey'})
        listing=next(s for s in statements if s.get('Action')==['s3:ListBucket'])
        self.assertEqual(listing['Condition']['NumericLessThanEquals'], {'s3:max-keys':'1'})
        self.assertEqual(t['Resources']['ExecutionRole']['Properties']['RoleName'], {'Fn::Sub':'${FunctionName}-execution'})

    def test_package_allowlist_and_project_pins_unchanged(self):
        self.assertEqual(len(package.SOURCE_FILES),10)
        self.assertTrue(all(p.endswith('.py') and p.startswith('src/') for p in package.SOURCE_FILES))
        self.assertFalse(any('/models/' in p or '/dataset.py' in p or 'notebook' in p for p in package.SOURCE_FILES))
        cloud=dict(line.split('==') for line in (ROOT/'infra/cloud-ingestion-requirements.txt').read_text().splitlines())
        project=dict(line.split('==') for line in (ROOT/'requirements.txt').read_text().splitlines())
        for name in cloud.keys() & project.keys():self.assertEqual(cloud[name],project[name])
        self.assertFalse({'numpy','pandas','scipy','scikit-learn','jupyter'} & cloud.keys())
