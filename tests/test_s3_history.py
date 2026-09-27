"""Offline checks for reading the 2021–2025 history back from S3 (download_raw and download_history)."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.features import dataset, games
from src.ingestion import s3_storage as s3
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.pipeline import week_refresh
from tests.test_dataset import game
from tests.test_s3_storage import MemoryS3


def season_rows(year):
    return [game(year), game(year, 2), game(year, 3, homeId=20, awayId=30), game(year, 4, homeId=30, awayId=10)]


class S3HistoryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('No AWS network')))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No CFBD network')))
        # Local copies exist only so the test can prove they are never read.
        self.local_raw = self.root / 'data/raw/cfbd/games'
        normalized, manifests = self.root / 'data/interim/cfbd/games', []
        for year in dataset.SEASONS:
            params = {'year': year, 'seasonType': 'regular', 'classification': 'fbs'}
            if year == 2026:
                params['week'] = 4
            response = GamesResponse(json.dumps(season_rows(year)).encode(), params, '2026-09-23T04:00:00Z', 200)
            manifest = save_snapshot(response, self.local_raw)[1]
            games.normalize_snapshot(manifest, normalized)
            manifests.append(manifest)
        self.history, self.week4 = manifests[:5], manifests[5]
        self.reference = self.root / 'data/processed/demo-features-v1'
        report = dataset.build_dataset(manifests, self.reference, allow_retrospective_demo=True, normalized_root=normalized)
        self.reference_id = report['dataset_id']
        self.client = MemoryS3()
        self.store = s3.S3Store(self.client, 'course-project-bucket', 'fbs-demo')
        for manifest in self.history:
            self.store.upload_raw(manifest)
        self.store.upload_dataset(self.reference, allow_retrospective_demo=True)
        self.client.calls.clear()
        self.target = self.root / 'data/raw/cfbd/nb-run/history'

    def key(self, season, suffix='.manifest.json'):
        name = next(path for path in self.history if f'season={season}' in str(path)).name
        return f'fbs-demo/raw/cfbd/games/season={season}/{name.removesuffix(".manifest.json")}{suffix}'

    def download(self):
        return week_refresh.download_history(self.store, self.target, self.reference_id)

    def test_happy_path_downloads_verified_history_that_rebuilds_identical_dataset(self):
        paths = self.download()
        self.assertEqual([path.parent.name for path in paths], [f'season={year}' for year in range(2021, 2026)])
        for downloaded, original in zip(paths, self.history):
            self.assertEqual(downloaded.name, original.name)
            self.assertTrue(downloaded.is_relative_to(self.target))
            for suffix in ('.manifest.json', '.json'):
                name = original.name.removesuffix('.manifest.json') + suffix
                self.assertEqual((downloaded.parent / name).read_bytes(), (original.parent / name).read_bytes())
        self.assertEqual({op for op, _ in self.client.calls}, {'privacy', 'get'})  # Read-only against S3.
        # The downloaded history rebuilds byte-identical train/holdout rows.
        normalized = self.root / 'downloaded-normalized'
        for manifest in [*paths, self.week4]:
            games.normalize_snapshot(manifest, normalized)
        rebuilt = self.root / 'rebuilt'
        report = dataset.build_dataset([*paths, self.week4], rebuilt, allow_retrospective_demo=True,
                                       normalized_root=normalized)
        self.assertEqual(report['dataset_id'], self.reference_id)
        for name in ('train.csv', 'holdout.csv', 'team_season_aggregates.csv'):
            self.assertEqual((rebuilt / name).read_bytes(), (self.reference / name).read_bytes())

    def test_never_reads_local_raw_history(self):
        reads, original = [], Path.read_bytes

        def spy(path):
            reads.append(str(path))
            return original(path)
        with patch.object(Path, 'read_bytes', spy), \
                patch.object(week_refresh, 'discover_history', side_effect=AssertionError('local discovery used')):
            self.download()
        self.assertTrue(reads)
        self.assertFalse([path for path in reads if str(self.local_raw) in path or 'data/raw/cfbd/games' in path])

    def test_tampered_raw_object_stops_and_publishes_nothing(self):
        self.client.objects[self.key(2022, '.json')] += b' '
        with self.assertRaisesRegex(s3.S3StorageError, 'failed SHA-256 or manifest verification'):
            self.download()
        self.assertFalse((self.target / 'season=2022').exists())
        self.assertFalse((self.target / 'season=2023').exists())

    def test_refuses_to_overwrite_conflicting_local_files(self):
        manifest = self.history[0].name
        conflict = self.target / 'season=2021'
        conflict.mkdir(parents=True)
        (conflict / manifest).write_bytes(b'keep me')
        with self.assertRaisesRegex(s3.S3StorageError, 'existing files preserved'):
            self.store.download_raw(2021, manifest, conflict)
        self.assertEqual((conflict / manifest).read_bytes(), b'keep me')
        unrelated = self.target / 'season=2022'
        unrelated.mkdir(parents=True)
        (unrelated / 'notes.txt').write_text('keep me too')
        with self.assertRaisesRegex(s3.S3StorageError, 'existing files preserved'):
            self.store.download_raw(2022, self.history[1].name, unrelated)
        self.assertEqual(sorted(p.name for p in unrelated.iterdir()), ['notes.txt'])

    def test_missing_season_fails_with_clear_message(self):
        del self.client.objects[self.key(2023)]
        with self.assertRaisesRegex(s3.S3StorageError, 'Season 2023 raw snapshot is not in S3; upload it with upload-raw'):
            self.download()
        self.assertFalse((self.target / 'season=2023').exists())

    def test_reference_report_from_s3_decides_which_manifests_and_metadata(self):
        with self.assertRaisesRegex(s3.S3StorageError, 'Required S3 object is missing'):
            week_refresh.download_history(self.store, self.root / 'other', 'c' * 64)
        # A manifest looked up in another season's folder is not found there.
        with self.assertRaisesRegex(s3.S3StorageError, 'is not in S3'):
            self.store.download_raw(2024, self.history[0].name, self.root / 'wrong-season')
        # A hash-consistent 2021 pair copied into the 2024 folder is still refused.
        for suffix in ('.manifest.json', '.json'):
            self.client.objects[self.key(2021, suffix).replace('season=2021', 'season=2024')] = \
                self.client.objects[self.key(2021, suffix)]
        with self.assertRaisesRegex(s3.S3StorageError, 'season does not match its S3 folder'):
            self.store.download_raw(2024, self.history[0].name, self.root / 'wrong-season')
        self.assertFalse((self.root / 'wrong-season').exists())

    def test_invalid_arguments_refused_before_any_aws_call(self):
        for season, name in ((True, 'a' * 32 + '.manifest.json'), ('2021', 'a' * 32 + '.manifest.json'),
                             (2021, '../escape.manifest.json'), (2021, 'a' * 32 + '.json')):
            with self.subTest(season=season, name=name), self.assertRaises(s3.S3StorageError):
                self.store.download_raw(season, name, self.root / 'refused')
        self.assertEqual(self.client.calls, [])
        self.assertFalse((self.root / 'refused').exists())


if __name__ == '__main__':
    unittest.main()
