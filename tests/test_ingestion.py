"""Offline ingestion/storage checks. All HTTP traffic is mocked."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dotenv import load_dotenv
import requests

from src.ingestion import cfbd, storage

TEST_KEY = "test-credential-not-a-real-api-key"


def game(**changes):
    record = {
        "id": 1, "season": 2025, "week": 1, "seasonType": "regular",
        "startDate": "2025-08-30T16:00:00Z", "startTimeTBD": False,
        "completed": True, "neutralSite": False,
        "homeId": 10, "homeTeam": "Home", "homeClassification": "fbs", "homePoints": 28,
        "awayId": 20, "awayTeam": "Away", "awayClassification": "fcs", "awayPoints": 7,
        "homePostgameWinProbability": 0.95, "extraSourceField": {"preserve": True},
    }
    return record | changes


def response(records=None, *, status=200, raw=None, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = raw if raw is not None else json.dumps([game()] if records is None else records).encode()
    result._content_consumed = True
    result.headers.update(headers or {})
    return result


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"CFBD_API_KEY": TEST_KEY}, clear=True))
        self.dotenv = self.enterContext(patch.object(cfbd, "load_dotenv"))
        self.http = self.enterContext(patch.object(cfbd.requests, "get", return_value=response()))
        self.sleep = self.enterContext(patch.object(cfbd.time, "sleep"))
        self.output_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_request_contract_without_week(self):
        result = cfbd.fetch_games(2025)
        self.http.assert_called_once_with(
            cfbd.ENDPOINT,
            params={"year": 2025, "seasonType": "regular", "classification": "fbs"},
            headers={"Authorization": f"Bearer {TEST_KEY}", "Accept": "application/json"},
            timeout=(5, 30), allow_redirects=False,
        )
        self.dotenv.assert_called_once_with(cfbd.PROJECT_ROOT / ".env", override=False)
        self.assertEqual(datetime.fromisoformat(result.retrieved_at).tzinfo, timezone.utc)
        self.assertNotIn(TEST_KEY, repr(result))

    def test_week_zero_is_not_omitted(self):
        cfbd.fetch_games(2025, week=0)
        self.assertEqual(self.http.call_args.kwargs["params"]["week"], 0)

    def test_persistence_preserves_bytes_hash_count_and_provenance(self):
        raw = (json.dumps([game(), game(id=2, awayClassification="fbs")], indent=3) + "\n").encode()
        self.http.return_value = response(raw=raw)
        result = cfbd.fetch_games(2025)
        raw_path, manifest_path = storage.save_snapshot(result, self.output_dir)
        self.assertEqual(raw_path.parent, self.output_dir / "season=2025")
        self.assertEqual(raw_path.read_bytes(), raw)
        manifest = json.loads(manifest_path.read_bytes())
        reloaded = json.loads(raw_path.read_bytes())
        self.assertEqual(manifest["sha256"], hashlib.sha256(raw_path.read_bytes()).hexdigest())
        self.assertEqual(manifest["record_count"], len(reloaded))
        self.assertEqual(manifest["record_count"], 2)
        self.assertEqual(manifest["http_status"], 200)
        self.assertEqual(manifest["endpoint"], cfbd.ENDPOINT)
        self.assertEqual(manifest["source"], "College Football Data")
        self.assertEqual(manifest["request_parameters"], result.parameters)
        self.assertEqual(manifest["retrieved_at"], result.retrieved_at)
        self.assertEqual(manifest["snapshot_version"], 1)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["response_file"], raw_path.name)
        self.assertEqual(manifest["source_availability"]["status"], "unknown")
        self.assertIsNone(manifest["source_availability"]["available_at"])
        self.assertFalse(manifest["approved_for_predictor_use"])
        self.assertEqual(reloaded[0]["extraSourceField"], {"preserve": True})
        self.assertIn("homePostgameWinProbability", reloaded[0])
        self.assertNotIn(TEST_KEY, manifest_path.read_text())
        self.assertNotIn("Authorization", manifest_path.read_text())

    def test_snapshots_are_unique_and_existing_files_survive(self):
        result = cfbd.fetch_games(2025)
        first = storage.save_snapshot(result, self.output_dir)
        original = [path.read_bytes() for path in first]
        second = storage.save_snapshot(result, self.output_dir)
        self.assertNotEqual(first, second)
        self.assertEqual([path.read_bytes() for path in first], original)
        with patch.object(storage, "uuid4") as uuid:
            uuid.return_value.hex = first[0].stem
            with self.assertRaises(storage.SnapshotError):
                storage.save_snapshot(result, self.output_dir)
        self.assertEqual([path.read_bytes() for path in first], original)
        self.assertEqual(len(list(first[0].parent.iterdir())), 4)

    def test_atomic_publish_is_complete_and_manifest_is_last(self):
        result = cfbd.fetch_games(2025)
        published = []
        real_link = os.link

        def observe_link(temp, destination):
            data = Path(temp).read_bytes()
            json.loads(data)  # Every linked file is already complete JSON.
            if destination.name.endswith(".manifest.json"):
                self.assertTrue(destination.with_name(destination.name.replace(".manifest", "")).exists())
            published.append(destination)
            real_link(temp, destination)

        with patch.object(storage.os, "link", side_effect=observe_link):
            paths = storage.save_snapshot(result, self.output_dir)
        self.assertEqual(published, list(paths))
        self.assertFalse(list(paths[0].parent.glob(".snapshot-*")))

    def test_storage_failure_has_no_partial_manifest_or_secret_error(self):
        result = cfbd.fetch_games(2025)
        real_create = storage._atomic_create

        def fail_manifest(path, content):
            if path.name.endswith(".manifest.json"):
                raise OSError(f"sensitive diagnostic {TEST_KEY}")
            real_create(path, content)

        with patch.object(storage, "_atomic_create", side_effect=fail_manifest):
            with self.assertRaises(storage.SnapshotError) as error:
                storage.save_snapshot(result, self.output_dir)
        self.assertNotIn(TEST_KEY, str(error.exception))
        self.assertIn("incomplete", str(error.exception))
        self.assertEqual(len(list(self.output_dir.rglob("*.json"))), 1)
        self.assertFalse(list(self.output_dir.rglob("*.manifest.json")))

    def test_failed_flush_leaves_no_published_or_temporary_files(self):
        result = cfbd.fetch_games(2025)
        with patch.object(storage.os, "fsync", side_effect=OSError("disk unavailable")):
            with self.assertRaises(storage.SnapshotError):
                storage.save_snapshot(result, self.output_dir)
        self.assertFalse(list((self.output_dir / "season=2025").iterdir()))

    def test_field_coverage_duplicates_nulls_and_mixed_classifications(self):
        first = game()
        del first["startDate"]
        records = [first, game(homePoints=None, awayClassification="fbs")]
        self.http.return_value = response(records)
        raw_path, manifest_path = storage.save_snapshot(cfbd.fetch_games(2025), self.output_dir)
        self.assertEqual(json.loads(raw_path.read_bytes()), records)
        report = json.loads(manifest_path.read_bytes())["coverage"]
        self.assertEqual(set(report["missing_fields"]), set(storage.REQUIRED_FIELDS))
        self.assertEqual(report["missing_fields"]["startDate"], 1)
        self.assertEqual(report["null_fields"]["homePoints"], 1)
        self.assertEqual(report["duplicate_game_ids"], {"1": 2})
        self.assertEqual(report["classification_counts"], {"home": {"fbs": 2}, "away": {"fbs": 1, "fcs": 1}})
        self.assertEqual(report["both_opponents_fbs_count"], 1)
        self.assertEqual(report["other_or_unknown_classification_count"], 1)

    def test_invalid_ids_and_classifications_are_reported_not_repaired(self):
        records = [{}, game(id=[], homeClassification=None, awayClassification=[]), game(id=True)]
        report = storage.coverage_report(records)
        self.assertEqual(report["invalid_game_id_count"], 2)
        self.assertEqual(report["missing_fields"]["id"], 1)
        self.assertEqual(report["classification_counts"]["home"]["<null>"], 1)
        self.assertEqual(report["classification_counts"]["away"]["<invalid>"], 1)

    def test_empty_response_is_saved_but_explicitly_reported_empty(self):
        self.http.return_value = response([])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = cfbd.main(["--season", "2025", "--output-dir", str(self.output_dir)])
        self.assertEqual(code, 0)
        self.assertIn("EMPTY response", stdout.getvalue())
        manifest_path = next(self.output_dir.rglob("*.manifest.json"))
        manifest = json.loads(manifest_path.read_bytes())
        raw_path = manifest_path.parent / manifest["response_file"]
        self.assertEqual(json.loads(raw_path.read_bytes()), [])
        self.assertEqual(manifest["record_count"], 0)
        self.assertEqual(manifest["coverage"]["status"], "empty")
        self.assertEqual(manifest["sha256"], hashlib.sha256(raw_path.read_bytes()).hexdigest())

    def test_cli_success_and_default_output(self):
        stdout = io.StringIO()
        with patch.object(storage, "DEFAULT_OUTPUT_DIR", self.output_dir), redirect_stdout(stdout):
            self.assertEqual(cfbd.main(["--season", "2025", "--week", "1"]), 0)
        self.assertIn("Stored 1 records", stdout.getvalue())
        self.assertIn('"classification_counts"', stdout.getvalue())
        self.assertEqual(self.http.call_args.kwargs["params"]["week"], 1)
        self.assertEqual(len(list(self.output_dir.rglob("*.json"))), 2)

    def test_missing_credentials_prevent_network_and_storage(self):
        del os.environ["CFBD_API_KEY"]
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cfbd.main(["--season", "2025", "--output-dir", str(self.output_dir)])
        self.assertEqual(code, 1)
        self.assertIn("Set CFBD_API_KEY", stderr.getvalue())
        self.http.assert_not_called()
        self.assertFalse(list(self.output_dir.iterdir()))

    def test_project_dotenv_is_used_without_overriding_environment(self):
        (self.output_dir / ".env").write_text("CFBD_API_KEY=dotenv-test-key\n")
        self.dotenv.side_effect = load_dotenv
        with patch.object(cfbd, "PROJECT_ROOT", self.output_dir):
            cfbd.fetch_games(2025)
            self.assertEqual(self.http.call_args.kwargs["headers"]["Authorization"], f"Bearer {TEST_KEY}")
            del os.environ["CFBD_API_KEY"]
            cfbd.fetch_games(2025)
            self.assertEqual(self.http.call_args.kwargs["headers"]["Authorization"], "Bearer dotenv-test-key")

    def test_blank_environment_key_does_not_fall_back_to_dotenv(self):
        (self.output_dir / ".env").write_text("CFBD_API_KEY=dotenv-test-key\n")
        self.dotenv.side_effect = load_dotenv
        os.environ["CFBD_API_KEY"] = ""
        with patch.object(cfbd, "PROJECT_ROOT", self.output_dir), self.assertRaises(cfbd.CFBDError):
            cfbd.fetch_games(2025)
        self.http.assert_not_called()

    def test_bad_key_format_is_sanitized_before_http(self):
        os.environ["CFBD_API_KEY"] = TEST_KEY + "\ninvalid"
        with self.assertRaises(cfbd.CFBDError) as error:
            cfbd.fetch_games(2025)
        self.assertNotIn(TEST_KEY, str(error.exception))
        self.http.assert_not_called()

    def test_authentication_failures_are_not_retried(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.http.reset_mock()
                self.http.return_value = response(status=status, raw=f"Authorization: Bearer {TEST_KEY}".encode())
                with self.assertRaises(cfbd.CFBDError) as error:
                    cfbd.fetch_games(2025)
                self.assertIn(str(status), str(error.exception))
                self.assertNotIn(TEST_KEY, str(error.exception))
                self.assertNotIn("Authorization", str(error.exception))
                self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()

    def test_rate_limit_retries_then_succeeds(self):
        self.http.side_effect = [response(status=429, headers={"Retry-After": "2"}), response()]
        self.assertEqual(cfbd.fetch_games(2025).http_status, 200)
        self.assertEqual(self.http.call_count, 2)
        self.sleep.assert_called_once_with(2.0)

    def test_rate_limit_and_server_errors_have_bounded_retries(self):
        for status in (429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.http.reset_mock()
                self.sleep.reset_mock()
                self.http.return_value = response(status=status)
                with self.assertRaises(cfbd.CFBDError) as error:
                    cfbd.fetch_games(2025)
                self.assertIn(str(status), str(error.exception))
                self.assertEqual(self.http.call_count, 3)
                self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [1.0, 2.0])

    def test_retry_after_date_and_invalid_value(self):
        now = datetime(2026, 9, 23, tzinfo=timezone.utc)
        with patch.object(cfbd, "datetime") as clock:
            clock.now.return_value = now
            self.assertEqual(cfbd._retry_delay(format_datetime(now.replace(second=10)), 0), 10)
        self.assertEqual(cfbd._retry_delay("invalid", 1), 2)
        self.assertEqual(cfbd._retry_delay("-1", 0), 0)

    def test_long_retry_after_stops_without_retrying_early(self):
        self.http.return_value = response(status=429, headers={"Retry-After": "3600"})
        with self.assertRaisesRegex(cfbd.CFBDError, "longer retry wait"):
            cfbd.fetch_games(2025)
        self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()

    def test_network_failures_are_bounded_and_secret_safe(self):
        for error_type in (requests.Timeout, requests.ConnectionError):
            with self.subTest(error=error_type):
                self.http.reset_mock()
                self.http.side_effect = error_type(f"Authorization: Bearer {TEST_KEY}")
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    code = cfbd.main(["--season", "2025", "--output-dir", str(self.output_dir)])
                self.assertEqual(code, 1)
                self.assertEqual(self.http.call_count, 3)
                self.assertNotIn(TEST_KEY, stderr.getvalue())
                self.assertNotIn("Authorization", stderr.getvalue())
        self.assertFalse(list(self.output_dir.iterdir()))

    def test_nontransient_request_exception_is_sanitized_and_not_retried(self):
        self.http.side_effect = requests.RequestException(TEST_KEY)
        with self.assertRaises(cfbd.CFBDError) as error:
            cfbd.fetch_games(2025)
        self.assertNotIn(TEST_KEY, str(error.exception))
        self.assertEqual(self.http.call_count, 1)

    def test_other_http_errors_and_redirects_are_not_retried(self):
        for status in (301, 302, 400, 404):
            with self.subTest(status=status):
                self.http.reset_mock()
                self.http.return_value = response(status=status)
                with self.assertRaisesRegex(cfbd.CFBDError, str(status)):
                    cfbd.fetch_games(2025)
                self.assertEqual(self.http.call_count, 1)

    def test_malformed_json_and_invalid_envelopes_are_not_saved(self):
        for raw in (b"not JSON", b"\xff", b"{}", b"null", b"[1]", b"[null]", b'[{"id": NaN}]'):
            with self.subTest(raw=raw):
                self.http.reset_mock()
                self.http.return_value = response(raw=raw)
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(cfbd.main(["--season", "2025", "--output-dir", str(self.output_dir)]), 1)
                self.assertEqual(self.http.call_count, 1)
                self.assertFalse(list(self.output_dir.iterdir()))

    def test_success_response_echoing_key_is_rejected_without_persistence(self):
        for raw in (json.dumps([game(notes=TEST_KEY)]).encode(),
                    json.dumps([game(notes=TEST_KEY)]).replace("test-credential", "\\u0074est-credential").encode()):
            with self.subTest(raw=raw):
                self.http.return_value = response(raw=raw)
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(cfbd.main(["--season", "2025", "--output-dir", str(self.output_dir)]), 1)
                self.assertNotIn(TEST_KEY, stderr.getvalue())
                self.assertFalse(list(self.output_dir.iterdir()))

    def test_invalid_arguments_prevent_http(self):
        for season, week in ((True, None), (2025.5, None), (1800, None), (2025, -1), (2025, True)):
            with self.subTest(season=season, week=week), self.assertRaises(cfbd.CFBDError):
                cfbd.fetch_games(season, week)
        self.http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
