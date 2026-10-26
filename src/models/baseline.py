"""Fixed logistic regression for explicitly permitted retrospective demo data."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation.metrics import evaluate_probabilities
from src.features import dataset

PREDICTORS = list(dataset.PREDICTOR_COLUMNS)
MODEL_SETTINGS = {"solver": "lbfgs", "C": 1.0, "max_iter": 1000, "random_state": 42}
DATA_FILES = {"train.csv", "holdout.csv", "prediction.csv", "exclusions.json", "team_season_aggregates.csv"}
STATUS = {"dataset_mode": "retrospective_demo", "historical_availability_verified": False,
          "approved_for_point_in_time_forecasting": False, "approved_for_predictor_use": False}
PREDICTION_COLUMNS = ("game_id", "season", "week", "home_id", "home_team", "away_id", "away_team",
                      "cutoff", "source_snapshot_id", "source_row_index", "historical_availability_status",
                      "historical_available_at", "home_win_probability", "away_win_probability",
                      "prediction_context", *STATUS)


class BaselineError(ValueError):
    """A demo input, model artifact, or output failed validation."""


def require_demo(allowed):
    """Raise BaselineError unless retrospective-demo use was explicitly acknowledged (``allowed is True``)."""
    if allowed is not True:
        raise BaselineError("Pass --allow-retrospective-demo; historical availability is unverified "
                            "and point-in-time forecasting remains unapproved.")


def digest(content):
    """Return the lowercase SHA-256 hex digest of ``content`` bytes."""
    return hashlib.sha256(content).hexdigest()


def read_file(path):
    """Read one artifact's bytes, refusing symbolic links; errors name only the file, never its path."""
    path = Path(path)
    if path.is_symlink():
        raise BaselineError("Symbolic-link artifacts are not supported.")
    try:
        return path.read_bytes()
    except OSError:
        raise BaselineError(f"Required artifact cannot be read: {path.name}") from None


