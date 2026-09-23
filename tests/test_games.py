"""Offline game normalization tests using synthetic, local snapshot fixtures."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.features import games
from src.ingestion.cfbd import GamesResponse
from src.ingestion.storage import save_snapshot


def game(**changes):
    return {
        "id": 1, "season": 2025, "week": 3, "seasonType": "regular",
        "startDate": "2025-09-13T12:00:00-04:00", "startTimeTBD": False,
        "completed": True, "neutralSite": False, "homeId": 10, "homeTeam": "Home",
        "homeClassification": "fbs", "homePoints": 0, "awayId": 20,
        "awayTeam": "Away", "awayClassification": "fbs", "awayPoints": 7,
    } | changes


class GameNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.output = self.root / "interim"
        # Any accidentally introduced network access fails these tests.
        self.http = self.enterContext(patch("requests.sessions.Session.request",
                                            side_effect=AssertionError("Network is forbidden")))

    def snapshot(self, records=None, week=None):
        params = {"year": 2025, "classification": "fbs", "seasonType": "regular"}
        if week is not None:
            params["week"] = week
        raw = json.dumps([game()] if records is None else records).encode()
        result = GamesResponse(raw, params, "2026-09-23T04:00:00Z", 200)
        return save_snapshot(result, self.root / "raw")[1]

    def edit_manifest(self, path, **changes):
        manifest = json.loads(path.read_bytes()) | changes
        path.write_text(json.dumps(manifest))
        return manifest

    def run_snapshot(self, manifest):
        directory = games.normalize_snapshot(manifest, self.output)
        with (directory / "games.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        exclusions = json.loads((directory / "exclusions.json").read_bytes())
        report = json.loads((directory / "quality_report.json").read_bytes())
        return directory, rows, exclusions, report

    def test_valid_zero_score_timezone_conversion_and_provenance(self):
        manifest = self.snapshot()
        original = json.loads(manifest.read_bytes())
        raw = (manifest.parent / original["response_file"]).read_bytes()
        directory, rows, exclusions, report = self.run_snapshot(manifest)
        self.assertEqual(directory, self.output / original["snapshot_id"])
        row = rows[0]
        self.assertEqual(row["home_points"], "0")
        self.assertEqual(row["start_date"], "2025-09-13T16:00:00Z")
        self.assertEqual(row["completed"], "true")
        self.assertEqual(row["neutral_site"], "false")
        self.assertEqual(row["source_snapshot_id"], original["snapshot_id"])
        self.assertEqual(row["source_raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row["source_row_index"], "0")
        self.assertEqual(row["retrieved_at"], original["retrieved_at"])
        self.assertEqual(row["historical_availability_status"], "unknown")
        self.assertEqual(row["historical_available_at"], "")
        self.assertEqual(row["approved_for_predictor_use"], "false")
        self.assertEqual(report["normalization_schema_version"], 1)
        self.assertEqual(report["source"]["source_availability"], original["source_availability"])
        self.assertEqual(report["source"]["manifest_sha256"], hashlib.sha256(manifest.read_bytes()).hexdigest())
        self.assertFalse(report["approved_for_predictor_use"])
        self.assertEqual(exclusions["excluded"], [])
        self.assertEqual(exclusions["quarantined"], [])
        self.assertEqual((manifest.parent / original["response_file"]).read_bytes(), raw)

    def test_upcoming_null_and_absent_scores_remain_null(self):
        absent = game(id=2, completed=False)
        del absent["homePoints"], absent["awayPoints"]
        _, rows, _, report = self.run_snapshot(self.snapshot([
            game(completed=False, homePoints=None, awayPoints=None), absent,
        ]))
        self.assertEqual(report["counts"]["retained"], 2)
        for row in rows:
            self.assertEqual(row["home_points"], "")
            self.assertEqual(row["away_points"], "")
            self.assertEqual(row["completed"], "false")

    def test_fbs_filter_is_separate_from_invalid_rows_and_counts_reconcile(self):
        records = [game(), game(id=2, awayClassification="fcs"),
                   game(id=3, homeClassification="fcs"),
                   game(id=4, awayClassification="fcs", startTimeTBD=True),
                   game(id=5, homeTeam=" ")]
        _, rows, dispositions, report = self.run_snapshot(self.snapshot(records))
        self.assertEqual(report["counts"], {"input": 5, "retained": 1, "excluded": 2, "quarantined": 2})
        self.assertEqual(report["input_both_fbs_count"], 2)
        self.assertEqual(report["quarantined_both_fbs_count"], 1)
        all_indices = ([int(row["source_row_index"]) for row in rows]
                       + [item["source_row_index"] for item in dispositions["excluded"]]
                       + [item["source_row_index"] for item in dispositions["quarantined"]])
        self.assertEqual(sorted(all_indices), list(range(len(records))))
        self.assertEqual(dispositions["excluded"][0]["game_id"], 2)
        self.assertEqual(dispositions["excluded"][0]["away_classification"], "fcs")

    def test_all_duplicate_occurrences_quarantined_before_filtering(self):
        _, rows, dispositions, report = self.run_snapshot(self.snapshot([
            game(), game(awayClassification="fcs"), game(id=2),
        ]))
        self.assertEqual([row["id"] for row in rows], ["2"])
        self.assertEqual(report["counts"], {"input": 3, "retained": 1, "excluded": 0, "quarantined": 2})
        self.assertEqual([item["source_row_index"] for item in dispositions["quarantined"]], [0, 1])
        for item in dispositions["quarantined"]:
            self.assertTrue(any("duplicate" in reason for reason in item["reasons"]))

    def test_invalid_types_are_not_coerced(self):
        cases = [
            {"id": True}, {"id": "1"}, {"id": 1.0}, {"id": 0}, {"id": []},
            {"homeId": False}, {"awayId": -2}, {"awayId": 10},
            {"homeTeam": ""}, {"awayTeam": None}, {"homeTeam": 1},
            {"neutralSite": "false"}, {"completed": 1}, {"startTimeTBD": 0},
            {"homeClassification": None}, {"awayClassification": []}, {"awayClassification": "unknown"},
            {"season": "2025"}, {"week": True}, {"week": -1}, {"seasonType": None},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                _, rows, exclusions, report = self.run_snapshot(self.snapshot([game(**changes)]))
                self.assertEqual(rows, [])
                self.assertEqual(report["counts"]["quarantined"], 1)
                self.assertTrue(exclusions["quarantined"][0]["reasons"])

    def test_missing_required_fields_quarantined(self):
        row = game()
        del row["id"], row["homeTeam"], row["completed"]
        _, _, exclusions, report = self.run_snapshot(self.snapshot([row]))
        item = exclusions["quarantined"][0]
        self.assertIsNone(item["game_id"])
        self.assertIn("homeTeam: required field missing", item["reasons"])
        self.assertEqual(report["counts"]["quarantined"], 1)

    def test_naive_invalid_or_unresolved_timestamps_quarantined(self):
        cases = [{"startDate": "2025-09-13T16:00:00"}, {"startDate": "2025-09-13"},
                 {"startDate": "not a timestamp"}, {"startDate": "2025-02-30T16:00:00Z"},
                 {"startDate": None}, {"startDate": 1750000000}, {"startTimeTBD": True}]
        for changes in cases:
            with self.subTest(changes=changes):
                _, rows, exclusions, report = self.run_snapshot(self.snapshot([game(**changes)]))
                self.assertEqual(rows, [])
                self.assertEqual(report["counts"]["quarantined"], 1)
                self.assertTrue(any(reason.startswith(("startDate:", "startTimeTBD:"))
                                    for reason in exclusions["quarantined"][0]["reasons"]))

    def test_scores_and_completion_contradictions_quarantined(self):
        cases = [{"homePoints": None}, {"awayPoints": -1}, {"homePoints": True},
                 {"homePoints": "0"}, {"awayPoints": 7.0}, {"homePoints": []},
                 {"homePoints": 7}, {"completed": False},
                 {"completed": False, "homePoints": None},
                 {"completed": False, "homePoints": 0, "awayPoints": 0}]
        for changes in cases:
            with self.subTest(changes=changes):
                _, rows, exclusions, report = self.run_snapshot(self.snapshot([game(**changes)]))
                self.assertEqual(rows, [])
                self.assertEqual(report["counts"]["quarantined"], 1)
                self.assertTrue(exclusions["quarantined"][0]["reasons"])

    def test_manifest_year_week_and_season_type_must_match_rows(self):
        for changes in ({"season": 2026}, {"week": 4}, {"seasonType": "postseason"}):
            with self.subTest(changes=changes):
                _, rows, _, report = self.run_snapshot(self.snapshot([game(**changes)], week=3))
                self.assertEqual(rows, [])
                self.assertEqual(report["counts"]["quarantined"], 1)

    def test_unspecified_week_accepts_multiple_weeks_and_zero(self):
        _, rows, _, report = self.run_snapshot(self.snapshot([game(week=0), game(id=2, week=4)]))
        self.assertEqual([row["week"] for row in rows], ["0", "4"])
        self.assertEqual(report["counts"]["retained"], 2)

    def test_empty_input_and_all_filtered_outputs_have_headers(self):
        for records in ([], [game(awayClassification="fcs")], [game(startTimeTBD=True)]):
            with self.subTest(records=records):
                directory, rows, _, report = self.run_snapshot(self.snapshot(records))
                self.assertEqual(rows, [])
                self.assertEqual((directory / "games.csv").read_text(), ",".join(games.COLUMNS) + "\n")
                self.assertEqual(report["counts"]["input"], len(records))
                self.assertEqual(report["status"], "no_retained_games" if records else "empty_input")

    def test_integrity_rejects_wrong_or_missing_manifest_metadata(self):
        cases = [
            {"schema_version": 2}, {"snapshot_version": None}, {"schema_version": True},
            {"snapshot_id": "../escape"}, {"response_file": "../elsewhere.json"},
            {"record_count": 9}, {"record_count": True}, {"sha256": "0" * 64},
            {"coverage": {}}, {"coverage": None}, {"http_status": 401},
            {"endpoint": "https://example.com/games"}, {"source": "other"},
            {"retrieved_at": "2026-09-23T00:00:00"},
            {"source_availability": None}, {"source_availability": {"status": "unknown"}},
            {"source_availability": {"status": "unknown", "available_at": "2025-01-01T00:00:00Z"}},
            {"approved_for_predictor_use": True}, {"approved_for_predictor_use": 0},
            {"request_parameters": {"year": True, "seasonType": "regular", "classification": "fbs"}},
            {"request_parameters": {"year": 2025, "seasonType": "regular", "classification": "fbs", "week": -1}},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                manifest = self.snapshot()
                self.edit_manifest(manifest, **changes)
                with self.assertRaises(games.NormalizationError):
                    games.normalize_snapshot(manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_coverage_type_change_is_not_treated_as_equal(self):
        manifest = self.snapshot()
        value = json.loads(manifest.read_bytes())
        value["coverage"]["record_count"] = True
        manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(games.NormalizationError, "coverage"):
            games.load_snapshot(manifest)

    def test_missing_manifest_or_raw_and_symlink_raw_rejected(self):
        with self.assertRaisesRegex(games.NormalizationError, "Manifest"):
            games.load_snapshot(self.root / "absent.manifest.json")
        manifest = self.snapshot()
        value = json.loads(manifest.read_bytes())
        raw_path = manifest.parent / value["response_file"]
        other = self.root / "moved.json"
        raw_path.rename(other)
        with self.assertRaisesRegex(games.NormalizationError, "missing"):
            games.load_snapshot(manifest)
        raw_path.symlink_to(other)
        with self.assertRaisesRegex(games.NormalizationError, "symbolic"):
            games.load_snapshot(manifest)

    def test_malformed_manifests_rejected(self):
        manifest = self.root / "bad.manifest.json"
        for raw in (b"{", b"[]", b"null", b"\xff", b'{"schema_version":1,"schema_version":1}'):
            with self.subTest(raw=raw):
                manifest.write_bytes(raw)
                with self.assertRaises(games.NormalizationError):
                    games.load_snapshot(manifest)

    def test_raw_tampering_is_detected_before_normalization(self):
        manifest = self.snapshot()
        value = json.loads(manifest.read_bytes())
        (manifest.parent / value["response_file"]).write_bytes(b"[]")
        with self.assertRaisesRegex(games.NormalizationError, "SHA-256"):
            games.normalize_snapshot(manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_raw_shape_rejected_even_with_matching_hash(self):
        for raw in (b"not JSON", b"{}", b"[1]", b'[{"id": NaN}]'):
            with self.subTest(raw=raw):
                manifest = self.snapshot()
                value = self.edit_manifest(manifest, sha256=hashlib.sha256(raw).hexdigest())
                (manifest.parent / value["response_file"]).write_bytes(raw)
                with self.assertRaises(games.NormalizationError):
                    games.normalize_snapshot(manifest, self.output)

    def test_rerun_is_byte_identical_no_rewrite_and_raw_unchanged(self):
        manifest = self.snapshot()
        directory, _, _, report = self.run_snapshot(manifest)
        files = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}
        games.normalize_snapshot(manifest, self.output)
        self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}, files)
        alternate = games.normalize_snapshot(manifest, self.root / "alternate")
        self.assertEqual({p.name: p.read_bytes() for p in alternate.iterdir()}, {name: v[0] for name, v in files.items()})
        raw = manifest.parent / report["source"]["raw_file"]
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), report["source"]["raw_sha256"])

    def test_conflicting_output_is_not_overwritten(self):
        manifest = self.snapshot()
        directory, _, _, _ = self.run_snapshot(manifest)
        (directory / "games.csv").write_text("preserve this edited work\n")
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        with self.assertRaisesRegex(games.NormalizationError, "differs"):
            games.normalize_snapshot(manifest, self.output)
        self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before)

    def test_partial_output_rerun_completes_without_replacing_files(self):
        manifest = self.snapshot()
        real_create = games._atomic_create

        def interrupted(path, content):
            if path.name == "exclusions.json":
                raise OSError("simulated disk error")
            return real_create(path, content)

        with patch.object(games, "_atomic_create", side_effect=interrupted):
            with self.assertRaises(games.NormalizationError):
                games.normalize_snapshot(manifest, self.output)
        csv_path = next(self.output.rglob("games.csv"))
        old_mtime = csv_path.stat().st_mtime_ns
        directory, _, _, _ = self.run_snapshot(manifest)
        self.assertEqual(csv_path.stat().st_mtime_ns, old_mtime)
        self.assertEqual({p.name for p in directory.iterdir()}, {"games.csv", "exclusions.json", "quality_report.json"})

    def test_extra_output_entry_or_symlink_blocks_write(self):
        manifest = self.snapshot()
        directory, _, _, _ = self.run_snapshot(manifest)
        (directory / "unrelated.txt").write_text("keep")
        with self.assertRaisesRegex(games.NormalizationError, "unexpected"):
            games.normalize_snapshot(manifest, self.output)
        alternate = self.root / "linked"
        alternate.mkdir()
        (alternate / directory.name).symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(games.NormalizationError, "symbolic"):
            games.normalize_snapshot(manifest, alternate)

    def test_historical_availability_metadata_is_preserved_without_approval(self):
        manifest = self.snapshot()
        availability = {"status": "source_reported_unverified", "available_at": "2025-09-01T00:00:00-04:00", "reason": "Fixture only"}
        self.edit_manifest(manifest, source_availability=availability)
        _, rows, _, report = self.run_snapshot(manifest)
        self.assertEqual(rows[0]["historical_availability_status"], availability["status"])
        self.assertEqual(rows[0]["historical_available_at"], "2025-09-01T04:00:00Z")
        self.assertEqual(report["source"]["source_availability"], availability)
        self.assertFalse(report["approved_for_predictor_use"])

    def test_cli_multiple_explicit_manifests_processed_separately(self):
        first, second = self.snapshot(), self.snapshot()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = games.main(["--manifest", str(first), str(second), "--manifest", str(first),
                                 "--output-root", str(self.output)])
        self.assertEqual(status, 0)
        self.assertEqual(len(list(self.output.iterdir())), 2)
        self.assertEqual(stdout.getvalue().count('"retained": 1'), 3)
        self.http.assert_not_called()

    def test_cli_reports_failure_without_skipping_other_explicit_inputs(self):
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout):
            status = games.main(["--manifest", str(self.root / "missing.json"), str(self.snapshot()),
                                 "--output-root", str(self.output)])
        self.assertEqual(status, 1)
        self.assertIn("Manifest is unreadable", stderr.getvalue())
        self.assertEqual(len(list(self.output.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
