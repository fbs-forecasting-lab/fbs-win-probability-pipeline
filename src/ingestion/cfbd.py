"""Authenticated CFBD games ingestion. Run with python -m src.ingestion.cfbd."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
import requests

from .storage import PROJECT_ROOT, SnapshotError, coverage_report, parse_games, save_snapshot

ENDPOINT = "https://api.collegefootballdata.com/games"
TIMEOUT = (5, 30)  # Connection timeout, read inactivity timeout (seconds).
MAX_ATTEMPTS = 3
MAX_RETRY_DELAY = 30


class CFBDError(RuntimeError):
    """An actionable error that contains no request, response body, or credentials."""


@dataclass(frozen=True)
class GamesResponse:
    raw_response: bytes = field(repr=False)
    parameters: dict
    retrieved_at: str
    http_status: int
    endpoint: str = ENDPOINT


def _api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    key = os.environ.get("CFBD_API_KEY", "").strip()
    if not key:
        raise CFBDError("Set CFBD_API_KEY in the environment or the project .env file.")
    if not key.isascii() or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in key):
        raise CFBDError("CFBD_API_KEY has an invalid format; check its configuration.")
    return key


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    delay = float(2 ** attempt)
    if retry_after:
        try:
            delay = float(int(retry_after))
        except (ValueError, OverflowError):
            try:
                until = parsedate_to_datetime(retry_after)
                delay = (until - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                pass
    if delay > MAX_RETRY_DELAY:
        raise CFBDError("CFBD requested a longer retry wait; stop and try again later.")
    return max(0.0, delay)


def fetch_games(season: int, week: int | None = None) -> GamesResponse:
    """Fetch an unfiltered raw games snapshot; storage is a separate operation."""
    if type(season) is not int or not 1869 <= season <= 9999:
        raise CFBDError("Season must be an integer year between 1869 and 9999.")
    if week is not None and (type(week) is not int or week < 0):
        raise CFBDError("Week must be a nonnegative integer when supplied.")
    key = _api_key()
    parameters = {"year": season, "seasonType": "regular", "classification": "fbs"}
    if week is not None:
        parameters["week"] = week

    for attempt in range(MAX_ATTEMPTS):
        retry_after = None
        try:
            response = requests.get(
                ENDPOINT, params=parameters,
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                timeout=TIMEOUT, allow_redirects=False,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            message = ("CFBD request timed out" if isinstance(exc, requests.Timeout)
                       else "CFBD connection failed")
            # Never interpolate exceptions: they can contain headers or credentials.
        except requests.RequestException:
            raise CFBDError("CFBD request failed; check network and request configuration.") from None
        else:
            try:
                status = response.status_code
                if status in (401, 403):
                    raise CFBDError(f"CFBD HTTP {status}: authentication or access denied; check key/access.")
                if status == 429:
                    message = "CFBD HTTP 429: rate limit or quota reached"
                    retry_after = response.headers.get("Retry-After")
                elif 500 <= status <= 599:
                    message = f"CFBD HTTP {status}: server error"
                    retry_after = response.headers.get("Retry-After")
                elif status != 200:
                    raise CFBDError(f"CFBD HTTP {status}: unexpected response; check request/access.")
                else:
                    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    raw = response.content
                    # Reject credential echoes rather than altering the raw response.
                    if key.encode() in raw:
                        raise CFBDError("CFBD response contained sensitive authentication data; not saved.")
                    try:
                        records = parse_games(raw)
                    except SnapshotError as exc:
                        raise CFBDError(str(exc)) from None
                    if key in json.dumps(records, ensure_ascii=False):
                        raise CFBDError("CFBD response contained sensitive authentication data; not saved.")
                    return GamesResponse(raw, parameters, retrieved_at, status)
            finally:
                response.close()
        if attempt == MAX_ATTEMPTS - 1:
            raise CFBDError(f"{message}; stopped after {MAX_ATTEMPTS} attempts.") from None
        time.sleep(_retry_delay(retry_after, attempt))
    raise AssertionError("Unreachable retry state")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save a raw CFBD games snapshot and provenance manifest.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int)
    parser.add_argument("--output-dir", type=Path, help="Games root; season=YYYY is appended.")
    args = parser.parse_args(argv)
    try:
        result = fetch_games(args.season, args.week)
        raw_path, manifest_path = save_snapshot(result, args.output_dir)
        report = coverage_report(parse_games(result.raw_response))
    except (CFBDError, SnapshotError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Raw snapshot: {raw_path}")
    print(f"Manifest: {manifest_path}")
    print("EMPTY response: no games; coverage could not be established." if report["status"] == "empty"
          else f"Stored {report['record_count']} records; coverage is descriptive, not predictor approval.")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
