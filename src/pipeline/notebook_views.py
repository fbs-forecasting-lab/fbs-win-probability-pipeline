"""Display helpers for the Initial Demo notebook.

These functions only format values returned by the existing, tested pipeline
functions into short tables and sentences. They never fetch, store, train, or
predict. ``say`` and ``show`` render as Markdown and inline-styled HTML so the
outputs use the notebook's own font, size, wrapping, and light/dark colors.
``step`` turns a failure into one short, sanitized message that names the
stage, the same way ``week_refresh`` and ``s3_demo`` report errors.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import html
import re
from zoneinfo import ZoneInfo

import pandas as pd

from src.models.baseline import DATA_FILES
from src.pipeline import s3_demo, week_refresh

EASTERN = ZoneInfo("America/New_York")
REHEARSAL_DATASET_ID = "b6b7c54503439ecc0ecad5b9d255281d6d6943c9da4013db2dff9eb8ab305e65"
HIDDEN_BUCKET = "<private project bucket>"
SANITIZED_ERRORS = (*week_refresh.PROJECT_ERRORS, week_refresh.RefreshError, s3_demo.DemoError)
MINUS = "\u2212"
LONG_TABLE_ROWS = 12
LONG_TABLE_MAX_HEIGHT = "420px"
NUMBER = re.compile(r"^[\u2212-]?[\d,]+(\.\d+)?%?$")
_failed_step = None


class StepFailed(Exception):
    """A notebook step failed. The message is shown with ``say``; the error box shows one short line."""

    def _render_traceback_(self):
        return ["Stopped: see the message above."]


def esc(value):
    """Escape text so Markdown shows it literally (team names, error details, placeholders)."""
    return re.sub(r"([\\`*_\[\]#|])", r"\\\1", html.escape(str(value), quote=False))


def say(text):
    """Show a line of Markdown in the notebook's body font; newlines become line breaks."""
    from IPython.display import Markdown, display
    output = Markdown(text.replace("\n", "  \n"))
    display(output)
    return output


def fallback_hint():
    return ("To keep recording, set `USE_EXISTING_DATASET_ID` in Step 0 to a dataset already in S3, for example the "
            f"September 24 rehearsal dataset `{REHEARSAL_DATASET_ID}`, then choose **Kernel → Restart Kernel and "
            "Clear All Outputs** and run the cells again. Steps 1–5 are then skipped.")


def reset():
    """Clear any earlier failure; Step 0 calls this at the start of every take."""
    global _failed_step
    _failed_step = None


@contextmanager
def step(number, stage):
    """Run one stage; on failure show a short stage-named message and stop later steps."""
    global _failed_step
    if _failed_step is not None and _failed_step < number:
        message = f"**Step {number} skipped:** Step {_failed_step} failed earlier.\n{fallback_hint()}"
        say(message)
        raise StepFailed(message)
    try:
        yield
    except StepFailed:
        raise
    except Exception as exc:
        _failed_step = number
        detail = str(exc) if isinstance(exc, SANITIZED_ERRORS) else f"unexpected {type(exc).__name__}; details suppressed."
        message = f"**Step {number} failed at {stage}:** {esc(detail)}\n{fallback_hint()}"
        say(message)
        raise StepFailed(message) from None
    if _failed_step == number:
        _failed_step = None


def live_step(number, existing_dataset_id, what="this step"):
    """Return True when the live API/S3 path runs; otherwise say why the step is skipped."""
    if existing_dataset_id:
        say(f"**Step {number}: skipped {what}** — using existing dataset `{fingerprint(existing_dataset_id)}` already "
            "in S3 (`USE_EXISTING_DATASET_ID`).")
        return False
    return True


