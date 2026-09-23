# Normalized CFBD Game Tables

Normalization schema version **1** produces one table per explicit source
manifest. It is a validated game/outcome table, not a model feature matrix.
Source fields beyond the 16 below remain available in the unchanged raw snapshot.
No historical predictor availability is established by normalization.

## `games.csv`

The CSV is UTF-8 with a header even when empty. Integers use decimal notation;
booleans use lowercase `true`/`false`. A blank score or availability timestamp
means null, never zero. CSV readers generally return strings; downstream code
must restore these types explicitly rather than infer missing values as zeros.
Game IDs remain named `id`; other source names are converted to snake_case.

| Column | Logical type | Meaning and validation |
| --- | --- | --- |
| `id` | Positive integer | CFBD game ID; all duplicate occurrences within the input snapshot are quarantined. |
| `season` | Integer year | At least 1869; must match the manifest request year (maximum 9999). |
| `week` | Nonnegative integer | CFBD regular-season week; must match an optional manifest week. Zero is permitted. |
| `season_type` | String | `regular`; must agree with the manifest request. |
| `start_date` | UTC timestamp | Source scheduled kickoff, normalized to an ISO timestamp ending in `Z`. Explicit source timezone required. |
| `start_time_tbd` | Boolean | Source kickoff-resolution flag; only `false` survives this initial scope. |
| `completed` | Boolean | Outcome metadata indicating whether CFBD marks the game completed. Not an approved predictor. |
| `neutral_site` | Boolean | Source neutral-site flag; no inference from venue or team names. |
| `home_id` | Positive integer | CFBD home team ID; must differ from away team ID. |
| `home_team` | Nonempty string | Source home team name; whitespace-only values rejected, valid strings preserved. |
| `home_classification` | String | Must be `fbs` for retention. |
| `home_points` | Nullable nonnegative integer | Source home score; required for completed games, null for uncompleted games. Zero is a valid score. |
| `away_id` | Positive integer | CFBD away team ID; must differ from home team ID. |
| `away_team` | Nonempty string | Source away team name, with the same validation as home. |
| `away_classification` | String | Must be `fbs` for retention. |
| `away_points` | Nullable nonnegative integer | Source away score, with the same validation as home. |
| `source_snapshot_id` | 32-character hex string | Original version-1 ingestion snapshot UUID. |
| `source_raw_sha256` | 64-character hex string | Verified hash of the exact raw-file bytes. |
| `source_row_index` | Nonnegative integer | Zero-based index into the original raw JSON array; retained rows preserve that order. |
| `retrieved_at` | UTC timestamp | Source snapshot retrieval instant, converted to UTC; not historical availability. |
| `historical_availability_status` | Nonempty string | Original manifest availability status, unchanged; currently `unknown`. |
| `historical_available_at` | Nullable timestamp | Only a timestamp already supplied by the manifest, converted to UTC. Currently null. Never inferred from kickoff or retrieval. |
| `approved_for_predictor_use` | Boolean | Always `false`; normalization grants no predictor approval. |

All fields except scores require the source key and a valid non-null value.
Absent score keys are treated as null only for uncompleted games; the source
coverage report still records their absence. Completed games with absent or null
scores are quarantined. No strings or floating-point values are coerced into
integers or booleans. Python/JSON booleans are not accepted as integer IDs or scores.

## Validation and Dispositions

Processing first verifies manifest `snapshot_version=1` and `schema_version=1`,
the sibling raw filename, SHA-256, record count, and recomputed ingestion coverage.
Metadata must identify an HTTP 200 CFBD games response with a valid regular-season
FBS request. Retrieval and any supplied availability timestamps must be aware.
Unknown availability must have a null timestamp, and predictor use must already
be explicitly unapproved. Version-1 snapshot IDs and raw filenames follow the
ingestion UUID contract; path traversal and raw-file symlinks are rejected.
Missing, corrupt, or unsupported inputs abort that manifest before output writes.
The manifest hash in output provenance identifies the exact metadata bytes used.
Hash checks detect inconsistency; they do not authenticate the data provider.

Every input row receives exactly one disposition, in this order:

1. **Quarantined:** any invalid required field, manifest/row season or week
   mismatch, unknown classification, duplicate game ID, or invalid outcome/time.
   Validation runs on non-FBS rows too. A row with multiple problems remains one
   quarantined row, with all detected reasons recorded.
2. **Excluded:** an otherwise valid row where either opponent is not `fbs`.
   Recognized divisions are `fbs`, `fcs`, `ii`, `ii/iii`, and `iii`.
3. **Retained:** a valid regular-season game with two FBS opponents.

Unresolved kickoff times (`startTimeTBD=true`), missing/naive/invalid kickoff
timestamps, and identical opponent IDs are quarantined. A known scheduled time
is required for the future cutoff step; it is not proof of historical schedule
availability, actual kickoff, or game completion time.

Completed games require two valid nonnegative integer scores and a non-tied
outcome for the initial binary-win scope. Uncompleted games require both scores
to be null or absent. Any score on an uncompleted game is quarantined, including
two zero scores: it could represent in-progress data or inconsistent metadata.
The code does not guess which interpretation is correct. Completed ties are
quarantined rather than mapped to a win/loss label. No label is generated here.

All occurrences of a duplicate integer game ID within an input snapshot are
quarantined, including otherwise valid or non-FBS occurrences. Repeated games
across different snapshots remain separate; cross-snapshot selection and merging
are deliberately deferred.

## `exclusions.json` and `quality_report.json`

`exclusions.json` has separate `excluded` and `quarantined` arrays. Each entry
contains `source_row_index`, `game_id` as found (null if absent), and a `reasons`
array. Invalid ID values are preserved for diagnosis, not treated as valid IDs.
Excluded entries also record both classifications. The original row is recoverable
using the raw hash and index; it is not copied or repaired in this output.

Both JSON artifacts include `normalization_schema_version` and a `source` object:
snapshot ID, CFBD source/endpoint, nonsecret request parameters, HTTP status, raw
filename/hash, manifest filename/hash, UTC retrieval time, the original complete
`source_availability` object, and unapproved predictor status. The original
availability object is preserved verbatim in meaning, even when its optional
timestamp is rendered in UTC in the CSV.

`quality_report.json` includes mutually exclusive `counts` for `input`, `retained`,
`excluded`, and `quarantined`. It enforces:

```text
input = retained + excluded + quarantined
```

`input_both_fbs_count` reports the raw classification count before validation;
`quarantined_both_fbs_count` explains any reduction in that count. `reason_counts`
counts occurrences of each reason separately by disposition, so those totals can
exceed the number of rows when a row has several problems. `status` is
`empty_input`, `no_retained_games`, or `complete`; none implies predictor approval.

## Reproducibility

Outputs go to `data/interim/cfbd/games/<snapshot_id>/`. No current clock value is
added: the same manifest/raw bytes and normalization version yield the same
output bytes and row order. Identical reruns leave existing artifacts untouched.
Different existing bytes, symlinks, or unexpected entries cause a conflict error;
use a separate output root to compare revisions. Raw snapshots are read-only.

Files are atomically published using the ingestion storage helper, with
`quality_report.json` last as the completion marker. The three files are not a
single filesystem transaction. A partial run can be resumed only when every
existing artifact matches the recomputed bytes. Consumers require all three
files; an incomplete directory is not a completed normalization. See
[data/README.md](../data/README.md) for CLI commands and verification results.
