"""Initial Demo: fetch one 2026 week from CFBD, store it in S3, and rebuild the dataset.

This thin command only chains existing, separately tested steps:

0. ``aws_preflight``: the existing read-only private-bucket check confirms AWS
   access and all four Block Public Access settings before the CFBD request.
1. ``cfbd_fetch``: ``fetch_games`` requests one regular-season 2026 week and
   ``save_snapshot`` stores the raw response and manifest under
   ``data/raw/cfbd/<run-tag>/games``.
2. ``s3_upload_raw``: ``S3Store.upload_raw`` stores that raw pair with
   conditional, no-overwrite writes.
3. ``normalize``: ``normalize_snapshot`` writes the new week and the five fixed
   2021–2025 history snapshots under ``data/interim/cfbd/<run-tag>/games``;
   ``build_dataset`` needs every season under one normalized root. Existing
   normalized outputs are never modified.
4. ``build_dataset``: builds ``data/processed/<run-tag>-features`` from the five
   history manifests plus the new week. Train and holdout rows depend only on
   2021–2025, so they match the earlier dataset.
5. ``s3_upload_dataset``: ``S3Store.upload_dataset`` stores the six dataset
   files under the new dataset ID.

It prints the ``src.pipeline.s3_demo`` command that downloads, trains, and
predicts from the uploaded dataset. The week is a saved snapshot; historical
availability remains unverified, so outputs are retrospective-demo results,
not approved live forecasts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from src.features import dataset, games
from src.ingestion import cfbd, s3_storage
from src.ingestion.storage import PROJECT_ROOT, SnapshotError, coverage_report, parse_games, save_snapshot
from src.models.baseline import STATUS, BaselineError, check_status, read_file, read_json
from src.pipeline.s3_demo import display_path

SEASON = 2026
HISTORY_SEASONS = tuple(range(2021, 2026))
REFERENCE_REPORT = Path("data/processed/demo-features-v1/dataset_report.json")
REFERENCE_DATASET_ID = "8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5"  # Week 4 reference.
HISTORY_RAW_ROOT = Path("data/raw/cfbd/games")
RETROSPECTIVE_REQUIRED = "Pass --allow-retrospective-demo; historical availability remains unverified."
PROJECT_ERRORS = (cfbd.CFBDError, SnapshotError, games.NormalizationError, dataset.DatasetError,
                  s3_storage.S3StorageError, BaselineError)


class RefreshError(ValueError):
    """A refresh stage failed; the message names the stage and never includes secrets."""


def stage_error(stage, exc):
    """Keep sanitized project messages; reduce anything unexpected to its type name."""
    if isinstance(exc, (*PROJECT_ERRORS, RefreshError)):
        return RefreshError(f"{stage} failed: {exc}")
    return RefreshError(f"{stage} failed: unexpected {type(exc).__name__}; details suppressed.")


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def run_tag(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise argparse.ArgumentTypeError("use 1–64 lowercase letters, digits, or hyphens, starting with a letter or digit")
    return value


def output_dirs(root, tag):
    return {"raw": root / "data/raw/cfbd" / tag, "interim": root / "data/interim/cfbd" / tag,
            "features": root / "data/processed" / f"{tag}-features", "run": root / "data/processed" / f"{tag}-run"}


def check_new_dir(path):
    """Refuse anything but a new or empty real directory; never touch existing files."""
    try:
        if path.is_symlink():
            raise RefreshError(f"Output path for this run tag must not be a symbolic link: {display_path(path)}")
        if path.exists() and (not path.is_dir() or any(path.iterdir())):
            raise RefreshError(f"Output path for this run tag already exists and is not empty: {display_path(path)}. "
                               "Choose a new --run-tag; nothing overwritten.")
    except OSError:
        raise RefreshError("Output path for this run tag cannot be inspected; choose a new --run-tag.") from None


def discover_history(root):
    """Find the five history manifests recorded in the reference dataset report."""
    try:
        names, expected = history_sources(read_json(read_file(root / REFERENCE_REPORT)))
    except BaselineError:
        raise RefreshError(f"Could not discover history manifests from {REFERENCE_REPORT}; "
                           "pass --history-manifest once per season 2021–2025.") from None
    return [root / HISTORY_RAW_ROOT / f"season={season}" / names[season] for season in HISTORY_SEASONS], expected


def history_sources(report):
    """Return the manifest filename and expected source metadata per history season from a dataset report."""
    try:
        names, expected = {}, {}
        for season in HISTORY_SEASONS:
            source = report["sources"][str(season)]["source"]
            name = source["manifest_file"]
            if not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{32}\.manifest\.json", name):
                raise RefreshError("Reference dataset report lists an unsafe manifest filename.")
            names[season], expected[season] = name, source
    except (KeyError, TypeError):
        raise RefreshError("Reference dataset report does not list the 2021–2025 history sources.") from None
    return names, expected


def download_history(store, directory, reference_dataset_id=REFERENCE_DATASET_ID):
    """Download and verify the 2021–2025 history from S3 only; no local raw history is read.

    The verified reference dataset in S3 names the five manifests and their expected
    source metadata. Each raw pair is SHA-256 verified on download, then checked
    against that metadata with ``verify_history``. Returns the local manifest paths.
    """
    directory = Path(directory)
    store.download_dataset(reference_dataset_id, directory / "reference-dataset", allow_retrospective_demo=True)
    names, expected = history_sources(read_json(read_file(directory / "reference-dataset" / "dataset_report.json")))
    paths = [store.download_raw(season, names[season], directory / f"season={season}") for season in HISTORY_SEASONS]
    return verify_history(paths, expected)


def verify_history(paths, expected=None):
    """Require exactly one hash-verified, full-season manifest per season 2021–2025."""
    selected = {}
    for path in paths:
        path = Path(path)
        try:
            snapshot = games.load_snapshot(path)
        except (games.NormalizationError, OSError):
            raise RefreshError(f"History manifest is missing or failed hash verification: {path.name}") from None
        params = snapshot.source["request_parameters"]
        season = params.get("year")
        if season not in HISTORY_SEASONS or "week" in params:
            raise RefreshError("History manifests must be full-season requests for seasons 2021–2025.")
        if season in selected:
            raise RefreshError(f"Duplicate history season {season}; pass exactly one manifest per season.")
        if expected is not None and snapshot.source != expected[season]:
            raise RefreshError(f"Season {season} manifest differs from the reference dataset report.")
        selected[season] = path
    missing = sorted(set(HISTORY_SEASONS) - selected.keys())
    if missing:
        raise RefreshError(f"Missing history seasons: {', '.join(map(str, missing))}.")
    return [selected[season] for season in HISTORY_SEASONS]


def next_command(dataset_id, tag, extra=()):
    return " ".join([".venv/bin/python -B -m src.pipeline.s3_demo", "--dataset-id", dataset_id,
                     "--run-dir", f"data/processed/{tag}-run", *extra,
                     "--prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 --allow-retrospective-demo"])


def run(store, week, tag, history, *, root=None, extra_args=()):
    """Run fetch -> raw upload -> normalize -> build -> dataset upload for one new run tag."""
    dirs = output_dirs(PROJECT_ROOT if root is None else Path(root), tag)
    normalized_root, features_dir = dirs["interim"] / "games", dirs["features"]
    stage = "aws_preflight"
    try:
        # Read-only: confirm credentials and all four Block Public Access flags before spending the CFBD request.
        store._private_bucket()
        stage = "cfbd_fetch"
        result = cfbd.fetch_games(SEASON, week)
        raw_path, manifest_path = save_snapshot(result, dirs["raw"] / "games")
        coverage = coverage_report(parse_games(result.raw_response))
        if coverage["record_count"] == 0:
            raise RefreshError("CFBD returned no games for this week; nothing uploaded.")
        stage = "s3_upload_raw"
        raw_objects = store.upload_raw(manifest_path)
        stage = "normalize"
        new_normalized = games.normalize_snapshot(manifest_path, normalized_root)
        for path in history:
            games.normalize_snapshot(path, normalized_root)
        quality = read_json(read_file(new_normalized / "quality_report.json"))
        stage = "build_dataset"
        report = dataset.build_dataset([*history, manifest_path], features_dir, allow_retrospective_demo=True,
                                       normalized_root=normalized_root)
        check_status(report)
        stage = "s3_upload_dataset"
        dataset_objects = store.upload_dataset(features_dir, allow_retrospective_demo=True)
    except Exception as exc:
        raise stage_error(stage, exc) from None

    dataset_id = report["dataset_id"]
    splits = report["splits"]
    return {
        "stages": {
            "1_cfbd_fetch": {"season": SEASON, "week": week, "raw_snapshot": display_path(raw_path),
                             "manifest": display_path(manifest_path), "http_status": result.http_status,
                             "retrieved_at": result.retrieved_at, "record_count": coverage["record_count"],
                             "both_opponents_fbs_count": coverage["both_opponents_fbs_count"]},
            "2_s3_upload_raw": {"objects": raw_objects},
            "3_normalize": {"normalized_root": display_path(normalized_root), "new_week_counts": quality["counts"],
                            "history_snapshots_normalized": len(history)},
            "4_build_dataset": {"features_dir": display_path(features_dir), "dataset_id": dataset_id,
                                "counts": {name: split["output"] for name, split in splits.items()},
                                "excluded": {name: split["excluded"] for name, split in splits.items()},
                                "prediction_exclusion_reasons": splits["prediction"]["exclusion_reason_counts"]},
            "5_s3_upload_dataset": {"s3_location": f"s3://{store.bucket}/{store.prefix}/datasets/{dataset_id}/",
                                    "objects": dataset_objects},
        },
        **STATUS,
        "dataset_id": dataset_id,
        "next_command": next_command(dataset_id, tag, extra_args),
    }


def main(argv=None):
    defaults = s3_storage.configuration()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int, choices=[SEASON], default=SEASON, help="Target season (only 2026)")
    parser.add_argument("--week", type=positive_int, required=True, help="Regular-season week to fetch")
    parser.add_argument("--run-tag", type=run_tag, required=True,
                        help="New tag for this run's output directories, e.g. week5-take-1")
    parser.add_argument("--history-manifest", type=Path, action="append",
                        help="2021–2025 manifest, once per season (default: those in the demo-features-v1 report)")
    parser.add_argument("--bucket", default=defaults["FBS_S3_BUCKET"])
    parser.add_argument("--prefix", default=defaults["FBS_S3_PREFIX"])
    parser.add_argument("--region", default=defaults["FBS_S3_REGION"])
    parser.add_argument("--profile", default=defaults["FBS_AWS_PROFILE"])
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    root = PROJECT_ROOT
    try:
        # Every refusal below happens before any CFBD request or AWS client exists.
        if args.allow_retrospective_demo is not True:
            raise RefreshError(RETROSPECTIVE_REQUIRED)
        store = s3_storage.S3Store(None, args.bucket, args.prefix)
        for path in output_dirs(root, args.run_tag).values():
            check_new_dir(path)
        if args.history_manifest:
            history = verify_history(args.history_manifest)
        else:
            history = verify_history(*discover_history(root))
        cfbd._api_key()  # Presence and format only; the value is never printed or stored.
    except Exception as exc:
        detail = str(exc) if isinstance(exc, (*PROJECT_ERRORS, RefreshError)) else (
            f"unexpected {type(exc).__name__}; details suppressed.")
        print(f"Error: cli_refusal: {detail}", file=sys.stderr)
        return 1
    try:
        store.client = s3_storage.make_client(args.region, args.profile)
    except Exception as exc:
        print(f"Error: {stage_error('aws_client', exc)}", file=sys.stderr)
        return 1
    # Keep the printed next step pointed at the same S3 settings when any were overridden.
    overrides = (("bucket", args.bucket, "FBS_S3_BUCKET"), ("prefix", args.prefix, "FBS_S3_PREFIX"),
                 ("region", args.region, "FBS_S3_REGION"), ("profile", args.profile, "FBS_AWS_PROFILE"))
    extra = [f"--{name} {value}" for name, value, key in overrides if value is not None and value != defaults[key]]
    try:
        result = run(store, args.week, args.run_tag, history, root=root, extra_args=extra)
    except RefreshError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