def table_html(frame):
    """Compact HTML table: no index, inherited font and colors, wrapping cells, numbers right-aligned."""
    columns = list(frame.columns)
    numeric = {column: len(frame) > 0 and all(NUMBER.match(str(value)) for value in frame[column])
               for column in columns}
    cell = "padding: 4px 10px; white-space: normal; overflow-wrap: anywhere; vertical-align: top;"
    header = ("position: sticky; top: 0; background: var(--jp-layout-color0, var(--vscode-editor-background, "
              "transparent)); border-bottom: 1px solid currentColor; font-weight: 600;")

    def align(column):
        return "right" if numeric[column] else "left"
    head = "".join(f'<th style="{cell} {header} text-align: {align(column)};">{html.escape(str(column))}</th>'
                   for column in columns)
    body = "".join("<tr>" + "".join(f'<td style="{cell} text-align: {align(column)};">{html.escape(str(value))}</td>'
                                    for column, value in zip(columns, row)) + "</tr>"
                   for row in frame.itertuples(index=False, name=None))
    table = ('<table style="font-family: inherit; font-size: inherit; color: inherit; background: transparent; '
             'border-collapse: collapse; width: auto; max-width: 100%; margin: 0.25em 0;">'
             f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
    scroll = f" max-height: {LONG_TABLE_MAX_HEIGHT}; overflow-y: auto;" if len(frame) > LONG_TABLE_ROWS else ""
    return f'<div style="max-width: 100%; overflow-x: auto;{scroll}">{table}</div>'


def show(frame):
    """Display a table as compact HTML, with a plain-text copy for exported notebooks."""
    from IPython.display import display
    display({"text/html": table_html(frame), "text/plain": frame.to_string(index=False)}, raw=True)


def fingerprint(value):
    return str(value)[:8]


def bucket_label(bucket, show_bucket_name):
    return bucket if show_bucket_name else HIDDEN_BUCKET


def _parse(timestamp):
    return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).astimezone(EASTERN)


def et_time(timestamp, *, tbd=False):
    """Format a UTC timestamp as Eastern time, e.g. 'Thu Oct 1, 8:00 PM'."""
    moment = _parse(timestamp)
    day = f"{moment:%a %b} {moment.day}"
    if tbd:
        return f"{day}, time TBD"
    hour = moment.hour % 12 or 12
    return f"{day}, {hour}:{moment:%M} {'AM' if moment.hour < 12 else 'PM'}"


def _signed(value, digits):
    return f"{value:.{digits}f}".replace("-", MINUS)


def _size(count):
    return f"{count} B" if count < 1024 else f"{count / 1024:.1f} KB"


def _s3_folder(uri, show_bucket_name):
    bucket, _, key = uri.removeprefix("s3://").partition("/")
    folder = key.rsplit("/", 1)[0] + "/"
    folder = re.sub(r"[0-9a-f]{64}", lambda match: fingerprint(match.group()) + "…", folder)
    return f"{bucket}/{folder}" if show_bucket_name else folder


def _status(value):
    return {"uploaded": "uploaded ✓", "reused": "already in S3, identical ✓"}.get(value, value)


def fetch_line(http_status, count, retrieved_at):
    return f"HTTP {http_status} — **{count} games** received at {et_time(retrieved_at)} ET"


def games_table(records):
    rows = sorted(records, key=lambda row: (_parse(row["startDate"]), row["homeTeam"]))
    return pd.DataFrame({"Home": [row["homeTeam"] for row in rows], "Away": [row["awayTeam"] for row in rows],
                         "Kickoff (ET)": [et_time(row["startDate"], tbd=row.get("startTimeTBD") is True)
                                          for row in rows]})


def raw_upload_table(objects, sizes, show_bucket_name):
    """objects: {s3 uri: status} from upload_raw; sizes: {file name: bytes}."""
    rows = []
    for uri, status in objects.items():
        name = uri.rsplit("/", 1)[1]
        rows.append({"File": "manifest (receipt)" if name.endswith(".manifest.json") else "raw API response",
                     "S3 folder": _s3_folder(uri, show_bucket_name), "Size": _size(sizes[name]),
                     "Status": _status(status)})
    return pd.DataFrame(rows)


def cleaning_counts(counts):
    return pd.DataFrame([{"Received": counts["input"], "Kept FBS vs FBS": counts["retained"],
                          "Excluded FBS vs FCS": counts["excluded"],
                          "Set aside: kickoff time TBD": counts["quarantined"]}])


def _plain_reason(reason):
    if reason.startswith("classification:"):
        return "Opponent is an FCS school, so the game is outside our FBS vs FBS scope"
    if reason.startswith("startTimeTBD:"):
        return "Kickoff time not announced yet (TBD), so there is no reliable cutoff time"
    return reason


def set_aside_table(exclusions, records):
    rows = []
    for status, items in (("Excluded", exclusions["excluded"]), ("Set aside", exclusions["quarantined"])):
        for item in items:
            record = records[item["source_row_index"]]
            rows.append({"Home": record.get("homeTeam"), "Away": record.get("awayTeam"), "Status": status,
                         "Reason": "; ".join(_plain_reason(reason) for reason in item["reasons"])})
    return pd.DataFrame(rows, columns=["Home", "Away", "Status", "Reason"])


