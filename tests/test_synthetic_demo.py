"""Exercise the public synthetic example without network or private configuration."""

import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.models.baseline import STATUS

SPEC = importlib.util.spec_from_file_location("synthetic_demo", Path(__file__).resolve().parents[1] / "bin/synthetic_demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class SyntheticDemoTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        for target in ("socket.socket.connect", "requests.sessions.Session.request", "dotenv.load_dotenv",
                       "src.ingestion.cfbd.fetch_games", "src.ingestion.s3_storage.make_client"):
            self.enterContext(patch(target, side_effect=AssertionError("Offline example must not access network/configuration")))

    def run_example(self, name="example"):
        path = self.root / "data/processed" / name
        result = demo.run(path, root=self.root, allow_retrospective_demo=True)
        return path, result

    def test_full_pipeline_chronology_saved_model_and_finite_probabilities(self):
        with patch.object(demo, "train_baseline", wraps=demo.train_baseline) as train:
            path, summary = self.run_example()
        self.assertEqual(train.call_args.args[0], path / "dataset")
        self.assertEqual(summary["counts"], {"train": 18, "holdout": 6, "prediction": 6})
        self.assertEqual(summary["generated_games"], 36)
        self.assertEqual(summary["saved_model_prediction_count"], 6)
        for key, value in STATUS.items():
            self.assertEqual(summary[key], value)
        for split, seasons in (("train", {2022, 2023, 2024}), ("holdout", {2025}), ("prediction", {2026})):
            with (path / "dataset" / f"{split}.csv").open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual({int(row["season"]) for row in rows}, seasons)
            self.assertTrue(all("Synthetic" in row["home_team"] for row in rows))
        with (path / "predictions/predictions.csv").open() as handle:
            predictions = list(csv.DictReader(handle))
        for row in predictions:
            home, away = (float(row[f"{side}_win_probability"]) for side in ("home", "away"))
            self.assertTrue(math.isfinite(home) and math.isfinite(away))
            self.assertTrue(0 <= home <= 1 and 0 <= away <= 1)
            self.assertAlmostEqual(home + away, 1)
        for scores in summary["synthetic_holdout_metrics"].values():
            self.assertEqual(set(scores), {"brier_score", "log_loss", "accuracy"})
            self.assertTrue(all(math.isfinite(value) for value in scores.values()))
        self.assertEqual((path / "predictions/predictions.csv").read_bytes(),
                         (path / "model/sample_predictions.csv").read_bytes())
        for name in ("model/model.joblib", "model/evaluation.json", "model/calibration.json",
                     "model/holdout_predictions.csv", "model/model_metadata.json",
                     "dataset/team_season_aggregates.csv", "dataset/exclusions.json",
                     "predictions/prediction_report.json", "synthetic_summary.json", "SYNTHETIC.txt"):
            self.assertTrue((path / name).is_file(), name)
        report = json.loads((path / "dataset/dataset_report.json").read_text())
        self.assertTrue(all("SYNTHETIC ONLY" in item["source"]["source_availability"]["reason"]
                            for item in report["sources"].values()))

    def test_repeat_fresh_run_is_deterministic(self):
        first, a = self.run_example("first")
        second, b = self.run_example("second")
        self.assertEqual(a["dataset_id"], b["dataset_id"])
        self.assertEqual(a["synthetic_holdout_metrics"], b["synthetic_holdout_metrics"])
        for file in (first / "dataset").iterdir():
            self.assertEqual(file.read_bytes(), (second / "dataset" / file.name).read_bytes())
        self.assertEqual((first / "predictions/predictions.csv").read_bytes(),
                         (second / "predictions/predictions.csv").read_bytes())

    def test_rerun_refuses_and_preserves_every_file(self):
        path, _ = self.run_example()
        def evidence():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in path.rglob("*") if p.is_file()}
        before = evidence()
        with self.assertRaisesRegex(ValueError, "already exists"):
            demo.run(path, root=self.root, allow_retrospective_demo=True)
        self.assertEqual(before, evidence())

    def test_flag_and_unsafe_outputs_refused_before_generation(self):
        with patch.object(demo, "make_snapshot") as generate:
            with self.assertRaisesRegex(ValueError, "allow-retrospective"):
                demo.run("data/processed/new", root=self.root)
            with self.assertRaisesRegex(ValueError, "beneath data/processed"):
                demo.run(self.root / "outside", root=self.root, allow_retrospective_demo=True)
            existing = self.root / "data/processed/existing"
            existing.parent.mkdir(parents=True)
            existing.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "already exists"):
                demo.run(existing, root=self.root, allow_retrospective_demo=True)
            self.assertEqual(existing.read_text(), "preserve")
            link = existing.parent / "link"
            link.symlink_to(existing)
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                demo.run(link, root=self.root, allow_retrospective_demo=True)
            generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
