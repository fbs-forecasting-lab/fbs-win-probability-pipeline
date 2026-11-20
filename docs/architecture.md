# Architecture

## Implemented flow

```text
CFBD response + manifest (or offline synthetic fixture)
    -> validate bytes, normalize each snapshot
    -> prior-season team aggregates and chronological dataset
    -> StandardScaler + LogisticRegression fitted on training rows
    -> held-out evaluation and saved-model prediction
```

`src/ingestion/cfbd.py` fetches regular-season FBS games. `storage.py` preserves
response bytes and a manifest receipt. `src/features/games.py` verifies hashes
and metadata, normalizes valid FBS-vs-FBS rows, excludes other classifications,
and quarantines invalid rows such as TBD kickoffs. Raw data is not repaired.

`src/features/dataset.py` requires one snapshot per season 2021–2026. It builds
prior-season win percentage and scoring-margin differences plus home-field
status. Training uses 2022–2024; holdout uses 2025; prediction uses eligible,
uncompleted rows in the saved 2026 snapshot. 2021 supplies history only. Missing
prior histories are excluded. Dataset identity includes source hashes and
metadata, so a new pull changes identity even when game content is unchanged.

`src/models/baseline.py` verifies dataset artifacts and fits the scaler and
logistic regression on training rows only. `src/evaluation/metrics.py` computes
Brier score, log loss, accuracy, and descriptive calibration bins for the model
and the constant training home-win rate. `src/models/predict.py` reloads a trusted
model for matching saved-dataset or hypothetical-vector predictions.

## Storage and orchestration

Local generated data lives in ignored `data/raw/`, `data/interim/`, and
`data/processed/` directories. Manifests, reports, and SHA-256 checks connect
inputs to outputs. Conflicting outputs are refused; some stage functions accept
identical existing artifacts. The offline example applies a stricter rule:
its entire output directory must be new, including after a partial failure.

`S3Store` transfers raw snapshot/manifest pairs and six-file datasets to a private
bucket. All four Block Public Access settings must be enabled. Uploads refuse
conflicting objects and reuse identical ones; downloads verify integrity before
publishing locally. No model training happens in S3.

- `week_refresh.run`: private-bucket preflight, fetch/save, raw upload,
  normalization, dataset build, dataset upload. The CLI's default history is
  discovered **locally** from `data/processed/demo-features-v1/dataset_report.json`
  and verified against the corresponding local 2021–2025 manifests.
- `week_refresh.download_history`: downloads the reference dataset report and
  history snapshots **from S3**, then verifies the five manifests against that
  report. The notebook uses this path, so it does not need local raw history.
- `s3_demo.run`: verified S3 dataset download, local training, saved-sample
  prediction, optional hypothetical prediction.
- `notebooks/initial_demo.ipynb`: exposes these functions as explanatory cells;
  selecting an existing S3 dataset skips ingestion/build/upload stages.
- `bin/synthetic_demo.py`: generates fictional fixtures and runs the local core
  with no credentials or network. It does not emulate S3 or duplicate the model.

## Verified cloud ingestion slice (PM-02C)

`src/pipeline/cloud_ingestion.py` is a thin Lambda adapter around the existing
fetch/save/raw-upload functions. It obtains one API key through the execution
role from Secrets Manager, uses cloud-local temporary files, and records an
immutable S3 claim/capture/completion ledger. Same-token retries never refetch;
recovery publishes only the original checkpoint. See the
[deployment and recovery runbook](cloud-ingestion-runbook.md).

The Python 3.14 Lambda, scoped role, bounded logs and retry configuration are
defined in `infra/cloud-ingestion.yaml`. This ingestion slice was **deployed and
verified in AWS on November 20, 2026**: 70 records captured, identical replay,
conflict rejection, and one CFBD attempt across three invocations. See the
[sanitized verification summary](cloud-ingestion-verification.md). No automatic schedule exists. S3 remains the existing private data
store, and the existing local notebook/CLIs remain retrospective demonstrations.
The notebook's graded cloud path will need to initiate cloud operations rather
than perform their data processing itself. Athena transformations, cloud model
training/inference, operational eligibility, alerts and monitoring are still
unimplemented; this adapter alone does not complete the serverless lifecycle.

## Boundaries and planned work

The fixed 2026 Week 5 demonstration is historical as of October 2026. September
rehearsal metrics describe saved bytes. A fresh pull can change completion or
kickoff fields and therefore prediction eligibility; it cannot recreate the old
snapshot. No automatic week rollover or production deployment is implemented.

Prior-season chronology does not prove historical publication availability.
Every dataset/model remains retrospective and unapproved for point-in-time
forecasting. API keys stay outside Git; joblib files must come from trusted
sources. MIT covers original code, not third-party data or restricted material.

In-season features, The Odds API benchmarking, weather inputs, drift monitoring,
and serverless automation remain future work. See the
[major-function guide](major-functions.md) for contracts and failure conditions.
