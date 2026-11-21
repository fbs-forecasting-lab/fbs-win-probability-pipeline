"""Offline launch, failure and interrupted-fit safeguards for the managed candidate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.pipeline import managed_training as managed
from src.pipeline.run_contract import digest


class ManagedTrainingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('offline')))
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        spec = importlib.util.spec_from_file_location('synthetic_managed', Path('bin/synthetic_demo.py'))
        example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(example)
        example.run('data/processed/synthetic', root=self.root, allow_retrospective_demo=True)
        self.data = self.root/'data/processed/synthetic/dataset'
        self.dataset_id = json.loads((self.data/'dataset_report.json').read_text())['dataset_id']
        self.sha = digest((self.data/'dataset_report.json').read_bytes())

    def test_failure_or_interruption_consumes_attempt_without_refit(self):
        for index, failure in enumerate((RuntimeError('private details'), SystemExit(143))):
            attempt = self.root/f'attempt-{index}'
            with patch.object(managed.baseline, 'train_baseline', side_effect=failure):
                with self.assertRaises(type(failure)):
                    managed.run(self.data, self.root/f'model-{index}', attempt, self.dataset_id,
                                self.sha, allow_retrospective_demo=True)
            self.assertTrue(attempt.exists())
            with patch.object(managed.baseline, 'train_baseline') as fit:
                with self.assertRaises(FileExistsError):
                    managed.run(self.data, self.root/f'model-{index}', attempt, self.dataset_id,
                                self.sha, allow_retrospective_demo=True)
                fit.assert_not_called()

    def test_tampered_channel_refuses_before_attempt_or_fit(self):
        (self.data/'train.csv').write_bytes(b'changed')
        with patch.object(managed.baseline, 'train_baseline') as fit:
            with self.assertRaises(ValueError):
                managed.run(self.data, self.root/'model', self.root/'attempt', self.dataset_id,
                            self.sha, allow_retrospective_demo=True)
            fit.assert_not_called()
        self.assertFalse((self.root/'attempt').exists())

    def test_invalid_launch_argument_is_refused_without_fit(self):
        with patch.object(managed, 'run') as run:
            with self.assertRaises(SystemExit) as stopped:
                managed.main(['serve'])
            self.assertEqual(stopped.exception.code, 2)
            run.assert_not_called()
