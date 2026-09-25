"""Synthetic local fixtures for reconstructed feature datasets; no network."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.features import dataset, games
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot


def game(year, number=1, **changes):
    return {
        "id": year * 100 + number, "season": year, "week": 4 if year == 2026 else 1,
        "seasonType": "regular", "startDate": f"{year}-09-{number:02d}T16:00:00Z",
        "startTimeTBD": False, "completed": year != 2026, "neutralSite": number == 2,
        "homeId": 10, "homeTeam": "Home", "awayId": 20 if number == 1 else 30,
        "awayTeam": "Away" if number == 1 else "Third", "homeClassification": "fbs",
        "awayClassification": "fbs", "homePoints": None if year == 2026 else (0 if number == 1 else 21),
        "awayPoints": None if year == 2026 else (7 if number == 1 else 14),
    } | changes


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.normalized = self.root / "interim"
        self.http = self.enterContext(patch("requests.sessions.Session.request",
                                            side_effect=AssertionError("Network is forbidden")))
        self.output_number = 0

    def fixtures(self, overrides=None, historical_week=None):
        overrides = overrides or {}
        paths = []
        for year in dataset.SEASONS:
            params = {"year": year, "seasonType": "regular", "classification": "fbs"}
            if year == 2026:
                params["week"] = 4
            elif historical_week is not None:
                params["week"] = historical_week
            rows = overrides.get(year, [game(year), game(year, 2)])
            result = GamesResponse(json.dumps(rows).encode(), params, "2026-09-23T04:00:00Z", 200)
            manifest = save_snapshot(result, self.root / "raw")[1]
            games.normalize_snapshot(manifest, self.normalized)
            paths.append(manifest)
        return paths

    def build(self, paths, output=None):
        if output is None:
            self.output_number += 1
            output = self.root / f"dataset-{self.output_number}"
        report = dataset.build_dataset(paths, output, allow_retrospective_demo=True, normalized_root=self.normalized)
        return output, report

    def rows(self, output, filename):
        with (output / filename).open(newline="") as handle:
            return list(csv.DictReader(handle))

    def test_correct_home_away_aggregates_zero_scores_and_predictor_order(self):
        output, report = self.build(self.fixtures())
        audit = {(int(row["season"]), int(row["team_id"])): row
                 for row in self.rows(output, "team_season_aggregates.csv")}
        home, away, third = (audit[(2021, team)] for team in (10, 20, 30))
        self.assertEqual((home["completed_game_count"], home["wins"], home["margin_sum"]), ("2", "1", "0"))
        self.assertEqual(float(home["prior_win_pct"]), 0.5)
        self.assertEqual(float(home["prior_avg_margin"]), 0.0)
        self.assertEqual(float(away["prior_win_pct"]), 1.0)
        self.assertEqual(float(away["prior_avg_margin"]), 7.0)
        self.assertEqual(float(third["prior_win_pct"]), 0.0)
        self.assertEqual(float(third["prior_avg_margin"]), -7.0)
        target = self.rows(output, "train.csv")[0]
        self.assertEqual([float(target[key]) for key in dataset.PREDICTOR_COLUMNS], [-0.5, -7.0, 1.0])
        self.assertEqual(target["home_points"], "0")
        self.assertEqual(target["home_win"], "0")
        self.assertEqual((target["home_prior_game_count"], target["away_prior_game_count"]), ("2", "1"))
        self.assertEqual(report["predictor_columns"], ["prior_win_pct_diff", "prior_avg_margin_diff", "home_field"])
        self.assertEqual(report["aggregate_row_count"], 15)

    def test_neutral_site_and_win_label(self):
        output, _ = self.build(self.fixtures())
        first, second = self.rows(output, "train.csv")[:2]
        self.assertEqual(first["home_field"], "1")
        self.assertEqual(second["neutral_site"], "true")
        self.assertEqual(second["home_field"], "0")
        self.assertEqual(second["home_win"], "1")

    def test_missing_team_history_excludes_without_strength_imputation(self):
        paths = self.fixtures({2022: [game(2022, homeId=98, awayId=99)]})
        output, report = self.build(paths)
        exclusions = json.loads((output / "exclusions.json").read_bytes())["rows"]
        rejected = next(row for row in exclusions if row["game_id"] == 202201)
        self.assertEqual(rejected["reasons"], ["missing_home_history", "missing_away_history"])
        self.assertEqual(rejected["home_prior_game_count"], 0)
        self.assertNotIn("prior_win_pct_diff", rejected)
        self.assertNotIn("home_win", rejected)
        self.assertNotIn("202201", [row["game_id"] for row in self.rows(output, "train.csv")])
        self.assertGreater(report["splits"]["train"]["excluded"], 0)

    def test_incomplete_game_never_enters_aggregates_or_training_labels(self):
        incomplete = game(2024, 3, id=401640992, completed=False, homePoints=None, awayPoints=None)
        output, report = self.build(self.fixtures({2024: [game(2024), game(2024, 2), incomplete]}))
        self.assertEqual(report["aggregate_usage"]["2024"]["completed_games_used"], 2)
        self.assertEqual(report["aggregate_usage"]["2024"]["incomplete_games_omitted"], [401640992])
        for row in self.rows(output, "team_season_aggregates.csv"):
            self.assertNotIn(401640992, json.loads(row["contributing_game_ids"]))
        exclusions = json.loads((output / "exclusions.json").read_bytes())["rows"]
        item = next(row for row in exclusions if row["game_id"] == 401640992)
        self.assertEqual(item["reasons"], ["target_uncompleted"])
        self.assertNotIn("401640992", [row["game_id"] for row in self.rows(output, "train.csv")])
        self.assertEqual(report["splits"]["train"]["output"], 6)

    def test_full_incomplete_season_does_not_supply_team_history(self):
        paths = self.fixtures({2021: [game(2021, completed=False, homePoints=None, awayPoints=None)]})
        output, report = self.build(paths)
        self.assertEqual(report["aggregate_usage"]["2021"]["completed_games_used"], 0)
        self.assertFalse(any(row["season"] == "2022" for row in self.rows(output, "train.csv")))

    def test_exact_previous_season_no_fallback_to_older_history(self):
        # Team 20 exists in 2021 but not 2022; it must not receive 2021 history in 2023.
        paths = self.fixtures({2022: [game(2022, 2)]})
        output, _ = self.build(paths)
        exclusions = json.loads((output / "exclusions.json").read_bytes())["rows"]
        rejected = next(row for row in exclusions if row["game_id"] == 202301)
        self.assertIn("missing_away_history", rejected["reasons"])
        for split in ("train", "holdout", "prediction"):
            for row in self.rows(output, f"{split}.csv"):
                self.assertEqual(int(row["feature_source_season"]), int(row["season"]) - 1)

    def test_fixed_split_boundaries_and_prediction_has_no_label_column(self):
        paths = self.fixtures({2026: [game(2026), game(2026, 2, completed=True, homePoints=7, awayPoints=0)]})
        output, report = self.build(paths)
        self.assertEqual({row["season"] for row in self.rows(output, "train.csv")}, {"2022", "2023", "2024"})
        self.assertEqual({row["season"] for row in self.rows(output, "holdout.csv")}, {"2025"})
        prediction = self.rows(output, "prediction.csv")
        self.assertEqual(len(prediction), 1)
        self.assertEqual(prediction[0]["season"], "2026")
        self.assertNotIn("home_win", prediction[0])
        self.assertEqual(prediction[0]["home_points"], "")
        self.assertEqual(report["splits"]["prediction"]["exclusion_reason_counts"], {"prediction_target_completed": 1})

    def test_week5_prediction_source_leaves_train_holdout_and_aggregates_unchanged(self):
        paths = self.fixtures()
        week4, week4_report = self.build(paths)
        rows = [game(2026, week=5, startDate="2026-10-03T16:00:00Z"),
                game(2026, 2, week=5, startDate="2026-10-03T19:30:00Z")]
        params = {"year": 2026, "seasonType": "regular", "classification": "fbs", "week": 5}
        week5_manifest = save_snapshot(GamesResponse(json.dumps(rows).encode(), params, "2026-09-25T02:00:00Z", 200),
                                       self.root / "raw")[1]
        games.normalize_snapshot(week5_manifest, self.normalized)
        week5, week5_report = self.build([*paths[:5], week5_manifest])
        for name in ("train.csv", "holdout.csv", "team_season_aggregates.csv"):
            self.assertEqual((week5 / name).read_bytes(), (week4 / name).read_bytes(), name)
        self.assertNotEqual(week5_report["dataset_id"], week4_report["dataset_id"])
        prediction = self.rows(week5, "prediction.csv")
        self.assertEqual({row["week"] for row in prediction}, {"5"})
        self.assertEqual({row["feature_source_season"] for row in prediction}, {"2025"})
        self.assertEqual(len(prediction), 2)

    def test_same_game_scores_change_label_but_not_its_predictors(self):
        first, _ = self.build(self.fixtures())
        second, _ = self.build(self.fixtures({2023: [game(2023, homePoints=70), game(2023, 2)]}))
        a = next(row for row in self.rows(first, "train.csv") if row["game_id"] == "202301")
        b = next(row for row in self.rows(second, "train.csv") if row["game_id"] == "202301")
        self.assertNotEqual(a["home_win"], b["home_win"])
        self.assertEqual([a[k] for k in dataset.PREDICTOR_COLUMNS], [b[k] for k in dataset.PREDICTOR_COLUMNS])

    def test_later_season_scores_cannot_change_earlier_predictors(self):
        first, _ = self.build(self.fixtures())
        second, _ = self.build(self.fixtures({2025: [game(2025, homePoints=99), game(2025, 2, awayPoints=80)]}))
        columns = ("game_id", *dataset.PREDICTOR_COLUMNS)
        for split in ("train", "holdout"):
            self.assertEqual([[row[k] for k in columns] for row in self.rows(first, f"{split}.csv")],
                             [[row[k] for k in columns] for row in self.rows(second, f"{split}.csv")])
        self.assertNotEqual(self.rows(first, "prediction.csv")[0]["prior_avg_margin_diff"],
                            self.rows(second, "prediction.csv")[0]["prior_avg_margin_diff"])

    def test_prior_games_must_start_strictly_before_target_cutoff(self):
        prior = game(2021, startDate="2022-09-01T16:00:00Z")
        output, report = self.build(self.fixtures({2021: [prior, game(2021, 2)]}))
        rejected = next(row for row in json.loads((output / "exclusions.json").read_bytes())["rows"]
                        if row["game_id"] == 202201)
        self.assertEqual(rejected["reasons"], ["home_history_not_before_cutoff", "away_history_not_before_cutoff"])
        self.assertIn("202202", [row["game_id"] for row in self.rows(output, "train.csv")])
        self.assertEqual(report["aggregate_usage"]["2021"]["completed_games_used"], 2)

    def test_flag_required_before_reading_or_writing(self):
        output = self.root / "blocked"
        with self.assertRaisesRegex(dataset.DatasetError, "allow-retrospective-demo"):
            dataset.build_dataset([self.root / "not_read.json"], output)
        self.assertFalse(output.exists())

    def test_availability_and_provenance_preserved_on_all_outputs(self):
        paths = self.fixtures()
        source_bytes = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        output, report = self.build(paths)
        self.assertEqual(report["dataset_mode"], "retrospective_demo")
        self.assertFalse(report["historical_availability_verified"])
        self.assertFalse(report["approved_for_point_in_time_forecasting"])
        for path in paths:
            source = json.loads(path.read_bytes())
            year = str(source["request_parameters"]["year"])
            provenance = report["sources"][year]["source"]
            self.assertEqual(provenance["snapshot_id"], source["snapshot_id"])
            self.assertEqual(provenance["raw_sha256"], source["sha256"])
            self.assertEqual(provenance["manifest_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(provenance["source_availability"], source["source_availability"])
            self.assertFalse(provenance["approved_for_predictor_use"])
        for filename in ("train.csv", "holdout.csv", "prediction.csv", "team_season_aggregates.csv"):
            for row in self.rows(output, filename):
                self.assertEqual(row["historical_availability_status"], "unknown")
                self.assertEqual(row["historical_available_at"], "")
                self.assertEqual(row["approved_for_predictor_use"], "false")
                self.assertEqual(row["approved_for_point_in_time_forecasting"], "false")
                self.assertEqual(row["dataset_mode"], "retrospective_demo")
                if filename != "team_season_aggregates.csv":
                    self.assertEqual(row["feature_source_availability_status"], "unknown")
                    self.assertEqual(row["feature_source_available_at"], "")
                    self.assertEqual(row["feature_source_approved_for_predictor_use"], "false")
                    self.assertEqual(row["source_manifest_sha256"], report["sources"][row["season"]]["source"]["manifest_sha256"])
        self.assertTrue(all(Path(name).read_bytes() == content for name, content in source_bytes.items()))
        self.http.assert_not_called()

    def test_counts_reconcile_and_report_hashes_match_files(self):
        output, report = self.build(self.fixtures({2022: [game(2022, awayId=99), game(2022, 2)]}))
        exclusions = json.loads((output / "exclusions.json").read_bytes())["rows"]
        for split, counts in report["splits"].items():
            self.assertEqual(counts["input"], counts["output"] + counts["excluded"])
            self.assertEqual(counts["output"], len(self.rows(output, f"{split}.csv")))
            self.assertEqual(counts["excluded"], sum(row["split"] == split for row in exclusions))
        for name, digest in report["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
        for season, usage in report["aggregate_usage"].items():
            total = sum(int(row["completed_game_count"]) for row in self.rows(output, "team_season_aggregates.csv")
                        if row["season"] == season)
            self.assertEqual(total, 2 * usage["completed_games_used"])

    def test_duplicate_missing_extra_seasons_and_week_limited_history_rejected(self):
        paths = self.fixtures()
        for candidate in (paths + [paths[0]], paths[1:], paths + [self.fixtures()[0]]):
            with self.subTest(paths=len(candidate)), self.assertRaises(dataset.DatasetError):
                self.build(candidate)
        with self.assertRaisesRegex(dataset.DatasetError, "full-season"):
            self.build(self.fixtures(historical_week=1))

    def test_corrupt_raw_or_normalized_artifacts_and_missing_outputs_rejected(self):
        for kind in ("raw", "games.csv", "quality_report.json", "missing"):
            with self.subTest(kind=kind):
                paths = self.fixtures()
                manifest = json.loads(paths[0].read_bytes())
                directory = self.normalized / manifest["snapshot_id"]
                if kind == "raw":
                    (paths[0].parent / manifest["response_file"]).write_text("[]")
                elif kind == "missing":
                    (directory / "exclusions.json").rename(directory / "moved.json")
                else:
                    (directory / kind).write_text("corrupt")
                with self.assertRaises(dataset.DatasetError):
                    self.build(paths)

    def test_empty_inputs_produce_headers_and_null_feature_ranges(self):
        output, report = self.build(self.fixtures({year: [] for year in dataset.SEASONS}))
        for split in dataset.SPLIT_SEASONS:
            self.assertEqual(self.rows(output, f"{split}.csv"), [])
            self.assertTrue((output / f"{split}.csv").read_text().startswith("game_id,"))
            self.assertEqual(report["splits"][split]["feature_ranges"]["home_field"], {"min": None, "max": None})

    def test_identical_reruns_and_manifest_order_are_byte_stable_without_rewrites(self):
        paths = self.fixtures()
        output, report = self.build(paths)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
        _, again = self.build(list(reversed(paths)), output)
        self.assertEqual(report, again)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()})
        other, _ = self.build(paths)
        self.assertEqual({p.name: p.read_bytes() for p in other.iterdir()}, {name: data[0] for name, data in before.items()})

    def test_conflicting_outputs_and_changed_inputs_are_not_overwritten(self):
        paths = self.fixtures()
        output, _ = self.build(paths)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with self.assertRaisesRegex(dataset.DatasetError, "differs"):
            self.build(self.fixtures(), output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
        (output / "unrelated.txt").write_text("keep")
        with self.assertRaisesRegex(dataset.DatasetError, "unexpected"):
            self.build(paths, output)

    def test_partial_publication_resumes_matching_files(self):
        paths = self.fixtures()
        output = self.root / "partial"
        create = dataset._atomic_create
        def interrupt(path, content):
            if path.name == "holdout.csv":
                raise OSError("disk failure")
            return create(path, content)
        with patch.object(dataset, "_atomic_create", side_effect=interrupt):
            with self.assertRaises(dataset.DatasetError):
                self.build(paths, output)
        self.assertFalse((output / "dataset_report.json").exists())
        mtime = (output / "train.csv").stat().st_mtime_ns
        self.build(paths, output)
        self.assertEqual((output / "train.csv").stat().st_mtime_ns, mtime)
        self.assertEqual(len(list(output.iterdir())), 6)

    def test_cli_requires_flag_and_builds_when_explicitly_enabled(self):
        paths = self.fixtures()
        output = self.root / "cli"
        args = ["--manifest", *map(str, paths), "--normalized-root", str(self.normalized), "--output-dir", str(output)]
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(dataset.main(args), 1)
        self.assertIn("Historical availability is unverified", stderr.getvalue())
        self.assertFalse(output.exists())
        with redirect_stdout(stdout):
            self.assertEqual(dataset.main(args + ["--allow-retrospective-demo"]), 0)
        self.assertIn("not approved for point-in-time forecasting", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
