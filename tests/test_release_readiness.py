"""Offline tests for managed-entry guards and public-safe dated observations."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.pipeline import managed_training, public_monitoring
from src.pipeline.run_contract import STATUS, digest, encode


class ReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request',side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send',side_effect=AssertionError('offline')))
        self.report=dict(STATUS,operational_forecast_approved=False,request={'as_of':'2026-11-20T22:30:00Z'},
            quality={'counts':{'input':65,'retained':55,'quarantined':10},'eligible':53,'source_age_seconds':871.3},
            distributions={'state':'measured'},performance={'state':'pending','matched':0,'pending':53},
            private_review='PRIVATE_PERSON',private_bucket='PRIVATE_RESOURCE')
    def view(self):
        raw=encode(self.report);return public_monitoring.build_view(raw,digest(raw))
    def test_public_view_keeps_pending_flags_and_excludes_private_text(self):
        text=public_monitoring.render(self.view()).decode()
        self.assertIn('53',text);self.assertIn('pending',text)
        self.assertNotIn('PRIVATE_',text);self.assertIn('not current live health',text)
        self.assertFalse(self.view()['approved_for_point_in_time_forecasting'])
    def test_changed_source_and_removed_approval_flags_fail(self):
        with self.assertRaises(ValueError):public_monitoring.build_view(encode(self.report),'0'*64)
        self.report['approved_for_predictor_use']=True
        with self.assertRaises(ValueError):self.view()
    def test_failed_measurement_is_unavailable_not_zero(self):
        self.report['performance']={'state':'failed'}
        v=self.view();self.assertIsNone(v['pending_outcomes']);self.assertIn(b'Unavailable',public_monitoring.render(v))
    def test_renderer_rejects_extra_fields_approval_and_arbitrary_text(self):
        v=self.view()
        for changed in (dict(v,reviewer='PRIVATE'),dict(v,operational_forecast_approved=True),dict(v,technical_rows='<script>bad</script>')):
            with self.assertRaises(ValueError):public_monitoring.render(changed)
    def test_invalid_counts_and_nonfinite_age_fail(self):
        for value in (-1,True,'PRIVATE'):
            r=copy.deepcopy(self.report);r['quality']['counts']['input']=value;raw=encode(r)
            with self.assertRaises(ValueError):public_monitoring.build_view(raw,digest(raw))
        self.report['quality']['source_age_seconds']=float('inf')
        raw=json.dumps(self.report).encode()
        with self.assertRaises(ValueError):public_monitoring.build_view(raw,digest(raw))
    def test_managed_entry_real_synthetic_training_and_no_overwrite(self):
        spec=importlib.util.spec_from_file_location('synthetic_example',Path(__file__).resolve().parents[1]/'bin/synthetic_demo.py')
        example=importlib.util.module_from_spec(spec);spec.loader.exec_module(example)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);example.run('data/processed/example',root=root,allow_retrospective_demo=True)
            data=root/'data/processed/example/dataset';report=json.loads((data/'dataset_report.json').read_text());sha=digest((data/'dataset_report.json').read_bytes())
            output=root/'managed';attempt=root/'attempt.json'
            metadata,evaluation=managed_training.run(data,output,attempt,report['dataset_id'],sha,allow_retrospective_demo=True)
            self.assertEqual(metadata['counts'],{'train':18,'holdout':6,'prediction':6})
            self.assertEqual(evaluation['model'],json.loads((root/'data/processed/example/model/evaluation.json').read_text())['model'])
            before={p.name:p.read_bytes() for p in output.iterdir()}
            with patch.object(managed_training.baseline,'train_baseline',side_effect=AssertionError('must not fit again')):
                with self.assertRaises(ValueError):managed_training.run(data,output,attempt,report['dataset_id'],sha,allow_retrospective_demo=True)
                with self.assertRaises(FileExistsError):managed_training.run(data,root/'other',attempt,report['dataset_id'],sha,allow_retrospective_demo=True)
            self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})
            with patch.object(managed_training.baseline,'train_baseline') as fit:
                for consent,bad_id,bad_sha in ((False,report['dataset_id'],sha),(True,report['dataset_id'],'0'*64),(True,'0'*64,sha)):
                    with self.assertRaises(ValueError):managed_training.run(data,root/'refused',root/'new-attempt',bad_id,bad_sha,allow_retrospective_demo=consent)
                fit.assert_not_called()
