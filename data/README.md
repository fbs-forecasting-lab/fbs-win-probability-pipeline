# Data

This directory documents data used by the FBS win-probability pipeline.

Raw and generated datasets should not be committed to GitHub. Local data should be organized under directories such as:

- `raw/` — unmodified API responses or source extracts
- `interim/` — intermediate transformation outputs
- `processed/` — derived datasets, including explicitly unapproved retrospective demo inputs

These directories are excluded from version control.

Production data will ultimately be stored and accessed through the project's cloud data pipeline.

## CFBD Games Snapshots (Version 1)

The current local slice saves the entire successful response body from
`GET https://api.collegefootballdata.com/games`. Parameters are `year`,
`seasonType=regular`, `classification=fbs`, and optional `week`.
[Official API reference](https://apinext.collegefootballdata.com/api/games).

```text
data/raw/cfbd/games/season=YYYY/<snapshot_id>.json
data/raw/cfbd/games/season=YYYY/<snapshot_id>.manifest.json
```

The raw file contains the bytes exposed by `requests.Response.content` (after
HTTP transfer/content decoding), without reformatting, field selection, repair,
or deduplication. The expected envelope is a JSON array of game objects. Invalid
JSON or a different envelope fails before storage. Missing or null game fields
are reported without removing records. Additional source fields are retained.

Coverage tracks these downstream fields:

| Fields | Expected source values |
| --- | --- |
| `id`, `season`, `week`, `homeId`, `awayId` | Integers |
| `seasonType` | Season-type string; request selects `regular` |
| `startDate` | Game start timestamp |
| `startTimeTBD`, `completed`, `neutralSite` | Booleans |
| `homeTeam`, `awayTeam` | Team names |
| `homeClassification`, `awayClassification` | Division classifications |
| `homePoints`, `awayPoints` | Integer scores or null |

Coverage includes per-field missing-key and null counts, duplicate integer game
IDs with occurrence counts, invalid non-null ID counts, separate home/away
classification counts, and counts of games with both opponents explicitly
`fbs`. Missing, null, and non-string classifications use separate report buckets.
Duplicate IDs are retained. Coverage describes presence and classification;
it is not full field-type validation or a pass/fail quality gate. For an empty
array, `coverage.status` is `empty`; zero missing counts do not indicate success.

`classification=fbs` does not establish that both opponents are FBS. The later
feature step must enforce both classifications and decide how to handle missing
or inconsistent metadata. This slice does not filter those games.

Each sibling manifest contains:

- `snapshot_id`, `snapshot_version=1`, and `schema_version=1`. These version this
  local snapshot/manifest contract, not CFBD's upstream API schema.
- `source`, `endpoint`, and nonsecret `request_parameters`.
- `retrieved_at`: UTC time when the successful response was received.
- `http_status`, `record_count`, `response_file`, and `sha256` of the exact saved
  raw bytes.
- `coverage`, `source_availability`, and `approved_for_predictor_use=false`.

Snapshots use UUID filenames. Each file is written and flushed to a temporary
file in the destination directory, then atomically published with a no-overwrite
hard link. Filesystems must support hard links. The manifest is published last
as the completion marker; the two files are not one atomic transaction. Consumers
must discover manifests and verify their referenced raw files. An interruption
can leave an orphan raw file or temporary file; neither is a completed snapshot.
Earlier snapshots are never replaced.

## Availability and Leakage Boundary

Retrieval time is separate from historical source availability. The documented
games contract supplies no historical publication timestamp, so manifests mark
`source_availability.status=unknown` and `available_at=null`. `startDate` is a
scheduled game time, never a substitute for `available_at`. A snapshot downloaded
today is not evidence that its values were known before a historical kickoff.
Unexpected additional source timestamps remain raw, unverified fields.

Scores, completion status, postgame probabilities, ratings, and other postgame
fields are stored for provenance. They are **not approved predictor inputs**.
Even fields named "pregame" require a historical-availability audit before use.
No leakage-safe training dataset or feature approval is produced by ingestion.
The retrospective dataset slice below defines a reconstruction cutoff and
explicit limitations in `docs/data-leakage-policy.md`; it does not establish
historical availability.

## Request Behavior and Verification

The client uses a 5-second connection timeout and a 30-second read inactivity
timeout. These are not a total wall-clock deadline. Timeouts, connection failures,
HTTP 429, and HTTP 5xx receive at most three total attempts. Default waits are
1 and 2 seconds; valid `Retry-After` seconds/dates take precedence up to 30 seconds.
A longer server-requested wait stops the run rather than retrying too soon.
Authentication/access errors (401/403), other HTTP errors, redirects, and malformed
responses are not retried. Redirect following is disabled. Errors do not include
response bodies, request headers, or underlying exception text. A successful
response that echoes the configured credential is rejected rather than saved.

### Live Verification: September 23, 2026

The authenticated `GET /calendar?year=2026` returned 16 calendar entries. At
`2026-09-23T04:42:52Z`, regular-season Week 4 was selected because the current
time fell between its `startDate=2026-09-21T07:00:00.000Z` and
`endDate=2026-09-28T06:59:00.000Z`. No week number was inferred from another source.
The calendar lookup was a verification-only request, not production ingestion.

Actual ingestion commands from the repository root:

```bash
.venv/bin/python -B -m src.ingestion.cfbd --season 2025
.venv/bin/python -B -m src.ingestion.cfbd --season 2026 --week 4
```

Both returned HTTP 200 and stored snapshots under `data/raw/cfbd/games/`:

| Observation | 2025 regular season | 2026 regular-season Week 4 |
| --- | --- | --- |
| Snapshot ID | `1657e1334c044ff0957e8e246f712d82` | `3b59d327dcb94e818b911b94902e0bd9` |
| UTC retrieval time | `2026-09-23T04:43:15.581843Z` | `2026-09-23T04:43:15.923148Z` |
| Records | 888 | 71 |
| Both opponents FBS | 762 | 58 |
| FBS home / FCS away | 126 | 13 |
| Missing tracked fields / duplicate IDs / invalid IDs | 0 / 0 / 0 | 0 / 0 / 0 |
| Null tracked values | None | `homePoints` and `awayPoints`: 71 each |
| Completed games | 888 | 0 |
| Start time TBD | 0 | 0 |

The raw files are `season=2025/1657e1334c044ff0957e8e246f712d82.json` and
`season=2026/3b59d327dcb94e818b911b94902e0bd9.json`, each with a sibling
`.manifest.json`. Reloaded record counts, SHA-256 hashes, and recomputed coverage
matched both manifests. Their raw SHA-256 values are:

```text
2025: 4d33422ab53224e62623d987ff31c6c79dfdcac7f5ab428f4538d9fa60bdc42e
2026: 468da4d38a5b296f343ae5704ebe1ef4b104efa15aedf1e03ef0d433d1bf8bb6
```

The authenticated [CFBD account-info endpoint](https://apinext.collegefootballdata.com/api/info)
reported `tierName=Academic`, `monthlyLimit=3000`, and a shared football/basketball
pool. Before verification it reported 0 used / 3,000 remaining; after the calendar
and two games requests, at `2026-09-23T04:43:44Z`, it reported **3 used / 2,997
remaining**. The reported reset is `2026-10-01T00:00:00.000Z` (September 30 at
8:00 p.m. America/New_York). No authentication, access, or quota errors occurred
in those live requests. Initial sandbox network restrictions required permitted
network access. Quota figures are a point-in-time account observation.

These checks verify ingestion/storage, not source completeness or historical
predictor availability. The null 2026 scores belong to uncompleted games; they
were preserved. Both manifests continue to mark historical availability unknown
and predictor use unapproved. Raw snapshots and the local key remain Git-ignored.

After a successful CLI run, reload completed snapshots and check their hashes,
counts, and coverage from the repository root:

```bash
.venv/bin/python -B - <<'PY'
import hashlib
import json
from pathlib import Path
from src.ingestion.storage import parse_games, coverage_report

manifests = sorted(Path("data/raw/cfbd/games").glob("season=*/*.manifest.json"))
if not manifests:
    raise SystemExit("No completed snapshots found; verification did not run.")
for path in manifests:
    manifest = json.loads(path.read_bytes())
    raw_path = path.parent / manifest["response_file"]
    raw = raw_path.read_bytes()
    records = parse_games(raw)
    assert hashlib.sha256(raw).hexdigest() == manifest["sha256"], path
    assert len(records) == manifest["record_count"], path
    assert coverage_report(records) == manifest["coverage"], path
    print(path, "records:", len(records), "hash/count/coverage verified")
    print(json.dumps(manifest["coverage"], indent=2))
PY
```

The `data/raw/` tree and `.env` are already ignored by Git. Authorization headers
and credentials are never included in manifests; do not add them to debug logs,
filenames, or tracked files.

## Normalized Game Outputs (Normalization Schema Version 1)

Run locally, without API requests, using explicit saved manifests:

```bash
.venv/bin/python -B -m src.features.games --manifest \
  data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json \
  data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json
```

One manifest is sufficient. Multiple paths or repeated `--manifest` options are
processed independently; the CLI never discovers/selects the newest snapshot.
An optional `--output-root data/interim/cfbd/games-review` changes the root but
preserves the per-snapshot directories. Relative custom paths use the current
working directory; the default root is anchored to the repository. Keep custom
outputs under ignored `data/interim/` or outside the repository.

Each output directory contains exactly:

- `games.csv`: validated regular-season FBS-versus-FBS rows in source order, with
  UTC timestamps, retained outcome data, and row-level provenance. Headers are
  written even if there are no retained rows.
- `exclusions.json`: separate `excluded` and `quarantined` arrays containing source
  row indices, game IDs when available, and specific reasons. Invalid rows take
  precedence over non-FBS exclusions; duplicates are never silently selected.
- `quality_report.json`: normalization version, source provenance, reason counts,
  and mutually exclusive input/retained/excluded/quarantined counts.

Existing files must match recomputed bytes to allow a rerun. Matching partial
outputs can be resumed; conflicting or unrelated files cause an error without
overwriting them. Publication uses atomic per-file writes with the report last;
consumers require all three artifacts. A new normalization version or altered
input metadata should use a separate output root for comparison.

### Offline Verification Results

| Source snapshot | Input | Retained | Excluded non-FBS | Quarantined |
| --- | --- | --- | --- | --- |
| 2025: `1657e1334c044ff0957e8e246f712d82` | 888 | 762 | 126 | 0 |
| 2026 Week 4: `3b59d327dcb94e818b911b94902e0bd9` | 71 | 58 | 13 | 0 |

Outputs are in:

```text
data/interim/cfbd/games/1657e1334c044ff0957e8e246f712d82/
data/interim/cfbd/games/3b59d327dcb94e818b911b94902e0bd9/
```

All exclusions were valid FBS-home/FCS-away matchups. No additional validation
quarantines reduced the previously observed FBS–FBS counts of 762 and 58.
The 2026 retained rows preserve null scores; completed-game zero scores remain
zero. Both raw hashes remain the values recorded above. Repeated normalization
produces byte-identical outputs. These are structural/consistency checks, not
independent confirmation of source completeness or historical availability.

To verify the two explicit normalized outputs and unchanged source bytes:

```bash
.venv/bin/python -B - <<'PY'
import csv
import hashlib
import json
from pathlib import Path
from src.ingestion.storage import parse_games, coverage_report

cases = [
    (2025, "1657e1334c044ff0957e8e246f712d82", 762, 126),
    (2026, "3b59d327dcb94e818b911b94902e0bd9", 58, 13),
]
for season, snapshot_id, expected_retained, expected_excluded in cases:
    raw_dir = Path(f"data/raw/cfbd/games/season={season}")
    manifest_path = raw_dir / f"{snapshot_id}.manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    raw = (raw_dir / manifest["response_file"]).read_bytes()
    records = parse_games(raw)
    assert hashlib.sha256(raw).hexdigest() == manifest["sha256"]
    assert len(records) == manifest["record_count"]
    assert coverage_report(records) == manifest["coverage"]
    output = Path("data/interim/cfbd/games") / snapshot_id
    with (output / "games.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    dispositions = json.loads((output / "exclusions.json").read_bytes())
    report = json.loads((output / "quality_report.json").read_bytes())
    counts = report["counts"]
    assert counts == {"input": len(records), "retained": expected_retained,
                      "excluded": expected_excluded, "quarantined": 0}
    assert counts["input"] == sum(counts[k] for k in ("retained", "excluded", "quarantined"))
    assert len(rows) == counts["retained"]
    assert len(dispositions["excluded"]) == counts["excluded"]
    assert len(dispositions["quarantined"]) == counts["quarantined"]
    assert report["source"]["raw_sha256"] == manifest["sha256"]
    assert report["source"]["manifest_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    indices = [int(row["source_row_index"]) for row in rows]
    indices += [item["source_row_index"] for item in dispositions["excluded"]]
    indices += [item["source_row_index"] for item in dispositions["quarantined"]]
    assert sorted(indices) == list(range(len(records)))
    for row in rows:
        assert row["source_snapshot_id"] == snapshot_id
        assert row["source_raw_sha256"] == manifest["sha256"]
        assert row["historical_availability_status"] == "unknown"
        assert row["historical_available_at"] == ""
        assert row["approved_for_predictor_use"] == "false"
    print(season, counts, "raw integrity, output counts, dispositions, and provenance verified")
PY
```

See [the data dictionary](../docs/data-dictionary.md) for all column meanings,
null handling, validation rules, and provenance fields. See
[the leakage policy](../docs/data-leakage-policy.md) for why normalization is not
historical availability verification. Both raw and interim trees remain ignored
by Git; shared code references their IDs without committing datasets.

## Retrospective Demo Datasets (Schema Version 1)

Run from the repository root against the six existing snapshots and their
existing normalized outputs. This command needs no credentials or network and
does not fetch or renormalize missing inputs:

```bash
.venv/bin/python -B -m src.features.dataset --manifest \
  data/raw/cfbd/games/season=2021/16cba29e664a496fb9ca9c7f6d23cb88.manifest.json \
  data/raw/cfbd/games/season=2022/bbd6dd3559074ab1ad2b291859dd37c0.manifest.json \
  data/raw/cfbd/games/season=2023/087a3002111c4a97abaad886ea5f760a.manifest.json \
  data/raw/cfbd/games/season=2024/cb45f74c1ad14f8ea7f19323bb034866.manifest.json \
  data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json \
  data/raw/cfbd/games/season=2026/3b59d327dcb94e818b911b94902e0bd9.manifest.json \
  --output-dir data/processed/demo-features-v1 \
  --allow-retrospective-demo
```

Exactly one explicit snapshot for each season 2021–2026 is required; duplicate
seasons are rejected even if a path is repeated. Historical requests (2021–2025)
must be full regular seasons; only 2026 may be week-limited. Repeated
`--manifest` options are also accepted. `--normalized-root` can select another
existing normalization root; the default is repository-anchored
`data/interim/cfbd/games/`. Relative custom paths use the current directory.
Keep derived outputs under ignored `data/processed/` or outside the repository.

The builder verifies the raw manifest/hash/count/coverage and compares all three
normalized artifacts against the existing normalization logic before reading
rows. It does not repair inconsistent inputs. Missing normalization artifacts
must first be prepared with the normalization CLI. Exit code 1 reports invalid
inputs, absent demo permission, or output conflicts; exit code 0 means publication
succeeded and does not imply data suitability or nonempty splits.

The command creates exactly these files:

```text
data/processed/demo-features-v1/train.csv
data/processed/demo-features-v1/holdout.csv
data/processed/demo-features-v1/prediction.csv
data/processed/demo-features-v1/exclusions.json
data/processed/demo-features-v1/dataset_report.json
data/processed/demo-features-v1/team_season_aggregates.csv
```

Only `prior_win_pct_diff`, `prior_avg_margin_diff`, and `home_field`, in that
order, are predictors. Use the report's explicit `predictor_columns` when
selecting model inputs. Labels, scores, completion status, IDs, sample counts,
and provenance are not predictors. `prediction.csv` has no `home_win` column.
See the [data dictionary](../docs/data-dictionary.md) for definitions and schemas.

Identical reruns preserve output bytes and modification times. Differing files,
symlinks, or unexpected entries cause an error without overwriting existing data;
use a separate directory for a changed selection/version. Each file is atomically
published; the report is last as the completion marker. Publication is not one
transaction. Matching partial output may resume, but consumers must require all
six artifacts and verify the report's five artifact hashes.

### Saved-Snapshot Build Results: September 23, 2026

| Split | Target seasons | Normalized input | Output | Excluded |
| --- | --- | ---: | ---: | ---: |
| Train | 2022–2024 | 2,237 | 2,194 | 43 |
| Holdout | 2025 | 762 | 740 | 22 |
| Prediction | 2026 Week 4 | 58 | 57 | 1 |

Train reason counts are 20 missing home histories, 23 missing away histories,
and 1 uncompleted target. One target has both missing-history reasons, so 44
reason occurrences describe 43 excluded rows. Missing histories involve James
Madison (2022), Jacksonville State and Sam Houston (2023), and Kennesaw State
(2024). Uncompleted 2024 App State–Liberty game `401640992` is excluded from both
training labels and 2024 aggregates. Holdout has 10 missing home histories and
12 missing away histories, involving Delaware and Missouri State. Prediction
has one missing home history for Sacramento State. The complete game IDs and
reasons are in `exclusions.json`; no team history is invented.

The aggregate table has 664 team-season rows from 732, 734, 750, 752, and 762
completed retained games in 2021–2025 respectively. These are FBS–FBS regular-season
counts, not all games played. Upstream normalization counts/quarantines remain
separate in `dataset_report.json`.

| Split | Win-percentage difference range | Mean-margin difference range (points) | Home-field range |
| --- | --- | --- | --- |
| Train | −0.916667 to 0.923077 | −48.348485 to 48.715385 | 0 to 1 |
| Holdout | −0.909091 to 0.916667 | −55.401515 to 57.068182 | 0 to 1 |
| Prediction | −0.742424 to 0.750000 | −40.234848 to 49.250000 | 1 to 1 |

These are rounded descriptive ranges from the saved inputs, not model results.
All 30 raw/manifest/normalized files remained byte-identical. An identical rerun
preserved all six dataset files and modification times. The complete offline
suite passed 70 tests on Python 3.14.2:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

To reload the derived files and verify hashes, counts, and feature ranges:

```bash
.venv/bin/python -B - <<'PY'
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

root = Path("data/processed/demo-features-v1")
report = json.loads((root / "dataset_report.json").read_bytes())
assert report["dataset_mode"] == "retrospective_demo"
assert report["historical_availability_verified"] is False
assert report["approved_for_point_in_time_forecasting"] is False
for name, expected in report["artifact_sha256"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
excluded = json.loads((root / "exclusions.json").read_bytes())["rows"]
for split, counts in report["splits"].items():
    with (root / f"{split}.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert ("home_win" in reader.fieldnames) == (split != "prediction")
        rows = list(reader)
    rejected = [row for row in excluded if row["split"] == split]
    assert len(rows) == counts["output"]
    assert len(rejected) == counts["excluded"]
    assert counts["input"] == len(rows) + len(rejected)
    assert dict(Counter(reason for row in rejected for reason in row["reasons"])) == counts["exclusion_reason_counts"]
    for column in report["predictor_columns"]:
        values = [float(row[column]) for row in rows]
        assert counts["feature_ranges"][column] == {
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    print(split, len(rows), "rows; hashes/counts/ranges verified")
with (root / "team_season_aggregates.csv").open(newline="") as handle:
    assert len(list(csv.DictReader(handle))) == report["aggregate_row_count"]
PY
```

Without the demo flag, construction is blocked because historical availability
is unverified. With it, all outputs stay `retrospective_demo` and unapproved for
point-in-time forecasting. The assumption is that prior-season results and
target matchup metadata could have been known before the target game, while
revisions and historical versions remain unverified. Scheduled kickoff is the
demo cutoff, not proof of actual kickoff, completion, or publication time.
Source availability remains unknown and no timestamp is invented. These outputs
do not demonstrate leakage-safe backtesting or predictive performance. No API
requests or model training were performed for this dataset slice.

## Baseline Model and Prediction Artifacts (Version 1)

The baseline uses the existing dataset directory above, with no API requests or
new data retrieval. Both scaler and logistic regression fit only 2022–2024;
2025 is used only for evaluation. The saved model is not refitted before
predicting the saved 2026 sample. Exact repository-root commands:

```bash
.venv/bin/python -B -m src.models.baseline \
  --dataset-dir data/processed/demo-features-v1 \
  --output-dir data/processed/demo-baseline-v1 \
  --allow-retrospective-demo

.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-v1 \
  --dataset-dir data/processed/demo-features-v1 \
  --output-dir data/processed/demo-baseline-reloaded-v1 \
  --allow-retrospective-demo

.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-v1 \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

All commands require explicit retrospective permission. The loader verifies
schema version 1, demo/approval flags, dataset identity, exactly the three
predictors in order, all five reported artifact hashes, and split counts and
seasons. Train/holdout must be nonempty with binary labels; training must have
both classes. Game IDs must be unique within and disjoint across splits. Missing,
nonfinite, or out-of-domain features fail rather than being imputed or dropped.
Prediction may be empty, in which case its CSV contains only the header.

`data/processed/demo-baseline-v1/` contains exactly:

| File | Contents |
| --- | --- |
| `model.joblib` | Fitted StandardScaler/LogisticRegression pipeline, using installed joblib with compression |
| `model_metadata.json` | Schema version, dataset ID/report hash and artifact hashes, predictor order, target, seasons/counts, model/scaler settings, class order, library versions, source availability, limitations, and hashes of all six companion files |
| `evaluation.json` | Actual 2025 count, model and constant-baseline Brier/log-loss/accuracy, training-only constant probability, threshold rule, and demo flags |
| `calibration.json` | Ten fixed equal-width bins for model and constant baseline; count, mean probability, observed home-win rate, explicit interval edges; empty-bin means/rates are null |
| `holdout_predictions.csv` | Game/team identifiers, cutoff, source snapshot/row, unknown availability, home/away probabilities, demo flags, and `saved_2025_holdout` context |
| `sample_predictions.csv` | The same prediction schema with `saved_2026_sample_not_live` context; no invented labels |
| `exclusions.json` | Byte-for-byte copy of the dataset exclusions; excluded games receive no predictions |

Prediction CSVs use UTF-8, lowercase boolean flags, and blank null timestamps,
consistent with dataset CSVs. They record `game_id`, `season`, `week`, `home_id`,
`home_team`, `away_id`, `away_team`, `cutoff`, `source_snapshot_id`,
`source_row_index`, `historical_availability_status`, `historical_available_at`,
`home_win_probability`, `away_win_probability`, `prediction_context`, and the
four dataset mode/availability/approval fields. The model metadata links each
run to the complete source dataset and hashes; labels remain in train/holdout
input files. Class label 1 identifies home-win probability. Away probability is
exactly 1 minus home probability; accuracy uses home probability >= 0.5.

The second command reloads the complete trusted model directory, requires the
exact dataset ID and report hash used during training, and reads its verified
`prediction.csv`. It writes three files in
`data/processed/demo-baseline-reloaded-v1/`:

- `predictions.csv`: predictions after file-based model reload.
- `exclusions.json`: unchanged dataset exclusions.
- `prediction_report.json`: count, model hash, dataset identity/report hash,
  feature order, source availability, limitations, flags, and two output hashes.

The third command prints a hypothetical vector's probabilities to stdout and
writes no artifact. For the stated vector, observed home probability is
0.662422294285731 and away probability is 0.33757770571426904. It represents no
real matchup. Single-vector and batch modes are mutually exclusive.

Only load trusted artifacts generated locally by this project. Joblib can
execute code during deserialization. The reload path verifies companion hashes
before loading, validates the pipeline types and feature/class/settings contract,
and requires matching recorded Python/library versions. Hashes are integrity
checks, not authenticity or trust guarantees. The environment and pinned
requirements were unchanged; joblib was already installed with scikit-learn.

All output directories should stay inside ignored `data/processed/` or outside
the repository. Safe publication reuses the existing dataset publisher:
atomic no-overwrite writes per file, matching existing files preserved, and
conflicting files or unexpected entries rejected. `model_metadata.json` or
`prediction_report.json` is published last as the completion marker. This is
not a multi-file transaction. Matching partial runs can resume, but consumers
require every artifact and matching hashes. Changed inputs, environments, or
results need a separate output directory. No timestamp is added merely for a
rerun; serialization bytes may differ across environments. CLI errors return
exit code 1; invalid CLI argument combinations use argparse's exit code 2.

### Actual Baseline Verification: September 23, 2026

Input counts verified from artifacts were 2,194 train, 740 holdout, and 57 saved
prediction rows. Logistic regression converged in 10 iterations with no warning.
The constant predictor used training home-win rate 0.5829535095715588.

| Holdout metric | Logistic model | Constant |
| --- | ---: | ---: |
| Brier score | 0.2106128715 | 0.2416357749 |
| Log loss | 0.6096025526 | 0.6763272181 |
| Accuracy | 0.6648648649 | 0.5918918919 |

Full offline suite: 84 tests passed using
`.venv/bin/python -B -m unittest discover -s tests -v` on Python 3.14.2.
The reloaded model matched saved probabilities with maximum absolute difference
0.0 across all 740 holdout and 57 prediction rows (tolerance 1e-12). The reloaded
batch file was byte-identical to the original sample prediction file. All 36
source/dataset files remained unchanged; all 10 new output files are Git-ignored.

To verify the saved results offline without fitting again:

```bash
.venv/bin/python -B - <<'PY'
import csv
import json
from pathlib import Path
import numpy as np
from src.models.baseline import load_dataset, load_trusted_model, home_probabilities

root = Path("data/processed/demo-baseline-v1")
model, metadata = load_trusted_model(root, allow_retrospective_demo=True)
data = load_dataset("data/processed/demo-features-v1", allow_retrospective_demo=True)
assert metadata["dataset_report_sha256"] == data["report_sha256"]
for split, filename in [("holdout", "holdout_predictions.csv"),
                        ("prediction", "sample_predictions.csv")]:
    with (root / filename).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    saved = np.array([float(row["home_win_probability"]) for row in rows])
    actual = home_probabilities(model, data["splits"][split]["x"])
    assert len(rows) == metadata["counts"][split]
    np.testing.assert_allclose(saved, actual, rtol=0, atol=1e-12)
    for row in rows:
        assert 0 <= float(row["home_win_probability"]) <= 1
        assert float(row["away_win_probability"]) == 1 - float(row["home_win_probability"])
    print(split, len(rows), "hashes/counts/reloaded predictions verified")
assert (root / "sample_predictions.csv").read_bytes() == Path(
    "data/processed/demo-baseline-reloaded-v1/predictions.csv").read_bytes()
PY
```

See the [model card](../docs/model-card.md) for the complete descriptive
calibration table, actual sample predictions, feature rationale, and limitations.
No calibration fitting or holdout tuning was performed. Previous-season inputs
omit current-season changes; missing histories exclude teams; historical
availability remains unverified. All outputs stay unapproved for point-in-time
forecasting, and these metrics are not evidence of live predictive performance
or leakage-safe backtesting.

## S3 Demo Storage (Explicit Transfers)

`src.ingestion.s3_storage` adds cloud storage for one selected raw snapshot pair
and one selected feature dataset. Computation remains local. It does not upload
models, recursively synchronize directories, discover buckets, create resources,
change access policies, or change historical-availability metadata.

### Configuration and Permissions

Select an **existing private project bucket**, its actual region, and a dedicated
project prefix. Put only these nonsecret settings in the ignored project `.env`
or environment; `.env.example` includes empty entries:

```text
FBS_S3_BUCKET=<selected-existing-project-bucket>
FBS_S3_REGION=<selected-bucket-region>
FBS_S3_PREFIX=<selected-project-prefix>
FBS_AWS_PROFILE=<optional-selected-profile>
```

Replace placeholders before running commands. A prefix may contain slash-separated
letters, digits, underscores, and hyphens, such as `fbs-win-probability/initial-demo`;
this is an example, not an automatically selected destination. Do not use leading
or trailing slashes. The CLI also accepts `--bucket`, `--region`, `--prefix`, and
`--profile` after each subcommand. Explicit CLI settings override project settings;
an environment value overrides `.env`, including an explicitly empty value.
When region/profile are omitted, boto3 uses its normal SDK configuration.

Authentication uses boto3's standard credential chain, including configured
profiles, SSO/role sessions, and temporary environment credentials with
`AWS_SESSION_TOKEN`. AWS credentials are not loaded from the project's `.env` by
this module. Use the existing AWS/course-lab authentication setup; never place
keys in command arguments, examples, logs, or tracked files. Do not enable SDK
HTTP debug logging. Refresh an expired course/SSO session through the usual AWS
login workflow. The code neither creates identities/keys nor alters security.

The selected bucket must already have all four **bucket-level Block Public
Access** flags enabled. The module reads that configuration before transfers and
fails closed if it is unavailable or any flag is false. Account-level blocking
alone is not sufficient for this narrow implementation. No ACL or encryption
setting is sent with uploads; the bucket's encryption configuration applies.

The current identity needs permission to read bucket Block Public Access, read
and conditionally write the selected objects, and receive missing-key responses
for the selected prefix (`s3:GetBucketPublicAccessBlock`, `s3:GetObject`,
`s3:PutObject`, and appropriately scoped `s3:ListBucket`). SSE-KMS buckets also
require applicable KMS permissions. Access failures are reported; this module
never modifies policies to resolve them. No delete permission is used.

### Upload and Download Commands

After selecting/configuring the destination, run from the repository root:

```bash
.venv/bin/python -B -m src.ingestion.s3_storage upload-raw \
  --manifest data/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json

.venv/bin/python -B -m src.ingestion.s3_storage upload-dataset \
  --dataset-dir data/processed/demo-features-v1 \
  --allow-retrospective-demo

.venv/bin/python -B -m src.ingestion.s3_storage download-dataset \
  --dataset-id 8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5 \
  --output-dir data/processed/demo-features-from-s3-v1 \
  --allow-retrospective-demo
```

Uploads print each actual S3 URI and `uploaded` or `reused`. The download prints
its actual source URI, local directory, dataset ID/report hash, six verified
files, and retrospective limitations. No CFBD request is made by these commands.

Object keys preserve identity, under the explicitly configured bucket/prefix:

```text
s3://<bucket>/<prefix>/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.json
s3://<bucket>/<prefix>/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json
s3://<bucket>/<prefix>/datasets/8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5/train.csv
```

The dataset directory also contains `holdout.csv`, `prediction.csv`,
`team_season_aggregates.csv`, `exclusions.json`, and `dataset_report.json`.
These are generic location templates; the verified destination is recorded below.
No serialized model is transferred.

### Integrity and Publication Rules

Raw uploads use existing snapshot validation (manifest versions, raw SHA-256,
count, recomputed coverage, and provenance). Dataset uploads use the existing
baseline dataset loader; they do not modify, reconstruct, or relabel the data.
Only the two raw files or six allowlisted dataset files are considered, even if
other files exist beside them. Each artifact is limited to 64 MiB for this demo.

Before writing, the module downloads any existing objects and compares actual
bytes. Conflicts stop without replacement. Every new `PutObject` also uses
`IfNoneMatch="*"` so a concurrent upload cannot bypass the no-overwrite rule.
A 412 response permits reuse only after reading and matching actual bytes.
A 409 concurrent conflict stops safely and can be retried by rerunning the
command. Uploaded objects are read back and checked. ETags are never treated as
SHA-256 hashes; uploads also supply the base64 SHA-256 checksum to S3.

Data files are published and verified before the raw manifest or dataset report,
which acts as the completion marker. The group is not one S3 transaction. A
failed partial upload has no new completion marker and can resume with identical
files. An existing marker with missing or conflicting data fails rather than
being silently repaired. Consumers must validate every referenced hash, not just
check that a marker exists. Other writers/deletions outside this client can still
invalidate a bundle; this client changes no bucket policy to prevent them.

Downloads require an explicit 64-character dataset ID, fetch the report first,
and accept only the exact five artifact filenames and SHA-256 hashes in the
versioned contract. Paths such as `../...`, absolute paths, nested paths, and
extra artifact names are rejected before becoming local paths. SHA-256 is
computed from downloaded bytes. All six files are validated in a temporary
staging directory using the existing dataset loader before local publication.
Temporary staging is separate from the final destination.

The existing atomic no-overwrite publisher places the local report last.
Identical local files retain bytes and modification times; conflicting files,
symlinks, or unrelated entries fail without replacement. A local disk failure
can leave verified partial output without a completion marker; an identical
rerun can finish it. Keep downloads under ignored `data/processed/` and use a
separate directory from the fixed original dataset.

SDK retries use standard mode with at most three total attempts per API call,
a five-second connect timeout, and a 30-second read inactivity timeout. There
is no unbounded application retry loop. Streaming-body failures stop the run;
rerun to retry. These limits are not an overall transfer deadline. Errors are
sanitized, omitting credential values, response messages, headers, and tokens.

### Local Model Verification After a Real Download

Only after a successful real S3 download, first compare all six files:

```bash
.venv/bin/python -B - <<'PY'
from pathlib import Path
from src.models.baseline import load_dataset
original = Path("data/processed/demo-features-v1")
downloaded = Path("data/processed/demo-features-from-s3-v1")
data = load_dataset(downloaded, allow_retrospective_demo=True)
names = sorted(data["artifacts"]) + ["dataset_report.json"]
assert {p.name for p in downloaded.iterdir()} == set(names)
for name in names:
    assert (downloaded / name).read_bytes() == (original / name).read_bytes(), name
print("Six downloaded files match the originals byte for byte.")
PY

.venv/bin/python -B -m src.models.baseline \
  --dataset-dir data/processed/demo-features-from-s3-v1 \
  --output-dir data/processed/demo-baseline-from-s3-v1 \
  --allow-retrospective-demo

.venv/bin/python -B -m src.models.predict \
  --model-dir data/processed/demo-baseline-from-s3-v1 \
  --prior-win-pct-diff 0.2 --prior-avg-margin-diff 7 --home-field 1 \
  --allow-retrospective-demo
```

Compare the new **local** run to the original without uploading either model:

```bash
.venv/bin/python -B - <<'PY'
import csv, json
from pathlib import Path
import numpy as np
from src.models.baseline import load_trusted_model
from src.models.predict import predict_vector
old = Path("data/processed/demo-baseline-v1")
new = Path("data/processed/demo-baseline-from-s3-v1")
old_model, old_meta = load_trusted_model(old, allow_retrospective_demo=True)
new_model, new_meta = load_trusted_model(new, allow_retrospective_demo=True)
assert old_meta["dataset_report_sha256"] == new_meta["dataset_report_sha256"]
assert old_meta["counts"] == new_meta["counts"]
a = json.loads((old / "evaluation.json").read_bytes())
b = json.loads((new / "evaluation.json").read_bytes())
for group in ("model", "constant_baseline"):
    for metric in ("brier_score", "log_loss", "accuracy"):
        np.testing.assert_allclose(a[group][metric], b[group][metric], rtol=0, atol=1e-12)
for filename in ("holdout_predictions.csv", "sample_predictions.csv"):
    with (old / filename).open(newline="") as handle:
        before = list(csv.DictReader(handle))
    with (new / filename).open(newline="") as handle:
        after = list(csv.DictReader(handle))
    assert [r["game_id"] for r in before] == [r["game_id"] for r in after]
    for column in ("home_win_probability", "away_win_probability"):
        np.testing.assert_allclose([float(r[column]) for r in before],
                                   [float(r[column]) for r in after], rtol=0, atol=1e-12)
vector = {"prior_win_pct_diff": 0.2, "prior_avg_margin_diff": 7, "home_field": 1}
p = predict_vector(old_model, vector)["home_win_probability"]
q = predict_vector(new_model, vector)["home_win_probability"]
np.testing.assert_allclose(p, q, rtol=0, atol=1e-12)
print("Metrics and probabilities match; hypothetical home probability:", q)
PY
```

Verified on September 24: train/holdout/prediction counts 2,194/740/57;
model Brier 0.21061287148858282, log loss 0.6096025525960278,
accuracy 0.6648648648648648. The constant comparison remains Brier
0.24163577488303326, log loss 0.6763272181260667, accuracy
0.5918918918918918. All six metrics equal the original run exactly.
Both probabilities for all 740 holdout and 57 sample rows matched exactly
(maximum absolute difference 0.0; tolerance 1e-12). Reloaded hypothetical
home probability is 0.662422294285731; away is 0.33757770571426904.
These are verified results from local training on the actual S3 download.
All retrospective-demo and unknown-availability limitations remain unchanged.

### Verification Status and Official API References

On September 24, 2026, boto3/botocore **1.43.86** were installed and supported
`PutObject.IfNoneMatch`, `ChecksumSHA256`, `GetObject`, and
`GetPublicAccessBlock`; no dependencies changed. The official documentation was
checked against the installed SDK service model before selecting calls:
[PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html),
[conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html),
[GetObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_object.html),
[Block Public Access lookup](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_public_access_block.html),
[SDK retries](https://docs.aws.amazon.com/boto3/latest/guide/retries.html), and
[credential chain](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).

Offline tests use synthetic local data, mocked clients, and botocore Stubber.
Run the complete suite with:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

Offline verification: **105 tests passed**, including 21 S3 storage tests.

Live S3 status: **verified September 24, 2026**. The user's selected bucket is
`fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an`, region
`us-east-1`, prefix `initial-demo`. These nonsecret settings are stored in ignored
`.env`; the existing CFBD key was preserved. Existing AWS credentials were used.
All four bucket-level Block Public Access flags passed before every transfer.
No IAM, ACL, bucket policy, encryption configuration, or other security setting
was changed. The initial sandbox network restriction was resolved with approved
network access; the live operations then succeeded without access/credential errors.

The two raw objects and all six dataset objects reported `uploaded`; each was
read back and compared with its source bytes. Completion markers were uploaded
last. Verified locations:

```text
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.json
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/raw/cfbd/games/season=2025/1657e1334c044ff0957e8e246f712d82.manifest.json
s3://fbs-win-probability-habbott-demo-2026-706016980237-us-east-1-an/initial-demo/datasets/8ecf7cf50b5f4ae68bde2ad902370b7528d327ed0919b5fed7a1211447c7e5c5/
```

The download is `data/processed/demo-features-from-s3-v1/`. It passed the existing
dataset loader and all six files matched the original bytes and SHA-256 hashes:

| File | Verified SHA-256 |
| --- | --- |
| `exclusions.json` | `c8a3c47830e7ca338e1264c160df3b88c2f867e5b99c9e52e67103b311b9ea62` |
| `holdout.csv` | `c382cf336c72e64de8e2bb5fed00f8014af8e5bd69da90548d8194926cef8a44` |
| `prediction.csv` | `5c026210c0768d320cc9b7236095336027da71c4f52ae608c486e081ed9f3747` |
| `team_season_aggregates.csv` | `54c89b604609b8c0f3134a36c478ab6de1fc32473ea2a98b3f85e4875fe61dad` |
| `train.csv` | `216eac480b78ef3417dda64a4cb652eeeac63458198d4795808b43e7cffcaa21` |
| `dataset_report.json` | `b4bb20873d36d6c526ec7ba045a1a82438498d21c581e920316eed95bb54c01f` |

The separate local training output is `data/processed/demo-baseline-from-s3-v1/`;
its evaluation, saved predictions, and reloaded hypothetical result matched as
reported above. No serialized model was transferred. Both new directories remain
Git-ignored. Existing source code and dataset/model bytes were preserved; no new
CFBD requests were made. There are no remaining blockers for this verification.