def read_json(content):
    """Parse JSON bytes into a dict, rejecting NaN/Infinity constants and non-object documents."""
    try:
        value = json.loads(content, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise BaselineError("Invalid JSON artifact.") from None
    if not isinstance(value, dict):
        raise BaselineError("Expected a JSON object.")
    return value


def check_status(value):
    """Require ``dataset_mode=retrospective_demo`` and the three availability/approval flags set to False."""
    if not isinstance(value, dict) or any(type(value.get(k)) is not type(v) or value[k] != v
                                          for k, v in STATUS.items()):
        raise BaselineError("Expected retrospective-demo mode and false availability/approval flags.")


def read_csv(content, columns):
    """Parse UTF-8 CSV bytes whose header exactly matches ``columns``; reject malformed or ragged rows."""
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")), strict=True)
        if reader.fieldnames != list(columns):
            raise BaselineError("Unexpected CSV columns/order; use the versioned dataset schema.")
        rows = list(reader)
    except (UnicodeError, csv.Error):
        raise BaselineError("Invalid CSV artifact.") from None
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise BaselineError("Malformed CSV row width.")
    return rows


def feature_frame(rows):
    """Select only the explicit predictors, ignoring outcome and audit columns."""
    try:
        values = [[float(row[name]) for name in PREDICTORS] for row in rows]
    except (KeyError, ValueError, TypeError, OverflowError):
        raise BaselineError("Missing or nonnumeric predictor value.") from None
    frame = pd.DataFrame(values, columns=PREDICTORS, dtype=float)
    validate_features(frame)
    return frame


def validate_features(frame):
    """Check predictor names and order, finite values, win-pct diff in [-1, 1], and home_field in {0, 1}."""
    if not isinstance(frame, pd.DataFrame) or list(frame.columns) != PREDICTORS:
        raise BaselineError("Predictor names/order must match the exact three-column contract.")
    try:
        values = frame.to_numpy(dtype=float)
    except (ValueError, TypeError):
        raise BaselineError("Predictors must be numeric.") from None
    if not np.isfinite(values).all():
        raise BaselineError("Predictors must be finite and nonmissing.")
    if ((values[:, 0] < -1) | (values[:, 0] > 1)).any() or not np.isin(values[:, 2], [0, 1]).all():
        raise BaselineError("Win-percentage differences must be in [-1, 1]; home_field must be 0 or 1.")


def load_dataset(directory, *, allow_retrospective_demo=False):
    """Load and fully verify a six-file retrospective demo dataset.

    Checks the report's schema version, demo flags, predictor contract, identity hash, and every
    artifact's SHA-256, then the split seasons and counts, exclusion reasons, unique game IDs,
    completion status, binary labels, and feature domains before returning anything.

    Args:
        directory: Folder containing dataset_report.json and the five data artifacts.
        allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

    Returns:
        Dict with ``report`` (parsed report), ``report_sha256``, ``artifacts`` (bytes by file name), and
        ``splits`` mapping train/holdout/prediction to ``{"rows", "x", "y"}``: the CSV rows, the
        three-column predictor frame, and the 0/1 labels (``None`` for prediction rows).

    Raises:
        BaselineError: If permission is missing or any file, hash, count, or field fails validation.
    """
    require_demo(allow_retrospective_demo)
    directory = Path(directory)
    # First verify the declared schema and file bytes, before trusting any training rows.
    report_bytes = read_file(directory / "dataset_report.json")
    report = read_json(report_bytes)
    check_status(report)
    if type(report.get("dataset_schema_version")) is not int or report["dataset_schema_version"] != 1:
        raise BaselineError("Unsupported dataset schema version.")
    if report.get("predictor_columns") != PREDICTORS or report.get("allow_retrospective_demo") is not True:
        raise BaselineError("Invalid predictor contract or retrospective permission metadata.")
    hashes = report.get("artifact_sha256")
    if not isinstance(hashes, dict) or set(hashes) != DATA_FILES:
        raise BaselineError("Dataset report must list exactly the five required artifact hashes.")
    artifacts = {name: read_file(directory / name) for name in sorted(DATA_FILES)}
    if any(digest(content) != hashes[name] for name, content in artifacts.items()):
        raise BaselineError("Dataset artifact hash mismatch.")
    try:
        identity = {"schema_version": 1, "sources": report["sources"], "predictor_columns": PREDICTORS,
                    "mode": "retrospective_demo"}
        if digest(dataset._json(identity)) != report["dataset_id"]:
            raise BaselineError("Dataset identity mismatch.")
        if set(report["sources"]) != {str(year) for year in dataset.SEASONS}:
            raise BaselineError("Dataset source seasons do not match the demo contract.")
        for item in report["sources"].values():
            source = item["source"]
            if source["approved_for_predictor_use"] is not False:
                raise BaselineError("Source predictor approval must remain false.")
            availability = source["source_availability"]
            if availability["status"] == "unknown" and availability["available_at"] is not None:
                raise BaselineError("Unknown source availability must have no invented timestamp.")
        # Reports and exclusions must describe the same sources and dataset, not mixed runs.
        exclusions = read_json(artifacts["exclusions.json"])
        check_status(exclusions)
        if exclusions["dataset_id"] != report["dataset_id"] or exclusions["sources"] != report["sources"]:
            raise BaselineError("Exclusion provenance differs from the dataset report.")
        rejected = exclusions["rows"]
        if not isinstance(rejected, list) or any(row["split"] not in dataset.SPLIT_SEASONS for row in rejected):
            raise BaselineError("Invalid exclusion split.")
        aggregates = read_csv(artifacts["team_season_aggregates.csv"], dataset.AGGREGATE_COLUMNS)
        if type(report["aggregate_row_count"]) is not int or len(aggregates) != report["aggregate_row_count"]:
            raise BaselineError("Aggregate row count differs from report.")
        # One shared set detects duplicate game IDs both within a split and across splits.
        splits, seen = {}, set()
        if set(report["splits"]) != set(dataset.SPLIT_SEASONS):
            raise BaselineError("Unexpected dataset splits.")
        for split, seasons in dataset.SPLIT_SEASONS.items():
            label = () if split == "prediction" else ("home_win",)
            columns = (*dataset.TARGET_COLUMNS, *PREDICTORS, *label, *dataset.AUDIT_COLUMNS)
            rows = read_csv(artifacts[f"{split}.csv"], columns)
            counts = report["splits"][split]
            excluded = [row for row in rejected if row["split"] == split]
            if (any(type(counts[k]) is not int or counts[k] < 0 for k in ("input", "output", "excluded"))
                    or counts["target_seasons"] != list(seasons) or counts["output"] != len(rows)
                    or counts["excluded"] != len(excluded) or counts["input"] != len(rows) + len(excluded)):
                raise BaselineError(f"{split} split seasons/counts do not match the report.")
            reasons = Counter(reason for row in excluded for reason in row["reasons"])
            if dict(reasons) != counts["exclusion_reason_counts"]:
                raise BaselineError("Exclusion reason counts do not match.")
            for row in rows:
                if not re.fullmatch(r"[1-9][0-9]*", row["game_id"]):
                    raise BaselineError("Game IDs must be positive integers.")
                if row["game_id"] in seen:
                    raise BaselineError("Duplicate or overlapping game IDs across dataset splits.")
                seen.add(row["game_id"])
                if row["season"] not in {str(year) for year in seasons}:
                    raise BaselineError("Target season outside its split.")
                if row["completed"] != ("false" if split == "prediction" else "true"):
                    raise BaselineError("Target completion status is ineligible for its split.")
                if any(row[k] != (str(v).lower() if type(v) is bool else v) for k, v in STATUS.items()):
                    raise BaselineError("Row availability/approval status changed.")
                if row["feature_source_approved_for_predictor_use"] != "false":
                    raise BaselineError("Feature source approval must remain false.")
                for status, timestamp in (("historical_availability_status", "historical_available_at"),
                                          ("feature_source_availability_status", "feature_source_available_at")):
                    if row[status] == "unknown" and row[timestamp] != "":
                        raise BaselineError("Unknown availability must remain null.")
                if not all(row[k] for k in ("home_id", "home_team", "away_id", "away_team", "cutoff")):
                    raise BaselineError("Missing game identity metadata.")
            # X contains only the three documented predictor columns, never scores or audit fields.
            # Schema membership does not establish historical availability or forecasting approval.
            x = feature_frame(rows)
            y = None
            if split != "prediction":
                if not rows or any(row["home_win"] not in ("0", "1") for row in rows):
                    raise BaselineError("Training/holdout must be nonempty with binary labels.")
                y = np.array([int(row["home_win"]) for row in rows])
                if split == "train" and set(y) != {0, 1}:
                    raise BaselineError("Training requires both outcome classes.")
            splits[split] = {"rows": rows, "x": x, "y": y}
    except (KeyError, TypeError, AttributeError):
        raise BaselineError("Missing or malformed dataset report metadata.") from None
    return {"report": report, "report_sha256": digest(report_bytes), "artifacts": artifacts, "splits": splits}


def home_probabilities(model, frame):
    """Return P(home team wins) per row, using the model's class order and rejecting invalid outputs."""
    validate_features(frame)
    classes = list(model.classes_)
    if len(classes) != 2 or set(classes) != {0, 1}:
        raise BaselineError("Model must have binary classes 0 and 1.")
    if len(frame) == 0:
        return np.array([], dtype=float)
    p = np.asarray(model.predict_proba(frame), dtype=float)
    if (p.shape != (len(frame), 2) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any()
            or not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-12)):
        raise BaselineError("Model emitted invalid probabilities.")
    # The label 1 means a home win; locate its column rather than assuming class-array order.
    return p[:, classes.index(1)]


