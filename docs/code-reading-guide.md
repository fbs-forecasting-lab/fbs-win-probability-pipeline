# Reading the pipeline

This guide follows the implemented code from data to a home-team win probability.
Start with the offline example: it runs the same normalization, feature, training,
and prediction functions as the authenticated demonstration without requiring
API keys, AWS access, or private datasets. The command is in the root
[README](../README.md#offline-quickstart-entirely-synthetic-data).

## A useful reading order

| Step | Read this function | What to look for |
| --- | --- | --- |
| 1 | [`bin/synthetic_demo.py`: `run`](../bin/synthetic_demo.py) | The short end-to-end call sequence; fictional fixtures replace API access only. |
| 2 | [`src/features/games.py`: `normalize_snapshot`](../src/features/games.py) | Validate snapshots, keep eligible FBS-versus-FBS games, and record exclusions/quarantines. |
| 3 | [`src/features/dataset.py`: `_aggregate`, then `build_dataset`](../src/features/dataset.py) | Convert each team's prior-season results into matchup features and chronological splits. |
| 4 | [`src/models/baseline.py`: `train_baseline`](../src/models/baseline.py) | Fit the scaler and logistic regression, score untouched holdout rows, and save the model. |
| 5 | [`src/models/baseline.py`: `home_probabilities`](../src/models/baseline.py) and [`src/models/predict.py`: `predict_vector` / `predict_saved_sample`](../src/models/predict.py) | Turn verified features into home/away probabilities using a reloaded model. |
| 6 | [`src/evaluation/metrics.py`: `evaluate_probabilities`](../src/evaluation/metrics.py) | Measure probability error and summarize calibration without fitting a calibrator. |

For each file, read those functions before exploring validation and publication
helpers. [`load_dataset`](../src/models/baseline.py) contains extensive checks
because stored files must agree on hashes, schema, seasons, exclusions, and game
identity before training starts. Those checks validate artifacts; they are not
extra model features or evidence of pre-kickoff source availability. The
[major-function guide](major-functions.md) describes their contracts.

## What the model learns from

Each retained matchup has exactly three predictors, in this order:

1. `prior_win_pct_diff`: home minus away previous-season win percentage.
2. `prior_avg_margin_diff`: home minus away previous-season average scoring margin.
3. `home_field`: 0 for a neutral site and 1 otherwise.

For example, a hypothetical home team with prior win percentage 0.75 versus 0.50
and prior average margin 10 versus 3 has the vector `(0.25, 7, 1)` at a non-neutral
site. This illustrates the definitions; it is not a claimed row from either dataset.

`_aggregate` counts every completed game from both teams' perspectives. A
seven-point win contributes margin +7 to the winner and -7 to the loser. For a
target in season Y, `build_dataset` joins the summaries from exactly Y-1 by team
ID. Missing history excludes a matchup instead of inventing values.

The target label is `home_win`: 1 if the designated home team won, otherwise 0.
Same-game final scores create that label only. Although scores and audit fields
are retained in the dataset for traceability, `feature_frame` selects only the
three predictor names above for the model.

| Role | Target seasons | Offline synthetic rows |
| --- | --- | ---: |
| Prior history only | 2021 | 6 games; not training targets |
| Fit scaler and classifier | 2022-2024 | 18 |
| Evaluate without fitting or tuning | 2025 | 6 |
| Score saved uncompleted matchups | 2026 | 6 |

The offline example generates 36 fictional games in total. The real CFBD
demonstration uses the same split years and feature definitions but different
data and counts; its saved evidence is in the [model card](model-card.md).
Synthetic metrics test pipeline behavior and do not estimate football forecasting
skill. The 2026 rows are saved demonstration inputs, not a live schedule.

## How the probability is calculated

The fitted scikit-learn pipeline first standardizes each feature using the
training mean and scale. Logistic regression learns an intercept and one weight
per standardized feature from the training labels. Conceptually, prediction is:

```text
scaled_feature[j] = (feature[j] - training_mean[j]) / training_scale[j]
score = intercept + sum(weight[j] * scaled_feature[j])
P(home win) = 1 / (1 + exp(-score))
P(away win) = 1 - P(home win)
```

For a constant training feature, StandardScaler uses scale 1 rather than dividing
by zero. Both scaling parameters and classifier weights are fitted on 2022-2024
rows only. A saved model applies those same parameters at inference; it does not
refit on the holdout or on a new matchup.

`home_probabilities` locates class label 1 in the model's class array. The score
of a hypothetical vector depends on the fitted model; the code does not hard-code
a probability for that vector. A probability of 0.67 means an estimated 67%
chance of a home win under the fitted model, not a predicted point total. The
0.5 threshold is used only when calculating classification accuracy.

## How the result is evaluated

The comparison baseline always predicts the home-win frequency in the training
labels. It does not use the holdout win rate. The model and this constant baseline
are evaluated on the same 2025 holdout rows:

- Brier score measures squared probability error; lower is better.
- Log loss penalizes incorrect confident probabilities; lower is better.
- Accuracy uses a home-win decision at probability 0.5 or higher; higher is better.
- Calibration bins compare average probabilities with observed home-win rates.
  They are descriptive diagnostics, not a fitted calibration step or proof of
  good calibration, especially with six synthetic holdout games.

The tests in [`test_baseline.py`](../tests/test_baseline.py) check that changing
holdout labels cannot change fitted weights or predictions, that the constant
baseline uses training labels, and that model reloads preserve probabilities.
[`test_dataset.py`](../tests/test_dataset.py) checks feature construction and
time splits. These tests provide concrete examples for following the contracts.

## Where the demonstration stops

Hashes establish byte integrity, and prior-season ordering establishes chronology.
Neither proves when a historical source value was published or available.
All current datasets and models remain `retrospective_demo` with forecasting
approval false. The [leakage policy](data-leakage-policy.md) explains this limit.

Training and inference run locally. S3 stores and transfers private data;
`week_refresh` and `s3_demo` orchestrate those operations. Monitoring, sportsbook
comparison, serverless deployment, and operational forecasting are future work.
The public reading/running path above does not require those future components.
