# Data Leakage Policy

## Current Scope

The ingestion and normalization slices preserve evidence and validate game tables.
The dataset slice produces explicitly permitted retrospective demo predictors
and labels under the limited reconstruction assumption below. No slice trains a
model, approves predictor inputs, or establishes that historical values were
available before kickoff. Source and normalized records retain
`approved_for_predictor_use=false`.

## Four Different Times

| Time | Meaning | Current treatment |
| --- | --- | --- |
| Source event time | When an event is scheduled or occurs. CFBD `startDate` is a scheduled kickoff, not a publication timestamp. | Normalize to UTC only from a timezone-aware value. Quarantine unresolved or invalid kickoff times. Do not infer actual completion or publication time. |
| Snapshot retrieval time | When this project received the API response (`retrieved_at`). | Preserve the source snapshot retrieval instant on every normalized row. It proves observation at retrieval, not before it. |
| Historical availability | When a particular source value/version was published and could actually be known. | Preserve the original manifest status. Current snapshots have status `unknown` and `available_at=null`. Do not substitute kickoff, retrieval, season/week, or a field's name. |
| Target cutoff | The instant used to separate past information from the target. | The retrospective demo uses scheduled kickoff in the selected snapshot, normalized to UTC. An operational forecast cutoff, historical schedule versions, actual kickoff, and reschedule handling are not verified or implemented. |

All normalized timestamps use UTC. Naive timestamps are rejected rather than
assumed to be UTC. Retaining a valid schedule timestamp does not verify which
schedule version was known before a historical cutoff. Snapshot integrity and
complete field coverage are not evidence of historical availability.

## Outcomes and Predictor Boundaries

`completed`, `home_points`, and `away_points` are retained outcome data. Scores,
postgame ratings/probabilities, and completion status must never be used as
predictors for that same game. Completed-game scores produce demo labels.
For approved point-in-time forecasts, prior-game scores may contribute aggregates only after verifying those
games had finished and the relevant source values were available before the
target game's forecast cutoff. Scheduled kickoff alone does not establish this.

Fields named "pregame" are not automatically approved. Team classifications,
neutral-site flags, schedules, and other apparently static metadata also need
historical-version/availability assessment before backtesting. Unknown availability
stays unknown; later code must explicitly exclude or flag unsupported candidate
features rather than silently invent timestamps or claim leakage-safe training.

## Normalization Controls

- Select source manifests explicitly. Verify versions, raw hash, row count,
  and recomputed coverage before processing. Never automatically choose the
  newest snapshot for a historical prediction.
- Preserve snapshot ID, raw hash, original zero-based row index, retrieval time,
  and historical-availability status on every retained row. Keep raw bytes
  unchanged and preserve the original availability object in report provenance.
- Retain only validated regular-season FBS-versus-FBS rows. Invalid rows are
  quarantined separately from otherwise valid non-FBS exclusions. All duplicate
  game-ID occurrences within a snapshot are quarantined.
- For this initial demo, quarantine unresolved kickoff times, completed games
  without valid scores, completed ties, and uncompleted games carrying scores.
  Preserve null upcoming scores and valid completed-game zero scores.
- Keep repeated snapshots separate. Normalization itself does not merge snapshots
  or generate aggregates, labels, temporal splits, or a forecast cutoff.

## Explicit Retrospective Demo Permission

Without `--allow-retrospective-demo`, dataset construction stops before writing
outputs because historical availability is unverified. With that flag, the
builder assumes prior-season results and target matchup metadata represent
information that could have been known before the target game. Source revisions
and historical versions remain unverified. This permission applies only to
reconstruction for the Initial Demo; it is not evidence of availability or
approval for point-in-time forecasting or leakage-safe backtesting.

Every dataset CSV row, aggregate audit row, exclusion, and report records
`dataset_mode=retrospective_demo`, `historical_availability_verified=false`, and
`approved_for_point_in_time_forecasting=false`. Source availability objects and
approval fields are preserved; unknown availability stays unknown with a null
timestamp. Neither the flag nor scheduled kickoff creates `available_at`.

Dataset controls:

- Explicitly select exactly one manifest for each season 2021–2026. Reject
  duplicates and week-limited historical sources; only the 2026 target sample
  may be week-limited. Verify raw and existing normalized artifacts using the
  normalization implementation before reading feature inputs.
- For season Y targets, aggregate only retained, completed, regular-season
  FBS–FBS games from Y-1, joined by team ID. Never fall back to another season,
  impute missing history, or include incomplete games in aggregate denominators.
- Require every contributing game's scheduled start to precede the target's
  scheduled kickoff. Reject the target if this fails, rather than truncating
  its season aggregate. This checks chronology only, not actual completion or
  publication time.
- Use exactly `prior_win_pct_diff`, `prior_avg_margin_diff`, and `home_field`,
  in that order. Same-game scores, completion status, game/team IDs, prior-game
  counts, and provenance are not predictors. Outcome data stays only for audit
  and labels; future model code must select the explicit predictor list.
- Train targets are completed 2022–2024 games; holdout targets are completed
  2025 games. Uncompleted 2026 sample games receive no label. Earlier-season
  predictors never depend on later-season outcomes. Completed 2025 games may
  supply prior-season aggregates for 2026 inputs without entering training.
- Exclude uncompleted 2024 game `401640992` from both training labels and
  prior-season aggregates. Preserve zero scores for valid completed games.
- Record source hashes, row indices, contributing game IDs, sample counts,
  cutoffs, and all exclusion reasons so each reconstruction can be audited.

Later forecasting/evaluation tasks must establish point-in-time input selection,
publication evidence, historical versions and revision handling, and operational
cutoffs before making leakage-safe claims. Temporal splits and outcome-isolation
tests alone do not establish historical availability or predictive performance.
See [data-dictionary.md](data-dictionary.md) for exact current validation rules.
