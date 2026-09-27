# Initial Demo Walkthrough — September 29, 2026

## Recommended recording path: notebooks/initial_demo.ipynb

The notebook runs the same pipeline functions as Step 1 and Section 1a below,
one stage per cell, each with a plain-English explanation. Launch it from the
repository root:

```bash
.venv/bin/jupyter lab notebooks/initial_demo.ipynb
```

Before each take, choose **Kernel → Restart Kernel and Clear All Outputs**, then
run the cells top to bottom with **Shift+Enter**. Every run creates a new run tag
and new S3 objects. If a step fails, it prints one short line naming the step;
set `USE_EXISTING_DATASET_ID` in Step 0 (for example, the rehearsal dataset
`b6b7c54503439ecc0ecad5b9d255281d6d6943c9da4013db2dff9eb8ab305e65`), restart, and
run again. Steps 1–5 are then skipped. The command-line steps below remain the
fallback.

Allow about 6–8 minutes for the verified local sequence, plus about 5 minutes
for Step 1 and Section 1a.

Open a terminal in your local clone of the repository (the folder containing
README.md), then run every command from there.

Current for `feature/week-refresh` (base `caa362b`) plus its uncommitted
`src.pipeline.week_refresh` changes, using the existing Python 3.14.x `.venv` and
local artifacts. Step 1 makes one live CFBD request and new S3 uploads; Section 1a
reads from S3 and trains locally. Steps 2–7 are read-only and offline. Both live
commands were rehearsed on September 24, 2026. Open the listed files in your
editor; paths below are relative to the repository root. Keep `.env` and
credentials off screen. Load only this project's trusted local model artifacts;
joblib deserialization can execute code.

Opening note: “This demo connects CFBD ingestion, raw storage, normalized games,
three historical predictors, a baseline model, evaluation, and probabilities.
During this recording we pull the upcoming Week 5 schedule from the API, store it
in S3, download and verify the dataset, train the model locally on that copy, and
predict games that have not been played yet, using prior-season features only.
In-season features are planned next. It is a retrospective demonstration.
Historical availability is unverified, so it is not yet an approved
point-in-time forecasting system.”

## Recording Checklist

| Assignment requirement | Where it is shown |
| --- | --- |
| Show how data is ingested | Step 1 (`week_refresh`: live CFBD request for 2026 Week 5) |
| Show where data is stored | Step 1 raw files and S3 uploads + Section 1a S3 console |
| Explain which features are stored and why | Step 3 |
| Show how data is used to train a model | Section 1a (training on the S3 download) + Step 4 |
| Show predictions on ideal data | Section 1a output (upcoming Week 5 matchups + hypothetical vector) + Steps 6–7 |

Present the predictions of the model trained live in Section 1a. Steps 5–6 read
saved artifacts in `data/processed/demo-baseline-v1` for explanation only; its
holdout results are byte-identical to the model trained in 1a. Steps 3 and 7 use
the September 24 Week 5 rehearsal outputs, which may differ slightly from the
real take.

## 1. Ingest from the API and Store in S3 (~2 minutes)

**Off screen, before recording:**

- Keep `.env`, `~/.aws`, and every credential window off screen. The commands
  read only the nonsecret `FBS_S3_BUCKET`, `FBS_S3_REGION`, and `FBS_S3_PREFIX`
  settings from the ignored `.env` and check that `CFBD_API_KEY` is present;
  no key value is ever printed. AWS credentials come from boto3's standard chain
  and are never typed or shown.
- Before recording, confirm off screen that your AWS access keys work (for
  example, run `aws sts get-caller-identity` off screen). Never show
  `~/.aws/credentials`, `.env`, or key values on screen. If your keys are
  temporary (they include a session token), refresh them before recording.
- Use a fresh `--run-tag` for every take (`week5-take-1`, `week5-take-2`, …;
  `week5-rehearsal-1` is already used). Each take makes exactly one CFBD request
  and writes new S3 objects. The command refuses a run tag whose output
  directories already exist and never overwrites a local file or S3 object.

**Run on screen** (change `take-1` for each take):