def feature_table():
    return pd.DataFrame([
        {"Feature": "prior_win_pct_diff",
         "Plain-English meaning": "Home team's win % last season minus the away team's win % last season",
         "Why we use it": "A simple measure of which team was stronger last season"},
        {"Feature": "prior_avg_margin_diff",
         "Plain-English meaning": "Home team's average points margin per game last season minus the away team's",
         "Why we use it": "Shows how decisively teams won or lost, not just whether they won"},
        {"Feature": "home_field",
         "Plain-English meaning": "1 if the home team plays at home, 0 if the game is at a neutral site",
         "Why we use it": "Teams tend to win more often at home"},
    ])


def example_matchup(row):
    """row: one prediction.csv row. Returns (heading, table) with rounded feature values."""
    heading = (f"Example Week {row['week']} matchup: **{esc(row['home_team'])}** (home) vs "
               f"**{esc(row['away_team'])}** — {et_time(row['cutoff'])} ET; features from the "
               f"{row['feature_source_season']} season")
    table = pd.DataFrame([
        {"Feature": "prior_win_pct_diff (win % diff)", "Value": _signed(float(row["prior_win_pct_diff"]), 2)},
        {"Feature": "prior_avg_margin_diff (margin diff)", "Value": _signed(float(row["prior_avg_margin_diff"]), 1)},
        {"Feature": "home_field", "Value": str(int(float(row["home_field"])))},
    ])
    return heading, table


def split_table(report, week):
    splits = report["splits"]
    seasons = {"train": "2022–2024", "holdout": "2025", "prediction": f"2026 Week {week}"}
    labels = {"train": "Train (the model learns from these)", "holdout": "Test (checks the model on unseen games)",
              "prediction": "Predict (upcoming games, no result yet)"}
    return pd.DataFrame([{"Split": labels[name], "Seasons": seasons[name], "Games": f"{splits[name]['output']:,}"}
                         for name in ("train", "holdout", "prediction")])


def dataset_upload_table(objects, show_bucket_name):
    return pd.DataFrame([{"File": uri.rsplit("/", 1)[1], "S3 folder": _s3_folder(uri, show_bucket_name),
                          "Status": _status(status)} for uri, status in objects.items()])


def download_table(download):
    names = [*sorted(DATA_FILES), "dataset_report.json"]
    if download["verified_files"] != len(names):
        raise s3_demo.DemoError("Downloaded file count does not match the six dataset files.")
    return pd.DataFrame([{"File": name, "Downloaded": "downloaded ✓", "Fingerprint": "fingerprint verified ✓"}
                         for name in names])


def training_counts(metadata):
    counts, train, holdout = metadata["counts"], metadata["training_seasons"], metadata["holdout_seasons"]
    return (f"Trained on **{counts['train']:,} games** from the {train[0]}–{train[-1]} seasons.\n"
            f"Tested on **{counts['holdout']:,} games** from the {holdout[0]} season (never used for training).")


def metrics_table(evaluation):
    model, baseline = evaluation["model"], evaluation["constant_baseline"]
    rows = []
    for key, label, lower_better in (("brier_score", "Brier score (lower is better)", True),
                                     ("log_loss", "Log loss (lower is better)", True),
                                     ("accuracy", "Accuracy (higher is better)", False)):
        ours, simple = model[key], baseline[key]
        better = ours < simple if lower_better else ours > simple
        fmt = (lambda value: f"{value * 100:.1f}%") if key == "accuracy" else (lambda value: f"{value:.4f}")
        rows.append({"Metric": label, "Our model": fmt(ours),
                     "Simple baseline (always predicts the historical home-win rate)": fmt(simple),
                     "Better?": "Yes ✓" if better else "No"})
    return pd.DataFrame(rows)


def predictions_table(rows):
    rows = sorted(rows, key=lambda row: (_parse(row["cutoff"]), row["game_id"]))
    output = []
    for row in rows:
        home = float(row["home_win_probability"])
        output.append({"Kickoff (ET)": et_time(row["cutoff"]), "Home": row["home_team"], "Away": row["away_team"],
                       "Home win %": f"{home * 100:.1f}%", "Away win %": f"{(1 - home) * 100:.1f}%",
                       "Model favors": row["home_team"] if home >= 0.5 else row["away_team"]})
    return pd.DataFrame(output)


def hypothetical_sentence(vector, home_probability):
    win_diff, margin_diff, home_field = vector
    points = abs(win_diff) * 100
    site = "" if int(home_field) == 1 else " at a neutral site"
    return (f"A home team{site} that won {points:g} percentage points {'more' if win_diff >= 0 else 'fewer'} games "
            f"last season and outscored opponents by {abs(margin_diff):g} "
            f"{'more' if margin_diff >= 0 else 'fewer'} points per game: "
            f"home win probability **{home_probability * 100:.1f}%**.")
