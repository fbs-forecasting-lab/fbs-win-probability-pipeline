# FBS Win Probability Pipeline

**REVIEW DRAFT - November 21, 2026.** Two-page core with required tutorial,
license and docstring appendices. Not a final submission or a declaration that
all course requirements are complete.

## Purpose and implemented scope

This UNC Charlotte DTSC 3601/3602 project estimates P(home team wins) for FBS
football using prior-season win-rate difference, prior-season scoring-margin
difference and home-field status. A standardized logistic regression fits only
2022-2024; 2025 is the untouched holdout. API captures, private S3 storage,
Athena/Python feature parity, Lambda training/inference, weekly scoring, private
monitoring and bounded explanation/market comparison have historical AWS evidence.

**Still unresolved:** the syllabus names SageMaker or EC2 training. Lambda has
not been accepted as an exemption; the existing quota request is awaiting AWS
and the professor has been emailed. A locally tested SageMaker candidate is not
cloud execution. Schedules/delivery are disabled. A [public saved monitoring
demonstration](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/) is published separately; it is not current health or
operational approval.

## Install and use - offline reviewer path

Python 3.14.x; pandas, NumPy, SciPy, scikit-learn and supporting libraries are
listed in `requirements.txt`. Work from the repository root. This example needs
no API key, AWS account, private data or project environment file.

```bash
git clone https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline.git
cd fbs-win-probability-pipeline
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B bin/synthetic_demo.py \
  --run-dir data/processed/synthetic-demo --allow-retrospective-demo
```

The example uses 36 fictional games: **18 train, 6 holdout, 6 prediction** rows.
It normalizes, builds features, trains/evaluates, reloads and predicts through the
existing functions. Read `synthetic_summary.json`, `model/evaluation.json` and
`predictions/predictions.csv`. Outputs are ignored. Choose a fresh directory each
time; reruns refuse overwrite. Synthetic metrics demonstrate mechanics only.
Windows uses `py -3.14` and `.venv\Scripts\python.exe`.

## Contributors, contact and evidence labels

Confirmed contributors: **Hampton Abbott, Dharm Patel, Josh Livengood, Sarah
Asianut Okwalinga**. Individual contribution assignments have not been verified.
Contact: [habbott1@charlotte.edu](mailto:habbott1@charlotte.edu).

Historical cloud measurements are dated observations, not new PM-10 runs.
Synthetic examples are entirely fictional. Real saved predictions remain
`retrospective_demo`: historical availability is unknown, predictor-use and
point-in-time forecasting approval remain false, and operational approval is
withheld. Prior-season features omit current roster/form/injury information.
No betting-profit, prospective-performance or market-outperformance claim is made.

[README and repository](https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline),
[requirement checklist](final-readiness.md),
[architecture](architecture.md), [full function guide](major-functions.md).

:::pagebreak
# Classes and major helpers

Every implemented class is named below. The [class reference](class-reference.md)
provides source locations and existing docstrings. Typed failures stop dependent
work rather than permit silent data repair or token replacement.

| Class | Implemented responsibility |
| --- | --- |
| `GamesResponse` | Exact API bytes and request/retrieval metadata. |
| `Snapshot` | Hash-verified raw capture and source metadata. |
| `SeasonInput` | Verified seasonal rows, counts and artifact identities. |
| `OddsResponse` | Captured odds bytes, observation and quota metadata. |
| `S3Store` | Private, immutable raw/dataset transfers and verified downloads. |
| `CloudS3Store` | Exact-key capture-ledger probes and immutable ingestion writes. |
| `PreparationStore` | Selected source, normalized, query and dataset artifact domains. |
| `ModelingStore` | Protected preparation/model reads and separate trainer/inference writes. |
| `WeeklyStore` | Pinned protected references and isolated weekly stages. |
| `MonitorStore` | Private monitoring evidence and reporting/review storage. |
| `InsightsStore` | Isolated explanation/market claims and response checkpoints. |
| `TrainingSpec` | Candidate managed-job resource/input/image/request identity pins. |
| `DatasetError` | Refuses invalid dataset inputs, permission or conflicting output. |
| `NormalizationError` | Refuses snapshot integrity, metadata or output conflicts. |
| `CFBDError` | Sanitized API ingestion failure without credential/body exposure. |
| `S3StorageError` | Sanitized transfer, privacy, configuration or integrity failure. |
| `SnapshotError` | Sanitized raw-response validation/storage failure. |
| `BaselineError` | Invalid dataset/model, failed convergence or artifact validation. |
| `ContractError` | Safe cloud-contract refusal without event/credential contents. |
| `DemoError` | Stage-named integrated S3 demo failure. |
| `RefreshError` | Stage-named weekly refresh failure. |
| `StepFailed` | Stops dependent notebook stages with a short fallback hint. |

