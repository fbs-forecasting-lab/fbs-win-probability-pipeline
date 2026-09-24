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
