"""Synthetic native lineage/parity tests; copy into the pinned Linux image too.

All service evidence is fictional. Passing on the host proves no Linux service
execution. Runtime pins are generated in this process, never patched to match.
"""

import copy
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from src.models import baseline
from src.pipeline import managed_lineage as lineage, managed_training
from src.pipeline.managed_contract import TrainingSpec, build_training_request
from src.pipeline.run_contract import ContractError, digest, encode

ROOT = Path(__file__).resolve().parents[1]
PRODUCERS = ('src/pipeline/model_contract.py', 'src/pipeline/cloud_modeling.py',
             'src/models/baseline.py', 'src/models/predict.py', 'src/features/dataset.py')


def archive(files, extra=(), omit=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz', format=tarfile.USTAR_FORMAT) as tar:
        for name, content in sorted(files.items()):
            if name not in omit:
                member = tarfile.TarInfo(name)
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
        for member, content in extra:
            tar.addfile(member, io.BytesIO(content))
    return buffer.getvalue()


class ManagedLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = {n: (ROOT/n).read_bytes() for n in PRODUCERS}
        for target in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection',
                       'requests.sessions.Session.request', 'botocore.httpsession.URLLib3Session.send'):
            guard = patch(target, side_effect=AssertionError('Offline synthetic tests only'))
            guard.start()
            cls.addClassCleanup(guard.stop)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        spec = importlib.util.spec_from_file_location('managed_synthetic_bin', ROOT/'bin/synthetic_demo.py')
        example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(example)
        example.run('data/processed/example', root=cls.root, allow_retrospective_demo=True)
        cls.original = cls.root/'data/processed/example'
        cls.dataset = cls.original/'dataset'
        report_bytes = (cls.dataset/'dataset_report.json').read_bytes()
        cls.report = json.loads(report_bytes)
        cls.model_dir = cls.root/'managed-model'
        managed_training.run(cls.dataset, cls.model_dir, cls.root/'attempt.json',
                             cls.report['dataset_id'], digest(report_bytes), allow_retrospective_demo=True)
        cls.files = {n: (cls.model_dir/n).read_bytes() for n in lineage.FILES}
        cls.tar = archive(cls.files)
        training_spec = TrainingSpec(account='123456789012', bucket='synthetic-training-bucket',
            prefix='synthetic', dataset_id=cls.report['dataset_id'], image_digest='sha256:'+'a'*64,
            job_name='synthetic-managed-01', report_sha256=digest(report_bytes))
        request = build_training_request(training_spec)
        cls.job = dict(copy.deepcopy(request), TrainingJobStatus='Completed', SecondaryStatus='Completed',
            TrainingJobArn=training_spec.job_arn, ModelArtifacts={'S3ModelArtifacts':
            request['OutputDataConfig']['S3OutputPath']+'/synthetic-managed-01/output/model.tar.gz'})
        # Representative harmless defaults, not a claim about a live API response.
        cls.job['AlgorithmSpecification']['EnableSageMakerMetricsTimeSeries'] = False
        cls.job['ResourceConfig']['KeepAlivePeriodInSeconds'] = 0
        cls.job['OutputDataConfig']['CompressionType'] = 'GZIP'
        cls.job['InputDataConfig'][0]['CompressionType'] = 'None'
        cls.evidence = {'schema_version': 1, 'producer_kind': lineage.PRODUCER,
            'create_request': request, 'describe_job': cls.job, 'runtime': baseline.versions(),
            'identities': {'job_arn': training_spec.job_arn,
                'image_uri': request['AlgorithmSpecification']['TrainingImage'],
                'source_sha256': 'b'*64, 'dataset_id': cls.report['dataset_id'],
                'dataset_report_sha256': digest(report_bytes),
                'dataset_s3_uri': request['InputDataConfig'][0]['DataSource']['S3DataSource']['S3Uri'],
                'dataset_artifact_sha256': cls.report['artifact_sha256'],
                'preparation_selection_id': 'c'*64, 'preparation_receipt_sha256': 'd'*64,
                'output_uri': cls.job['ModelArtifacts']['S3ModelArtifacts']}}
        cls.evidence_bytes = encode(cls.evidence)
        cls.receipt = lineage.build_verified_receipt(cls.evidence_bytes, digest(cls.evidence_bytes), cls.tar)
        cls.pin = digest(cls.receipt)

    @classmethod
    def tearDownClass(cls):
        if any((ROOT/n).read_bytes() != before for n, before in cls.before.items()):
            raise AssertionError('Existing producer source bytes changed during lineage tests')

    def setUp(self):
        self.scratch = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.fit = self.enterContext(patch.object(baseline, 'train_baseline',
                                                side_effect=AssertionError('Inference must never fit')))

    def request(self, mode='hypothetical'):
        value = {'schema_version': 1, 'producer_kind': lineage.PRODUCER,
            'managed_model_id': json.loads(self.receipt)['managed_model_id'], 'receipt_sha256': self.pin,
            'allow_retrospective_demo': True, 'mode': mode}
        if mode == 'hypothetical':
            value['features'] = {'home_field': 1, 'prior_avg_margin_diff': 7, 'prior_win_pct_diff': .2}
        return value

    def build(self, evidence=None, tar=None):
        raw = encode(self.evidence if evidence is None else evidence)
        return lineage.build_verified_receipt(raw, digest(raw), self.tar if tar is None else tar)

    def assert_unloaded(self, operation):
        with patch.object(baseline.joblib, 'load', side_effect=AssertionError('Must reject before joblib')) as load:
            with self.assertRaises((ContractError, baseline.BaselineError)):
                operation()
            load.assert_not_called()
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_real_synthetic_independent_saved_and_vector_parity(self):
        with patch.object(baseline.joblib, 'load', wraps=baseline.joblib.load) as load:
            self.assertEqual(self.build(), self.receipt)
            load.assert_not_called()  # Receipt building never deserializes.
        vector = lineage.infer(self.request(), self.receipt, self.pin, self.tar, self.scratch/'vector')
        expected = json.loads((self.original/'synthetic_summary.json').read_bytes())['synthetic_hypothetical']
        self.assertEqual(vector['home_win_probability'], expected['home_win_probability'])
        self.assertEqual(vector['features'], expected['features'])
        batch = lineage.infer(self.request('saved_sample'), self.receipt, self.pin, self.tar,
                              self.scratch/'batch', self.dataset)
        self.assertEqual(batch['count'], 6)
        predictions = (self.scratch/'batch/predictions/predictions.csv').read_bytes()
        self.assertEqual(predictions, self.files['sample_predictions.csv'])
        self.assertEqual(predictions, (self.original/'predictions/predictions.csv').read_bytes())
        self.assertEqual(json.loads(self.files['model_metadata.json'])['counts'],
                         {'train': 18, 'holdout': 6, 'prediction': 6})
        self.assertNotIn('training_token_sha256', batch)
        self.assertNotIn('implementation_sha256', json.loads(self.receipt))
        self.assertFalse(batch['approved_for_point_in_time_forecasting'])
        self.assertFalse(any('cloud-modeling' in str(p) for p in self.scratch.rglob('*')))
        self.fit.assert_not_called()

    def test_changed_receipt_and_caller_supplied_pin_rejected(self):
        changed = self.receipt + b' '
        self.assert_unloaded(lambda: lineage.load_verified_model(changed, self.pin, self.tar, self.scratch))
        request = self.request() | {'receipt_sha256': digest(changed)}
        self.assert_unloaded(lambda: lineage.infer(request, changed, self.pin, self.tar, self.scratch))

    def test_changed_job_image_source_preparation_reject_original_evidence_pin(self):
        for field in ('job_arn', 'image_uri', 'source_sha256', 'preparation_selection_id',
                      'preparation_receipt_sha256'):
            value = copy.deepcopy(self.evidence)
            value['identities'][field] += 'changed'
            with self.subTest(field=field):
                self.assert_unloaded(lambda: lineage.build_verified_receipt(
                    encode(value), digest(self.evidence_bytes), self.tar))

    def test_job_semantic_changes_fail_even_with_fresh_evidence_hash(self):
        changes = (
            ('TrainingJobStatus', 'Failed'), ('SecondaryStatus', 'Training'),
            ('TrainingJobName', 'other-job'), ('TrainingJobArn', self.job['TrainingJobArn']+'other'),
            ('RoleArn', 'arn:aws:iam::123456789012:role/other'),
            ('EnableNetworkIsolation', False), ('EnableManagedSpotTraining', True),
            ('ProfilerConfig', {'DisableProfiler': False}), ('RetryStrategy', {'MaximumRetryAttempts': 1}),
            ('VpcConfig', {'Subnets': ['unapproved']}),
            ('ModelArtifacts', {'S3ModelArtifacts': 's3://synthetic-training-bucket/other/model.tar.gz'}),
        )
        for field, changed in changes:
            evidence = copy.deepcopy(self.evidence)
            evidence['describe_job'][field] = changed
            with self.subTest(field=field):
                self.assert_unloaded(lambda: self.build(evidence))
        for area, field, changed in (
            ('AlgorithmSpecification', 'TrainingImage', 'unapproved:tag'),
            ('AlgorithmSpecification', 'EnableSageMakerMetricsTimeSeries', True),
            ('ResourceConfig', 'KeepAlivePeriodInSeconds', 60),
            ('Environment', 'EXPECTED_REPORT_SHA256', '0'*64),
            ('Environment', 'EXPECTED_DATASET_ID', '0'*64),
        ):
            evidence = copy.deepcopy(self.evidence)
            evidence['describe_job'][area][field] = changed
            with self.subTest(area=area, field=field):
                self.assert_unloaded(lambda: self.build(evidence))

    def test_shared_request_validator_refuses_unapproved_knobs(self):
        for field, changed in (('RetryStrategy', {'MaximumRetryAttempts': 0}),
                               ('EnableManagedSpotTraining', True),
                               ('ResourceConfig', {'InstanceType': 'ml.m5.large', 'InstanceCount': 2,
                                                   'VolumeSizeInGB': 5})):
            evidence = copy.deepcopy(self.evidence)
            evidence['create_request'][field] = changed
            evidence['describe_job'][field] = changed
            with self.subTest(field=field):
                self.assert_unloaded(lambda: self.build(evidence))

    def test_tar_corruption_metadata_and_version_changes_rejected_before_load(self):
        self.assert_unloaded(lambda: lineage.load_verified_model(
            self.receipt, self.pin, self.tar[:-10], self.scratch))
        for field in ('dataset_id', 'dataset_report_sha256', 'versions', 'artifact_sha256'):
            files = dict(self.files)
            metadata = json.loads(files['model_metadata.json'])
            metadata[field] = {} if isinstance(metadata[field], dict) else '0'*64
            files['model_metadata.json'] = encode(metadata)
            with self.subTest(field=field):
                self.assert_unloaded(lambda: self.build(tar=archive(files)))
        evidence = copy.deepcopy(self.evidence)
        evidence['runtime']['python'] = '0.0.0'
        self.assert_unloaded(lambda: self.build(evidence))
        with patch.object(baseline, 'versions', return_value=baseline.versions() | {'python': '0.0.0'}):
            self.assert_unloaded(lambda: lineage.load_verified_model(
                self.receipt, self.pin, self.tar, self.scratch))

    def test_unsafe_tar_members_missing_files_and_compressed_bomb_refused(self):
        for name, kind in (('../model.joblib', tarfile.REGTYPE), ('/model.joblib', tarfile.REGTYPE),
                           ('./model.joblib', tarfile.REGTYPE), ('unexpected', tarfile.REGTYPE),
                           ('model.joblib', tarfile.REGTYPE), ('directory/', tarfile.DIRTYPE),
                           ('model.joblib', tarfile.SYMTYPE), ('model.joblib', tarfile.LNKTYPE),
                           ('model.joblib', tarfile.FIFOTYPE), ('pax', tarfile.XHDTYPE)):
            member = tarfile.TarInfo(name)
            member.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = '/outside'
            with self.subTest(name=name, kind=kind):
                self.assert_unloaded(lambda: self.build(tar=archive(self.files, [(member, b'')])))
        self.assert_unloaded(lambda: self.build(tar=archive(self.files, omit=('evaluation.json',))))
        with patch.object(lineage, 'MAX_TAR_BYTES', 512):
            self.assert_unloaded(lambda: self.build())
        with patch.object(lineage, 'MAX_BYTES', 32):
            self.assert_unloaded(lambda: self.build())

    def test_standard_tar_root_and_dot_prefix_preserve_exact_files(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz', format=tarfile.USTAR_FORMAT) as tar:
            root = tarfile.TarInfo('./')
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            for name, content in sorted(self.files.items()):
                member = tarfile.TarInfo('./'+name)
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
        receipt = json.loads(self.build(tar=buffer.getvalue()))
        self.assertEqual(receipt['artifact_sha256'], {n:digest(b) for n,b in self.files.items()})

    def test_receipt_internal_binding_refused_even_with_changed_receipt_pin(self):
        for field, changed in (('managed_model_id', '0'*64), ('artifact_sha256', {}),
                               ('archive_sha256', '0'*64), ('producer_kind', 'lambda_training')):
            receipt = json.loads(self.receipt)
            receipt[field] = changed
            raw = encode(receipt)
            with self.subTest(field=field):
                self.assert_unloaded(lambda: lineage.load_verified_model(raw, digest(raw), self.tar, self.scratch))

    def test_strict_native_requests_and_feature_rules(self):
        good = self.request()
        bad = [good | {'training_token_sha256': '0'*64}, good | {'schema_version': True},
               good | {'producer_kind': 'lambda'}, good | {'allow_retrospective_demo': False},
               good | {'mode': 'live'}, good | {'managed_model_id': '0'*64}]
        for features in ({'score': 1}, good['features'] | {'home_field': True},
                         good['features'] | {'home_field': .5},
                         good['features'] | {'prior_win_pct_diff': 2},
                         good['features'] | {'prior_avg_margin_diff': float('nan')},
                         good['features'] | {'prior_avg_margin_diff': '7'}):
            bad.append(good | {'features': features})
        for request in bad:
            with self.subTest(request=request):
                self.assert_unloaded(lambda: lineage.infer(request, self.receipt, self.pin, self.tar, self.scratch))
        self.assert_unloaded(lambda: lineage.infer(
            self.request('saved_sample'), self.receipt, self.pin, self.tar, self.scratch))

    def test_duplicate_json_and_symlink_or_existing_roots_refused(self):
        raw = self.evidence_bytes.rstrip()[:-1] + b',"schema_version":1}'
        self.assert_unloaded(lambda: lineage.build_verified_receipt(raw, digest(raw), self.tar))
        link = self.scratch/'link'
        link.symlink_to(self.scratch, target_is_directory=True)
        with patch.object(baseline.joblib, 'load') as load:
            with self.assertRaises(ContractError):
                lineage.load_verified_model(self.receipt, self.pin, self.tar, link/'fresh')
            load.assert_not_called()
        existing = self.scratch/'existing'
        existing.mkdir()
        (existing/'keep').write_bytes(b'preserve')
        with self.assertRaises(ContractError):
            lineage.load_verified_model(self.receipt, self.pin, self.tar, existing)
        self.assertEqual((existing/'keep').read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
