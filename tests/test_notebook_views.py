"""Offline checks for the Initial Demo notebook display helpers and the committed notebook file."""

import ast
import io
import json
from pathlib import Path
import tempfile
from contextlib import redirect_stdout
import re
import unittest
from unittest.mock import patch

import nbformat
import pandas as pd

from src.ingestion import s3_storage as s3
from src.ingestion.storage import PROJECT_ROOT
from src.models.baseline import BaselineError
from src.pipeline import notebook_views as views

NOTEBOOK = PROJECT_ROOT / "notebooks" / "initial_demo.ipynb"
DATASET_ID = "ab" * 32


class NotebookViewsTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('No network')))
        views.reset()
        self.addCleanup(views.reset)

    def test_eastern_time_formatting_and_tbd(self):
        self.assertEqual(views.et_time("2026-10-02T00:00:00Z"), "Thu Oct 1, 8:00 PM")
        self.assertEqual(views.et_time("2026-10-03T16:30:00.000Z"), "Sat Oct 3, 12:30 PM")
        self.assertEqual(views.et_time("2026-10-03T04:00:00.000Z", tbd=True), "Sat Oct 3, time TBD")
        self.assertEqual(views.fetch_line(200, 59, "2026-09-25T02:59:44.466329Z"),
                         "HTTP 200 — **59 games** received at Thu Sep 24, 10:59 PM ET")

    def test_games_table_sorted_by_kickoff(self):
        records = [{"homeTeam": "Late", "awayTeam": "B", "startDate": "2026-10-04T03:59:00Z", "startTimeTBD": False},
                   {"homeTeam": "Early", "awayTeam": "A", "startDate": "2026-10-02T00:00:00Z", "startTimeTBD": False},
                   {"homeTeam": "Tbd", "awayTeam": "C", "startDate": "2026-10-03T04:00:00Z", "startTimeTBD": True}]
        table = views.games_table(records)
        self.assertEqual(list(table.columns), ["Home", "Away", "Kickoff (ET)"])
        self.assertEqual(list(table["Home"]), ["Early", "Tbd", "Late"])
        self.assertEqual(table["Kickoff (ET)"][1], "Sat Oct 3, time TBD")

    def test_upload_tables_hide_bucket_and_shorten_dataset_id(self):
        raw = {"s3://secret-bucket-123/initial-demo/raw/cfbd/games/season=2026/abc.json": "uploaded",
               "s3://secret-bucket-123/initial-demo/raw/cfbd/games/season=2026/abc.manifest.json": "reused"}
        table = views.raw_upload_table(raw, {"abc.json": 20480, "abc.manifest.json": 900}, False)
        self.assertEqual(list(table["File"]), ["raw API response", "manifest (receipt)"])
        self.assertEqual(list(table["S3 folder"]), ["initial-demo/raw/cfbd/games/season=2026/"] * 2)
        self.assertEqual(list(table["Size"]), ["20.0 KB", "900 B"])
        self.assertEqual(list(table["Status"]), ["uploaded ✓", "already in S3, identical ✓"])
        self.assertNotIn("secret-bucket", table.to_string())
        shown = views.raw_upload_table(raw, {"abc.json": 1, "abc.manifest.json": 1}, True)
        self.assertTrue(shown["S3 folder"][0].startswith("secret-bucket-123/"))
        dataset = {f"s3://secret-bucket-123/initial-demo/datasets/{DATASET_ID}/train.csv": "uploaded"}
        table = views.dataset_upload_table(dataset, False)
        self.assertEqual(table["S3 folder"][0], "initial-demo/datasets/abababab…/")
        self.assertNotIn(DATASET_ID, table.to_string())
        self.assertEqual(views.bucket_label("secret-bucket-123", False), "<private project bucket>")
        self.assertEqual(views.fingerprint(DATASET_ID), "abababab")

    def test_cleaning_tables_use_team_names_and_plain_reasons(self):
        counts = views.cleaning_counts({"input": 59, "retained": 52, "excluded": 3, "quarantined": 4})
        self.assertEqual(list(counts.columns), ["Received", "Kept FBS vs FBS", "Excluded FBS vs FCS",
                                                "Set aside: kickoff time TBD"])
        self.assertEqual(counts.iloc[0].tolist(), [59, 52, 3, 4])
        records = [{"homeTeam": "UAB", "awayTeam": "Samford"}, {"homeTeam": "Clemson", "awayTeam": "Miami"}]
        exclusions = {"excluded": [{"source_row_index": 0, "reasons": ["classification: both opponents must be FBS"]}],
                      "quarantined": [{"source_row_index": 1, "reasons": ["startTimeTBD: unresolved kickoff time"]}]}
        table = views.set_aside_table(exclusions, records)
        self.assertEqual(table.values.tolist()[0][:3], ["UAB", "Samford", "Excluded"])
        self.assertIn("FCS", table["Reason"][0])
        self.assertIn("Kickoff time not announced", table["Reason"][1])
        self.assertTrue(views.set_aside_table({"excluded": [], "quarantined": []}, []).empty)

    def test_features_example_and_split_tables(self):
        self.assertEqual(list(views.feature_table()["Feature"]),
                         ["prior_win_pct_diff", "prior_avg_margin_diff", "home_field"])
        row = {"week": "5", "home_team": "New Mexico State", "away_team": "Western Kentucky",
               "cutoff": "2026-10-02T00:00:00Z", "feature_source_season": "2025",
               "prior_win_pct_diff": "-0.36363636363636365", "prior_avg_margin_diff": "-10.454545454545455",
               "home_field": "1"}
        heading, table = views.example_matchup(row)
        self.assertIn("**New Mexico State** (home) vs **Western Kentucky** — Thu Oct 1, 8:00 PM ET", heading)
        self.assertEqual(list(table["Value"]), ["−0.36", "−10.5", "1"])
        report = {"splits": {"train": {"output": 2194}, "holdout": {"output": 740}, "prediction": {"output": 51}}}
        split = views.split_table(report, 5)
        self.assertEqual(list(split["Seasons"]), ["2022–2024", "2025", "2026 Week 5"])
        self.assertEqual(list(split["Games"]), ["2,194", "740", "51"])

    def test_download_training_metrics_and_prediction_tables(self):
        table = views.download_table({"verified_files": 6})
        self.assertEqual(len(table), 6)
        self.assertEqual(set(table["Fingerprint"]), {"fingerprint verified ✓"})
        with self.assertRaises(ValueError):
            views.download_table({"verified_files": 5})
        metadata = {"counts": {"train": 2194, "holdout": 740}, "training_seasons": [2022, 2023, 2024],
                    "holdout_seasons": [2025]}
        self.assertEqual(views.training_counts(metadata),
                         "Trained on **2,194 games** from the 2022–2024 seasons.\n"
                         "Tested on **740 games** from the 2025 season (never used for training).")
        evaluation = {"model": {"brier_score": 0.21061287148858282, "log_loss": 0.6096025525960278,
                                "accuracy": 0.6648648648648648},
                      "constant_baseline": {"brier_score": 0.24163577488303326, "log_loss": 0.6763272181260667,
                                            "accuracy": 0.5918918918918918}}
        metrics = views.metrics_table(evaluation)
        self.assertEqual(metrics.values.tolist(), [
            ["Brier score (lower is better)", "0.2106", "0.2416", "Yes ✓"],
            ["Log loss (lower is better)", "0.6096", "0.6763", "Yes ✓"],
            ["Accuracy (higher is better)", "66.5%", "59.2%", "Yes ✓"]])
        rows = [{"game_id": "2", "cutoff": "2026-10-02T01:00:00Z", "home_team": "Tulsa", "away_team": "North Texas",
                 "home_win_probability": "0.2777652902323672"},
                {"game_id": "1", "cutoff": "2026-10-02T00:00:00Z", "home_team": "New Mexico State",
                 "away_team": "Western Kentucky", "home_win_probability": "0.5"}]
        predictions = views.predictions_table(rows)
        self.assertEqual(predictions.values.tolist(), [
            ["Thu Oct 1, 8:00 PM", "New Mexico State", "Western Kentucky", "50.0%", "50.0%", "New Mexico State"],
            ["Thu Oct 1, 9:00 PM", "Tulsa", "North Texas", "27.8%", "72.2%", "North Texas"]])

    def test_hypothetical_sentence(self):
        self.assertEqual(views.hypothetical_sentence((0.2, 7, 1), 0.662422294285731),
                         "Hypothetical: the home team's win rate last season was 20 points higher than its "
                         "opponent's (e.g., 70% vs. 50%), and it won by 7 more points per game on average. "
                         "Home win probability: **66.2%**.")
        self.assertEqual(views.hypothetical_sentence((-0.1, -3, 0), 0.4),
                         "Hypothetical (at a neutral site): the home team's win rate last season was 10 points "
                         "lower than its opponent's (e.g., 40% vs. 50%), and its average margin per game was 3 "
                         "points worse. Home win probability: **40.0%**.")
        self.assertIn("(e.g., 100% vs. 40%)", views.hypothetical_sentence((0.6, 0, 1), 0.9))   # Stays within 0–100%.
        self.assertIn("(e.g., 0% vs. 70%)", views.hypothetical_sentence((-0.7, 0, 1), 0.1))

    def shown(self, run):
        """Run ``run`` while capturing everything passed to IPython's display, and any stdout."""
        shown, out = [], io.StringIO()
        with patch("IPython.display.display", side_effect=lambda *args, **kwargs: shown.append(args[0])), \
                redirect_stdout(out):
            run()
        self.assertEqual(out.getvalue(), "")        # Nothing is ever plain stdout text.
        return shown

    def test_say_renders_fixed_size_html_not_stdout(self):
        shown = self.shown(lambda: views.say("**59 games** received at " + views.esc("<private project bucket>")
                                             + "\nfolder `initial-demo/` " + views.esc("A*B `x`")))
        self.assertEqual(len(shown), 1)
        self.assertEqual(set(shown[0]), {"text/html", "text/plain"})
        html = shown[0]["text/html"]
        self.assertTrue(html.startswith('<div style="font-size: 13px; line-height: 1.45; font-family: system-ui'))
        self.assertIn("<strong>59 games</strong> received at &lt;private project bucket&gt;<br>", html)
        self.assertIn("font-size: 12px", html)               # `code` renders as small monospace.
        self.assertIn(">initial-demo/</code> A*B `x`</div>", html)  # Escaped markup stays literal.
        self.assertNotIn('"Segoe UI"', html)                # Quotes never break the style attribute.
        self.assertEqual(shown[0]["text/plain"], "59 games received at <private project bucket>\n"
                                                 "folder initial-demo/ A*B `x`")
        self.assertEqual(views.text_html("<script>"), f'<div style="{views.WRAPPER_STYLE}">&lt;script&gt;</div>')

    def test_show_renders_compact_theme_neutral_html(self):
        frame = pd.DataFrame({"Home": ["Tulsa <b>"], "Games": ["2,194"], "Home win %": ["45.8%"]})
        shown = self.shown(lambda: views.show(frame))
        self.assertEqual(set(shown[0]), {"text/html", "text/plain"})
        html = shown[0]["text/html"]
        self.assertTrue(html.startswith(f'<div style="{views.WRAPPER_STYLE}'))
        self.assertIn("font-size: 13px", html)
        self.assertIn("white-space: normal", html)
        self.assertIn("max-width: 100%", html)
        self.assertIn("border-bottom: 1px solid currentColor", html)
        headers = re.findall(r'<th style="([^"]*)"', html)
        self.assertEqual(len(headers), 3)                   # No index column.
        for style in headers:
            self.assertEqual(re.findall(r"background:\s*([^;]+);", style), ["transparent"])
            self.assertIn("color: inherit", style)
            self.assertIn("font-weight: 600", style)
        self.assertEqual(set(re.findall(r"background:\s*([^;]+);", html)), {"transparent"})
        for banned in ("#fff", "white;", "white ", "var(--", "sticky", "black"):
            self.assertNotIn(banned, html.lower())
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", html))
        self.assertIn("Tulsa &lt;b&gt;", html)             # Cell text is escaped, never raw HTML.
        self.assertIn('text-align: right;">2,194</td>', html)
        self.assertIn('text-align: left;">Tulsa', html)
        self.assertNotIn("max-height", html)
        long = pd.DataFrame({"Home": [f"Team {n}" for n in range(51)]})
        long_html = views.table_html(long)
        self.assertIn("max-height: 420px; overflow-y: auto", long_html)
        self.assertNotIn("sticky", long_html)
        self.assertEqual(long_html.count("<tr"), 52)       # All rows kept, header included.
        self.assertEqual(long_html.count(f"background: {views.ZEBRA};"), 25)  # Subtle zebra on every other row.
        self.assertEqual(set(re.findall(r"background:\s*([^;]+);", long_html)), {"transparent", views.ZEBRA})

    def test_feature_names_are_monospace_and_never_split(self):
        for table in (views.feature_table(), views.example_matchup({
                "week": "5", "home_team": "A", "away_team": "B", "cutoff": "2026-10-02T00:00:00Z",
                "feature_source_season": "2025", "prior_win_pct_diff": "0.1", "prior_avg_margin_diff": "1",
                "home_field": "1"})[1]):
            html = views.table_html(table)
            cells = re.findall(r'<tr style="[^"]*"><td style="([^"]*)">(.*?)</td>', html)
            self.assertEqual(len(cells), 3)
            for style, content in cells:
                self.assertIn("white-space: nowrap", style)
                self.assertRegex(content, r'^<code style="[^"]*font-size: 12px[^"]*">'
                                          r"(prior_win_pct_diff|prior_avg_margin_diff|home_field)</code>")
            self.assertIn("white-space: normal", html)      # Other columns still wrap.

    def test_step_failures_are_short_sanitized_and_stop_later_steps(self):
        shown = []
        with patch("IPython.display.display", side_effect=lambda *args, **kwargs: shown.append(args[0])):
            with self.assertRaises(views.StepFailed) as caught:
                with views.step(1, "cfbd_fetch"):
                    raise RuntimeError("SECRET token value")
        message = str(caught.exception)
        self.assertTrue(message.startswith("**Step 1 failed at cfbd_fetch:** unexpected RuntimeError; "
                                           "details suppressed."))
        self.assertNotIn("SECRET", message)
        self.assertIn(views.REHEARSAL_DATASET_ID, message)
        self.assertIn("USE_EXISTING_DATASET_ID", message)
        self.assertIn("<strong>Step 1 failed at cfbd_fetch:</strong>", shown[0]["text/html"])
        self.assertIn("font-size: 13px", shown[0]["text/html"])
        self.assertEqual(caught.exception._render_traceback_(), ["Stopped: see the message above."])
        ran = []
        with self.assertRaisesRegex(views.StepFailed, r"Step 2 skipped:\*\* Step 1 failed earlier"):
            with views.step(2, "s3_upload_raw"):
                ran.append(2)
        self.assertEqual(ran, [])
        with views.step(1, "cfbd_fetch"):          # Re-running the failed step is allowed and clears it.
            ran.append(1)
        with views.step(2, "s3_upload_raw"):
            ran.append(2)
        self.assertEqual(ran, [1, 2])
        with self.assertRaisesRegex(views.StepFailed, r"Step 6 failed at s3_download:\*\* AWS access denied"):
            with views.step(6, "s3_download"):
                raise s3.S3StorageError("AWS access denied; check permissions for the selected bucket/prefix.")
        views.reset()
        with self.assertRaisesRegex(views.StepFailed, r"Step 7 failed at local_training:\*\* Model artifact"):
            with views.step(7, "local_training"):
                raise BaselineError("Model artifact hash mismatch; nothing deserialized.")

    def test_step_labels_and_history_table(self):
        shown = []
        with patch("IPython.display.display", side_effect=lambda *args, **kwargs: shown.append(args[0])):
            with self.assertRaisesRegex(views.StepFailed, r"Step 2b failed at s3_download_history:"):
                with views.step(2, "s3_download_history", label="2b"):
                    raise s3.S3StorageError("Season 2023 raw snapshot is not in S3; upload it with upload-raw first.")
            with self.assertRaisesRegex(views.StepFailed, r"Step 3 skipped:\*\* Step 2b failed earlier"):
                with views.step(3, "normalize"):
                    pass
            self.assertFalse(views.live_step(2, DATASET_ID, label="2b"))
        self.assertIn("<strong>Step 2b: skipped this step</strong>", shown[-1]["text/html"])
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for year, count in ((2021, 849), (2025, 888)):
                path = Path(folder) / f"{year}.manifest.json"
                path.write_text(json.dumps({"request_parameters": {"year": year}, "record_count": count}))
                paths.append(path)
            table = views.history_table(paths)
        self.assertEqual(table.values.tolist(), [["2021", "849", "downloaded ✓", "✓"],
                                                 ["2025", "888", "downloaded ✓", "✓"]])
        self.assertEqual(list(table.columns), ["Season", "Games", "Downloaded", "Fingerprint verified"])

    def test_live_step_skips_with_existing_dataset(self):
        results = []
        shown = self.shown(lambda: results.extend([views.live_step(1, None), views.live_step(1, DATASET_ID)]))
        self.assertEqual(results, [True, False])
        self.assertEqual(len(shown), 1)
        self.assertIn("Step 1: skipped this step — using existing dataset abababab already in S3",
                      shown[0]["text/plain"])
        self.assertIn("<strong>Step 1: skipped this step</strong>", shown[0]["text/html"])