def prediction_csv(rows, probabilities, context):
    """Serialize rows with home/away win probabilities, a context label, and the unchanged status flags."""
    output = []
    for row, probability in zip(rows, probabilities, strict=True):
        result = {key: row[key] for key in PREDICTION_COLUMNS if key in row and key not in STATUS}
        result.update(home_win_probability=float(probability), away_win_probability=float(1 - probability),
                      prediction_context=context, **STATUS)
        output.append(result)
    return dataset._csv(output, PREDICTION_COLUMNS)


def publish(directory, artifacts):
    """Publish artifacts with the dataset module's no-overwrite rules, raising BaselineError on conflict."""
    try:
        dataset._publish(Path(directory), artifacts)
    except dataset.DatasetError as exc:
        raise BaselineError(str(exc)) from None


def versions():
    """Return the Python and library versions saved in model metadata and required to match on reload."""
    return {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "numpy": np.__version__,
            "scipy": scipy.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}


def train_baseline(dataset_dir, output_dir, *, allow_retrospective_demo=False):
    """Fit the fixed scaler + logistic regression and evaluate it on the 2025 holdout.

    The pipeline is fitted on the 2022–2024 training rows only. Holdout rows are scored, never used
    for fitting, and compared with a constant baseline that always predicts the training home-win
    rate. The saved 2026 prediction rows are also scored. The fitted pipeline is serialized and
    reloaded, and its predictions must be unchanged before anything is published.

    Args:
        dataset_dir: Verified dataset directory (see ``load_dataset``).
        output_dir: New or matching directory for the seven model artifacts.
        allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

    Returns:
        ``(metadata, evaluation)``: the metadata written to model_metadata.json, and the holdout
        evaluation with Brier score, log loss, and accuracy for the model and the constant baseline.

    Raises:
        BaselineError: If the dataset is invalid, the model does not converge, serialization changes
            predictions, or existing output conflicts.
    """
    data = load_dataset(dataset_dir, allow_retrospective_demo=allow_retrospective_demo)
    train, holdout, prediction = (data["splits"][name] for name in ("train", "holdout", "prediction"))
    # Scaler and logistic regression are fitted on training rows only; holdout labels never reach the fit.
    model = Pipeline([("scaler", StandardScaler()), ("logistic", LogisticRegression(**MODEL_SETTINGS))])
    try:
        with warnings.catch_warnings():
            # Nonconvergence becomes an error, so an unconverged model is never published.
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(train["x"], train["y"])
    except ConvergenceWarning:
        raise BaselineError("Logistic regression did not converge; no outputs published. Investigate before retrying.") from None
    # Score the untouched 2025 holdout and a constant baseline (always the training home-win rate).
    holdout_p = home_probabilities(model, holdout["x"])
    prediction_p = home_probabilities(model, prediction["x"])
    rate = float(train["y"].mean())
    model_scores, calibration = evaluate_probabilities(holdout["y"], holdout_p)
    constant_scores, constant_calibration = evaluate_probabilities(holdout["y"], np.full(len(holdout_p), rate))
    # Round-trip the serialized model and require identical predictions before publishing anything.
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=3, protocol=5)
    model_bytes = buffer.getvalue()
    restored = joblib.load(io.BytesIO(model_bytes))  # Bytes just created locally; never untrusted input.
    for split in (holdout, prediction):
        if not np.allclose(home_probabilities(model, split["x"]), home_probabilities(restored, split["x"]),
                           rtol=0, atol=1e-12):
            raise BaselineError("Model serialization changed predictions.")
    evaluation = {**STATUS, "evaluation_seasons": [2025], "count": len(holdout_p),
                  "accuracy_rule": "home win when probability >= 0.5", "constant_training_home_win_rate": rate,
                  "model": model_scores, "constant_baseline": constant_scores,
                  "calibration_description": "Ten fixed equal-width bins; descriptive only, no calibration fitting."}
    artifacts = {
        "model.joblib": model_bytes, "evaluation.json": dataset._json(evaluation),
        "calibration.json": dataset._json({**STATUS, "model": calibration, "constant_baseline": constant_calibration}),
        "holdout_predictions.csv": prediction_csv(holdout["rows"], holdout_p, "saved_2025_holdout"),
        "sample_predictions.csv": prediction_csv(prediction["rows"], prediction_p, "saved_2026_sample_not_live"),
        "exclusions.json": data["artifacts"]["exclusions.json"],
    }
    # Metadata records artifact hashes, settings, and library versions that load_trusted_model checks.
    metadata = {
        "model_schema_version": 1, **STATUS, "dataset_id": data["report"]["dataset_id"],
        "dataset_report_sha256": data["report_sha256"], "dataset_artifact_sha256": data["report"]["artifact_sha256"],
        "predictor_columns": PREDICTORS, "target": "probability the designated home team wins",
        "training_seasons": [2022, 2023, 2024], "holdout_seasons": [2025], "prediction_seasons": [2026],
        "counts": {name: len(split["rows"]) for name, split in data["splits"].items()},
        "pipeline": ["StandardScaler", "LogisticRegression"], "model_settings": model.named_steps["logistic"].get_params(),
        "scaler_settings": model.named_steps["scaler"].get_params(), "class_order": model.classes_.tolist(),
        "versions": versions(), "constant_training_home_win_rate": rate,
        "source_availability": {year: item["source"]["source_availability"] for year, item in data["report"]["sources"].items()},
        "limitations": data["report"]["limitations"] + [
            "Previous-season summaries omit current-season changes; missing histories exclude some teams.",
            "The model remains fitted on 2022–2024; holdout outcomes are never used for fitting or tuning.",
            "2026 outputs describe the saved sample, not refreshed live forecasts.",
        ],
        "reload_max_absolute_tolerance": 1e-12,
        "artifact_sha256": {name: digest(content) for name, content in artifacts.items()},
    }
    artifacts["model_metadata.json"] = dataset._json(metadata)
    publish(output_dir, artifacts)
    return metadata, evaluation


