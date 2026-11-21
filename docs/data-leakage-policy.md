# Data Leakage Policy

## Current Scope

The ingestion and normalization slices preserve evidence and validate game tables.
The dataset slice produces explicitly permitted retrospective demo predictors
and labels under the limited reconstruction assumption below. The baseline
fits only on 2022–2024, evaluates on 2025 without tuning/refitting, and uses the
same fitted model for saved 2026 inputs. No slice approves predictor inputs or
establishes that historical values were available before kickoff. Source and normalized records retain
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

PM-06's [monitoring contract](monitoring-contract.md) keeps later outcome captures
in an evaluation-only branch. It requires explicit source/capture hashes, a later
observation than the scoring snapshot and forecast cutoff, and an as-of bound.
Game/team/season/week/kickoff identities must match; revised schedules are not
silently relabeled. Outcomes never enter feature construction. Missing labels
remain pending, and rolling windows require sufficient coverage before metrics.
Neither distribution indicators, measured outcomes nor a human acknowledgment
change historical-availability or approval flags, or authorize retraining.
The PM-06B/PM-06C bounded AWS smoke verified saved-input monitoring, replay and
explicitly simulated review without another capture, model fit or scoring call.
All 53 labels remain pending; no prospective performance is verified. Functions
are at concurrency one, with delivery disabled and the display private.

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
  and labels; baseline training and inference select the explicit predictor list.
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

## Cloud capture observation evidence (PM-02C; ingestion verified)

The cloud adapter records claim start, API retrieval/observation, failure and
completion times separately. Request identity explicitly includes the requested
season and optional week. A durable capture checkpoint and final object hashes
allow retries to reuse exactly the same observation; a token never means
"whatever is latest." Claim expiry diagnoses interruption and does not grant
permission to refetch or overwrite. See the [runbook](cloud-ingestion-runbook.md).

These times do not define forecast issuance time or prove historical publication
availability. The existing manifest format still has unknown availability, null
`available_at`, and `approved_for_predictor_use=false`. Receipts retain all
retrospective/unapproved status flags. Prospective capture evidence must not
retroactively certify September backtests. Operational cutoff selection,
reschedules, and source-version eligibility remain separate implementation work.

The November 20 cloud verification captured 70 records and preserved these limits
through replay and conflict rejection. Successful AWS execution establishes the
capture mechanism, not point-in-time forecasting approval. See the
[sanitized verification summary](cloud-ingestion-verification.md).

## Cloud preparation (PM-03D; deployed and verified in recovery-only mode)

One explicitly hashed snapshot per season is isolated in a deterministic query
partition. SQL does not combine all versions as independent games; target
outcomes enter labels only. Missing history is an explicit exclusion, not zero
strength or imputation. Capture-receipt verification proves origin and bytes,
not historical availability. Legacy uploads cannot satisfy a cloud-source
requirement.

All four retrospective/unapproved flags are unchanged. `forecast_cutoff`
rejects observations/publications at or after that instant; earlier observation
still cannot approve operational use. The operational path fails closed. See the
[preparation runbook](cloud-preparation-runbook.md) for future evidence needs.
November 20 AWS recovery verified actual Athena/Python parity, publication,
replay and cutoff refusal. That execution evidence does not establish historical
availability or approve forecasts. New query creation is explicitly denied in
the current recovery-only deployment.

## Cloud modeling (PM-04C; AWS verified November 20, 2026)

The training adapter verifies the pinned preparation completion and all six
dataset hashes before reusing the existing train-only scaler/logistic fit.
Holdout outcomes are used only for evaluation, with no tuning/refit. The constant
comparison uses training labels. Model metadata and coefficient interpretation
retain the training/scaling context. Independent inference reloads only a model
from the protected trainer domain after claim/completion/companion-hash checks;
hashes alone do not authorize arbitrary serialized objects.

All results keep retrospective mode and false availability/predictor/forecasting
approval. A valid cloud model or probability does not establish historical source
availability or operational eligibility. The saved Week 12 split remains a saved
snapshot; a hypothetical vector remains hypothetical. No later capture or source
substitution is used to improve sample coverage. The bounded AWS run verified
train-only fitting and model reload without changing these safeguards; it made
no new CFBD request or Athena query. See the
[modeling runbook](cloud-modeling-runbook.md).

## Weekly technical eligibility (PM-05C; AWS verified November 20, 2026)

The weekly contract pins season/week, source versions, model, forecast cutoff and
stable run identity. Source observations and any known publication times must
precede cutoff; weekly schedule observations older than 24 hours are stale.
Scheduled kickoff must strictly follow cutoff, including after UTC-offset
normalization. Completed, scheduled-started, TBD and missing-history rows are
excluded/quarantined with reasons. Selected prior schedule evidence can reject a
game moved later after an earlier recorded start. Original evidence is immutable.

These are technical row checks, not proof of actual kickoff, historical completion
or publication. Unknown timestamps are never invented from capture time. Current
models/sources stay retrospective and unapproved; completed processing explicitly
withholds operational publication even when rows are technically eligible. Weekly
inference verifies the original model and unchanged training/holdout/aggregate
hashes, with separate new scoring-input provenance and no fit. Alerts may request
review, never automatic retraining. See the [weekly contract](weekly-cloud-contract.md).

Cloud verification preserved these controls: the cutoff-equality event produced
zero eligible rows and zero predictions, and the distinct Week 13 input produced
53 retrospective predictions with the same protected model and no fit. All
processing completions remained withheld/unapproved; no source publication time
was invented. The schedule stays disabled. See the
[dated verification](weekly-cloud-verification.md).

## Explanation and market timing (PM-07; local implementation)

The explanation adapter sends only an allowlisted factual catalog from verified
monitoring artifacts. Its provider selects exact fact sentences; it cannot
introduce metrics, replace probabilities, change pending/failed states or approve
publication. LLM output is not an authoritative measurement or availability
attestation. Invalid responses leave explanation unavailable without a generated
fallback claim. No external call has been verified for this new adapter.

Sportsbook observations are benchmarks only, isolated from predictors, labels,
fitting and model selection. An explicit provider-event/CFBD-game map must preserve
home/away identity and kickoff. A market needs its own update timestamp and actual
retrieval time; bookmaker-level metadata cannot replace a missing market update.
Both retrieval and update must strictly precede the verified weekly cutoff.
The model prediction object's recorded S3 observation time must also precede
cutoff, which itself precedes scheduled kickoff. Equality is ineligible.

S3 observation time and market retrieval establish recorded observation, not
historical public availability. Neither an older quote timestamp nor later
historical/closing-price API access proves the quote was available at an old
cutoff. The saved Week 13 cutoff has passed: a fresh current capture yields no
aligned pre-cutoff evidence for it. Paid historical access, fabricated markets
and weaker eligibility are excluded. Later outcomes use the existing verified
evaluation-only path; paired metrics require the exact same eligible games and
coverage thresholds for model and bookmaker. Unknown labels remain pending.
All original retrospective flags and withheld publication persist; genuine
external market evidence remains unverified. See the
[contract](stakeholder-insights-contract.md).