```bash
.venv/bin/python -B -m src.pipeline.week_refresh --week 5 \
  --run-tag week5-take-1 --allow-retrospective-demo
```

It runs these stages in order. Each stage appears in the output, and any error
names its stage and exits with code 1:

1. `aws_preflight`: a read-only check that AWS access works and all four Block
   Public Access settings are on, before the CFBD request is spent.
2. `cfbd_fetch`: one College Football Data API request for the 2026
   regular-season Week 5 schedule. The unchanged response and its manifest are
   saved under `data/raw/cfbd/week5-take-1/games/season=2026/`.
3. `s3_upload_raw`: the raw pair is uploaded to
   `initial-demo/raw/cfbd/games/season=2026/` with no-overwrite writes and byte
   readback.
4. `normalize`: the new week and the five fixed 2021–2025 history snapshots are
   normalized under `data/interim/cfbd/week5-take-1/games/`.
5. `build_dataset`: the feature dataset is built in
   `data/processed/week5-take-1-features/` (train 2022–2024, holdout 2025,
   prediction = the Week 5 games).
6. `s3_upload_dataset`: the six dataset files are uploaded to
   `initial-demo/datasets/<dataset_id>/`.

The output ends with the new `dataset_id` and `next_command`, the exact command
for Section 1a.

**Expected output** (September 24 rehearsal, `week5-rehearsal-1`, about 4 seconds;
the real take may differ slightly):

| Output field | Rehearsal value |
| --- | --- |
| `1_cfbd_fetch` | HTTP 200, 59 records, 56 FBS vs. FBS |
| `2_s3_upload_raw.objects` | 2 objects, `uploaded` |
| `3_normalize.new_week_counts` | input 59 / retained 52 / excluded 3 (FBS–FCS) / quarantined 4 (kickoff time TBD) |
| `4_build_dataset.counts` | train 2,194 / holdout 740 / prediction 51 |
| `4_build_dataset.prediction_exclusion_reasons` | `missing_home_history`: 1 (North Dakota State–Wyoming) |
| `5_s3_upload_dataset.objects` | 6 objects, `uploaded` |
| Status flags | `dataset_mode: retrospective_demo`; the other three flags `false` |

Counts can change between takes: if CFBD publishes the four TBD kickoff times
(Mississippi State–Alabama, North Carolina–Notre Dame, Georgia–Vanderbilt, and
Clemson–Miami), those games are retained, up to 55 prediction rows. The snapshot
ID, retrieval time, and dataset ID are new on every pull. Train and holdout rows
never change.

**Files to open** (the command prints the exact paths):

```text
data/raw/cfbd/week5-take-1/games/season=2026/<snapshot_id>.json
data/raw/cfbd/week5-take-1/games/season=2026/<snapshot_id>.manifest.json
data/interim/cfbd/week5-take-1/games/<snapshot_id>/quality_report.json
data/interim/cfbd/week5-take-1/games/<snapshot_id>/exclusions.json
data/processed/week5-take-1-features/prediction.csv
data/processed/week5-take-1-features/dataset_report.json
```

Say: “This is a live request to the College Football Data API for the upcoming
Week 5 schedule. We keep the raw response unchanged, with its retrieval time,
request parameters, and hash, and store it both locally and in our private S3
bucket. Then we build the model dataset and upload it as well. Games without an
announced kickoff time are quarantined rather than guessed, and FBS–FCS games are
excluded. Retrieval time is not historical publication time.”

If the command fails, it names the failing stage. Report the failure and use the
fallback plan in Section 1a; do not describe a failed pull as successful.

**Optional: a stored history snapshot.** The five history seasons are fixed,
previously retrieved snapshots. To show one, open:

```text
data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.json
data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json
```

Verify the stored reference and display its key provenance:

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from src.features.games import load_snapshot
path = Path("data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json")
snapshot = load_snapshot(path)
manifest = json.loads(path.read_bytes())
print("Verified raw hash, record count, and recomputed coverage:", len(snapshot.records))
for key in ("source", "endpoint", "request_parameters", "retrieved_at", "http_status",
            "record_count", "sha256", "source_availability", "approved_for_predictor_use"):
    print(key, manifest[key])