def load_trusted_model(directory, *, allow_retrospective_demo=False):
    """Reload a trusted, locally generated model after verifying its saved artifacts.

    Checks the metadata's demo flags, schema, predictor and class order, and library versions, then
    every artifact's SHA-256, before deserializing model.joblib. The restored pipeline must match the
    recorded structure and settings. Hashes detect changes but do not make an untrusted joblib file
    safe: joblib can execute code, so load only model directories this project created.

    Args:
        directory: Model directory written by ``train_baseline``.
        allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

    Returns:
        ``(model, metadata)``: the restored scikit-learn pipeline and its parsed metadata.

    Raises:
        BaselineError: If permission is missing, versions or hashes do not match, or the model fails
            validation.
    """
    require_demo(allow_retrospective_demo)
    directory = Path(directory)
    metadata = read_json(read_file(directory / "model_metadata.json"))
    check_status(metadata)
    if (type(metadata.get("model_schema_version")) is not int or metadata["model_schema_version"] != 1
            or metadata.get("predictor_columns") != PREDICTORS or metadata.get("class_order") != [0, 1]
            or metadata.get("versions") != versions()):
        raise BaselineError("Unsupported model schema, predictor/class contract, or library versions.")
    names = {"model.joblib", "evaluation.json", "calibration.json", "holdout_predictions.csv",
             "sample_predictions.csv", "exclusions.json"}
    hashes = metadata.get("artifact_sha256")
    if not isinstance(hashes, dict) or set(hashes) != names:
        raise BaselineError("Incomplete model artifact manifest.")
    artifacts = {name: read_file(directory / name) for name in names}
    if any(digest(content) != hashes[name] for name, content in artifacts.items()):
        raise BaselineError("Model artifact hash mismatch; nothing deserialized.")
    try:
        model = joblib.load(io.BytesIO(artifacts["model.joblib"]))
        valid = (type(model) is Pipeline and list(model.named_steps) == ["scaler", "logistic"]
                 and type(model.named_steps["scaler"]) is StandardScaler
                 and type(model.named_steps["logistic"]) is LogisticRegression
                 and list(model.feature_names_in_) == PREDICTORS and list(model.classes_) == metadata["class_order"]
                 and model.named_steps["logistic"].get_params() == metadata["model_settings"]
                 and model.named_steps["scaler"].get_params() == metadata["scaler_settings"])
    except Exception:
        raise BaselineError("Trusted local model could not be restored or validated.") from None
    if not valid:
        raise BaselineError("Restored pipeline does not match its metadata.")
    return model, metadata


def main(argv=None):
    """Command-line entry point: train and evaluate the baseline from --dataset-dir into --output-dir."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        metadata, evaluation = train_baseline(args.dataset_dir, args.output_dir,
                                              allow_retrospective_demo=args.allow_retrospective_demo)
    except (BaselineError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output_dir.resolve()), "counts": metadata["counts"],
                      "evaluation": evaluation}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
