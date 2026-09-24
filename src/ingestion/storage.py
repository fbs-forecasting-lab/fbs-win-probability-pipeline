"""Preserve CFBD response bytes and publish versioned provenance manifests."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from .cfbd import GamesResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "cfbd" / "games"
REQUIRED_FIELDS = (
    "id", "season", "week", "seasonType", "startDate", "startTimeTBD",
    "completed", "neutralSite", "homeId", "homeTeam", "homeClassification",
    "homePoints", "awayId", "awayTeam", "awayClassification", "awayPoints",
)


class SnapshotError(ValueError):
    """A sanitized response-validation or snapshot-storage error."""


def _reject_non_json_constant(value: str) -> None:
    raise ValueError("Non-JSON numeric constant")


def parse_games(raw_response: bytes) -> list[dict]:
    """Validate the envelope, without filtering or repairing individual games."""
    try:
        records = json.loads(raw_response, parse_constant=_reject_non_json_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise SnapshotError("CFBD returned malformed JSON.") from None
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise SnapshotError("CFBD response must be a JSON array of game objects.")
    return records


def coverage_report(records: list[dict]) -> dict:
    """Describe field presence and classifications; this is not leakage approval."""
    missing = {field: sum(field not in row for row in records) for field in REQUIRED_FIELDS}
    nulls = {field: sum(field in row and row[field] is None for row in records)
             for field in REQUIRED_FIELDS}
    ids = Counter(row["id"] for row in records if type(row.get("id")) is int)
    invalid_ids = sum("id" in row and row["id"] is not None
                      and type(row["id"]) is not int for row in records)

    def classification(row: dict, field: str) -> str:
        if field not in row:
            return "<missing>"
        if row[field] is None:
            return "<null>"
        return row[field] if isinstance(row[field], str) else "<invalid>"

    classifications = {
        side: dict(sorted(Counter(classification(row, f"{side}Classification")
                                  for row in records).items()))
        for side in ("home", "away")
    }
    both_fbs = sum(row.get("homeClassification") == "fbs"
                   and row.get("awayClassification") == "fbs" for row in records)
    return {
        "status": "empty" if not records else "reported",
        "record_count": len(records),
        "missing_fields": missing,
        "null_fields": nulls,
        "duplicate_game_ids": {str(game_id): count for game_id, count in sorted(ids.items())
                               if count > 1},
        "invalid_game_id_count": invalid_ids,
        "classification_counts": classifications,
        "both_opponents_fbs_count": both_fbs,
        "other_or_unknown_classification_count": len(records) - both_fbs,
    }


def _atomic_create(path: Path, content: bytes) -> None:
    """Publish a complete file atomically, refusing to replace an existing path."""
    # A same-filesystem hard link is atomic and, unlike replace(), never clobbers.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".snapshot-", delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.link(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def save_snapshot(result: GamesResponse, output_dir: Path | str | None = None) -> tuple[Path, Path]:
    """Save raw bytes, then a manifest completion marker; return both paths."""
    records = parse_games(result.raw_response)
    root = DEFAULT_OUTPUT_DIR if output_dir is None else Path(output_dir)
    directory = root / f"season={result.parameters['year']}"
    snapshot_id = uuid4().hex
    raw_path = directory / f"{snapshot_id}.json"
    manifest_path = directory / f"{snapshot_id}.manifest.json"
    manifest = {
        "snapshot_id": snapshot_id,
        "snapshot_version": 1,
        "schema_version": 1,
        "source": "College Football Data",
        "endpoint": result.endpoint,
        "request_parameters": result.parameters,
        "retrieved_at": result.retrieved_at,
        "http_status": result.http_status,
        "record_count": len(records),
        "response_file": raw_path.name,
        "sha256": hashlib.sha256(result.raw_response).hexdigest(),
        "source_availability": {
            "status": "unknown",
            "available_at": None,
            "reason": "No documented historical publication timestamp in the games contract.",
        },
        "approved_for_predictor_use": False,
        "coverage": coverage_report(records),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        _atomic_create(raw_path, result.raw_response)
        # Consumers discover manifests, not raw files: the pair is not a transaction.
        _atomic_create(manifest_path, manifest_bytes)
    except OSError:
        raise SnapshotError(
            "Snapshot could not be published; check output permissions, free space, "
            "and filesystem hard-link support. Existing snapshots were not overwritten. "
            "A raw file without a manifest is incomplete."
        ) from None
    return raw_path, manifest_path