PY
```

Expected: **888 records**, HTTP 200, `year=2025`, `seasonType=regular`,
`classification=fbs`; retrieval `2026-09-23T04:43:15.581843Z`; availability
`unknown`, `available_at=null`, predictor approval false.

## 1a. Recording Core: S3 Download → Local Training → Prediction (~3 minutes)

Run the `next_command` printed by `week_refresh`. It downloads the dataset that
Step 1 just uploaded, trains the fixed model on the downloaded copy, reloads that
new model, and generates predictions for the upcoming Week 5 games on camera.

**S3 console to show:** open the project bucket (`<FBS_S3_BUCKET>`), show the
Permissions tab with all four Block Public Access settings on, then open:

```text
initial-demo/raw/cfbd/games/season=2026/
initial-demo/datasets/<dataset_id printed by week_refresh>/
```

Show the new raw `.json` and `.manifest.json` pair (the snapshot ID printed in
`1_cfbd_fetch`), then the six dataset objects: `train.csv`, `holdout.csv`,
`prediction.csv`, `team_season_aggregates.csv`, `exclusions.json`, and
`dataset_report.json`. The bucket name contains the AWS account ID; crop or blur
it in the recording if you prefer not to show it.

**Run on screen:** copy `next_command` from the `week_refresh` output. For take 1
it has this form:

```bash
.venv/bin/python -B -m src.pipeline.s3_demo \
  --dataset-id <dataset_id printed by week_refresh> \
  --run-dir data/processed/week5-take-1-run \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

**Expected output:** one JSON summary with three stages and the status flags.
These values come from the September 24 rehearsal (dataset
`b6b7c54503439ecc0ecad5b9d255281d6d6943c9da4013db2dff9eb8ab305e65`, about 2
seconds). Counts and matchups may vary slightly by take; the holdout metrics must
match exactly on every take.

| Output field | Expected |
| --- | --- |
| `1_s3_download.s3_location` | `s3://<FBS_S3_BUCKET>/initial-demo/datasets/<dataset_id>/` |
| `1_s3_download.verified_files` | 6 |
| `1_s3_download.dataset_report_sha256` | New on every pull (rehearsal: `f4246f308f062e870ec6f0aa2e4be4ccb415a882cbb1e4bc564736746538b61a`) |
| `1_s3_download.method` | `downloaded and SHA-256 verified before use; not streamed` |
| `2_local_training.counts` | train 2,194 / holdout 740 / prediction 51 (prediction may vary by take) |
| `2_local_training.trained_on` | `data/processed/week5-take-1-run/dataset` |
| Holdout model Brier / log loss / accuracy | 0.21061287148858282 / 0.6096025525960278 / 0.6648648648648648 |
| Constant baseline Brier / log loss / accuracy | 0.24163577488303326 / 0.6763272181260667 / 0.5918918918918918 |
| `3_prediction.count` / `context` | 51 / `saved_2026_sample_not_live` |
| First Week 5 matchups (home probability) | New Mexico State–Western Kentucky 0.4580831843000378; Tulsa–North Texas 0.2777652902323672; Virginia Tech–Pittsburgh 0.35628483220960383 |
| Hypothetical `(0.2, 7, 1)` | home 0.662422294285731 / away 0.33757770571426904 |
| Status flags | `dataset_mode: retrospective_demo`; the other three flags `false` |

The `saved_2026_sample_not_live` context marks predictions made from a saved
snapshot; it does not mean the games have been played. Afterward, open
`data/processed/week5-take-1-run/model/evaluation.json` and
`data/processed/week5-take-1-run/predictions/predictions.csv`.

**What the command does:** the six dataset files are downloaded from S3 and each
one's actual bytes are checked against its SHA-256 before anything uses them. The
existing dataset loader then validates the files, and only then are they written
to `<run-dir>/dataset`. Training reads only that local copy and writes
`<run-dir>/model`; prediction reloads that new model and writes
`<run-dir>/predictions`. Nothing is streamed from S3 into the model, and S3 does
not train or host the model. S3 stores the data; training and inference run
locally. If a download fails its integrity check, the run stops before training
and no model directory is created. Any failure names its stage (AWS client, S3
download, local training, or prediction) and exits with code 1.

