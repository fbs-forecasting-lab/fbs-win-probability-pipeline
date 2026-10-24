"""Initial Demo: verified S3 dataset download -> local training -> prediction.

This thin command only chains existing, separately tested steps:

1. ``S3Store.download_dataset`` reads the dataset from the selected private
   bucket, verifies every object's SHA-256 and the dataset loader, then
   publishes the files to ``<run-dir>/dataset``. Data are downloaded and
   verified first; nothing is streamed from S3 into the model.
2. ``train_baseline`` fits the fixed scaler + logistic model on that downloaded
   directory only and writes ``<run-dir>/model``.
3. ``predict_saved_sample`` reloads that new model and scores the saved 2026
   sample into ``<run-dir>/predictions``; an optional hypothetical vector is
   also scored.

Training and inference run locally. Historical feature availability remains
unverified, so outputs are retrospective-demo results, not live forecasts.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys

from src.ingestion import s3_storage
from src.models.baseline import PREDICTORS, STATUS, BaselineError, load_trusted_model, read_file, train_baseline
from src.models.predict import predict_saved_sample, predict_vector

SAMPLE_ROWS_SHOWN = 3
RETROSPECTIVE_REQUIRED = "Pass --allow-retrospective-demo; historical availability remains unverified."


class DemoError(ValueError):
    """A demo stage failed; the message names the stage and never includes secrets."""


def stage_error(stage, exc):
    """Keep sanitized project messages; reduce anything unexpected to its type name."""
    if isinstance(exc, (s3_storage.S3StorageError, BaselineError, DemoError)):
        return DemoError(f"{stage} failed: {exc}")
    return DemoError(f"{stage} failed: unexpected {type(exc).__name__}; details suppressed.")


def display_path(path):
    """Show a path relative to the working directory when inside it, so recordings omit home paths."""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(resolved)


def check_run_dir(run_dir):
    """Refuse anything but a new or empty real directory; never touch existing files."""
    run_dir = Path(run_dir)
    try:
        if run_dir.is_symlink():
            raise DemoError("Run directory must not be a symbolic link; choose a fresh ignored directory.")
        if run_dir.exists():
            if not run_dir.is_dir():
                raise DemoError("Run directory path is an existing file; choose a fresh ignored directory.")
            if any(run_dir.iterdir()):
                raise DemoError("Run directory must be new or empty; choose a fresh ignored directory. "
                                "Nothing overwritten.")
    except OSError:
        raise DemoError("Run directory cannot be inspected; choose a fresh ignored directory.") from None
    return run_dir


def run(store, dataset_id, run_dir, *, allow_retrospective_demo=False, vector=None):
    """Download a dataset from S3, train locally, and predict, in fresh subdirectories of ``run_dir``.

    Stages: verified ``download_dataset`` into ``dataset/``, ``train_baseline`` into ``model/`` (the
    model must reference the downloaded dataset ID), ``predict_saved_sample`` into ``predictions/``,
    and an optional hypothetical vector scored with the reloaded model.

    Args:
        store: S3Store with a client attached.
        dataset_id: Dataset ID already uploaded under the store's prefix.
        run_dir: New or empty, non-symlink directory.
        allow_retrospective_demo: Must be True to acknowledge unverified historical availability.
        vector: Optional ``(prior_win_pct_diff, prior_avg_margin_diff, home_field)`` tuple.

    Returns:
        Summary dict with per-stage results (paths relative to the working directory when inside it)
        and the retrospective status flags.

    Raises:
        DemoError: If permission is missing, ``run_dir`` is unusable, or any stage fails; the message
            names the stage and is sanitized.
    """
    if allow_retrospective_demo is not True:
        raise DemoError(RETROSPECTIVE_REQUIRED)
    run_dir = check_run_dir(run_dir)
    dataset_dir, model_dir, prediction_dir = run_dir / "dataset", run_dir / "model", run_dir / "predictions"

    stage = "S3 download"
    try:
        download = store.download_dataset(dataset_id, dataset_dir, allow_retrospective_demo=True)
        stage = "local training"
        metadata, evaluation = train_baseline(dataset_dir, model_dir, allow_retrospective_demo=True)
        if metadata["dataset_id"] != download["dataset_id"]:
            raise DemoError("Trained model does not reference the downloaded dataset.")
        stage = "prediction"
        report = predict_saved_sample(model_dir, dataset_dir, prediction_dir, allow_retrospective_demo=True)
        rows = list(csv.DictReader(io.StringIO(read_file(prediction_dir / "predictions.csv").decode("utf-8"))))
        matchups = [{"game_id": row["game_id"], "home_team": row["home_team"], "away_team": row["away_team"],
                     "home_win_probability": float(row["home_win_probability"]),
                     "away_win_probability": float(row["away_win_probability"])}
                    for row in rows[:SAMPLE_ROWS_SHOWN]]
        hypothetical = None
        if vector is not None:
            model, _ = load_trusted_model(model_dir, allow_retrospective_demo=True)
            hypothetical = predict_vector(model, dict(zip(PREDICTORS, vector, strict=True)))
    except Exception as exc:
        raise stage_error(stage, exc) from None

    return {
        "stages": {
            "1_s3_download": {"s3_location": download["s3_location"], "verified_files": download["verified_files"],
                              "dataset_report_sha256": download["dataset_report_sha256"],
                              "local_copy": display_path(dataset_dir),
                              "method": "downloaded and SHA-256 verified before use; not streamed"},
            "2_local_training": {"model_dir": display_path(model_dir), "trained_on": display_path(dataset_dir),
                                 "dataset_id": metadata["dataset_id"], "counts": metadata["counts"],
                                 "predictors": PREDICTORS,
                                 "holdout_2025": {"model": evaluation["model"],
                                                  "constant_baseline": evaluation["constant_baseline"]}},
            "3_prediction": {"output_dir": display_path(prediction_dir), "count": report["count"],
                             "context": report["prediction_context"], "first_saved_matchups": matchups,
                             "hypothetical_vector": hypothetical},
        },
        **STATUS,
    }


def main(argv=None):
    """Command-line entry point: refuse unsafe inputs before creating an AWS client, then run the chain."""
    defaults = s3_storage.configuration()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-id", required=True, help="SHA-256 dataset ID stored under <prefix>/datasets/")
    parser.add_argument("--run-dir", type=Path, required=True, help="New ignored directory, e.g. data/processed/recording-...")
    parser.add_argument("--bucket", default=defaults["FBS_S3_BUCKET"])
    parser.add_argument("--prefix", default=defaults["FBS_S3_PREFIX"])
    parser.add_argument("--region", default=defaults["FBS_S3_REGION"])
    parser.add_argument("--profile", default=defaults["FBS_AWS_PROFILE"])
    parser.add_argument("--prior-win-pct-diff", type=float)
    parser.add_argument("--prior-avg-margin-diff", type=float)
    parser.add_argument("--home-field", type=float)
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    vector = (args.prior_win_pct_diff, args.prior_avg_margin_diff, args.home_field)
    if all(value is None for value in vector):
        vector = None
    elif any(value is None for value in vector):
        parser.error("A hypothetical vector needs all three: --prior-win-pct-diff, --prior-avg-margin-diff, --home-field.")
    try:
        # Every refusal below happens before any AWS client exists.
        if args.allow_retrospective_demo is not True:
            raise DemoError(RETROSPECTIVE_REQUIRED)
        store = s3_storage.S3Store(None, args.bucket, args.prefix)
        check_run_dir(args.run_dir)
    except (DemoError, s3_storage.S3StorageError) as exc:
        print(f"Error: Refused before contacting AWS: {exc}", file=sys.stderr)
        return 1
    try:
        store.client = s3_storage.make_client(args.region, args.profile)
    except Exception as exc:
        print(f"Error: {stage_error('AWS client', exc)}", file=sys.stderr)
        return 1
    try:
        result = run(store, args.dataset_id, args.run_dir, allow_retrospective_demo=True, vector=vector)
    except DemoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
