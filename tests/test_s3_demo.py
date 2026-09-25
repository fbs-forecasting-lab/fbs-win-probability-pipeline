"""Offline checks for the integrated S3 download -> train -> predict demo command."""

from contextlib import chdir, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.features import dataset, games
from src.ingestion import s3_storage as s3
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.models import baseline, predict
from src.pipeline import s3_demo
from tests.test_dataset import game
from tests.test_s3_storage import MemoryS3

VECTOR = (0.2, 7.0, 1.0)
VECTOR_ARGS = ['--prior-win-pct-diff', '0.2', '--prior-avg-margin-diff', '7', '--home-field', '1']
CONFIG = {'FBS_S3_BUCKET': 'course-project-bucket', 'FBS_S3_PREFIX': 'fbs-demo',
          'FBS_S3_REGION': 'us-east-1', 'FBS_AWS_PROFILE': None}


class S3DemoTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS network')))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No CFBD network')))
        normalized, manifests = self.root / 'normalized', []
        for year in dataset.SEASONS:
            params = {'year': year, 'seasonType': 'regular', 'classification': 'fbs'}
            rows = [game(year), game(year, 2), game(year, 3, homeId=20, awayId=30),
                    game(year, 4, homeId=30, awayId=10)]
            if year == 2026:
                params['week'] = 4
            manifest = save_snapshot(GamesResponse(json.dumps(rows).encode(), params, '2026-09-23T04:00:00Z', 200),
                                     self.root / 'raw')[1]
            games.normalize_snapshot(manifest, normalized)
            manifests.append(manifest)
        self.local = self.root / 'local-dataset'
        self.identifier = dataset.build_dataset(manifests, self.local, allow_retrospective_demo=True,
                                                normalized_root=normalized)['dataset_id']
        self.client = MemoryS3()
        self.store = s3.S3Store(self.client, 'course-project-bucket', 'fbs-demo')
        self.store.upload_dataset(self.local, allow_retrospective_demo=True)
        self.client.calls.clear()
        self.run_dir = self.root / 'recording'

    def run_demo(self, **kwargs):
        return s3_demo.run(self.store, self.identifier, self.run_dir, allow_retrospective_demo=True, **kwargs)

    def cli(self, *extra, run_dir=None, config=CONFIG, client=None, retrospective=True):
        """Run the CLI against the fake bucket; returns (code, stdout, stderr, make_client mock)."""
        argv = ['--dataset-id', self.identifier, '--run-dir', str(run_dir or self.run_dir), *extra]
        if retrospective:
            argv.append('--allow-retrospective-demo')
        out, err = io.StringIO(), io.StringIO()
        with patch.object(s3, 'configuration', return_value=config), \
                patch.object(s3, 'make_client', return_value=client or self.client) as maker, \
                redirect_stdout(out), redirect_stderr(err):
            code = s3_demo.main(argv)
        return code, out.getvalue(), err.getvalue(), maker

    def test_chain_matches_separate_existing_commands(self):
        code, out, _, _ = self.cli(*VECTOR_ARGS)
        self.assertEqual(code, 0)
        stages = json.loads(out)['stages']
        separate = {name: self.root / f'separate-{name}' for name in ('dataset', 'model', 'predictions')}
        with patch.object(s3, 'configuration', return_value=CONFIG), \
                patch.object(s3, 'make_client', return_value=self.client):
            outputs = []
            for command in (lambda: s3.main(['download-dataset', '--dataset-id', self.identifier,
                                             '--output-dir', str(separate['dataset']), '--allow-retrospective-demo']),
                            lambda: baseline.main(['--dataset-dir', str(separate['dataset']),
                                                   '--output-dir', str(separate['model']), '--allow-retrospective-demo']),
                            lambda: predict.main(['--model-dir', str(separate['model']), '--dataset-dir',
                                                  str(separate['dataset']), '--output-dir', str(separate['predictions']),
                                                  '--allow-retrospective-demo']),
                            lambda: predict.main(['--model-dir', str(separate['model']), *VECTOR_ARGS,
                                                  '--allow-retrospective-demo'])):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    self.assertEqual(command(), 0)
                outputs.append(json.loads(buffer.getvalue()))
        downloaded, trained, _, hypothetical = outputs
        self.assertEqual(stages['1_s3_download']['dataset_report_sha256'], downloaded['dataset_report_sha256'])
        self.assertEqual(stages['1_s3_download']['verified_files'], downloaded['verified_files'])
        holdout = stages['2_local_training']['holdout_2025']
        self.assertEqual(holdout['model'], trained['evaluation']['model'])
        self.assertEqual(holdout['constant_baseline'], trained['evaluation']['constant_baseline'])
        self.assertEqual(stages['2_local_training']['counts'], trained['counts'])
        for name in ('sample_predictions.csv', 'holdout_predictions.csv'):
            self.assertEqual((self.run_dir / 'model' / name).read_bytes(), (separate['model'] / name).read_bytes())
        self.assertEqual((self.run_dir / 'predictions' / 'predictions.csv').read_bytes(),
                         (separate['predictions'] / 'predictions.csv').read_bytes())
        self.assertEqual(stages['3_prediction']['hypothetical_vector']['home_win_probability'],
                         hypothetical['home_win_probability'])
        self.assertEqual(stages['3_prediction']['hypothetical_vector']['away_win_probability'],
                         hypothetical['away_win_probability'])

    def test_training_reads_only_downloaded_directory(self):
        with patch.object(s3_demo, 'train_baseline', wraps=baseline.train_baseline) as trainer:
            result = self.run_demo()
        trainer.assert_called_once_with(self.run_dir / 'dataset', self.run_dir / 'model', allow_retrospective_demo=True)
        self.assertEqual(result['stages']['2_local_training']['trained_on'], str((self.run_dir / 'dataset').resolve()))
        self.assertEqual(result['stages']['2_local_training']['dataset_id'], self.identifier)
        for name in ('dataset_report.json', *baseline.DATA_FILES):
            self.assertEqual((self.run_dir / 'dataset' / name).read_bytes(), (self.local / name).read_bytes())
        self.assertEqual(sorted(p.name for p in self.run_dir.iterdir()), ['dataset', 'model', 'predictions'])

    def test_summary_paths_relative_inside_cwd_absolute_outside(self):
        with chdir(self.root):
            code, out, _, _ = self.cli(*VECTOR_ARGS, run_dir=Path('recording'))
        self.assertEqual(code, 0)
        stages = json.loads(out)['stages']
        self.assertEqual(stages['1_s3_download']['local_copy'], 'recording/dataset')
        self.assertEqual(stages['2_local_training']['trained_on'], 'recording/dataset')
        self.assertEqual(stages['2_local_training']['model_dir'], 'recording/model')
        self.assertEqual(stages['3_prediction']['output_dir'], 'recording/predictions')
        self.assertEqual(stages['1_s3_download']['s3_location'],
                         f's3://course-project-bucket/fbs-demo/datasets/{self.identifier}/')
        self.assertNotIn(str(self.root.resolve()), out)
        # Outside the working directory, the absolute path is kept.
        outside = self.root / 'outside'
        with chdir(self.root / 'recording'):
            result = s3_demo.run(self.store, self.identifier, outside, allow_retrospective_demo=True)
        self.assertEqual(result['stages']['3_prediction']['output_dir'], str((outside / 'predictions').resolve()))

    def test_no_s3_writes(self):
        objects = dict(self.client.objects)
        self.run_demo(vector=VECTOR)
        self.assertEqual({op for op, _ in self.client.calls}, {'privacy', 'get'})
        self.assertEqual(self.client.objects, objects)

    def test_vector_is_optional(self):
        self.assertIsNone(self.run_demo()['stages']['3_prediction']['hypothetical_vector'])

    def test_tampered_s3_object_stops_before_training(self):
        key = f'fbs-demo/datasets/{self.identifier}/train.csv'
        self.client.objects[key] += b'\n'
        with patch.object(s3_demo, 'train_baseline') as trainer:
            with self.assertRaisesRegex(s3_demo.DemoError, '^S3 download failed: .*SHA-256'):
                self.run_demo()
            trainer.assert_not_called()
        self.assertFalse((self.run_dir / 'dataset').exists())
        self.assertFalse((self.run_dir / 'model').exists())

    def test_missing_dataset_reports_s3_download_stage(self):
        with self.assertRaisesRegex(s3_demo.DemoError, '^S3 download failed: Required S3 object is missing'):
            s3_demo.run(self.store, 'a' * 64, self.run_dir, allow_retrospective_demo=True)
        self.assertFalse((self.run_dir / 'model').exists())

    def test_cli_refusals_happen_before_aws_and_preserve_files(self):
        nonempty = self.root / 'nonempty'
        nonempty.mkdir()
        (nonempty / 'keep.txt').write_text('preserve me')
        existing_file = self.root / 'existing.txt'
        existing_file.write_text('preserve me too')
        link = self.root / 'link'
        link.symlink_to(self.root / 'elsewhere', target_is_directory=True)
        no_bucket = {**CONFIG, 'FBS_S3_BUCKET': None}
        cases = [('nonempty', {'run_dir': nonempty}, 'new or empty'),
                 ('existing file', {'run_dir': existing_file}, 'existing file'),
                 ('symlink', {'run_dir': link}, 'symbolic link'),
                 ('no retrospective flag', {'retrospective': False}, 'allow-retrospective-demo'),
                 ('missing bucket', {'config': no_bucket}, '--bucket')]
        for name, kwargs, message in cases:
            with self.subTest(name):
                code, out, err, maker = self.cli(**kwargs)
                self.assertEqual(code, 1)
                self.assertEqual(out, '')
                self.assertIn('Refused before contacting AWS', err)
                self.assertIn(message, err)
                self.assertNotIn('Traceback', err)
                maker.assert_not_called()
        self.assertEqual((nonempty / 'keep.txt').read_text(), 'preserve me')
        self.assertEqual(list(nonempty.iterdir()), [nonempty / 'keep.txt'])
        self.assertEqual(existing_file.read_text(), 'preserve me too')
        self.assertFalse((self.root / 'elsewhere').exists())
        self.assertFalse(self.run_dir.exists())
        self.assertEqual(self.client.calls, [])

    def test_make_client_failure_is_stage_named_and_sanitized(self):
        for exc in (s3.S3StorageError('AWS credentials or SSO session expired/invalid; refresh the selected session.'),
                    RuntimeError('SECRET profile details')):
            with self.subTest(type(exc).__name__):
                err = io.StringIO()
                with patch.object(s3, 'configuration', return_value=CONFIG), \
                        patch.object(s3, 'make_client', side_effect=exc), redirect_stderr(err):
                    code = s3_demo.main(['--dataset-id', self.identifier, '--run-dir', str(self.run_dir),
                                         '--allow-retrospective-demo'])
                self.assertEqual(code, 1)
                self.assertTrue(err.getvalue().startswith('Error: AWS client failed: '))
                self.assertNotIn('SECRET', err.getvalue())
        self.assertIn('unexpected RuntimeError', err.getvalue())
        self.assertFalse(self.run_dir.exists())

    def test_unexpected_exception_is_stage_named_and_sanitized(self):
        for target, stage in (('train_baseline', 'local training'), ('predict_saved_sample', 'prediction')):
            with self.subTest(stage):
                run_dir = self.root / f'unexpected-{stage.replace(" ", "-")}'
                with patch.object(s3_demo, target, side_effect=RuntimeError('SECRET /Users/someone/path')):
                    code, out, err, _ = self.cli(run_dir=run_dir)
                self.assertEqual(code, 1)
                self.assertEqual(out, '')
                self.assertEqual(err.strip(), f'Error: {stage} failed: unexpected RuntimeError; details suppressed.')

    def test_model_dataset_mismatch_is_stage_named(self):
        def wrong_dataset(*args, **kwargs):
            metadata, evaluation = baseline.train_baseline(*args, **kwargs)
            return {**metadata, 'dataset_id': 'b' * 64}, evaluation
        with patch.object(s3_demo, 'train_baseline', side_effect=wrong_dataset):
            with self.assertRaisesRegex(s3_demo.DemoError, '^local training failed: .*downloaded dataset'):
                self.run_demo()
        self.assertFalse((self.run_dir / 'predictions').exists())

    def test_partial_hypothetical_vector_is_parser_error(self):
        for partial in (VECTOR_ARGS[:2], VECTOR_ARGS[:4], VECTOR_ARGS[2:]):
            with self.subTest(partial=partial):
                err = io.StringIO()
                with patch.object(s3, 'configuration', return_value=CONFIG), \
                        patch.object(s3, 'make_client') as maker, redirect_stderr(err), \
                        self.assertRaises(SystemExit) as caught:
                    s3_demo.main(['--dataset-id', self.identifier, '--run-dir', str(self.run_dir), *partial,
                                  '--allow-retrospective-demo'])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn('needs all three', err.getvalue())
                maker.assert_not_called()

    def test_cli_json_status_flags_and_float_probabilities(self):
        code, out, err, maker = self.cli(*VECTOR_ARGS)
        self.assertEqual((code, err), (0, ''))
        maker.assert_called_once_with('us-east-1', None)
        printed = json.loads(out)
        self.assertEqual({key: printed[key] for key in baseline.STATUS}, baseline.STATUS)
        self.assertEqual(printed['dataset_mode'], 'retrospective_demo')
        self.assertEqual([printed[k] for k in baseline.STATUS if k != 'dataset_mode'], [False] * 3)
        stages = printed['stages']
        self.assertEqual(stages['1_s3_download']['verified_files'], 6)
        self.assertEqual(stages['1_s3_download']['s3_location'],
                         f's3://course-project-bucket/fbs-demo/datasets/{self.identifier}/')
        self.assertEqual(stages['1_s3_download']['method'], 'downloaded and SHA-256 verified before use; not streamed')
        self.assertEqual(stages['2_local_training']['predictors'], baseline.PREDICTORS)
        prediction = stages['3_prediction']
        self.assertEqual(prediction['context'], 'saved_2026_sample_not_live')
        self.assertEqual(prediction['count'], 4)
        matchups = prediction['first_saved_matchups']
        self.assertEqual(len(matchups), s3_demo.SAMPLE_ROWS_SHOWN)
        for row in [*matchups, prediction['hypothetical_vector']]:
            for key in ('home_win_probability', 'away_win_probability'):
                self.assertIs(type(row[key]), float)
            np.testing.assert_allclose(row['home_win_probability'] + row['away_win_probability'], 1, atol=1e-12)
        self.assertEqual(prediction['hypothetical_vector']['features'], dict(zip(baseline.PREDICTORS, VECTOR)))


if __name__ == '__main__':
    unittest.main()
