# Retrospective Demo Logistic Baseline

This local Initial Demo baseline estimates the probability that the designated
home team wins a retained regular-season FBS–FBS game. It is a reconstructed
historical experiment, not a refreshed live forecast or an approved point-in-time
backtest. All artifacts retain `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`, and
`approved_for_point_in_time_forecasting=false`. Source predictor approval remains
false; unknown availability stays unknown, with no invented publication time.

## Inputs and Feature Rationale

The input is `data/processed/demo-features-v1/`, dataset ID
`8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5`.
Its report SHA-256 is
`b4bb20873d36d6c526ec7ba045a1a82438498d21c581e920316eed95bb54c01f`.
The dataset builder's snapshot selections, source hashes, and row provenance
remain unchanged. The model loader verifies the report's version, demo flags,
identity, exact predictor order, required artifact hashes, split counts/seasons,
unique game IDs, no overlap, finite feature values, and binary labels. Training
and holdout must be nonempty; training must contain both outcomes. Invalid rows
fail the run rather than being dropped or imputed.

Only these columns enter the model, in this order:

| Predictor | Rationale and domain |
| --- | --- |
| `prior_win_pct_diff` | Home minus away previous-season win percentage; a coarse relative-strength summary, restricted to [-1, 1]. |
| `prior_avg_margin_diff` | Home minus away previous-season average scoring margin; a relative point-margin summary, finite numeric values required. |
| `home_field` | 0 for neutral-site games, otherwise 1; a simple home-site indicator. |

Previous-season means use only retained completed regular-season FBS–FBS games
from exactly Y-1, joined by team ID. Scores, labels, completion status, IDs,
sample counts, and provenance are never automatically selected as predictors.
The target label is `home_win` (1 if home points exceed away points, else 0).
Prediction inputs marked uncompleted in the saved snapshot have no invented label.

| Role | Target seasons | Actual rows |
| --- | --- | ---: |
| Fit scaler and model | 2022–2024 | 2,194 |
| Holdout evaluation only | 2025 | 740 |
| Saved-sample inference | 2026 Week 4 | 57 |
| Recording inference (Week 5 rehearsal dataset `b6b7c545…5e65`) | 2026 Week 5 | 51 |

The Week 5 dataset, built by `src.pipeline.week_refresh` on September 24, has
byte-identical train, holdout, and aggregate files, so a model trained on it has
the same coefficients and holdout results. Only its prediction split differs:
51 Week 5 games marked uncompleted in the September 24 snapshot, with North Dakota State–Wyoming (`401864515`) excluded
for missing 2025 FBS history and four games with TBD kickoffs quarantined during
normalization. Dataset `8ecf7cf5…c5c5` remains available as the Week 4 reference
described below. Week 5 is now historical; fetching it again can change
completion status and eligibility and does not reproduce the September snapshot.

Dataset eligibility excluded 43 train, 22 holdout, and 1 prediction targets.
The uncompleted 2024 App State–Liberty game `401640992` has neither a training
label nor a contribution to the prior-season aggregates. Sacramento
State–Massachusetts (`401866429`) lacks qualifying Sacramento State history and
receives no probability. All exclusions are copied unchanged into the model and
batch-output directories. Upstream normalization exclusions/quarantines are
recorded separately in the dataset provenance.

## Fixed Training Procedure

A scikit-learn `Pipeline` contains `StandardScaler` followed by
`LogisticRegression(solver="lbfgs", C=1.0, max_iter=1000, random_state=42)`.
Other parameters use installed defaults, all recorded in model metadata.
Both steps fit exclusively on train.csv. The installed scikit-learn 1.9.0 API
uses `l1_ratio=0.0` by default; the code does not pass the deprecated `penalty`
argument. The scaler saw 2,194 samples. The model converged in 10 iterations;
a convergence warning would fail the run before publication.

No hyperparameter search, class weighting, oversampling, feature selection,
calibration fitting, or alternative model was used. The model stays fitted on
2022–2024 for both evaluation and 2026 inference. It is not refitted on 2025.

## Observed 2025 Holdout Results

The constant comparison predicts the training-label home-win frequency,
**0.5829535095715588**, for every holdout game. It does not use the holdout win
rate. Accuracy predicts a home win when probability **>= 0.5**. Log loss uses
scikit-learn's binary log loss, including its numerical clipping at endpoints.
Lower Brier score and log loss are better; higher accuracy is better.

| Metric | Logistic model | Training-frequency constant |
| --- | ---: | ---: |
| Brier score | 0.2106128715 | 0.2416357749 |
| Log loss | 0.6096025526 | 0.6763272181 |
| Accuracy | 0.6648648649 | 0.5918918919 |

The fixed model improved all three descriptive metrics on these saved holdout
rows. No tuning followed this comparison. These results do not establish live
performance, statistical significance, historical availability, or performance
on teams excluded for missing history.

Descriptive calibration uses ten equal-width bins. Intervals include the lower
edge and exclude the upper edge, except the last includes 1.0. Empty bins have
count 0 and null means/rates. `calibration.json` includes tables for both the
model and constant baseline. The model table from this run is:

| Probability bin | Count | Mean prediction | Observed home-win rate |
| --- | ---: | ---: | ---: |
| [0.0, 0.1) | 2 | 0.080122 | 0.000000 |
| [0.1, 0.2) | 6 | 0.169721 | 0.333333 |
| [0.2, 0.3) | 34 | 0.258127 | 0.235294 |
| [0.3, 0.4) | 72 | 0.359678 | 0.291667 |
| [0.4, 0.5) | 118 | 0.454581 | 0.491525 |
| [0.5, 0.6) | 158 | 0.549126 | 0.506329 |
| [0.6, 0.7) | 154 | 0.649144 | 0.733766 |
| [0.7, 0.8) | 135 | 0.752029 | 0.770370 |
| [0.8, 0.9) | 59 | 0.845292 | 0.847458 |
| [0.9, 1.0] | 2 | 0.934775 | 1.000000 |

This is a diagnostic table, not a fitted calibration procedure or a claim that
the model is well calibrated. Several bins contain very few games.

## Reproduce Locally

Run from the repository root with the existing Python 3.14.x environment and
saved datasets. No credentials or API requests are needed.

Train, evaluate, serialize, and produce holdout and saved-sample probabilities:

```bash
.venv/bin/python -B -m src.models.baseline \
  --dataset-dir data/processed/demo-features-v1 \
  --output-dir data/processed/demo-baseline-v1 \
  --allow-retrospective-demo
```

Reload the trusted local model and predict the verified `prediction.csv` from
that exact dataset directory:

```bash
.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-v1 \
  --dataset-dir data/processed/demo-features-v1 \
  --output-dir data/processed/demo-baseline-reloaded-v1 \
  --allow-retrospective-demo
```

Reload and predict an idealized, **hypothetical** feature vector: a 0.20 advantage
in prior win percentage, a 7-point advantage in prior mean margin, and a
non-neutral home site. This is not a real matchup or an asserted optimal input:

```bash
.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-v1 \
  --prior-win-pct-diff 0.2 \
  --prior-avg-margin-diff 7 \
  --home-field 1 \
  --allow-retrospective-demo
```

Observed output: home **0.662422294285731**, away **0.33757770571426904**.
The single-vector CLI prints JSON identifying the input as hypothetical; it
writes no file. Feature names/order, finite values, and training domains are
validated in inference too. Home probability is selected by class label 1,
not by assuming a fixed probability-array column. Away probability is 1 minus
home probability. Empty prediction batches produce a header-only CSV and count 0.

Only load trusted models generated locally by this project. Joblib uses
pickle-based deserialization and can execute code. Hash checks detect changes;
they do not make an untrusted model safe. The loader verifies all companion
artifact hashes before deserialization and requires the recorded library
versions to match. Keep the model and metadata together; see
[data/README.md](../data/README.md) for file contracts and safe-publication rules.

## Actual Saved 2026 Sample Predictions

These are examples from the saved Week 4 inputs, not refreshed live forecasts.
The home/away designations are those in the source snapshot.

| Game ID | Home | Away | Home probability | Away probability |
| --- | --- | --- | ---: | ---: |
| 401869941 | Coastal Carolina | Liberty | 0.4442311042 | 0.5557688958 |
| 401862779 | Temple | Army | 0.4977009154 | 0.5022990846 |
| 401862778 | UAB | Navy | 0.4007523747 | 0.5992476253 |

## Verification and Limits

Verification on September 23, 2026 used Python 3.14.2, scikit-learn 1.9.0,
NumPy 2.5.2, SciPy 1.18.1, pandas 3.0.5, and joblib 1.6.0. Dependencies were not
changed. Full offline tests:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

All 84 tests passed, including 14 new model/evaluation tests. They cover
training-only scaling, holdout-label isolation, constant-baseline provenance,
hand-calculated metrics, fixed bins, explicit features, invalid inputs, overlap,
convergence failure, serialization, class mapping, hypothetical and empty-batch
inference, and conflicting outputs. Reloaded predictions had maximum absolute
difference **0.0** for all 740 holdout and 57 prediction rows, against tolerance
1e-12. The reloaded batch CSV matched the initial sample CSV byte for byte.
All 36 source/dataset files remained unchanged; all 10 new model/batch artifacts
remain Git-ignored.

Previous-season summaries omit current-season form, roster/coaching changes,
injuries, and other contemporaneous context. Missing history excludes some
teams, so coverage is incomplete and the evaluation population is selected.
The simplistic home indicator and correlated strength summaries are baseline
choices, not established causal effects. There are no uncertainty intervals or
subgroup-performance guarantees.

Historical publication times, source revisions, historical schedule versions,
and actual kickoff/completion times remain unverified. The scheduled-start
chronology check is not availability proof. Future point-in-time forecasting
needs that evidence and an operational cutoff policy; see
[data-leakage-policy.md](data-leakage-policy.md). No live predictive-performance
or leakage-safe-backtesting claim is made.
