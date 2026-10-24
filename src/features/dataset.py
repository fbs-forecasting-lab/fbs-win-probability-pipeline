"""Reconstructed demo datasets with explicit inputs and unverified availability."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys

from src.features import games
from src.ingestion.storage import _atomic_create

DATASET_SCHEMA_VERSION = 1
PREDICTOR_COLUMNS = ("prior_win_pct_diff", "prior_avg_margin_diff", "home_field")
SEASONS = tuple(range(2021, 2027))
SPLIT_SEASONS = {"train": (2022, 2023, 2024), "holdout": (2025,), "prediction": (2026,)}
MODE = "retrospective_demo"
LIMITATIONS = (
    "Historical availability is unverified; outputs are not approved for point-in-time forecasting.",
    "Prior-season results and target matchup metadata are assumed to represent information that could "
    "have been known before the target game; revisions and historical versions remain unverified.",
    "Cutoff is scheduled kickoff in the selected snapshot; historical schedules and actual kickoff are unverified.",
    "Prior-game scheduled starts before cutoff prove chronology only, not publication or completion time.",
)
FEATURE_DEFINITIONS = {
    "prior_win_pct_diff": "home prior-season wins/completed games minus away prior-season wins/completed games",
    "prior_avg_margin_diff": "home prior-season mean(points minus opponent points) minus away prior-season mean margin",
    "home_field": "0 when target neutral_site is true, otherwise 1",
}
TARGET_COLUMNS = (
    "game_id", "season", "week", "home_id", "home_team", "away_id", "away_team",
    "cutoff", "neutral_site", "completed", "home_points", "away_points",
)
AUDIT_COLUMNS = (
    "home_prior_game_count", "away_prior_game_count", "feature_source_season",
    "feature_source_snapshot_id", "feature_source_raw_sha256", "feature_source_manifest_sha256",
    "feature_source_availability_status", "feature_source_available_at",
    "feature_source_approved_for_predictor_use",
    "source_snapshot_id", "source_raw_sha256", "source_manifest_sha256", "source_row_index", "retrieved_at",
    "historical_availability_status", "historical_available_at", "approved_for_predictor_use",
    "dataset_mode", "historical_availability_verified", "approved_for_point_in_time_forecasting",
)
AGGREGATE_COLUMNS = (
    "season", "team_id", "completed_game_count", "wins", "margin_sum", "prior_win_pct", "prior_avg_margin",
    "latest_scheduled_start", "contributing_game_ids", "source_row_indices",
    "source_snapshot_id", "source_raw_sha256", "source_manifest_sha256", "retrieved_at",
    "historical_availability_status", "historical_available_at", "approved_for_predictor_use",
    "dataset_mode", "historical_availability_verified", "approved_for_point_in_time_forecasting",
)


class DatasetError(ValueError):
    """Invalid inputs, missing explicit demo permission, or conflicting output."""


@dataclass(frozen=True)
class SeasonInput:
    """Verified inputs for one season: source metadata, typed normalized rows, counts, artifact hashes."""
    source: dict
    rows: list[dict]
    normalization_counts: dict
    artifact_hashes: dict


def _json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _csv(rows: list[dict], columns: tuple) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: str(value).lower() if type(value) is bool else value
                         for key, value in row.items()})
    return buffer.getvalue().encode("utf-8")


def _load_inputs(manifest_paths: list[Path | str], normalized_root: Path) -> dict[int, SeasonInput]:
    selected = {}
    for manifest_path in manifest_paths:
        path = Path(manifest_path)
        snapshot = games.load_snapshot(path)
        season = snapshot.source["request_parameters"]["year"]
        if season in selected:
            raise DatasetError(f"Duplicate season {season}: select exactly one explicit snapshot, even if paths repeat.")
        if season not in SEASONS:
            raise DatasetError("This demo requires exactly the 2021–2026 seasons.")
        if season <= 2025 and "week" in snapshot.source["request_parameters"]:
            raise DatasetError(f"Season {season} must use a full-season historical request, not a week sample.")
        selected[season] = (path, snapshot)
    missing = sorted(set(SEASONS) - selected.keys())
    if missing:
        raise DatasetError(f"Missing required seasons: {', '.join(map(str, missing))}.")

    inputs = {}
    for season, (path, snapshot) in sorted(selected.items()):
        directory = normalized_root / snapshot.source["snapshot_id"]
        names = ("games.csv", "exclusions.json", "quality_report.json")
        try:
            before = {name: (directory / name).read_bytes() for name in names}
        except OSError:
            raise DatasetError(f"Season {season}: complete normalized outputs are required; run normalization first.") from None
        # Reuse the existing full raw/normalized validation. Because all artifacts
        # already exist, a valid rerun does not write or repair anything.
        games.normalize_snapshot(path, normalized_root)
        if any((directory / name).read_bytes() != data for name, data in before.items()):
            raise DatasetError("Normalized artifacts changed during verification.")
        report = json.loads(before["quality_report.json"])
        if report["source"] != snapshot.source:
            raise DatasetError("Source metadata changed during verification.")
        reader = csv.DictReader(io.StringIO(before["games.csv"].decode("utf-8")))
        if reader.fieldnames != list(games.COLUMNS):
            raise DatasetError("Unexpected normalized CSV columns.")
        rows = []
        for record in reader:
            # Types were already validated by normalization and byte comparison.
            row = dict(record)
            for field in ("id", "season", "week", "home_id", "away_id", "source_row_index"):
                row[field] = int(row[field])
            for field in ("home_points", "away_points"):
                row[field] = None if row[field] == "" else int(row[field])
            for field in ("completed", "neutral_site", "start_time_tbd", "approved_for_predictor_use"):
                row[field] = row[field] == "true"
            row["historical_available_at"] = row["historical_available_at"] or None
            rows.append(row)
        rows.sort(key=lambda row: (datetime.fromisoformat(row["start_date"]), row["id"], row["source_row_index"]))
        inputs[season] = SeasonInput(snapshot.source, rows, report["counts"],
                                     {name: hashlib.sha256(data).hexdigest() for name, data in before.items()})
    return inputs


def _source_audit(source: dict) -> dict:
    available = source["source_availability"]["available_at"]
    return {
        "source_snapshot_id": source["snapshot_id"], "source_raw_sha256": source["raw_sha256"],
        "source_manifest_sha256": source["manifest_sha256"], "retrieved_at": source["retrieved_at"],
        "historical_availability_status": source["source_availability"]["status"],
        "historical_available_at": games._utc_timestamp(available) if available is not None else None,
        "approved_for_predictor_use": source["approved_for_predictor_use"],
        "dataset_mode": MODE, "historical_availability_verified": False,
        "approved_for_point_in_time_forecasting": False,
    }


def _aggregate(inputs: dict[int, SeasonInput]) -> tuple[dict, dict]:
    aggregates, usage = {}, {}
    for season in range(2021, 2026):
        source = inputs[season].source
        rows = inputs[season].rows
        complete = [row for row in rows if row["completed"]]
        usage[str(season)] = {"normalized_games": len(rows), "completed_games_used": len(complete),
                              "incomplete_games_omitted": [row["id"] for row in rows if not row["completed"]]}
        for row in complete:
            for side, opponent in (("home", "away"), ("away", "home")):
                key = (season, row[f"{side}_id"])
                aggregate = aggregates.setdefault(key, {
                    "season": season, "team_id": key[1], "completed_game_count": 0,
                    "wins": 0, "margin_sum": 0, "latest_scheduled_start": row["start_date"],
                    "contributing_game_ids": [], "source_row_indices": [], **_source_audit(source),
                })
                margin = row[f"{side}_points"] - row[f"{opponent}_points"]
                aggregate["completed_game_count"] += 1
                aggregate["wins"] += int(margin > 0)
                aggregate["margin_sum"] += margin
                aggregate["contributing_game_ids"].append(row["id"])
                aggregate["source_row_indices"].append(row["source_row_index"])
                if datetime.fromisoformat(row["start_date"]) > datetime.fromisoformat(aggregate["latest_scheduled_start"]):
                    aggregate["latest_scheduled_start"] = row["start_date"]
        usage[str(season)]["team_count"] = sum(key[0] == season for key in aggregates)
    for aggregate in aggregates.values():
        aggregate["prior_win_pct"] = aggregate["wins"] / aggregate["completed_game_count"]
        aggregate["prior_avg_margin"] = aggregate["margin_sum"] / aggregate["completed_game_count"]
    return aggregates, usage


def _target_audit(row: dict, source: dict, prior_source: dict) -> dict:
    prior_available = prior_source["source_availability"]["available_at"]
    return {
        "game_id": row["id"], **{field: row[field] for field in TARGET_COLUMNS
                                  if field not in ("game_id", "cutoff")},
        "cutoff": row["start_date"], "source_row_index": row["source_row_index"],
        "feature_source_season": row["season"] - 1,
        "feature_source_snapshot_id": prior_source["snapshot_id"],
        "feature_source_raw_sha256": prior_source["raw_sha256"],
        "feature_source_manifest_sha256": prior_source["manifest_sha256"],
        "feature_source_availability_status": prior_source["source_availability"]["status"],
        "feature_source_available_at": games._utc_timestamp(prior_available) if prior_available is not None else None,
        "feature_source_approved_for_predictor_use": prior_source["approved_for_predictor_use"],
        **_source_audit(source),
    }


def _publish(directory: Path, artifacts: dict[str, bytes]) -> None:
    try:
        if directory.is_symlink():
            raise DatasetError("Dataset output directory must not be a symbolic link.")
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.iterdir():
            if path.name not in artifacts or path.is_symlink() or not path.is_file():
                raise DatasetError("Output directory contains unexpected entries; use a separate output directory.")
            if path.read_bytes() != artifacts[path.name]:
                raise DatasetError("Existing dataset differs; use a separate output directory. No files overwritten.")
        for name, content in artifacts.items():
            path = directory / name
            if path.exists():
                if path.is_symlink() or path.read_bytes() != content:
                    raise DatasetError("Concurrent dataset output conflict; no files overwritten.")
                continue
            try:
                _atomic_create(path, content)
            except FileExistsError:
                if path.is_symlink() or path.read_bytes() != content:
                    raise DatasetError("Concurrent dataset output conflict; no files overwritten.") from None
    except OSError:
        raise DatasetError("Could not publish dataset; check permissions and storage. Matching partial outputs can be resumed.") from None


def build_dataset(manifest_paths: list[Path | str], output_dir: Path | str, *,
                  allow_retrospective_demo: bool = False,
                  normalized_root: Path | str = games.DEFAULT_OUTPUT_ROOT) -> dict:
    """Build the fixed train/holdout/prediction splits from one verified snapshot per season.

    Each target game gets three predictors computed from the previous season's completed FBS-vs-FBS
    games: win-percentage difference, average-margin difference, and home field. Training targets
    are 2022–2024, holdout is 2025, and prediction rows are uncompleted 2026 games; 2021 supplies
    history only. Games with no prior history, the wrong completion status, or history that is not
    before the scheduled kickoff are excluded with recorded reasons.

    Args:
        manifest_paths: Exactly one manifest per season 2021–2026; 2021–2025 must be full seasons.
        output_dir: New or matching directory for the six dataset files.
        allow_retrospective_demo: Must be True to acknowledge unverified historical availability.
        normalized_root: Folder holding each snapshot's existing normalized outputs, re-verified here.

    Returns:
        The dataset report (also written as dataset_report.json), including ``dataset_id``: the
        SHA-256 of the source metadata and hashes, predictor columns, and mode.

    Raises:
        DatasetError: If permission is missing, seasons are missing or duplicated, inputs fail
            verification, or existing output conflicts.
    """
    if allow_retrospective_demo is not True:
        raise DatasetError("Historical availability is unverified. Pass --allow-retrospective-demo to explicitly "
                           "permit reconstruction; it does not approve point-in-time forecasting.")
    try:
        inputs = _load_inputs(manifest_paths, Path(normalized_root))
    except games.NormalizationError as exc:
        raise DatasetError(f"Input verification failed: {exc}") from None
    except (OSError, ValueError) as exc:
        if isinstance(exc, DatasetError):
            raise
        raise DatasetError("Could not read verified inputs; check manifest and normalized artifacts.") from None
    aggregates, aggregate_usage = _aggregate(inputs)
    exclusions, splits, split_reports = [], {}, {}
    for split, seasons in SPLIT_SEASONS.items():
        rows, rejected = [], []
        for season in seasons:
            for target in inputs[season].rows:
                home = aggregates.get((season - 1, target["home_id"]))
                away = aggregates.get((season - 1, target["away_id"]))
                audit = _target_audit(target, inputs[season].source, inputs[season - 1].source)
                audit.update(home_prior_game_count=home["completed_game_count"] if home else 0,
                             away_prior_game_count=away["completed_game_count"] if away else 0)
                reasons = []
                if split != "prediction" and not target["completed"]:
                    reasons.append("target_uncompleted")
                if split == "prediction" and target["completed"]:
                    reasons.append("prediction_target_completed")
                for side, aggregate in (("home", home), ("away", away)):
                    if aggregate is None:
                        reasons.append(f"missing_{side}_history")
                    elif datetime.fromisoformat(aggregate["latest_scheduled_start"]) >= datetime.fromisoformat(target["start_date"]):
                        reasons.append(f"{side}_history_not_before_cutoff")
                if reasons:
                    rejected.append(audit | {"split": split, "reasons": reasons})
                    continue
                features = {
                    "prior_win_pct_diff": home["prior_win_pct"] - away["prior_win_pct"],
                    "prior_avg_margin_diff": home["prior_avg_margin"] - away["prior_avg_margin"],
                    "home_field": 0 if target["neutral_site"] else 1,
                }
                result = audit | features
                if split != "prediction":
                    result["home_win"] = int(target["home_points"] > target["away_points"])
                rows.append(result)
        rows.sort(key=lambda row: (row["season"], datetime.fromisoformat(row["cutoff"]), row["game_id"]))
        rejected.sort(key=lambda row: (row["season"], datetime.fromisoformat(row["cutoff"]), row["game_id"]))
        splits[split] = rows
        exclusions.extend(rejected)
        split_reports[split] = {
            "target_seasons": list(seasons), "input": sum(len(inputs[year].rows) for year in seasons),
            "output": len(rows), "excluded": len(rejected),
            "exclusion_reason_counts": dict(sorted(Counter(reason for row in rejected for reason in row["reasons"]).items())),
            "feature_ranges": {name: {"min": min(row[name] for row in rows), "max": max(row[name] for row in rows)}
                               if rows else {"min": None, "max": None} for name in PREDICTOR_COLUMNS},
            "prior_game_count_ranges": {side: {"min": min(row[f"{side}_prior_game_count"] for row in rows),
                                               "max": max(row[f"{side}_prior_game_count"] for row in rows)}
                                        if rows else {"min": None, "max": None} for side in ("home", "away")},
        }
        assert split_reports[split]["input"] == len(rows) + len(rejected)

    metadata = {
        "dataset_schema_version": DATASET_SCHEMA_VERSION, "dataset_mode": MODE,
        "historical_availability_verified": False, "approved_for_point_in_time_forecasting": False,
        "approved_for_predictor_use": False, "allow_retrospective_demo": True,
        "limitations": list(LIMITATIONS), "predictor_columns": list(PREDICTOR_COLUMNS),
        "cutoff_definition": "scheduled kickoff recorded in the selected target snapshot",
        "sources": {str(year): {"source": item.source, "normalization_counts": item.normalization_counts,
                               "normalized_artifact_sha256": item.artifact_hashes} for year, item in inputs.items()},
    }
    identity = {"schema_version": DATASET_SCHEMA_VERSION, "sources": metadata["sources"],
                "predictor_columns": metadata["predictor_columns"], "mode": MODE}
    metadata["dataset_id"] = hashlib.sha256(_json(identity)).hexdigest()
    artifacts = {}
    for split, rows in splits.items():
        label = ("home_win",) if split != "prediction" else ()
        artifacts[f"{split}.csv"] = _csv(rows, (*TARGET_COLUMNS, *PREDICTOR_COLUMNS, *label, *AUDIT_COLUMNS))
    aggregate_rows = []
    for key in sorted(aggregates):
        row = dict(aggregates[key])
        for field in ("contributing_game_ids", "source_row_indices"):
            row[field] = json.dumps(row[field], separators=(",", ":"))
        aggregate_rows.append(row)
    artifacts["team_season_aggregates.csv"] = _csv(aggregate_rows, AGGREGATE_COLUMNS)
    artifacts["exclusions.json"] = _json(metadata | {"rows": exclusions})
    report = metadata | {"feature_definitions": FEATURE_DEFINITIONS, "splits": split_reports,
                         "aggregate_usage": aggregate_usage, "aggregate_row_count": len(aggregate_rows),
                         "input_count_definition": "Retained normalized target rows, before dataset eligibility exclusions.",
                         "artifact_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}}
    artifacts["dataset_report.json"] = _json(report)  # Completion marker published last.
    _publish(Path(output_dir), artifacts)
    return report


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: build a dataset from --manifest files into --output-dir and print its ID."""
    parser = argparse.ArgumentParser(description="Build explicitly permitted retrospective demo datasets offline.")
    parser.add_argument("--manifest", nargs="+", action="extend", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--normalized-root", type=Path, default=games.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_dataset(args.manifest, args.output_dir, allow_retrospective_demo=args.allow_retrospective_demo,
                               normalized_root=args.normalized_root)
    except DatasetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Output: {args.output_dir.resolve()}")
    print(f"Dataset ID: {report['dataset_id']}")
    print("retrospective_demo: historical availability unverified; not approved for point-in-time forecasting.")
    print(json.dumps(report["splits"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