class InitialDemoNotebookTests(unittest.TestCase):
    def setUp(self):
        self.notebook = nbformat.read(NOTEBOOK, as_version=4)

    def test_valid_nbformat_with_outputs_cleared_and_clean_metadata(self):
        nbformat.validate(self.notebook)
        self.assertEqual(set(self.notebook.metadata), {"kernelspec", "language_info"})
        self.assertEqual(self.notebook.metadata.kernelspec.name, "python3")
        for cell in self.notebook.cells:
            self.assertEqual(cell.metadata, {})
            if cell.cell_type == "code":
                self.assertEqual(cell.outputs, [])
                self.assertIsNone(cell.execution_count)
                ast.parse(cell.source)
        self.assertIsNone(re.search(r"\b\d{12}\b", NOTEBOOK.read_text(encoding="utf-8")))  # No AWS account ID.

    def test_every_code_cell_follows_a_step_explanation(self):
        cells = self.notebook.cells
        for index, cell in enumerate(cells):
            if cell.cell_type != "code":
                continue
            previous = cells[index - 1]
            self.assertEqual(previous.cell_type, "markdown")
            self.assertRegex(previous.source, r"^## Step \d+b? — ")
            self.assertIn("**What this does:**", previous.source)
            self.assertIn("**Why it matters:**", previous.source)
        first_code = next(cell for cell in cells if cell.cell_type == "code")
        self.assertIn("os.chdir(_root)", first_code.source)
        for setting in ("SEASON = 2026", "WEEK = 5", "HYPOTHETICAL = (0.2, 7, 1)", "USE_EXISTING_DATASET_ID = None",
                        "SHOW_BUCKET_NAME = False", 'RUN_TAG = f"nb-week{WEEK}-'):
            self.assertIn(setting, first_code.source)

    def test_notebook_reuses_pipeline_functions_with_retrospective_flag(self):
        source = "\n".join(cell.source for cell in self.notebook.cells if cell.cell_type == "code")
        for call in ("cfbd.fetch_games(", "save_snapshot(", "store.upload_raw(", "games.normalize_snapshot(",
                     "dataset.build_dataset(", "store.upload_dataset(", "store.download_dataset(", "train_baseline(",
                     "predict_saved_sample(", "predict_vector(", "store._private_bucket()"):
            self.assertIn(call, source)
        for call in ("dataset.build_dataset(", "store.upload_dataset(", "store.download_dataset(", "train_baseline(",
                     "predict_saved_sample(", "load_trusted_model("):
            segment = source[source.index(call):source.index(")", source.index(call) + len(call) + 60) + 1]
            self.assertIn("allow_retrospective_demo=True", segment, call)
        self.assertNotIn("put_object", source)
        self.assertNotIn("get_object", source)

    def test_history_comes_from_s3_not_local_files(self):
        source = "\n".join(cell.source for cell in self.notebook.cells if cell.cell_type == "code")
        self.assertIn('HISTORY = week_refresh.download_history(store, RUN_DIRS["raw"] / "history")', source)
        for local in ("discover_history", "verify_history", "data/raw/cfbd/games", "HISTORY_RAW_ROOT"):
            self.assertNotIn(local, source)
        ids = [cell.id for cell in self.notebook.cells]
        self.assertEqual(ids[ids.index("step-2-code") + 1:ids.index("step-2-code") + 3], ["step-2b-md", "step-2b-code"])
        self.assertTrue(self.notebook.cells[ids.index("step-2b-md")].source.startswith(
            "## Step 2b — Load past seasons from S3"))
        # History is loaded before Step 3 uses it.
        self.assertLess(source.index("download_history("), source.index("for _path in HISTORY"))

    def test_no_plain_stdout_calls_in_code_cells(self):
        for cell in self.notebook.cells:
            if cell.cell_type == "code":
                self.assertIsNone(re.search(r"(?<![\w.])print\(", cell.source), cell.id)
                self.assertNotIn("sys.stdout", cell.source)


if __name__ == "__main__":
    unittest.main()
