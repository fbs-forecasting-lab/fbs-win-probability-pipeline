# Initial Demo Walkthrough — September 29, 2026

Allow about 6–8 minutes for the verified local sequence, plus 2–3 minutes for
the verified S3 segment. Run commands from the repository root:

```bash
cd /Users/hampton/Development/Projects/fbs-win-probability-pipeline
```

Prepared against `feature/demo-baseline` at
`b3d10524159f9dcff11944090d834f6548357971`, using the existing Python 3.14.x
`.venv` and local artifacts. The original seven steps are read-only/offline except
for the marked recording ingestion command. The added S3 segment below requires
AWS access and includes a separate local training run. It was live-verified on
September 24, 2026 on `feature/demo-s3`. Open the
listed files in your editor; paths below are relative to the repository root.
Keep `.env` and credentials off screen. Load only this project's trusted local
model artifacts; joblib deserialization can execute code.

Opening note: “This demo connects CFBD ingestion, raw storage, normalized games,
three historical predictors, a baseline model, evaluation, and probabilities.
Training and inference run locally; the S3 extension stores and retrieves data.
It is a retrospective demonstration. Historical availability is unverified,
so it is not yet an approved point-in-time forecasting system.”

## 1. Ingest and Show Raw Provenance (~1 minute)

**Recording only — not run during preparation.** With the locally configured
CFBD key, run one regular-season request into a separate recording directory:

```bash
.venv/bin/python -B -m src.ingestion.cfbd --season 2025 \
  --output-dir data/raw/cfbd/recording/games
```

Expected on success: `Raw snapshot: ...`, `Manifest: ...`, `Stored N records`,
and coverage JSON. Open the two exact paths printed by the CLI:

```text
data/raw/cfbd/recording/games/season=2025/<new_snapshot_id>.json
data/raw/cfbd/recording/games/season=2025/<new_snapshot_id>.manifest.json
```

`N`, retrieval time, hash, and snapshot ID come from that actual request; do not
promise they match the older snapshot. If access fails, report the failure and
continue with the stored reference below, clearly identifying it as previously
retrieved. The live ingestion command has not been verified during this
preparation. Do not pass its new manifest into normalization, dataset building,
or training for this walkthrough. The fixed inputs and saved model remain intact.

**Offline reference files to open:**

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

Say: “We retain the response fields unchanged and record retrieval time, request
parameters, count, and hash. Retrieval time is not historical publication time.
Scores and completion status are stored evidence, not same-game predictors.”

## 1a. S3 Storage and Verified Download (Verified September 24)

