# FBS Win Probability Pipeline

A UNC Charlotte DTSC 3601/3602 project by the FBS Forecasting Lab team.

- Hampton Abbott
- Dharm Patel
- Josh Livengood
- Sarah Asianut Okwalinga

The project estimates the probability that the designated home team wins an
FBS college-football game.

Implemented: versioned game snapshots, SHA-256 integrity checks, normalization,
prior-season features, chronological dataset splits, logistic regression,
holdout evaluation against a constant home-win-rate baseline, saved-model
prediction, and explicit private-S3 transfers. Training runs locally. The
notebook and command-line workflows reuse the same functions.

This is a **retrospective demonstration, not an approved live forecast**.
Historical publication times have not been verified. In-season features,
sportsbook benchmarking, drift monitoring, and serverless deployment remain
planned rather than implemented.

## Install

Use **Python 3.14.x**. Direct dependencies are NumPy, pandas, SciPy,
scikit-learn, matplotlib, Jupyter, requests, python-dotenv, and boto3; exact
versions are in [requirements.txt](requirements.txt). The offline example uses
the same environment as the project. Installing packages requires internet
access; running the example does not.

From a terminal on macOS/Linux:

```bash
git clone https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline.git
cd fbs-win-probability-pipeline
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On Windows, create the environment with `py -3.14 -m venv .venv` and replace
`.venv/bin/python` with `.venv\Scripts\python.exe` in the commands below.

## Offline quickstart: entirely synthetic data

Run from the repository root. No `.env`, API key, AWS configuration, private
archive, or downloaded dataset is needed:

```bash
.venv/bin/python -B bin/synthetic_demo.py --run-dir data/processed/synthetic-demo --allow-retrospective-demo
```

The [example](bin/synthetic_demo.py) creates **36 deterministic fictional games**
for four fictional teams. Six 2021 games supply the first prior-season features;
2022–2024 provide **18 training rows**, 2025 provides **6 holdout rows**, and
2026 provides **6 saved prediction rows**. All teams, scores, dates, and metrics
in this example are synthetic. They measure pipeline behavior, not football
forecasting skill. The manifest's CFBD source/endpoint/HTTP fields simulate the
existing input schema; they are not evidence of a network request. Every source
carries a synthetic notice that is retained in downstream provenance.

The command normalizes snapshots, builds features, trains and evaluates the
existing model, reloads it, and predicts the saved sample and a hypothetical
vector. It prints a labeled JSON summary with split counts, synthetic Brier
score/log loss/accuracy for both models, and complementary home/away
probabilities. Exact numerical results can depend on library versions.

Generated outputs stay beneath the ignored `data/processed/synthetic-demo/`:

| Path | Contents |
| --- | --- |
| `SYNTHETIC.txt`, `synthetic_summary.json` | Synthetic-data notice and run summary |
| `raw/season=YYYY/` | Six fictional games and a hash-verified manifest per season |
| `normalized/<snapshot_id>/` | `games.csv`, `exclusions.json`, `quality_report.json` |
| `dataset/` | `train.csv`, `holdout.csv`, `prediction.csv`, `team_season_aggregates.csv`, `exclusions.json`, `dataset_report.json` |
| `model/` | `model.joblib`, `model_metadata.json`, `evaluation.json`, `calibration.json`, `holdout_predictions.csv`, `sample_predictions.csv`, `exclusions.json` |
| `predictions/` | `predictions.csv`, `prediction_report.json`, `exclusions.json` |

**Rerunning with the same directory fails without overwriting it.** Choose a new
name beneath `data/processed/`, such as `synthetic-demo-2`, for another run. A
failed partial run is also preserved. No cleanup or deletion is required.

## Tests

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests use synthetic fixtures and fake services, block network calls, and check
integrity, chronology, refusals, model loading, prediction, and output rendering.
The example tests also check deterministic datasets, finite complementary
probabilities, and preservation of prior output bytes and modification times.

## Optional authenticated API/S3 demonstration

The [Initial Demo notebook](notebooks/initial_demo.ipynb) and
[walkthrough](docs/initial-demo-walkthrough.md) preserve the real API/S3 workflow.
They require separately configured CFBD access and private-bucket AWS access;
keep credentials and `.env` off screen and out of Git. No raw CFBD responses or
private datasets are included; documentation retains selected historical results.

```bash
.venv/bin/jupyter lab notebooks/initial_demo.ipynb
```

The notebook reads its 2021–2025 history from S3. The `week_refresh` CLI defaults
to local history manifests discovered from a local reference dataset report;
see [major functions](docs/major-functions.md) and
[teammate setup](docs/teammate-setup.md). `s3_demo` downloads and verifies a dataset,
then trains and predicts locally; S3 neither trains nor hosts the model.

**2026 Week 5 is now a historical sample.** September 24 rehearsal counts and
metrics describe that saved snapshot, not today's schedule. Fetching the same
week again may return completed games or corrected kickoff times, changing
eligibility, counts, dataset identity, and results. It does not recreate the
September snapshot. Use an existing saved dataset to reproduce that evidence;
this repository does not automatically roll forward to a new forecast week.

## Design, limitations, and navigation

The three predictors are prior-season home-minus-away win percentage,
prior-season home-minus-away average scoring margin, and home-field status.
Target-game final scores are labels only, never predictor inputs. The scaler and logistic
regression fit only 2022–2024; 2025 is held out. Missing prior histories exclude
matchups, and unknown kickoff times are set aside. The fixed seasons and simple
features are deliberate demo constraints.

All runs retain `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`,
`approved_for_point_in_time_forecasting=false`, and
`approved_for_predictor_use=false`. `--allow-retrospective-demo` explicitly
acknowledges those limits. Load only trusted locally generated model artifacts:
`joblib` deserialization can execute code, and a hash alone does not establish
who created a file.

- [Runnable examples](bin/README.md)
- [Architecture](docs/architecture.md) and [major-function guide](docs/major-functions.md)
- [Data dictionary](docs/data-dictionary.md) and [leakage policy](docs/data-leakage-policy.md)
- [Model card](docs/model-card.md) and [storage guidance](data/README.md)
- `src/`: ingestion, features, models, evaluation, orchestration; `src/monitoring/` is a placeholder
- `tests/`: offline verification; `notebooks/`: the real demonstration

## License and contact

Original project code and documentation are available under the [MIT License](LICENSE).
Copyright is credited to Hampton Abbott and the FBS Forecasting Lab project
contributors. This grant does **not** license third-party data, API responses,
restricted course/reference material, or dependencies, which retain their own
terms. Obtain data through authorized access; do not redistribute CFBD data.
The offline example generates fictional data locally.

Contact: **Hampton Abbott**, [securehabits@proton.me](mailto:securehabits@proton.me).