| Major function/helper group | Inputs, outputs and validation |
| --- | --- |
| `cfbd.fetch_games`, `storage.save_snapshot` | Explicit request -> original bytes/manifest; validate status/schema; never expose keys. |
| `games.load_snapshot`, `normalize_snapshot` | Manifest/raw -> verified FBS rows, exclusions and quarantine/provenance. |
| `dataset.build_dataset` | Six selected seasons -> six files; prior-year features, chronological splits, hashes/status. |
| `baseline.train_baseline`, `evaluate_probabilities` | Verified dataset -> fitted scaler/logistic model, holdout losses, calibration, artifacts. |
| `load_dataset`, `load_trusted_model` | Verify split, source/runtime/companion hashes before use or deserialization. |
| `predict_saved_sample`, `predict_vector` | Trusted model plus saved rows or valid vector -> complementary probabilities. |
| `S3Store` upload/download methods | Verified raw/dataset transfers; private bucket, no-overwrite and SHA-256 checks. |
| Cloud handlers, `checked_stage`, `publish_stage` | Explicit receipts -> next missing stage/completion; immutable replay, no implicit refit. |
| Managed contract/lineage helpers | Candidate one-job guard and native origin verification; not deployed/compliance proof. |

:::pagebreak
# Tutorial, evaluation and troubleshooting

## 1. Start with fictional data

Run the offline command on page 1. Inspect `dataset/dataset_report.json` for
split counts and five artifact hashes plus the report identity. Inspect the
model metadata/evaluation and saved prediction CSV. Each probability must be
finite, within [0,1], and home plus away must equal one. Do not deserialize a
model downloaded from an arbitrary source. Inspect existing JSON without a fit:

```bash
.venv/bin/python -B -m json.tool \
  data/processed/synthetic-demo/model/evaluation.json
```

## 2. Distinguish the real cloud path

Only after separate workload approval: verify the selected preparation receipt
and all six S3 files, pin request/code/image/runtime, then submit the approved
single-attempt controller. The verified Lambda path uses nine artifacts and its
trainer claim/completion. A future SageMaker result needs its own verified
job/archive/receipt and seven baseline files; matching libraries do not establish
producer trust. Reload independently, require saved CSV equality, then validate a
hypothetical vector. Never retrain during inference or retry an ambiguous fit.

[Cloud modeling runbook](cloud-modeling-runbook.md) and
[managed-job gates](managed-training-readiness.md) supply detailed contracts.
Old workload allowances are exhausted; examples are instructions, not permission.
The API/S3 notebook remains a historical optional workflow. Its history comes
from S3; the `week_refresh` CLI defaults to locally discovered history manifests.

## 3. Read measured evaluation honestly

These are **historical PM-04C AWS results from November 20, 2026**, using 2,194
training and 740 holdout games, not fresh evaluation or rolling performance.

| Metric | Model | Constant training-rate baseline |
| --- | --- | --- |
| Brier (lower better) | 0.21061287148858282 | 0.24163577488303326 |
| Log loss (lower better) | 0.6096025525960278 | 0.6763272181260667 |
| Accuracy (higher better) | 0.6648648648648648 | 0.5918918918918918 |

Brier is squared probability error; log loss penalizes confident errors. Accuracy
uses P(home win) >= 0.5. Ten fixed calibration bins describe counts/observed rates;
empty bins are unavailable, and no calibration model is fitted. Coefficients
are conditional associations, not causal importance. The saved monitoring batch
has 53 pending outcomes and no rolling metrics; this does not mean zero error.
Five of 53 saved rows had paired market comparisons, with no outcome-based skill
or profitability conclusion.

| Problem | Proportionate action |
| --- | --- |
| Existing output or consumed attempt | Preserve it; do not replace evidence or invent a fresh training token. |
| Missing consent, bad hash/source or invalid vector | Stop before use; correct the selected input only after review. |
| Runtime/producer mismatch or unsafe joblib | Stop before deserialization; verify approved native lineage, never rewrite metadata. |
| Ambiguous response or partial completion | Preserve journal/objects; no automatic refetch/refit/resubmission. |
| Pending labels, distribution warning | Report unavailable performance; investigate data/coverage, not automatic retraining. |
| Quota zero or paid-access requirement | Await the existing request/instructor response; no upgrade, substitution or workload. |

:::pagebreak
# License, docstrings and sources

Original project code/documentation use MIT; this grant does not license or
redistribute third-party data, provider responses or restricted course material.
The following is the complete repository license, without omitted clauses.

:::license

## Actual inline docstring excerpts

The following first paragraphs are extracted from source by the offline renderer,
not proposed interfaces. Longer contracts and missing-inline-docstring dispositions
remain in the [class guide](class-reference.md) and
[docstring review](inline-docstring-review.md).

:::docstring src/models/baseline.py load_dataset
:::docstring src/models/baseline.py train_baseline
:::docstring src/models/baseline.py load_trusted_model
:::docstring src/evaluation/metrics.py evaluate_probabilities

## Sources and final assembly

The actual Final Documentation instructions require a PDF, short README,
classes/major helpers with docstrings, tutorials and full license; this draft
keeps the two-page core and appends required detail. The source audit is in
[research references](research-references.md): South & Egros (2020),
Coleman (2025), Gneiting & Raftery (2007), Kapoor & Narayanan (2023; final-text
access limited) and Pedregosa et al. (2011). Bibliography balance, final layout,
SageMaker/EC2 acceptance, genuine review, recurring delivery and release integration
remain open. Earlier coursework/peer reviews remain complete.

Final PDF/code: **December 1, 2026, 10 a.m. Eastern**. Presentation PPTX:
**9 a.m. Eastern**, five-minute hard stop plus one-minute questions.
