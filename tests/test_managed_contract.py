"""Offline exact-request, scoped-policy and ambiguous-submission safeguards."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from botocore.config import Config
from src.models import baseline
from src.pipeline import managed_contract as contract
from src.pipeline.run_contract import ContractError


class ManagedContractTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('offline')))
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.spec=contract.TrainingSpec('123456789012','synthetic-project-bucket','project',
            'a'*64,'sha256:'+'b'*64,'synthetic-managed-01','c'*64)
        self.request=contract.build_training_request(self.spec)
        self.client=Mock()
        self.client.meta=SimpleNamespace(config=contract.sdk_config())
        self.client.create_training_job.return_value={'TrainingJobArn':self.spec.job_arn}

    def submit(self, request=None, journal=None):
        request=self.request if request is None else request
        return contract.submit_once(self.client,request,journal or self.root/'submit.json',contract.request_sha256(request))

    def test_exact_request_sdk_shape_limits_and_scope(self):
        self.assertEqual(contract.validate_request(self.request),self.request)
        self.assertEqual(self.request['StoppingCondition'],{'MaxRuntimeInSeconds':300})
        self.assertEqual(self.request['ResourceConfig'],{'InstanceType':'ml.m5.large','InstanceCount':1,'VolumeSizeInGB':5})
        self.assertNotIn('RetryStrategy',self.request)
        policy=contract.training_role_policy(self.spec)
        reads=policy['Statement'][0]['Resource']
        self.assertEqual({p.rsplit('/',1)[1] for p in reads},baseline.DATA_FILES|{'dataset_report.json'})
        self.assertEqual(policy['Statement'][1]['Condition'],{'StringEquals':{'s3:prefix':self.spec.dataset_prefix}})
        puts=[s for s in policy['Statement'] if 's3:PutObject' in s['Action']]
        self.assertEqual(puts[0]['Resource'],[f'arn:aws:s3:::synthetic-project-bucket/project/final-readiness/managed-training/{self.spec.job_name}/output/*'])
        inference=contract.managed_inference_policy(self.spec)
        self.assertFalse(any(a.startswith(('secretsmanager:','athena:')) or 'PutObject' in a for s in inference['Statement'] for a in s['Action']))
        self.assertEqual(contract.training_role_trust(self.spec)['Statement'][0]['Condition']['ArnEquals']['aws:SourceArn'],self.spec.job_arn)

    def test_settings_or_input_change_rejected_before_journal(self):
        for key,value in [('RetryStrategy',{'MaximumRetryAttempts':1}),('EnableNetworkIsolation',False),
                          ('EnableManagedSpotTraining',True),('StoppingCondition',{'MaxRuntimeInSeconds':301}),
                          ('ResourceConfig',{'InstanceType':'ml.g5.xlarge','InstanceCount':1,'VolumeSizeInGB':5}),
                          ('Environment',dict(self.request['Environment'],ALLOW_RETROSPECTIVE_DEMO='false'))]:
            with self.subTest(key=key):
                with self.assertRaises(ContractError):self.submit(dict(self.request,**{key:value}))
        bad=copy.deepcopy(self.request)
        bad['InputDataConfig'][0]['DataSource']['S3DataSource']['S3Uri']='s3://unapproved/path/'
        with self.assertRaises(ContractError):self.submit(bad)
        self.client.create_training_job.assert_not_called()
        self.assertEqual(list(self.root.iterdir()),[])

    def test_success_and_ambiguous_response_consume_entire_directory(self):
        self.assertEqual(self.submit()['TrainingJobArn'],self.spec.job_arn)
        self.assertTrue((self.root/contract.JOURNAL_GUARD).exists())
        newer=copy.deepcopy(self.request);newer['TrainingJobName']='other-managed-job'
        for request,journal in [(self.request,self.root/'submit.json'),(newer,self.root/'new-name.json')]:
            with self.assertRaises(FileExistsError):self.submit(request,journal)
        self.client.create_training_job.assert_called_once()
        other=self.root/'separate';other.mkdir()
        self.client.create_training_job.return_value={}
        with self.assertRaises(ContractError):self.submit(journal=other/'submit.json')
        with self.assertRaises(FileExistsError):self.submit(journal=other/'another.json')
        self.assertEqual(self.client.create_training_job.call_count,2)

    def test_exception_or_interruption_never_retries(self):
        for i,failure in enumerate((TimeoutError('ambiguous'),KeyboardInterrupt())):
            directory=self.root/str(i);directory.mkdir()
            self.client.create_training_job.side_effect=failure
            with self.assertRaises(type(failure)):self.submit(journal=directory/'submit.json')
            with self.assertRaises(FileExistsError):self.submit(journal=directory/'retry.json')
        self.assertEqual(self.client.create_training_job.call_count,2)

    def test_wrong_hash_or_retry_config_does_not_consume_or_call(self):
        with self.assertRaises(ContractError):
            contract.submit_once(self.client,self.request,self.root/'submit.json','0'*64)
        self.client.meta.config=Config(region_name='us-east-1',retries={'total_max_attempts':2})
        with self.assertRaises(ContractError):self.submit()
        self.client.create_training_job.assert_not_called()
        self.assertEqual(list(self.root.iterdir()),[])

    def test_journal_symlink_and_unprotected_parent_refused(self):
        (self.root/'link').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(OSError):self.submit(journal=self.root/'link/submit.json')
        self.root.chmod(0o777)
        try:
            with self.assertRaises(ContractError):self.submit()
        finally:self.root.chmod(0o700)
        self.client.create_training_job.assert_not_called()
