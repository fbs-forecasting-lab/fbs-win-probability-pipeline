"""Offline synthetic checks for the fixed demo model and artifact contract."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning

from src.evaluation.metrics import evaluate_probabilities
from src.features import dataset, games
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot
from src.models import baseline, predict
from tests.test_dataset import game


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No network')))
        self.data = self.root / 'dataset'
        normalized = self.root / 'normalized'
        manifests = []
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
        dataset.build_dataset(manifests, self.data, allow_retrospective_demo=True, normalized_root=normalized)
        self.output = self.root / 'model'

    def read_rows(self, name):
        with (self.data / name).open(newline='') as handle:
            reader = csv.DictReader(handle)
            return reader.fieldnames, list(reader)

    def change_rows(self, name, change):
        columns, rows = self.read_rows(name)
        change(rows)
        (self.data / name).write_bytes(dataset._csv(rows, columns))
        self.refresh_hash(name)

    def refresh_hash(self, name):
        path = self.data / 'dataset_report.json'
        report = json.loads(path.read_bytes())
        report['artifact_sha256'][name] = baseline.digest((self.data / name).read_bytes())
        path.write_bytes(dataset._json(report))

    def load(self):
        return baseline.load_dataset(self.data, allow_retrospective_demo=True)

    def train(self, output=None):
        return baseline.train_baseline(self.data, output or self.output, allow_retrospective_demo=True)

    def restore(self, output=None):
        return baseline.load_trusted_model(output or self.output, allow_retrospective_demo=True)[0]

    def test_exact_predictors_and_training_only_scaler_fit(self):
        self.change_rows('holdout.csv', lambda rows: [row.update(prior_avg_margin_diff='5000') for row in rows])
        data = self.load()
        self.train()
        model = self.restore()
        self.assertEqual(list(model.feature_names_in_), baseline.PREDICTORS)
        self.assertEqual(model.named_steps['logistic'].n_features_in_, 3)
        np.testing.assert_allclose(model.named_steps['scaler'].mean_, data['splits']['train']['x'].mean())
        np.testing.assert_allclose(model.named_steps['scaler'].var_, data['splits']['train']['x'].var(ddof=0))
        self.assertEqual(model.named_steps['scaler'].n_samples_seen_, len(data['splits']['train']['y']))
        row = dict(data['splits']['train']['rows'][0])
        a = baseline.feature_frame([row])
        row.update(home_points='99999', away_points='99999', home_win='1', home_prior_game_count='9999', game_id='9999')
        np.testing.assert_array_equal(a, baseline.feature_frame([row]))

    def test_holdout_labels_cannot_change_fit_or_predictions(self):
        _, first_metrics = self.train()
        first = self.restore()
        data = self.load()
        before = baseline.home_probabilities(first, data['splits']['holdout']['x'])
        # Make every holdout label wrong under the original predictions; the
        # synthetic fixture originally has some correct decisions.
        self.change_rows('holdout.csv', lambda rows: [row.update(home_win=str(int(p < .5)))
                                                      for row, p in zip(rows, before)])
        other = self.root / 'other-model'
        _, second_metrics = self.train(other)
        second = self.restore(other)
        np.testing.assert_array_equal(first.named_steps['logistic'].coef_, second.named_steps['logistic'].coef_)
        np.testing.assert_array_equal(first.named_steps['logistic'].intercept_, second.named_steps['logistic'].intercept_)
        np.testing.assert_array_equal(first.named_steps['scaler'].mean_, second.named_steps['scaler'].mean_)
        np.testing.assert_array_equal(before, baseline.home_probabilities(second, data['splits']['holdout']['x']))
        self.assertNotEqual(first_metrics['model'], second_metrics['model'])

    def test_constant_baseline_uses_training_rate(self):
        self.change_rows('holdout.csv', lambda rows: [row.update(home_win='1') for row in rows])
        data = self.load()
        metadata, evaluation = self.train()
        rate = float(data['splits']['train']['y'].mean())
        self.assertNotEqual(rate, 1)
        self.assertEqual(metadata['constant_training_home_win_rate'], rate)
        expected, _ = evaluate_probabilities(data['splits']['holdout']['y'], [rate] * 4)
        self.assertEqual(evaluation['constant_baseline'], expected)

    def test_metrics_and_fixed_bins_hand_calculations(self):
        metrics, bins = evaluate_probabilities([0, 1], [.25, .75])
        self.assertAlmostEqual(metrics['brier_score'], .0625)
        self.assertAlmostEqual(metrics['log_loss'], -np.log(.75))
        self.assertEqual(metrics['accuracy'], 1)
        self.assertEqual(len(bins), 10)
        self.assertEqual(bins[2]['count'], 1)
        self.assertEqual(bins[2]['mean_predicted_probability'], .25)
        self.assertEqual(bins[7]['observed_home_win_rate'], 1)
        self.assertEqual(bins[0]['count'], 0)
        self.assertIsNone(bins[0]['mean_predicted_probability'])
        self.assertIsNone(bins[0]['observed_home_win_rate'])
        _, endpoints = evaluate_probabilities([0, 1, 1, 1], [0, .1, .5, 1])
        self.assertEqual([endpoints[i]['count'] for i in (0, 1, 5, 9)], [1, 1, 1, 1])
        self.assertEqual(evaluate_probabilities([1], [.5])[0]['accuracy'], 1)
        for y, p in (([], []), ([1], [float('nan')]), ([2], [.5]), ([1], [1.1])):
            with self.assertRaises(ValueError):
                evaluate_probabilities(y, p)

    def test_probability_class_mapping_complements_and_reload(self):
        self.train()
        model = self.restore()
        data = self.load()
        for split in data['splits'].values():
            p = baseline.home_probabilities(model, split['x'])
            self.assertTrue(((p >= 0) & (p <= 1)).all())
        report = predict.predict_saved_sample(self.output, self.data, self.root / 'batch', allow_retrospective_demo=True)
        self.assertEqual(report['count'], 4)
        self.assertEqual((self.output / 'sample_predictions.csv').read_bytes(), (self.root / 'batch/predictions.csv').read_bytes())
        rows = list(csv.DictReader(io.StringIO((self.root / 'batch/predictions.csv').read_text())))
        for row in rows:
            self.assertAlmostEqual(float(row['home_win_probability']) + float(row['away_win_probability']), 1)
            self.assertEqual(row['historical_availability_status'], 'unknown')
        class ReverseModel:
            classes_ = np.array([1, 0])
            def predict_proba(self, x):
                return np.tile([.8, .2], (len(x), 1))
        np.testing.assert_allclose(baseline.home_probabilities(ReverseModel(), data['splits']['prediction']['x']), .8)

    def test_invalid_feature_values_names_and_order(self):
        for name, value in [('prior_win_pct_diff', ''), ('prior_win_pct_diff', 'nan'),
                            ('prior_avg_margin_diff', 'inf'), ('prior_avg_margin_diff', 'bad'),
                            ('prior_win_pct_diff', '1.01'), ('home_field', '.5')]:
            columns, rows = self.read_rows('train.csv')
            original = (self.data / 'train.csv').read_bytes()
            rows[0][name] = value
            (self.data / 'train.csv').write_bytes(dataset._csv(rows, columns))
            self.refresh_hash('train.csv')
            with self.subTest(name=name, value=value), self.assertRaises(baseline.BaselineError):
                self.load()
            (self.data / 'train.csv').write_bytes(original)
            self.refresh_hash('train.csv')
        with self.assertRaises(baseline.BaselineError):
            baseline.feature_frame([{'home_field': 1}])
        frame = baseline.feature_frame([dict(zip(baseline.PREDICTORS, [0, 0, 1]))])
        with self.assertRaises(baseline.BaselineError):
            baseline.validate_features(frame[baseline.PREDICTORS[::-1]])
        path = self.data / 'dataset_report.json'
        report = json.loads(path.read_bytes())
        report['predictor_columns'].append('home_points')
        path.write_bytes(dataset._json(report))
        with self.assertRaises(baseline.BaselineError):
            self.load()

    def test_bad_hash_or_missing_artifact_rejected(self):
        path = self.data / 'train.csv'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(baseline.BaselineError, 'hash'):
            self.load()
        (self.data / 'team_season_aggregates.csv').rename(self.data / 'moved.csv')
        with self.assertRaisesRegex(baseline.BaselineError, 'read'):
            self.load()

    def test_labels_split_seasons_duplicates_and_overlap_rejected(self):
        original = (self.data / 'train.csv').read_bytes()
        _, holdout = self.read_rows('holdout.csv')
        edits = [lambda rows: rows[0].update(home_win='2'), lambda rows: rows[0].update(home_win=''),
                 lambda rows: rows[0].update(season='2025'), lambda rows: rows[0].update(game_id=rows[1]['game_id']),
                 lambda rows: rows[0].update(game_id=holdout[0]['game_id']),
                 lambda rows: [row.update(home_win='1') for row in rows]]
        for edit in edits:
            self.change_rows('train.csv', edit)
            with self.assertRaises(baseline.BaselineError):
                self.load()
            (self.data / 'train.csv').write_bytes(original)
            self.refresh_hash('train.csv')

    def test_flag_status_schema_and_counts_fail_closed(self):
        with self.assertRaisesRegex(baseline.BaselineError, 'allow-retrospective-demo'):
            baseline.train_baseline(self.data, self.output)
        self.assertFalse(self.output.exists())
        path = self.data / 'dataset_report.json'
        original = path.read_bytes()
        edits = [lambda r: r.update(dataset_schema_version=2), lambda r: r.update(dataset_mode='live'),
                 lambda r: r.update(approved_for_point_in_time_forecasting=True),
                 lambda r: r['splits']['train'].update(output=999)]
        for edit in edits:
            report = json.loads(original)
            edit(report)
            path.write_bytes(dataset._json(report))
            with self.assertRaises(baseline.BaselineError):
                self.load()
        path.write_bytes(original)

    def test_nonempty_training_and_holdout_required_empty_prediction_supported(self):
        for split in ('train', 'holdout', 'prediction'):
            name = f'{split}.csv'
            original = (self.data / name).read_bytes()
            report_path = self.data / 'dataset_report.json'
            original_report = report_path.read_bytes()
            columns, _ = self.read_rows(name)
            (self.data / name).write_bytes(dataset._csv([], columns))
            self.refresh_hash(name)
            report = json.loads(report_path.read_bytes())
            report['splits'][split].update(input=0, output=0)
            report_path.write_bytes(dataset._json(report))
            if split == 'prediction':
                metadata, _ = self.train()
                self.assertEqual(metadata['counts']['prediction'], 0)
                result = predict.predict_saved_sample(self.output, self.data, self.root / 'empty', allow_retrospective_demo=True)
                self.assertEqual(result['count'], 0)
                self.assertEqual(len((self.root / 'empty/predictions.csv').read_text().splitlines()), 1)
            else:
                with self.assertRaises(baseline.BaselineError):
                    self.load()
            (self.data / name).write_bytes(original)
            report_path.write_bytes(original_report)

    def test_hypothetical_vector_and_cli(self):
        self.train()
        model = self.restore()
        values = dict(zip(baseline.PREDICTORS, [.2, 7, 1]))
        result = predict.predict_vector(model, values)
        self.assertIn('hypothetical', result['input_context'])
        self.assertAlmostEqual(result['home_win_probability'] + result['away_win_probability'], 1)
        for bad in ({**values, 'score': 7}, dict(reversed(list(values.items()))), {**values, 'home_field': 2}):
            with self.assertRaises(baseline.BaselineError):
                predict.predict_vector(model, bad)
        out = io.StringIO()
        with redirect_stdout(out):
            code = predict.main(['--model-dir', str(self.output), '--prior-win-pct-diff', '.2',
                                 '--prior-avg-margin-diff', '7', '--home-field', '1', '--allow-retrospective-demo'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['features'], values)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(baseline.main(['--dataset-dir', str(self.data), '--output-dir', str(self.output)]), 1)

    def test_convergence_warning_fails_before_publication(self):
        def fail(*args, **kwargs):
            warnings.warn('synthetic convergence failure', ConvergenceWarning)
        with patch.object(baseline.Pipeline, 'fit', side_effect=fail):
            with self.assertRaisesRegex(baseline.BaselineError, 'converge'):
                self.train()
        self.assertFalse(self.output.exists())

    def test_metadata_hashes_availability_and_conflicting_outputs(self):
        metadata, _ = self.train()
        self.assertEqual(metadata['counts'], {'train': 12, 'holdout': 4, 'prediction': 4})
        self.assertEqual(metadata['dataset_report_sha256'], baseline.digest((self.data / 'dataset_report.json').read_bytes()))
        self.assertFalse(metadata['approved_for_point_in_time_forecasting'])
        self.assertTrue(all(v['status'] == 'unknown' and v['available_at'] is None
                            for v in metadata['source_availability'].values()))
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.output.iterdir()}
        for name, hashed in metadata['artifact_sha256'].items():
            self.assertEqual(baseline.digest((self.output / name).read_bytes()), hashed)
        self.train()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.output.iterdir()})
        self.change_rows('holdout.csv', lambda rows: rows[0].update(home_win=str(1-int(rows[0]['home_win']))))
        with self.assertRaisesRegex(baseline.BaselineError, 'differs'):
            self.train()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.output.iterdir()})
        with self.assertRaisesRegex(baseline.BaselineError, 'exact verified dataset'):
            predict.predict_saved_sample(self.output, self.data, self.root / 'conflict', allow_retrospective_demo=True)

    def test_corrupt_model_never_deserialized(self):
        self.train()
        path = self.output / 'model.joblib'
        path.write_bytes(b'broken')
        with patch.object(baseline.joblib, 'load') as load:
            with self.assertRaisesRegex(baseline.BaselineError, 'hash'):
                self.restore()
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
