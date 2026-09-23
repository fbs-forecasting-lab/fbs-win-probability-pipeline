# Data Leakage Policy

## Current Scope

The ingestion and normalization slices preserve evidence and validate game tables.
They do not produce a feature matrix, train a model, approve predictor inputs, or
establish that historical values were available before kickoff. All normalized
rows and reports retain `approved_for_predictor_use=false`.

## Four Different Times

| Time | Meaning | Current treatment |
| --- | --- | --- |
| Source event time | When an event is scheduled or occurs. CFBD `startDate` is a scheduled kickoff, not a publication timestamp. | Normalize to UTC only from a timezone-aware value. Quarantine unresolved or invalid kickoff times. Do not infer actual completion or publication time. |
| Snapshot retrieval time | When this project received the API response (`retrieved_at`). | Preserve the source snapshot retrieval instant on every normalized row. It proves observation at retrieval, not before it. |
| Historical availability | When a particular source value/version was published and could actually be known. | Preserve the original manifest status. Current snapshots have status `unknown` and `available_at=null`. Do not substitute kickoff, retrieval, season/week, or a field's name. |
| Future forecast cutoff | The explicit instant at or before kickoff at which a prediction is frozen. | Not yet defined or implemented. The next feature design must specify the cutoff, timezone, reschedule handling, and availability evidence for each input. |

All normalized timestamps use UTC. Naive timestamps are rejected rather than
assumed to be UTC. Retaining a valid schedule timestamp does not verify which
schedule version was known before a historical cutoff. Snapshot integrity and
complete field coverage are not evidence of historical availability.

## Outcomes and Predictor Boundaries

`completed`, `home_points`, and `away_points` are retained outcome data. Scores,
postgame ratings/probabilities, and completion status must never be used as
predictors for that same game. Completed-game scores may later produce labels.
Prior-game scores may later contribute aggregates only after verifying those
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
- Keep repeated snapshots separate. No cross-snapshot merging, feature aggregates,
  labels, temporal evaluation split, or forecast cutoff is implemented here.

The later feature/model tasks must document point-in-time input selection,
publication evidence and revision risks, chronological training/evaluation
boundaries, and same-game outcome exclusion before making leakage-safe claims.
See [data-dictionary.md](data-dictionary.md) for exact current validation rules.