Say: “The dataset we just built from the API is downloaded from our private S3
bucket, and every file is verified against SHA-256. The baseline is trained
locally on that verified copy, and the newly trained model predicts the Week 5
games. These games have not been played yet; Week 5 starts October 1. The model
uses prior-season features only; in-season features are planned next. These are
retrospective-demo results from a saved snapshot: historical availability is
unverified, and they are not approved forecasts.”

**Fallback plan:**

- **The CFBD pull fails** (`week_refresh` stops at `cfbd_fetch`): use the
  rehearsal dataset that is already in S3, and say it was pulled on September 24:

  ```bash
  .venv/bin/python -B -m src.pipeline.s3_demo \
    --dataset-id b6b7c54503439ecc0ecad5b9d255281d6d6943c9da4013db2dff9eb8ab305e65 \
    --run-dir data/processed/week5-fallback-take-1 \
    --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
    --allow-retrospective-demo
  ```

- **AWS fails** (`week_refresh` stops at `aws_preflight` or an S3 upload stage):
  use the Week 4 chain below. Describe it as a saved Week 4 sample; its games
  have already been played. It expects 57 predictions, starting with Coastal
  Carolina–Liberty 0.44423110419960504, and the same holdout metrics. This chain
  also reads from S3. If S3 cannot be reached at all, report the blocker and
  continue with the local steps. Do not present local results as a successful S3
  demonstration.

  ```bash
  .venv/bin/python -B -m src.pipeline.s3_demo \
    --dataset-id 8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5 \
    --run-dir data/processed/week4-fallback-take-1 \
    --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
    --allow-retrospective-demo
  ```

- **`s3_demo` fails after a successful upload:** run the three separate existing
  commands with the same dataset ID, in a fresh directory:

```bash
.venv/bin/python -B -m src.ingestion.s3_storage download-dataset \
  --dataset-id <dataset_id printed by week_refresh> \
  --output-dir data/processed/fallback-take-1/dataset --allow-retrospective-demo

.venv/bin/python -B -m src.models.baseline \
  --dataset-dir data/processed/fallback-take-1/dataset \
  --output-dir data/processed/fallback-take-1/model --allow-retrospective-demo

.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/fallback-take-1/model \
  --dataset-dir data/processed/fallback-take-1/dataset \
  --output-dir data/processed/fallback-take-1/predictions --allow-retrospective-demo
```

For the hypothetical vector:

