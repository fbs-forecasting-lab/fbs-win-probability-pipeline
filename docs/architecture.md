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
than perform their data processing itself. Operational approval and deployed
monitoring remain unfinished; the PM-06 monitoring candidate is described below.
Cloud modeling is
separately verified in PM-04C below. This ingestion adapter alone
does not complete the serverless lifecycle.

## Verified cloud normalization and Athena slice (PM-03D)

`cloud_preparation.handler` selects six explicitly hashed S3 snapshots, verifies
capture lineage when required, and runs existing normalization and the dataset
serializer in Lambda temporary storage. It publishes immutable normalized,
quality, exclusion and provenance artifacts. One injected Athena partition
contains only the selected versions. SQL computes the three Y-1 predictors,
labels and eligibility; all targets must match the Python reference before the
six baseline-compatible files are published. Durable query identity supports
recovery; completed replays verify all bytes. A pinned compatibility record
preserves the original selection across the reviewed whitespace-verification fix.

The Lambda, scoped role, Glue database/table and bounded Athena workgroup are in
`infra/cloud-preparation.yaml`. AWS Linux recovery passed on November 20, 2026:
all six cloud sources were verified, actual Athena results passed parity for
3,065 targets, and the published dataset contains 2,194 train, 740 holdout and
59 prediction rows. Four recovery invocations reused the original successful
query with no new query or CFBD fetch; replay and both refusal checks passed.
The function is enabled at concurrency one in recovery-only mode, with query
creation explicitly denied. New weekly preparation requires deliberate reviewed
configuration/IAM changes and separate authorization. Five full-season cloud
backfills for 2021–2025 are preserved alongside the original 2026 Week 12 capture.
CLI local-history defaults and notebook S3-history behavior above are unchanged. See the
[preparation runbook](cloud-preparation-runbook.md) for scope and refusals.

## Verified cloud modeling slice (PM-04C; November 20, 2026)

`cloud_modeling.training_handler` reads the explicitly pinned preparation
completion and six S3 dataset files, verifies their hashes and reuses the fixed
baseline implementation inside Lambda. Immutable token claims/checkpoints
prevent completed replay or interrupted publication from retraining. Nine model,
evaluation, calibration, interpretation and provenance artifacts precede the
completion receipt. Scaler/model fitting stays train-only; metrics are newly
computed, not copied from historical examples.

`cloud_modeling.inference_handler` independently reloads a trusted published
model after verifying its producer claim, completion hash and all companion
artifacts. It either batch-scores the exact saved prediction split or accepts
three validated hypothetical features through private IAM-authorized invocation.
Only the trainer can write models; inference writes only its result prefix.

Two Python 3.14 x86_64 Lambdas use an S3-backed ZIP under the measured 250 MiB
uncompressed limit after excluding bundled dependency tests/bytecode. There are
no public endpoints or always-running servers. The approved AWS Linux smoke
verified real-data training/evaluation, independent saved-model inference and
immutable replay: one fit, two training and four inference invocations, with
zero CFBD requests or Athena queries. All nine model artifacts were verified;
59 saved predictions matched the training sample. This is a bounded execution,
not an operational forecasting or scheduling system. See the
[verification summary](cloud-modeling-verification.md) for actual metrics and limits.
Ingestion and recovery-only preparation are unchanged. See the
[modeling runbook](cloud-modeling-runbook.md) for exact scope and limitations.

## Boundaries and planned work

PM-05 adds an [AWS-verified weekly workflow](weekly-cloud-runbook.md) as of
November 20, 2026: Standard Step Functions owns bounded cloud stage progress, with a
new Lambda worker and a disabled fixed-request weekly schedule. Explicit capture/
history/model/cutoff identities feed existing normalization and Python feature
building, then trusted saved-model scoring without fitting. Original recovery-only
Athena preparation and exact saved-sample inference remain unchanged. New scoring
provenance is distinct from training provenance; train/holdout/aggregate bytes must
match the original model. Stage receipts and a verified summary preserve replay.
Technical pre-kickoff selection never promotes operational approval: current runs
finish withheld/unapproved. See the [contract](weekly-cloud-contract.md) for cutoff,
revision, stale-input and failure boundaries. No query or automatic training is
introduced. Scoped recovery preserved the original failed execution and added
only raw season listing probes with max-keys one. All physical identities and
predecessors were preserved. The bounded verification used seven executions and
16 worker calls cumulatively, one ingestion invocation/CFBD attempt, zero queries
and zero fits. Week 12 replay produced 59 retrospective predictions, cutoff
equality produced zero, and fresh Week 13 produced 53. Completed replay preserved
bytes/metadata without repeating external work. See the
[verification summary](weekly-cloud-verification.md) for evidence and limits;
operational publication remains withheld and the schedule remains disabled.

The fixed 2026 Week 5 demonstration is historical as of October 2026. September
rehearsal metrics describe saved bytes. A fresh pull can change completion or
kickoff fields and therefore prediction eligibility; it cannot recreate the old
snapshot. No automatic week rollover or complete production forecasting system is implemented.

Prior-season chronology does not prove historical publication availability.
Every dataset/model remains retrospective and unapproved for point-in-time
forecasting. API keys stay outside Git; joblib files must come from trusted
sources. MIT covers original code, not third-party data or restricted material.

## Prepared private monitoring (PM-06; not deployed)

The monitoring adapter verifies an explicit weekly summary, protected model and
training reference. It measures quality and feature distributions, and joins
predictions to explicitly selected later outcomes in an evaluation-only branch.
It reuses existing normalization/provenance and probabilistic metrics; it neither
fits nor reloads/executes the model. Immutable private reports, content-derived
alerts and a separate allowlisted stakeholder draft retain source hashes,
thresholds, sample sizes and pending/insufficient/failed states.

A separate review function appends acknowledgment, investigation and disposition
records bound to an exact alert and prior transition hash. Private IAM invocation
attests the configured human identity; this is not independent human login or
permission to retrain/publish. Report/review roles write only isolated monitoring
domains and cannot invoke predecessors. Existing retrospective flags persist.

The fourteen-resource candidate includes two functions/roles/log groups/async
configs, a disabled failure-event rule and permission, and four alarms with no
actions. Execution-history inspection detects application failure objects even
when Lambda succeeded. Expected withheld processing stays distinct from failure.
Automatic rule activation, notifications and public hosting are excluded.
Offline tests and read-only template/IAM validation have passed; new-handler AWS
Linux execution, deployed replay and later-outcome performance remain unverified.
See the [contract](monitoring-contract.md), [runbook](cloud-monitoring-runbook.md)
and [verification summary](cloud-monitoring-verification.md).

In-season features, The Odds API benchmarking, weather inputs, operational
monitoring/approval and further automation remain future work. See the
[major-function guide](major-functions.md) for contracts and failure conditions.
