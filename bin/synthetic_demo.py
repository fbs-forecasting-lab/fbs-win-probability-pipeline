"""Run the real pipeline on deterministic fictional games, entirely offline."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features import dataset, games
from src.ingestion.storage import coverage_report
from src.models.baseline import PREDICTORS, STATUS, load_trusted_model, train_baseline
from src.models.predict import predict_saved_sample, predict_vector

NOTICE = "SYNTHETIC ONLY: fictional teams, scores, timestamps, and metrics; no API request or real football data."
TEAMS = ("Synthetic Alder Owls", "Synthetic Birch Foxes", "Synthetic Cedar Kites", "Synthetic Dune Otters")


def json_bytes(value):
    """Serialize a value as sorted, indented JSON bytes with a trailing newline."""
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write_new(path, content):
    """Write bytes to a path that must not already exist (exclusive create)."""
    with path.open("xb") as handle:
        handle.write(content)


def make_snapshot(year, directory):
    """Create a deterministic synthetic fixture in the existing CFBD wire schema.

    The source, endpoint and HTTP status are simulated contract fields, never
    evidence of an API call. The synthetic notice propagates in source availability.
    """
    rows = []
    for number, (home, away) in enumerate(itertools.combinations(range(4), 2), 1):
        home_wins = (number + year) % 3 != 0
        rows.append({
            "id": year * 100 + number, "season": year, "week": 5 if year == 2026 else number,
            "seasonType": "regular", "startDate": f"{year}-09-{number:02d}T18:00:00Z",
            "startTimeTBD": False, "completed": year != 2026, "neutralSite": number == 3,
            "homeId": home + 1, "awayId": away + 1,
            "homeTeam": TEAMS[home], "awayTeam": TEAMS[away],
            "homeClassification": "fbs", "awayClassification": "fbs",
            "homePoints": None if year == 2026 else (28 + number if home_wins else 10),
            "awayPoints": None if year == 2026 else (14 if home_wins else 24 + number),
        })
    raw = json_bytes(rows)
    snapshot_id = uuid.uuid5(uuid.NAMESPACE_URL, f"synthetic-demo-v1/{year}").hex
    params = {"year": year, "seasonType": "regular", "classification": "fbs"}
    if year == 2026:
        params["week"] = 5
    manifest = {
        "snapshot_id": snapshot_id, "snapshot_version": 1, "schema_version": 1,
        "source": "College Football Data", "endpoint": "https://api.collegefootballdata.com/games",
        "http_status": 200, "synthetic_notice": NOTICE, "request_parameters": params,
        "retrieved_at": "2026-09-01T00:00:00Z", "record_count": len(rows),
        "response_file": f"{snapshot_id}.json", "sha256": hashlib.sha256(raw).hexdigest(),
        "source_availability": {"status": "unknown", "available_at": None, "reason": NOTICE},
        "approved_for_predictor_use": False, "coverage": coverage_report(rows),
    }
    directory.mkdir(parents=True)
    write_new(directory / manifest["response_file"], raw)
    path = directory / f"{snapshot_id}.manifest.json"
    write_new(path, json_bytes(manifest))
    return path


def run(run_dir, *, allow_retrospective_demo=False, root=ROOT):
    """Run the real pipeline end to end on deterministic fictional games, entirely offline.

    Creates a synthetic snapshot for each season 2021–2026, then calls normalize_snapshot,
    build_dataset, train_baseline, predict_saved_sample, load_trusted_model, and predict_vector. No
    network or credentials are used, and all teams, scores, and metrics are fictional.

    Args:
        run_dir: New directory beneath ``data/processed``; relative paths are resolved against ``root``.
        allow_retrospective_demo: Must be True to acknowledge that results are not approved forecasts.
        root: Repository root used to resolve and confine ``run_dir``.

    Returns:
        The summary also written to synthetic_summary.json: notice, status flags, dataset ID, counts,
        synthetic holdout metrics, saved-model prediction count, hypothetical result, and output
        directory.

    Raises:
        ValueError: If permission is missing, or ``run_dir`` already exists, contains a symbolic link,
            or is not beneath ``data/processed``. Pipeline stages raise ValueError subclasses
            (NormalizationError, DatasetError, BaselineError) if they reject the synthetic inputs.
    """
    if not allow_retrospective_demo:
        raise ValueError("Pass --allow-retrospective-demo; synthetic results are not approved forecasts.")
    root = Path(root).resolve()
    path = Path(run_dir)
    if not path.is_absolute():
        path = root / path
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Output path must not contain symbolic links.")
    path = path.resolve()
    allowed = root / "data/processed"
    if path == allowed or not path.is_relative_to(allowed):
        raise ValueError("Use a new directory beneath data/processed (ignored generated outputs).")
    if path.exists():
        raise ValueError("Run directory already exists; choose a new name. Nothing was overwritten.")
    path.mkdir(parents=True, exist_ok=False)
    write_new(path / "SYNTHETIC.txt", (NOTICE + "\n").encode())
    # Prepare fictional raw snapshots, then use the same normalizer as the CFBD workflow.
    manifests = []
    for year in dataset.SEASONS:
        manifest = make_snapshot(year, path / "raw" / f"season={year}")
        games.normalize_snapshot(manifest, path / "normalized")
        manifests.append(manifest)
    # Build the chronological splits: 2021 supplies history; it is not a training target season.
    report = dataset.build_dataset(manifests, path / "dataset", normalized_root=path / "normalized",
                                   allow_retrospective_demo=True)
    # Fit on training rows and evaluate on holdout rows inside the production baseline function.
    metadata, evaluation = train_baseline(path / "dataset", path / "model", allow_retrospective_demo=True)
    # Reload the saved model for both a batch and one hypothetical matchup, exercising inference too.
    prediction = predict_saved_sample(path / "model", path / "dataset", path / "predictions",
                                      allow_retrospective_demo=True)
    model, _ = load_trusted_model(path / "model", allow_retrospective_demo=True)
    hypothetical = predict_vector(model, dict(zip(PREDICTORS, (0.2, 7, 1))))
    summary = {"notice": NOTICE, **STATUS, "dataset_id": report["dataset_id"],
               "generated_games": 36, "counts": metadata["counts"],
               "synthetic_holdout_metrics": {key: evaluation[key] for key in ("model", "constant_baseline")},
               "saved_model_prediction_count": prediction["count"],
               "synthetic_hypothetical": hypothetical,
               "output_directory": str(path.relative_to(root))}
    write_new(path / "synthetic_summary.json", json_bytes(summary))
    return summary


def main(argv=None):
    """Command-line entry point: run the synthetic example and print its summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="data/processed/synthetic-demo", type=Path)
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run(args.run_dir, allow_retrospective_demo=args.allow_retrospective_demo)
    except (ValueError, OSError) as exc:
        print(f"Synthetic example failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