**Prerequisite:** explicitly select an existing private project bucket, its
region, and a project prefix. Set `FBS_S3_BUCKET`, `FBS_S3_REGION`, and
`FBS_S3_PREFIX` in the environment or ignored `.env`; optionally set
`FBS_AWS_PROFILE`. Authentication uses the existing AWS profile/SSO/temporary
credential chain, never keys shown on screen. All four bucket-level Block Public
Access settings must already be enabled. See [data/README.md](../data/README.md#s3-demo-storage-explicit-transfers)
for permissions and setup. The user created and selected this bucket; these
nonsecret settings are saved in the ignored local `.env`:

```text
FBS_S3_BUCKET=fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an
FBS_S3_REGION=us-east-1
FBS_S3_PREFIX=initial-demo
```

The existing CFBD key was preserved. All four Block Public Access flags were
verified enabled. No IAM or bucket policy/security settings were changed.

Use the fixed 2025 snapshot below, not a fresh recording snapshot. These are
**live AWS commands that passed verification** with the configuration above:

```bash
.venv/bin/python -B -m src.ingestion.s3_storage upload-raw \
  --manifest data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json

.venv/bin/python -B -m src.ingestion.s3_storage upload-dataset \
  --dataset-dir data/processed/demo-features-v1 --allow-retrospective-demo

.venv/bin/python -B -m src.ingestion.s3_storage download-dataset \
  --dataset-id 8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5 \
  --output-dir data/processed/demo-features-from-s3-v1 --allow-retrospective-demo
```

Observed: both raw files and all six dataset files reported `uploaded`, with
successful byte readback. The download reported `verified_files: 6` and
`data/processed/demo-features-from-s3-v1`. In the S3 console, open
`fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an`,
confirm Block Public Access, then open:

```text
initial-demo/raw/cfbd/games/season=2025/
initial-demo/datasets/8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5/
```

Show the raw `.json` and `.manifest.json` objects. Then show `train.csv`,
`holdout.csv`, `prediction.csv`, `team_season_aggregates.csv`, `exclusions.json`,
and `dataset_report.json` in the dataset prefix. Verified S3 locations:

```text
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.json
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/datasets/8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5/
```

Say: “S3 provides private object storage. We preserve source identity and upload
data before its completion marker. Conditional writes prevent replacement.
Downloads are verified from actual bytes against SHA-256, not ETags. Cloud
storage does not establish historical availability.”

After the download, compare all six files without changing the originals:

```bash
.venv/bin/python -B - <<'PY'
from pathlib import Path
from hashlib import sha256
from src.models.baseline import load_dataset
old = Path("data/processed/demo-features-v1")
new = Path("data/processed/demo-features-from-s3-v1")
verified = load_dataset(new, allow_retrospective_demo=True)
names = sorted(verified["artifacts"]) + ["dataset_report.json"]
for name in names:
    original = (old / name).read_bytes()
    downloaded = (new / name).read_bytes()
    assert original == downloaded, name
    assert sha256(original).hexdigest() == sha256(downloaded).hexdigest(), name
print("All six downloaded files match the originals byte for byte and by SHA-256.")
PY

.venv/bin/python -B -m src.models.baseline \
  --dataset-dir data/processed/demo-features-from-s3-v1 \
  --output-dir data/processed/demo-baseline-from-s3-v1 --allow-retrospective-demo

.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-from-s3-v1 \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

Verified results from the S3 download: 2,194 training / 740 holdout / 57 sample
rows. The six downloaded SHA-256 hashes equal the originals; the existing loader
also validated the downloaded dataset. Its report SHA-256 is
`b4bb20873d36d6c526ec7ba045a1a82438498d21c581e920316eed95bb54c01f`.

| 2025 holdout metric | Local model trained from S3 download | Constant baseline |
| --- | ---: | ---: |
| Brier score | 0.21061287148858282 | 0.24163577488303326 |
| Log loss | 0.6096025525960278 | 0.6763272181260667 |
| Accuracy | 0.6648648648648648 | 0.5918918918918918 |

All six metrics matched the original local run exactly. Both probabilities for
all 740 holdout games and all 57 sample games matched with maximum absolute
difference **0.0** (tolerance `1e-12`). The reloaded model's hypothetical vector
`(0.2, 7, 1)` returned home **0.662422294285731** and away
**0.33757770571426904**, also equal to the original. This is not an actual matchup.
The exact comparison command is in
[data/README.md](../data/README.md#local-model-verification-after-a-real-download).

**Files to open:** `data/processed/demo-baseline-from-s3-v1/evaluation.json`,
`model_metadata.json`, `holdout_predictions.csv`, and `sample_predictions.csv`
in the same directory. The downloaded dataset and new local model outputs are
Git-ignored; original datasets and model artifacts were preserved.

Say: “The downloaded dataset feeds the same local training and prediction code.
S3 stores the data; it does not train or host this model. We use a separate model
output directory and preserve the original evaluation.” If cloud access is
blocked, report the blocker and continue the local sequence; do not describe
mocked tests or original local results as a successful S3 demonstration.

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

**Files to open:** `data/processed/demo-features-v1/prediction.csv` and
`data/processed/demo-features-v1/team_season_aggregates.csv`.

```bash
.venv/bin/python -B - <<'PY'
import csv
from pathlib import Path
from src.models.baseline import PREDICTORS
with Path("data/processed/demo-features-v1/prediction.csv").open(newline="") as handle:
    row = next(r for r in csv.DictReader(handle) if r["game_id"] == "401869941")
print("Actual saved matchup:", row["game_id"], row["home_team"], "vs", row["away_team"])
print("Predictors in model order:", {name: float(row[name]) for name in PREDICTORS})
print("Audit only: prior season/counts/cutoff:", row["feature_source_season"],
      row["home_prior_game_count"], row["away_prior_game_count"], row["cutoff"])
PY
```

Expected: actual saved **Coastal Carolina–Liberty**, game **401869941**:

| Predictor, in model order | Value | Rationale |
| --- | ---: | --- |
| `prior_win_pct_diff` | 0.1818181818 | Home minus away previous-season win percentage: coarse relative strength |
| `prior_avg_margin_diff` | −10.3636363636 | Home minus away previous-season average point margin |
| `home_field` | 1 | 0 for neutral sites, otherwise 1 |

Audit fields: source season **2025**, **11 games per team**, cutoff
`2026-09-24T23:30:00Z`. This is the scheduled kickoff in the saved snapshot.

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
prediction 57 / 2026**. This command also validates dataset hashes, schema,
counts, feature domains, labels, and disjoint game IDs.

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

## 7. Show Saved-Sample Predictions and Limits (~1 minute)

**Files to open:** `data/processed/demo-baseline-v1/sample_predictions.csv` and
`data/processed/demo-baseline-v1/exclusions.json`.

Read saved predictions and recompute them after model reload, without rewriting:

```bash
.venv/bin/python -B - <<'PY'
import csv
from pathlib import Path
import numpy as np
from src.models.baseline import load_dataset, load_trusted_model, home_probabilities
model, metadata = load_trusted_model("data/processed/demo-baseline-v1", allow_retrospective_demo=True)
data = load_dataset("data/processed/demo-features-v1", allow_retrospective_demo=True)
assert data["report_sha256"] == metadata["dataset_report_sha256"]
with Path("data/processed/demo-baseline-v1/sample_predictions.csv").open(newline="") as handle:
    rows = list(csv.DictReader(handle))
saved = np.array([float(r["home_win_probability"]) for r in rows])
reloaded = home_probabilities(model, data["splits"]["prediction"]["x"])
np.testing.assert_allclose(saved, reloaded, rtol=0, atol=1e-12)
print("Saved 2026 sample rows:", len(rows), "reload max difference:", float(np.max(abs(saved - reloaded))))
for row in rows[:3]:
    print(row["game_id"], row["home_team"], "vs", row["away_team"],
          "home:", row["home_win_probability"], "away:", row["away_win_probability"])
PY
```

Expected: **57 rows**, reload maximum difference **0.0**:

| Game ID | Actual saved matchup (home vs. away) | Home | Away |
| --- | --- | ---: | ---: |
| 401869941 | Coastal Carolina vs. Liberty | 44.4231% | 55.5769% |
| 401862779 | Temple vs. Army | 49.7701% | 50.2299% |
| 401862778 | UAB vs. Navy | 40.0752% | 59.9248% |

Say: “These identify actual matchups in the saved September 23 Week 4 snapshot;
they are not refreshed live forecasts, even if the recording date is later.
Sacramento State–Massachusetts, game 401866429, has no qualifying prior history
and receives no invented probability. Previous-season summaries omit current
form and roster changes. Historical versions and availability remain unverified,
so these results do not demonstrate leakage-safe backtesting. Serverless
orchestration and monitoring remain future work.”

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
