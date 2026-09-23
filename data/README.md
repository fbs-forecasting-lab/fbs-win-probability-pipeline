# Data

This directory documents data used by the FBS win-probability pipeline.

Raw and generated datasets should not be committed to GitHub. Local data should be organized under directories such as:

- `raw/` — unmodified API responses or source extracts
- `interim/` — intermediate transformation outputs
- `processed/` — model-ready datasets

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
No leakage-safe training dataset or feature approval is produced here. The
prediction cutoff and feature availability policy must be specified in the later
feature task, including updates to `docs/data-leakage-policy.md`.

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