```bash
.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/fallback-take-1/model \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

**Record of the S3 uploads (do not re-run during recording):**

- **September 24, Week 4 reference:** the fixed 2025 raw snapshot pair and the six
  `data/processed/demo-features-v1` files were uploaded with
  `src.ingestion.s3_storage upload-raw` and `upload-dataset` to
  `s3://<FBS_S3_BUCKET>/initial-demo/` in `us-east-1`. Every object reported
  `uploaded` and passed byte readback, and completion markers were written last.
  All four Block Public Access flags were enabled. No IAM, bucket policy, or
  security setting was changed. See
  [data/README.md](../data/README.md#s3-demo-storage-explicit-transfers) for keys,
  permissions, and the byte-level comparison.
- **September 24, Week 5 rehearsal:** `week_refresh` uploaded one new raw pair
  under `initial-demo/raw/cfbd/games/season=2026/` and the six files of dataset
  `b6b7c545…5e65`. Both remain available.

## 2. Show Normalization and Exclusions (~45 seconds)

**Files to open:**

```text
data/interim/cfbd/games/1657e1334c044ff0957e8e246f712d82/games.csv
data/interim/cfbd/games/1657e1334c044ff0957e8e246f712d82/exclusions.json
data/interim/cfbd/games/1657e1334c044ff0957e8e246f712d82/quality_report.json
```

```bash
.venv/bin/python -B - <<'PY'
import csv, json
from pathlib import Path
root = Path("data/interim/cfbd/games/1657e1334c044ff0957e8e246f712d82")
report = json.loads((root / "quality_report.json").read_bytes())
with (root / "games.csv").open(newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == report["counts"]["retained"]
assert all(r["home_classification"] == r["away_classification"] == "fbs" for r in rows)
print(report["counts"])
print("First exclusion:", json.loads((root / "exclusions.json").read_bytes())["excluded"][0])
PY
```

Expected: input **888**, retained **762**, excluded **126**, quarantined **0**.

Say: “An FBS API filter does not guarantee two FBS opponents. These 126 valid
FBS–FCS games are excluded. Invalid records would be quarantined separately,
with reasons and raw-row references; nothing is silently repaired.”

## 3. Show Exactly Three Predictors and an Actual Row (~1 minute)

**Files to open** (September 24 rehearsal outputs; the real take's
`data/processed/week5-take-1-features/` files may differ slightly):
`data/processed/week5-rehearsal-1-features/prediction.csv` and
`data/processed/week5-rehearsal-1-features/team_season_aggregates.csv`.

```bash
.venv/bin/python -B - <<'PY'
import csv
from pathlib import Path
from src.models.baseline import PREDICTORS
with Path("data/processed/week5-rehearsal-1-features/prediction.csv").open(newline="") as handle:
    row = next(r for r in csv.DictReader(handle) if r["game_id"] == "401871049")
print("Upcoming Week 5 matchup:", row["game_id"], row["home_team"], "vs", row["away_team"])
print("Predictors in model order:", {name: float(row[name]) for name in PREDICTORS})
print("Audit only: prior season/counts/cutoff:", row["feature_source_season"],
      row["home_prior_game_count"], row["away_prior_game_count"], row["cutoff"])
PY
```

Expected (rehearsal values): upcoming **New Mexico State–Western Kentucky**, game
**401871049**:

| Predictor, in model order | Value | Rationale |
| --- | ---: | --- |
| `prior_win_pct_diff` | −0.3636363636 | Home minus away previous-season win percentage: coarse relative strength |
| `prior_avg_margin_diff` | −10.4545454545 | Home minus away previous-season average point margin |
| `home_field` | 1 | 0 for neutral sites, otherwise 1 |

Audit fields: source season **2025**, **11 games per team**, cutoff
`2026-10-02T00:00:00Z` (Thursday, October 1, 8:00 p.m. ET). This is the scheduled
kickoff in the saved snapshot; the game has not been played yet.

Say: “Only these three columns enter the model. We join teams by ID and use
completed regular-season FBS–FBS games from exactly Y−1. IDs, scores, completion
status, sample counts, labels, and provenance stay out of predictors. Scheduled
starts establish chronology only, not historical publication or completion time.”

## 4. Explain Training and Holdout (~45 seconds)

**Files to open:** `data/processed/demo-features-v1/dataset_report.json` and
`data/processed/demo-baseline-v1/model_metadata.json`.

```bash
.venv/bin/python -B - <<'PY'
from src.models.baseline import load_dataset
loaded = load_dataset("data/processed/demo-features-v1", allow_retrospective_demo=True)
for name, split in loaded["splits"].items():
    print(name, "rows:", len(split["rows"]), "seasons:", sorted({r["season"] for r in split["rows"]}))
print("Predictors:", loaded["report"]["predictor_columns"])
PY
```

Expected: **train 2,194 / 2022–2024; holdout 740 / 2025;
prediction 57 / 2026** (the Week 4 reference dataset). This command also
validates dataset hashes, schema, counts, feature domains, labels, and disjoint
game IDs. The Week 5 dataset has byte-identical `train.csv` and `holdout.csv`;
only its prediction split differs (51 rows in the rehearsal).

Say: “Both StandardScaler and the fixed logistic regression fit only on
2022–2024. We evaluate on 2025 without tuning or refitting. The same fitted model
serves the saved 2026 inputs. `home_win` is a training/holdout label; prediction
rows have no invented outcome. Dataset exclusions include missing histories and
uncompleted targets, including 2024 game 401640992.”

## 5. Show Saved Evaluation (~1 minute)

**Files to open:** `data/processed/demo-baseline-v1/evaluation.json` and
`data/processed/demo-baseline-v1/calibration.json`.

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from src.models.baseline import load_trusted_model
_, metadata = load_trusted_model("data/processed/demo-baseline-v1", allow_retrospective_demo=True)
print("Verified model/result hashes; fitted training rows:", metadata["counts"]["train"])
print(json.dumps(json.loads(Path("data/processed/demo-baseline-v1/evaluation.json").read_bytes()), indent=2))
PY
```

Expected comparison on **740 holdout games**:

| Metric | Logistic model | Constant baseline |
| --- | ---: | ---: |
| Brier score | 0.210613 | 0.241636 |
| Log loss | 0.609603 | 0.676327 |
| Accuracy | 66.4865% | 59.1892% |

Say: “The constant always predicts the training home-win rate, 0.5829535096.
Lower Brier and log loss are better; accuracy uses home probability ≥ 0.5.
The fixed model improves these descriptive holdout scores. The ten fixed-bin
calibration table is a diagnostic, not calibration fitting or proof that the
model is well calibrated. Empty bins have zero count and null means/rates.”

## 6. Reload and Predict a Hypothetical Vector (~45 seconds)

Run the production prediction CLI; it reloads the existing trusted model and
prints JSON without training or writing outputs:

```bash
.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-v1 \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

Expected: `input_context` explicitly says hypothetical, home probability
**0.662422294285731**, away probability **0.33757770571426904**, and false
point-in-time approval.

Say: “This is an invented feature vector, not a real matchup: a 0.20 prior win
percentage advantage, a 7-point mean-margin advantage, and a home site. The
model gives approximately 66.24% home and 33.76% away; they sum to one.”

## 7. Show Week 5 Predictions and Limits (~1 minute)

**Files to open** (September 24 rehearsal outputs; the real take's
`data/processed/week5-take-1-run/` files may differ slightly):
`data/processed/week5-rehearsal-1-run/predictions/predictions.csv` and
`data/processed/week5-rehearsal-1-features/exclusions.json`.

Read the saved Week 5 predictions and recompute them after model reload, without
rewriting:

```bash
.venv/bin/python -B - <<'PY'
import csv
from pathlib import Path
import numpy as np
from src.models.baseline import load_dataset, load_trusted_model, home_probabilities
run = Path("data/processed/week5-rehearsal-1-run")
model, metadata = load_trusted_model(run / "model", allow_retrospective_demo=True)
data = load_dataset(run / "dataset", allow_retrospective_demo=True)
assert data["report_sha256"] == metadata["dataset_report_sha256"]
with (run / "predictions" / "predictions.csv").open(newline="") as handle:
    rows = list(csv.DictReader(handle))
saved = np.array([float(r["home_win_probability"]) for r in rows])
reloaded = home_probabilities(model, data["splits"]["prediction"]["x"])
np.testing.assert_allclose(saved, reloaded, rtol=0, atol=1e-12)
print("Week 5 rows:", len(rows), "reload max difference:", float(np.max(abs(saved - reloaded))))
for row in rows[:3]:
    print(row["game_id"], row["home_team"], "vs", row["away_team"], row["cutoff"],
          "home:", row["home_win_probability"], "away:", row["away_win_probability"])
PY
```

Expected (rehearsal values): **51 rows**, reload maximum difference **0.0**:

| Game ID | Upcoming Week 5 matchup (home vs. away) | Home | Away |
| --- | --- | ---: | ---: |
| 401871049 | New Mexico State vs. Western Kentucky | 45.8083% | 54.1917% |
| 401862786 | Tulsa vs. North Texas | 27.7765% | 72.2235% |
| 401858245 | Virginia Tech vs. Pittsburgh | 35.6285% | 64.3715% |

Say: “These are upcoming games that have not been played yet; the earliest
kicks off Thursday, October 1. The model uses prior-season 2025 features only,
and in-season features are planned next. North Dakota State–Wyoming, game
401864515, has no qualifying 2025 FBS history for North Dakota State and receives
no invented probability. Four games without announced kickoff times were
quarantined. Previous-season summaries omit current form and roster changes.
Historical versions and availability remain unverified, so these are
retrospective-demo results, not approved forecasts. Serverless orchestration and
monitoring remain future work.”

## Preparation Verification

On September 24, 2026, the expected branch/HEAD and initially clean working tree
were confirmed; no `AGENTS.md` was present. All seven offline step commands above
passed with the stated outputs. The single-vector CLI and saved-sample reload
ran against existing trusted artifacts. All 46 existing data/model artifact
files retained their bytes and modification times. No API request, training,
dataset regeneration, dependency change, or production-code edit was performed.
Only the walkthrough was added during that preparation. The recording-only
ingestion request remains unexecuted; current CFBD credential/network/quota
access is therefore unverified.

S3 extension status, September 24: live upload, readback, download, integrity
validation, local retraining, and reloaded prediction passed on `feature/demo-s3`.
The selected bucket's four Block Public Access flags were enabled. All 105 offline
tests passed. Existing source/data files were preserved; no CFBD request, policy
change, commit, or push was made during this verification. Historical availability
remains unknown and predictor approval remains false.

Recording-core command, September 24, on `main` (base `024eab7`): all 117 offline
tests passed (the 105 existing tests plus 12 for `src.pipeline.s3_demo`). The live,
read-only run into the new `data/processed/recording-verify-1` downloaded and
verified 6 files. It reproduced counts 2,194 / 740 / 57, all six holdout metrics,
and hypothetical home 0.662422294285731 / away 0.33757770571426904 exactly. Its
`model/sample_predictions.csv` and `model/holdout_predictions.csv` are
byte-identical to `data/processed/demo-baseline-v1/` (maximum absolute probability
difference 0.0). No S3 write, CFBD request, or AWS setting change was made.

Follow-up, September 24: after the summary paths were made relative to the
working directory, all 118 offline tests passed. A live, read-only re-check into
the new `data/processed/recording-verify-2` reproduced every value above exactly,
and every printed local path was relative. The Step 1 ingestion command was
rehearsed once into the new `data/raw/cfbd/rehearsal-1/games` directory. It
succeeded with HTTP 200 and 888 records, `retrieved_at`
`2026-09-25T01:24:11.491865Z` (the evening of September 24 in ET). That snapshot
was not normalized or used in any dataset, training, or S3 step. No S3 write or
AWS setting change was made.

Week 5 refresh rehearsal, September 24, on `feature/week-refresh` (base
`caa362b`): all 128 offline tests passed, including the new `aws_preflight`
check.
- `src.pipeline.week_refresh --week 5 --run-tag week5-rehearsal-1` ran in 3.9
  seconds with one CFBD request (HTTP 200, 59 records, `retrieved_at`
  `2026-09-25T02:59:44.466329Z`).
- Normalization retained 52 games, excluded 3 FBS–FCS games, and quarantined 4
  with TBD kickoffs. The build gave train 2,194 / holdout 740 / prediction 51
  (North Dakota State–Wyoming excluded for missing history).
- It uploaded 2 new raw objects and the 6 files of dataset
  `b6b7c54503439ecc0ecad5b9d255281d6d6943c9da4013db2dff9eb8ab305e65`; every
  object reported `uploaded`, and nothing was overwritten.
- The printed `next_command` then ran in 1.8 seconds. It verified 6 downloaded
  files and reproduced all six holdout metrics and the hypothetical probabilities
  exactly.
- `train.csv`, `holdout.csv`, and `team_season_aggregates.csv` are byte-identical
  to `demo-features-v1`, and `holdout_predictions.csv` is byte-identical to
  `demo-baseline-v1`.
- All 59 fetched games were still upcoming at run time; the earliest kicks off
  October 1 at 8:00 p.m. ET.
- No existing local file or S3 object was modified, and no AWS setting was
  changed.
