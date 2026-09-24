# CFBD Game and Demo Dataset Dictionary

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

## Retrospective Demo Dataset (Schema Version 1)

`src.features.dataset` requires exactly one explicit manifest for each season
2021–2026 and the three corresponding normalization artifacts. It reuses
normalization validation and requires existing normalized bytes to match the
recomputed artifacts. Full-season requests are required for 2021–2025; 2026 may
be a week sample. Duplicate season selections, even repeated identical paths,
are rejected. No automatic snapshot discovery, merging, or selection occurs.

For a season Y target, each team's history contains only retained, completed,
regular-season FBS–FBS games in Y-1, joined by team ID. For each team:
`prior_win_pct = wins / completed_game_count` and
`prior_avg_margin = margin_sum / completed_game_count`, where each margin is
team points minus opponent points. Incomplete games contribute neither results
nor denominators. Zero points remain valid. Missing history excludes the target;
there is no imputation, older-season fallback, scaling, or current-season input.

### Split CSVs and Predictor Order

| File | Eligible targets | Label |
| --- | --- | --- |
| `train.csv` | Completed 2022–2024 games | `home_win`: integer 1 when home points exceed away points, else 0 |
| `holdout.csv` | Completed 2025 games | Same binary label |
| `prediction.csv` | Uncompleted games in the selected 2026 snapshot | No `home_win` column |

Each target must have both histories and every contributing game's scheduled
start must precede its `cutoff`. Completed ties were already quarantined by
normalization. All CSVs retain headers when empty and use the normalization
CSV conventions above. Target ordering is season, UTC cutoff, then game ID.

The **only predictors**, in exact order, are:

| Column | Logical type | Definition |
| --- | --- | --- |
| `prior_win_pct_diff` | Float | Home prior win percentage minus away prior win percentage |
| `prior_avg_margin_diff` | Float | Home prior mean margin minus away prior mean margin, in points |
| `home_field` | Integer 0/1 | 0 when the target's `neutral_site` is true, otherwise 1 |

CSV column order is target fields below, those three predictors, `home_win`
(train/holdout only), then audit fields. Future model code must select the
report's `predictor_columns` explicitly; all remaining columns are excluded.

| Target/audit columns | Type and meaning |
| --- | --- |
| `game_id`, `season`, `week`, `home_id`, `home_team`, `away_id`, `away_team` | Normalized target identifiers/metadata, with `id` renamed `game_id` |
| `cutoff` | UTC scheduled kickoff in the selected snapshot; historical schedule version and actual kickoff unverified |
| `neutral_site`, `completed`, `home_points`, `away_points` | Preserved target site/outcome audit fields; prediction scores remain null |
| `home_prior_game_count`, `away_prior_game_count` | Integer counts of qualifying prior-season games; positive for retained targets; 0 on an exclusion denotes absent qualifying history, never imputed strength |
| `feature_source_season` | Exactly target season minus 1 |
| `feature_source_snapshot_id`, `feature_source_raw_sha256`, `feature_source_manifest_sha256` | Exact prior-season snapshot and hashes |
| `feature_source_availability_status`, `feature_source_available_at`, `feature_source_approved_for_predictor_use` | Preserved prior-source availability and approval; current values `unknown`, null, false |
| `source_snapshot_id`, `source_raw_sha256`, `source_manifest_sha256`, `source_row_index` | Exact target snapshot, raw/manifest hashes, and zero-based original raw row index |
| `retrieved_at`, `historical_availability_status`, `historical_available_at`, `approved_for_predictor_use` | Target-source provenance, not inferred availability; approval remains false |
| `dataset_mode` | Always `retrospective_demo` |
| `historical_availability_verified`, `approved_for_point_in_time_forecasting` | Always false |

### Aggregate Audit Table

`team_season_aggregates.csv` has one row per team with qualifying games in each
source season 2021–2025, sorted by season/team ID. It contains `season`, `team_id`,
`completed_game_count`, `wins`, `margin_sum`, `prior_win_pct`, `prior_avg_margin`,
and `latest_scheduled_start`. The last field supports the chronology gate:
the maximum contributing scheduled start must be strictly before target cutoff.
This does not establish when those games finished or results were published.

`contributing_game_ids` and `source_row_indices` are JSON arrays inside CSV
cells, paired in scheduled-start/game-ID/source-index order. Together with
source snapshot ID and raw/manifest hashes, they identify every contribution.
The table also preserves `retrieved_at`, source availability/approval fields,
and the three demo mode/verification fields listed above. It is an audit table,
not extra predictor columns.

### Exclusions and Report

Dataset `exclusions.json` contains metadata and a single `rows` array. Each row
has target/source audit metadata, prior sample counts, `split`, and `reasons`.
No missing predictors or labels are fabricated. Possible reasons are:

- `target_uncompleted`: train/holdout target lacks a completed outcome.
- `prediction_target_completed`: prediction target already completed.
- `missing_home_history`, `missing_away_history`: no qualifying Y-1 games.
- `home_history_not_before_cutoff`, `away_history_not_before_cutoff`: at least
  one contributing scheduled start is at or after cutoff.

A row can have several reasons. Reason counts can therefore exceed excluded
row counts. These are dataset eligibility exclusions after normalization;
upstream non-FBS exclusions and invalid-row quarantines remain in the source
normalization reports and are summarized separately in `sources`.

`dataset_report.json` contains schema version, deterministic `dataset_id`, exact
source metadata and raw/manifest/normalized-artifact hashes, feature definitions,
ordered `predictor_columns`, cutoff definition, limitations, and demo flags.
Each split reports `input`, `output`, `excluded`, reason counts, feature ranges,
and home/away prior-game-count ranges. Here `input` means retained normalized
target rows before dataset filtering; `input = output + excluded`. Empty splits
have null range endpoints. `aggregate_usage` reports completed-game counts,
omitted incomplete game IDs, and team counts by source season;
`aggregate_row_count` counts audit rows. `artifact_sha256` covers the other five
dataset files. `exclusions.json` also contains the shared source/demo metadata.

The dataset ID hashes the schema version, source metadata/artifact hashes,
predictor order, and mode. File hashes verify actual content. No current time is
added, and reordering manifest arguments cannot change outputs. Publication uses
the ingestion atomic no-overwrite helper per file with `dataset_report.json`
last. Consumers require all six artifacts and matching hashes. Identical reruns
preserve bytes and modification times; matching partial runs resume; differing
or unexpected files cause an error. Use a separate directory for revisions.

All source availability and approval values remain unchanged. Construction
requires `--allow-retrospective-demo`; see the [leakage policy](data-leakage-policy.md)
for the explicit assumption and why these datasets do not establish approved
point-in-time forecasting or leakage-safe backtesting.
