"""Reload a trusted local demo model for saved-sample or hypothetical inference."""

import argparse
import json
from pathlib import Path
import sys

from src.features import dataset
from src.models.baseline import (
    BaselineError, PREDICTORS, STATUS, digest, feature_frame, home_probabilities,
    load_dataset, load_trusted_model, prediction_csv, publish,
)


def predict_vector(model, values):
    if not isinstance(values, dict) or list(values) != PREDICTORS:
        raise BaselineError("Hypothetical feature names/order must match the three predictors exactly.")
    probability = float(home_probabilities(model, feature_frame([values]))[0])
    return {"input_context": "hypothetical feature vector; not a real matchup", "features": values,
            "home_win_probability": probability, "away_win_probability": 1 - probability, **STATUS}


def predict_saved_sample(model_dir, dataset_dir, output_dir, *, allow_retrospective_demo=False):
    model, metadata = load_trusted_model(model_dir, allow_retrospective_demo=allow_retrospective_demo)
    data = load_dataset(dataset_dir, allow_retrospective_demo=allow_retrospective_demo)
    if (data["report_sha256"] != metadata["dataset_report_sha256"]
            or data["report"]["dataset_id"] != metadata["dataset_id"]):
        raise BaselineError("Batch inference must use the saved run's exact verified dataset.")
    split = data["splits"]["prediction"]
    probabilities = home_probabilities(model, split["x"])
    artifacts = {
        "predictions.csv": prediction_csv(split["rows"], probabilities, "saved_2026_sample_not_live"),
        "exclusions.json": data["artifacts"]["exclusions.json"],
    }
    report = {**STATUS, "prediction_context": "saved_2026_sample_not_live", "count": len(probabilities),
              "dataset_id": metadata["dataset_id"], "dataset_report_sha256": data["report_sha256"],
              "model_sha256": metadata["artifact_sha256"]["model.joblib"], "predictor_columns": PREDICTORS,
              "source_availability": metadata["source_availability"], "limitations": metadata["limitations"],
              "artifact_sha256": {name: digest(content) for name, content in artifacts.items()}}
    artifacts["prediction_report.json"] = dataset._json(report)
    publish(output_dir, artifacts)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True, help="Trusted locally generated model directory only")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dataset-dir", type=Path, help="Reads and verifies prediction.csv in this dataset")
    mode.add_argument("--prior-win-pct-diff", type=float)
    parser.add_argument("--prior-avg-margin-diff", type=float)
    parser.add_argument("--home-field", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-retrospective-demo", action="store_true")
    args = parser.parse_args(argv)
    if args.dataset_dir is not None:
        if args.output_dir is None or args.prior_avg_margin_diff is not None or args.home_field is not None:
            parser.error("Batch mode requires --output-dir and does not accept hypothetical feature arguments.")
    elif args.prior_avg_margin_diff is None or args.home_field is None or args.output_dir is not None:
        parser.error("Hypothetical mode requires all three named features and prints to stdout; omit --output-dir.")
    try:
        if args.dataset_dir is not None:
            result = predict_saved_sample(args.model_dir, args.dataset_dir, args.output_dir,
                                          allow_retrospective_demo=args.allow_retrospective_demo)
        else:
            model, _ = load_trusted_model(args.model_dir, allow_retrospective_demo=args.allow_retrospective_demo)
            values = dict(zip(PREDICTORS, (args.prior_win_pct_diff, args.prior_avg_margin_diff, args.home_field)))
            result = predict_vector(model, values)
    except (BaselineError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
