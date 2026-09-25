"""Offline checks for the CFBD week -> S3 raw -> normalize -> build -> S3 dataset refresh command."""

from contextlib import chdir, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import NoCredentialsError

from src.features import dataset, games
from src.ingestion import cfbd
from src.ingestion import s3_storage as s3
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.models import baseline
from src.pipeline import week_refresh
from tests.test_dataset import game
from tests.test_s3_storage import MemoryS3, error

CONFIG = {'FBS_S3_BUCKET': 'course-project-bucket', 'FBS_S3_PREFIX': 'fbs-demo',
          'FBS_S3_REGION': 'us-east-1', 'FBS_AWS_PROFILE': None}
STAGES = ['aws_preflight', 'cfbd_fetch', 's3_upload_raw', 'normalize', 'build_dataset', 's3_upload_dataset']


def season_rows(year, **changes):
    return [game(year, **changes), game(year, 2, **changes), game(year, 3, homeId=20, awayId=30, **changes),
            game(year, 4, homeId=30, awayId=10, **changes)]


def week5_response(rows=None):
    rows = rows or [row | {'startDate': f'2026-10-03T{15 + i}:00:00Z'} for i, row in enumerate(season_rows(2026, week=5))]
    params = {'year': 2026, 'seasonType': 'regular', 'classification': 'fbs', 'week': 5}
    return GamesResponse(json.dumps(rows).encode(), params, '2026-09-25T02:00:00Z', 200)


class WeekRefreshTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(chdir(self.root))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS network')))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No CFBD network')))
        self.enterContext(patch.object(week_refresh, 'PROJECT_ROOT', self.root))
        # A reference dataset built the same way as demo-features-v1, with a saved 2026 Week 4 sample.
        raw, normalized, manifests = self.root / 'data/raw/cfbd/games', self.root / 'data/interim/cfbd/games', []
        for year in dataset.SEASONS:
            params = {'year': year, 'seasonType': 'regular', 'classification': 'fbs'}
            if year == 2026:
                params['week'] = 4
            response = GamesResponse(json.dumps(season_rows(year)).encode(), params, '2026-09-23T04:00:00Z', 200)
            manifest = save_snapshot(response, raw)[1]
            games.normalize_snapshot(manifest, normalized)
            manifests.append(manifest)
        self.history = manifests[:5]
        self.reference = self.root / 'data/processed/demo-features-v1'
        dataset.build_dataset(manifests, self.reference, allow_retrospective_demo=True, normalized_root=normalized)
        self.client = MemoryS3()
        self.enterContext(patch.object(s3, 'configuration', return_value=CONFIG))
        self.maker = self.enterContext(patch.object(s3, 'make_client', return_value=self.client))
        self.fetcher = self.enterContext(patch.object(cfbd, 'fetch_games', return_value=week5_response()))
        self.enterContext(patch.object(cfbd, '_api_key', return_value='synthetic-key'))

    def cli(self, *extra, tag='take-1', retrospective=True):
        argv = ['--week', '5', '--run-tag', tag, *extra]
        if retrospective:
            argv.append('--allow-retrospective-demo')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = week_refresh.main(argv)
        return code, out.getvalue(), err.getvalue()

    def snapshot_tree(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_stage_order_summary_dataset_id_and_next_command(self):
        order = []

        def spy(name, original):
            def call(*args, **kwargs):
                order.append(name)
                return original(*args, **kwargs)
            return call
        self.fetcher.side_effect = spy('cfbd_fetch', lambda *a, **k: week5_response())
        with patch.object(s3.S3Store, '_private_bucket', autospec=True,
                          side_effect=spy('aws_preflight', s3.S3Store._private_bucket)), \
                patch.object(s3.S3Store, 'upload_raw', autospec=True, side_effect=spy('s3_upload_raw', s3.S3Store.upload_raw)), \
                patch.object(games, 'normalize_snapshot', side_effect=spy('normalize', games.normalize_snapshot)), \
                patch.object(dataset, 'build_dataset', side_effect=spy('build_dataset', dataset.build_dataset)), \
                patch.object(s3.S3Store, 'upload_dataset', autospec=True,
                             side_effect=spy('s3_upload_dataset', s3.S3Store.upload_dataset)):
            code, out, err = self.cli()
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(list(dict.fromkeys(order)), STAGES)
        self.assertEqual(self.client.calls[0][0], 'privacy')  # Read-only preflight is the first AWS call.
        self.fetcher.assert_called_once_with(2026, 5)
        self.maker.assert_called_once_with('us-east-1', None)
        # Raw objects are written before any dataset object.
        puts = [params['Key'] for op, params in self.client.calls if op == 'put']
        raw_puts = [i for i, key in enumerate(puts) if key.startswith('fbs-demo/raw/')]
        dataset_puts = [i for i, key in enumerate(puts) if key.startswith('fbs-demo/datasets/')]
        self.assertEqual((len(raw_puts), len(dataset_puts)), (2, 6))
        self.assertLess(max(raw_puts), min(dataset_puts))

        printed = json.loads(out)
        stages = printed['stages']
        features = Path('data/processed/take-1-features')
        report = json.loads((features / 'dataset_report.json').read_bytes())
        identifier = report['dataset_id']
        self.assertEqual(printed['dataset_id'], identifier)
        self.assertEqual(stages['4_build_dataset']['dataset_id'], identifier)
        self.assertEqual(list(printed)[-1], 'next_command')
        self.assertEqual(printed['next_command'],
                         f'.venv/bin/python -B -m src.pipeline.s3_demo --dataset-id {identifier} '
                         '--run-dir data/processed/take-1-run --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 '
                         '--home-field 1 --allow-retrospective-demo')
        fetch = stages['1_cfbd_fetch']
        self.assertEqual((fetch['season'], fetch['week'], fetch['record_count'], fetch['http_status']), (2026, 5, 4, 200))
        self.assertTrue(fetch['manifest'].startswith('data/raw/cfbd/take-1/games/season=2026/'))
        self.assertEqual(stages['3_normalize']['normalized_root'], 'data/interim/cfbd/take-1/games')
        self.assertEqual(stages['3_normalize']['new_week_counts'],
                         {'input': 4, 'retained': 4, 'excluded': 0, 'quarantined': 0})
        self.assertEqual(stages['3_normalize']['history_snapshots_normalized'], 5)
        self.assertEqual(stages['4_build_dataset']['features_dir'], 'data/processed/take-1-features')
        self.assertEqual(stages['4_build_dataset']['counts'], {name: split['output'] for name, split in report['splits'].items()})
        self.assertEqual(stages['5_s3_upload_dataset']['s3_location'],
                         f's3://course-project-bucket/fbs-demo/datasets/{identifier}/')
        self.assertTrue(all(status == 'uploaded' for stage in ('2_s3_upload_raw', '5_s3_upload_dataset')
                            for status in stages[stage]['objects'].values()))
        self.assertNotIn(str(self.root), out)
        # Train/holdout match the reference dataset; only the 2026 week differs.
        for name in ('train.csv', 'holdout.csv', 'team_season_aggregates.csv'):
            self.assertEqual((features / name).read_bytes(), (self.reference / name).read_bytes())
        self.assertNotEqual(identifier, json.loads((self.reference / 'dataset_report.json').read_bytes())['dataset_id'])

    def test_status_flags_keep_their_values(self):
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual({key: printed[key] for key in baseline.STATUS}, baseline.STATUS)
        self.assertEqual(printed['dataset_mode'], 'retrospective_demo')
        report = json.loads(Path('data/processed/take-1-features/dataset_report.json').read_bytes())
        self.assertEqual({key: report[key] for key in baseline.STATUS}, baseline.STATUS)

    def test_history_defaults_come_from_reference_report(self):
        paths, expected = week_refresh.discover_history(self.root)
        self.assertEqual(paths, self.history)
        self.assertEqual(week_refresh.verify_history(paths, expected), self.history)

    def test_refusals_happen_before_fetch_or_client_and_preserve_files(self):
        kept = self.root / 'data/processed/take-1-features'
        kept.mkdir(parents=True)
        (kept / 'keep.txt').write_text('preserve me')
        file_tag = self.root / 'data/raw/cfbd/file-tag'
        file_tag.write_text('preserve me too')
        (self.root / 'data/interim/cfbd/link-tag').symlink_to(self.root / 'elsewhere', target_is_directory=True)
        week4 = sorted((self.root / 'data/raw/cfbd/games/season=2026').glob('*.manifest.json'))[0]
        history_args = [arg for path in self.history[:4] for arg in ('--history-manifest', str(path))]
        cases = [
            ('no retrospective flag', dict(tag='fresh', retrospective=False), [], 'allow-retrospective-demo'),
            ('missing bucket', dict(tag='fresh'), ['--bucket', ''], '--bucket'),
            ('invalid prefix', dict(tag='fresh'), ['--prefix', 'bad prefix'], 'prefix'),
            ('non-empty run-tag dir', dict(tag='take-1'), [], 'already exists'),
            ('run-tag path is a file', dict(tag='file-tag'), [], 'already exists'),
            ('run-tag path is a symlink', dict(tag='link-tag'), [], 'symbolic link'),
            ('missing history season', dict(tag='fresh'), history_args, 'Missing history seasons: 2025'),
            ('week-limited history', dict(tag='fresh'),
             history_args + ['--history-manifest', str(week4)], 'full-season'),
            ('missing history manifest', dict(tag='fresh'),
             history_args + ['--history-manifest', 'data/raw/cfbd/games/season=2025/missing.manifest.json'],
             'missing or failed hash verification'),
        ]
        before = self.snapshot_tree()
        for name, kwargs, extra, message in cases:
            with self.subTest(name):
                code, out, err = self.cli(*extra, **kwargs)
                self.assertEqual((code, out), (1, ''))
                self.assertTrue(err.startswith('Error: cli_refusal: '), err)
                self.assertIn(message, err)
        with self.subTest('missing CFBD key'), patch.object(cfbd, '_api_key', side_effect=cfbd.CFBDError(
                'Set CFBD_API_KEY in the environment or the project .env file.')):
            code, _, err = self.cli(tag='fresh')
            self.assertEqual(code, 1)
            self.assertIn('cli_refusal: Set CFBD_API_KEY', err)
        with self.subTest('reference report missing'), \
                patch.object(week_refresh, 'REFERENCE_REPORT', Path('data/processed/missing/dataset_report.json')):
            code, _, err = self.cli(tag='fresh')
            self.assertEqual(code, 1)
            self.assertIn('cli_refusal: Could not discover history manifests', err)
        with self.subTest('tampered default history'):
            raw = next(p for p in self.history[0].parent.glob('*.json') if not p.name.endswith('.manifest.json'))
            original = raw.read_bytes()
            raw.write_bytes(original + b' ')
            try:
                code, _, err = self.cli(tag='fresh')
            finally:
                raw.write_bytes(original)
            self.assertEqual(code, 1)
            self.assertIn('cli_refusal: History manifest is missing or failed hash verification', err)
        self.fetcher.assert_not_called()
        self.maker.assert_not_called()
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.snapshot_tree(), before)
        self.assertFalse((self.root / 'data/raw/cfbd/fresh').exists())

    def test_parser_errors(self):
        for argv in (['--week', '5', '--run-tag', 'a', '--season', '2025'], ['--week', '0', '--run-tag', 'a'],
                     ['--week', '5', '--run-tag', 'Bad_Tag'], ['--run-tag', 'a']):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                week_refresh.main([*argv, '--allow-retrospective-demo'])
            self.assertEqual(caught.exception.code, 2)
        self.fetcher.assert_not_called()
        self.maker.assert_not_called()

    def test_stage_errors_are_named_and_sanitized(self):
        cases = [
            ('fetch failure', 'cfbd_fetch',
             patch.object(cfbd, 'fetch_games', side_effect=cfbd.CFBDError('CFBD HTTP 429: rate limit or quota reached; '
                                                                           'stopped after 3 attempts.')),
             'Error: cfbd_fetch failed: CFBD HTTP 429'),
            ('fetch unexpected', 'cfbd_fetch',
             patch.object(cfbd, 'fetch_games', side_effect=RuntimeError('SECRET token')),
             'Error: cfbd_fetch failed: unexpected RuntimeError; details suppressed.'),
            ('raw upload failure', 's3_upload_raw',
             patch.object(s3.S3Store, 'upload_raw', side_effect=s3.S3StorageError(
                 'AWS access denied; check permissions for the selected bucket/prefix and encryption key.')),
             'Error: s3_upload_raw failed: AWS access denied'),
            ('build unexpected', 'build_dataset',
             patch.object(dataset, 'build_dataset', side_effect=RuntimeError('SECRET /Users/someone/path')),
             'Error: build_dataset failed: unexpected RuntimeError; details suppressed.'),
            ('dataset upload failure', 's3_upload_dataset',
             patch.object(s3.S3Store, 'upload_dataset', side_effect=s3.S3StorageError(
                 'AWS connection or read failed after bounded SDK attempts; check network access.')),
             'Error: s3_upload_dataset failed: AWS connection or read failed'),
        ]
        for number, (name, stage, patcher, expected) in enumerate(cases):
            with self.subTest(name), patcher:
                self.client.calls.clear()
                code, out, err = self.cli(tag=f'error-{number}')
                self.assertEqual((code, out), (1, ''))
                self.assertTrue(err.startswith(expected), err)
                self.assertNotIn('SECRET', err)
                self.assertNotIn('Traceback', err)
                if stage == 'cfbd_fetch':
                    self.assertEqual({op for op, _ in self.client.calls}, {'privacy'})
                if stage in ('cfbd_fetch', 's3_upload_raw'):
                    self.assertFalse((self.root / f'data/interim/cfbd/error-{number}').exists())
                if stage != 's3_upload_dataset':
                    self.assertFalse(any(op == 'put' and params['Key'].startswith('fbs-demo/datasets/')
                                         for op, params in self.client.calls))

    def test_aws_preflight_failures_stop_before_fetch(self):
        cases = [
            ('missing credentials', NoCredentialsError(), 'AWS credentials are missing or incomplete'),
            ('expired session', error('ExpiredToken'), 'AWS credentials or SSO session expired/invalid'),
            ('access denied', error('AccessDenied', 403), 'AWS access denied'),
            ('block public access absent', error('NoSuchPublicAccessBlockConfiguration', 404),
             'Bucket-level Block Public Access is absent'),
        ]
        for number, (name, exc, expected) in enumerate(cases):
            with self.subTest(name), patch.object(self.client, 'get_public_access_block', side_effect=exc):
                code, out, err = self.cli(tag=f'preflight-{number}')
                self.assertEqual((code, out), (1, ''))
                self.assertTrue(err.startswith(f'Error: aws_preflight failed: {expected}'), err)
                self.assertNotIn('SECRET', err)
                self.assertFalse((self.root / f'data/raw/cfbd/preflight-{number}').exists())
        with self.subTest('public access not fully blocked'):
            self.client.flags['BlockPublicPolicy'] = False
            code, out, err = self.cli(tag='preflight-flags')
            self.assertEqual((code, out), (1, ''))
            self.assertTrue(err.startswith('Error: aws_preflight failed: All four bucket-level Block Public Access '
                                           'settings must be enabled.'), err)
            self.assertEqual({op for op, _ in self.client.calls}, {'privacy'})
        self.fetcher.assert_not_called()
        self.assertEqual(self.client.objects, {})
        self.assertFalse((self.root / 'data/raw/cfbd/preflight-flags').exists())

    def test_make_client_failure_is_stage_named_before_fetch(self):
        self.maker.side_effect = RuntimeError('SECRET profile details')
        code, out, err = self.cli()
        self.assertEqual((code, out), (1, ''))
        self.assertEqual(err.strip(), 'Error: aws_client failed: unexpected RuntimeError; details suppressed.')
        self.fetcher.assert_not_called()

    def test_no_s3_overwrite_reuses_identical_and_refuses_conflicts(self):
        fixed = Mock(hex='f' * 32)
        with patch('src.ingestion.storage.uuid4', return_value=fixed):
            code, out, _ = self.cli(tag='take-1')
            self.assertEqual(code, 0)
            first = json.loads(out)
            objects = dict(self.client.objects)
            self.client.calls.clear()
            # Same snapshot bytes and ID: every object already exists with identical content.
            code, out, _ = self.cli(tag='take-2')
            self.assertEqual(code, 0)
            second = json.loads(out)
            self.assertEqual(second['dataset_id'], first['dataset_id'])
            for stage in ('2_s3_upload_raw', '5_s3_upload_dataset'):
                self.assertTrue(all(status == 'reused' for status in second['stages'][stage]['objects'].values()))
            self.assertFalse(any(op == 'put' for op, _ in self.client.calls))
            self.assertEqual(self.client.objects, objects)
            # Same snapshot ID with different bytes: the existing object is preserved.
            changed = [row | {'startDate': '2026-10-03T20:00:00Z'} for row in season_rows(2026, week=5)]
            self.fetcher.return_value = week5_response(changed)
            code, out, err = self.cli(tag='take-3')
        self.assertEqual((code, out), (1, ''))
        self.assertTrue(err.startswith('Error: s3_upload_raw failed: Conflicting remote content'), err)
        self.assertEqual(self.client.objects, objects)
        self.assertFalse((self.root / 'data/processed/take-3-features').exists())


if __name__ == '__main__':
    unittest.main()
