"""Normalize explicit, verified CFBD snapshots without establishing availability."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys

from src.ingestion.storage import (
    PROJECT_ROOT, REQUIRED_FIELDS, SnapshotError, _atomic_create, coverage_report, parse_games,
)

NORMALIZATION_SCHEMA_VERSION = 1
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data/interim/cfbd/games"
FIELD_NAMES = dict(zip(REQUIRED_FIELDS, (
    "id", "season", "week", "season_type", "start_date", "start_time_tbd",
    "completed", "neutral_site", "home_id", "home_team", "home_classification",
    "home_points", "away_id", "away_team", "away_classification", "away_points",
), strict=True))
PROVENANCE_COLUMNS = (
    "source_snapshot_id", "source_raw_sha256", "source_row_index", "retrieved_at",
    "historical_availability_status", "historical_available_at", "approved_for_predictor_use",
)
COLUMNS = (*FIELD_NAMES.values(), *PROVENANCE_COLUMNS)
CLASSIFICATIONS = {"fbs", "fcs", "ii", "ii/iii", "iii"}


class NormalizationError(ValueError):
    """A snapshot-integrity, metadata, or output-conflict error."""


@dataclass(frozen=True)
class Snapshot:
    """A verified raw snapshot: the parsed game records and their source metadata."""
    records: list[dict]
    source: dict


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _utc_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise NormalizationError("must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise NormalizationError("must include an explicit timezone; naive timestamps are not accepted")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError) as exc:
        if isinstance(exc, NormalizationError):
            raise
        raise NormalizationError("must be a valid timezone-aware ISO timestamp") from None


def _integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _unique_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise NormalizationError("Manifest contains duplicate keys.")
        result[key] = value
    return result


def load_snapshot(manifest_path: Path | str) -> Snapshot:
    """Validate version-1 ingestion metadata and bytes before any row processing."""
    path = Path(manifest_path)
    try:
        manifest_bytes = path.read_bytes()
        manifest = json.loads(manifest_bytes, object_pairs_hook=_unique_keys)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise NormalizationError("Manifest is unreadable or malformed JSON.") from None
    if not isinstance(manifest, dict):
        raise NormalizationError("Manifest must be a JSON object.")
    for version in ("schema_version", "snapshot_version"):
        if type(manifest.get(version)) is not int or manifest[version] != 1:
            raise NormalizationError(f"Unsupported or missing manifest {version}; expected integer 1.")
    snapshot_id = manifest.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not re.fullmatch(r"[0-9a-f]{32}", snapshot_id):
        raise NormalizationError("Manifest snapshot_id must be the version-1 UUID hex identifier.")
    filename = manifest.get("response_file")
    if filename != f"{snapshot_id}.json":
        raise NormalizationError("Manifest response_file must name its sibling snapshot JSON file.")
    raw_path = path.parent / filename
    if raw_path.is_symlink():
        raise NormalizationError("Referenced raw file must not be a symbolic link.")
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise NormalizationError("Manifest sha256 must be a lowercase SHA-256 hex digest.")
    if not _integer(manifest.get("record_count")):
        raise NormalizationError("Manifest record_count must be a nonnegative integer.")
    if (manifest.get("source") != "College Football Data"
            or manifest.get("endpoint") != "https://api.collegefootballdata.com/games"
            or type(manifest.get("http_status")) is not int or manifest["http_status"] != 200):
        raise NormalizationError("Manifest must describe a successful CFBD games response.")
    params = manifest.get("request_parameters")
    if (not isinstance(params, dict)
            or set(params) not in ({"year", "seasonType", "classification"},
                                   {"year", "seasonType", "classification", "week"})
            or not _integer(params.get("year"), 1869) or params["year"] > 9999
            or params.get("seasonType") != "regular" or params.get("classification") != "fbs"
            or ("week" in params and not _integer(params["week"]))):
        raise NormalizationError("Manifest request_parameters must match the regular-season FBS ingestion contract.")
    try:
        retrieved_at = _utc_timestamp(manifest.get("retrieved_at"))
    except NormalizationError as exc:
        raise NormalizationError(f"Manifest retrieved_at: {exc}") from None
    availability = manifest.get("source_availability")
    if (not isinstance(availability, dict)
            or not isinstance(availability.get("status"), str) or not availability["status"].strip()
            or "available_at" not in availability):
        raise NormalizationError("Manifest historical availability metadata is missing or invalid.")
    if availability["status"] == "unknown" and availability["available_at"] is not None:
        raise NormalizationError("Unknown historical availability must have available_at=null.")
    if availability["available_at"] is not None:
        try:
            _utc_timestamp(availability["available_at"])
        except NormalizationError as exc:
            raise NormalizationError(f"Manifest available_at: {exc}") from None
    if manifest.get("approved_for_predictor_use") is not False:
        raise NormalizationError("Manifest must explicitly mark predictor use unapproved.")
    try:
        raw = raw_path.read_bytes()
    except OSError:
        raise NormalizationError("Referenced raw snapshot is missing or unreadable.") from None
    if hashlib.sha256(raw).hexdigest() != digest:
        raise NormalizationError("Raw snapshot SHA-256 does not match manifest.")
    try:
        records = parse_games(raw)
    except SnapshotError as exc:
        raise NormalizationError(str(exc)) from None
    if len(records) != manifest["record_count"]:
        raise NormalizationError("Raw snapshot record count does not match manifest.")
    try:
        matches = _json_bytes(coverage_report(records)) == _json_bytes(manifest.get("coverage"))
        _json_bytes(availability)
    except (ValueError, RecursionError):
        raise NormalizationError("Manifest coverage or availability metadata is invalid.") from None
    if not matches:
        raise NormalizationError("Recomputed raw coverage does not match manifest.")
    return Snapshot(records, {
        "snapshot_id": snapshot_id, "source": manifest["source"], "endpoint": manifest["endpoint"],
        "request_parameters": params, "http_status": manifest["http_status"],
        "raw_file": filename, "raw_sha256": digest, "manifest_file": path.name,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "retrieved_at": retrieved_at, "source_availability": availability,
        "approved_for_predictor_use": False,
    })


def _validate_row(row: dict, params: dict) -> tuple[dict, list[str]]:
    reasons = [f"{name}: required field missing" for name in REQUIRED_FIELDS
               if name not in row and name not in ("homePoints", "awayPoints")]
    normalized = {target: row.get(source) for source, target in FIELD_NAMES.items()}
    for name in ("id", "homeId", "awayId"):
        if not _integer(row.get(name), 1):
            reasons.append(f"{name}: must be a positive integer (not a boolean)")
    if _integer(row.get("homeId"), 1) and row.get("homeId") == row.get("awayId"):
        reasons.append("homeId/awayId: opponents must have distinct team IDs")
    for name in ("homeTeam", "awayTeam"):
        if not isinstance(row.get(name), str) or not row[name].strip():
            reasons.append(f"{name}: must be a nonempty team name")
    for name in ("startTimeTBD", "completed", "neutralSite"):
        if type(row.get(name)) is not bool:
            reasons.append(f"{name}: must be an actual boolean")
    for name in ("homeClassification", "awayClassification"):
        if not isinstance(row.get(name), str) or row[name] not in CLASSIFICATIONS:
            reasons.append(f"{name}: must be a recognized division classification")
    if not _integer(row.get("season"), 1869) or row["season"] != params["year"]:
        reasons.append("season: must be an integer matching the manifest year")
    if not _integer(row.get("week")) or ("week" in params and row["week"] != params["week"]):
        reasons.append("week: must be a nonnegative integer matching any manifest week")
    if row.get("seasonType") != params["seasonType"]:
        reasons.append("seasonType: must match the manifest regular season")
    try:
        normalized["start_date"] = _utc_timestamp(row.get("startDate"))
    except NormalizationError as exc:
        reasons.append(f"startDate: {exc}")
    if row.get("startTimeTBD") is True:
        reasons.append("startTimeTBD: unresolved kickoff time")
    for name in ("homePoints", "awayPoints"):
        score = row.get(name)
        if score is not None and not _integer(score):
            reasons.append(f"{name}: score must be a nonnegative integer or null")
    if row.get("completed") is True:
        if not all(_integer(row.get(name)) for name in ("homePoints", "awayPoints")):
            reasons.append("completed: both valid nonnegative integer scores are required")
        elif row["homePoints"] == row["awayPoints"]:
            reasons.append("completed: tied outcomes are outside the initial binary-win scope")
    elif row.get("completed") is False and any(row.get(name) is not None for name in ("homePoints", "awayPoints")):
        reasons.append("completed: uncompleted games must have two null or absent scores")
    return normalized, reasons


def _normalize(snapshot: Snapshot) -> tuple[list[dict], dict, dict]:
    source = snapshot.source
    available_at = source["source_availability"]["available_at"]
    if available_at is not None:
        available_at = _utc_timestamp(available_at)
    ids = Counter(row["id"] for row in snapshot.records if type(row.get("id")) is int)
    games, excluded, quarantined = [], [], []
    for index, row in enumerate(snapshot.records):
        normalized, reasons = _validate_row(row, source["request_parameters"])
        if type(row.get("id")) is int and ids[row["id"]] > 1:
            reasons.append("id: duplicate within source snapshot; all occurrences quarantined")
        item = {"source_row_index": index, "game_id": row.get("id")}
        if reasons:
            quarantined.append(item | {"reasons": reasons})
        elif row["homeClassification"] != "fbs" or row["awayClassification"] != "fbs":
            excluded.append(item | {
                "home_classification": row["homeClassification"],
                "away_classification": row["awayClassification"],
                "reasons": ["classification: both opponents must be FBS"],
            })
        else:
            games.append(normalized | {
                "source_snapshot_id": source["snapshot_id"], "source_raw_sha256": source["raw_sha256"],
                "source_row_index": index, "retrieved_at": source["retrieved_at"],
                "historical_availability_status": source["source_availability"]["status"],
                "historical_available_at": available_at,
                "approved_for_predictor_use": False,
            })
    counts = {"input": len(snapshot.records), "retained": len(games),
              "excluded": len(excluded), "quarantined": len(quarantined)}
    assert counts["input"] == counts["retained"] + counts["excluded"] + counts["quarantined"]
    metadata = {"normalization_schema_version": NORMALIZATION_SCHEMA_VERSION, "source": source}
    report = metadata | {
        "status": "empty_input" if not snapshot.records else ("complete" if games else "no_retained_games"),
        "counts": counts,
        "input_both_fbs_count": coverage_report(snapshot.records)["both_opponents_fbs_count"],
        "quarantined_both_fbs_count": sum(
            snapshot.records[item["source_row_index"]].get("homeClassification") == "fbs"
            and snapshot.records[item["source_row_index"]].get("awayClassification") == "fbs"
            for item in quarantined),
        "reason_counts": {name: dict(sorted(Counter(reason for item in items for reason in item["reasons"]).items()))
                          for name, items in (("excluded", excluded), ("quarantined", quarantined))},
        "approved_for_predictor_use": False,
    }
    return games, metadata | {"excluded": excluded, "quarantined": quarantined}, report


def normalize_snapshot(manifest_path: Path | str, output_root: Path | str | None = None) -> Path:
    """Verify one raw snapshot and publish its normalized games, exclusions, and quality report.

    Rows with two FBS opponents are kept; other classifications are excluded, and invalid rows (for
    example, unresolved TBD kickoff times) are quarantined with reasons. Raw data is never repaired,
    and uncompleted games keep null scores. Output is deterministic, so an identical partial write
    can be resumed safely.

    Args:
        manifest_path: Manifest whose sibling raw file passes ``load_snapshot``.
        output_root: Root folder; a subfolder named by the snapshot ID is created (default
            ``data/interim/cfbd/games``).

    Returns:
        The snapshot's output directory containing games.csv, exclusions.json, and quality_report.json.

    Raises:
        NormalizationError: If the snapshot fails verification or existing output conflicts.
    """
    snapshot = load_snapshot(manifest_path)
    games, exclusions, report = _normalize(snapshot)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in games:
        writer.writerow({key: str(value).lower() if type(value) is bool else value for key, value in row.items()})
    artifacts = {"games.csv": buffer.getvalue().encode("utf-8"),
                 "exclusions.json": _json_bytes(exclusions), "quality_report.json": _json_bytes(report)}
    root = DEFAULT_OUTPUT_ROOT if output_root is None else Path(output_root)
    directory = root / snapshot.source["snapshot_id"]
    try:
        if directory.is_symlink():
            raise NormalizationError("Output snapshot directory must not be a symbolic link.")
        directory.mkdir(parents=True, exist_ok=True)
        # Preflight all outputs before writing; never overwrite conflicting or unrelated files.
        for path in directory.iterdir():
            if path.name not in artifacts or path.is_symlink() or not path.is_file():
                raise NormalizationError("Output directory contains unexpected entries; use a separate output root.")
            if path.read_bytes() != artifacts[path.name]:
                raise NormalizationError("Existing output differs; use a separate output root. No files overwritten.")
        for name, data in artifacts.items():
            path = directory / name
            if path.exists():
                if path.is_symlink() or path.read_bytes() != data:
                    raise NormalizationError("Concurrent output conflict; no files overwritten.")
            else:
                try:
                    _atomic_create(path, data)
                except FileExistsError:
                    if path.is_symlink() or path.read_bytes() != data:
                        raise NormalizationError("Concurrent output conflict; no files overwritten.") from None
    except OSError:
        raise NormalizationError("Could not publish normalization outputs; check permissions and storage.") from None
    return directory


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: normalize each --manifest offline and print its counts."""
    parser = argparse.ArgumentParser(description="Normalize explicitly selected CFBD manifests offline.")
    parser.add_argument("--manifest", type=Path, nargs="+", action="extend", required=True,
                        help="One or more paths; this option can also be repeated.")
    parser.add_argument("--output-root", type=Path, help="Output root; a snapshot-ID subdirectory is appended.")
    args = parser.parse_args(argv)
    failed = False
    for manifest_path in args.manifest:
        try:
            directory = normalize_snapshot(manifest_path, args.output_root)
            report = json.loads((directory / "quality_report.json").read_bytes())
        except (NormalizationError, OSError) as exc:
            message = str(exc) if isinstance(exc, NormalizationError) else "Could not read published quality report."
            print(f"Error for {manifest_path.name}: {message}", file=sys.stderr)
            failed = True
            continue
        print(f"Output: {directory}")
        print(json.dumps({"status": report["status"], "counts": report["counts"]}, sort_keys=True))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
