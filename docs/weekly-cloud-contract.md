# Weekly cloud request and evidence contract (PM-05)

**Implemented locally; deployment and end-to-end cloud verification are pending.**
The [runbook](weekly-cloud-runbook.md) describes the concrete proposal and limits.

## Explicit version-one request

All fields below are required. Unknown fields, URLs, naive timestamps and missing
retrospective permission fail before a stage starts. References never mean latest.

| Field | Contract |
| --- | --- |
| `schema_version` | Integer 1 |
| `season` | Integer 2026; the existing fixed feature builder/model is not generalized to later seasons |
| `week` | Explicit integer 1–99; no automatic rollover |
| `forecast_cutoff` | Timezone-aware ISO timestamp, canonicalized to UTC; comparisons retain microseconds |
| `run_token` | Stable 8–64 lowercase letters/digits/hyphens; first character alphanumeric |
| `history_sources` | Exactly one full-season cloud capture reference for each year 2021–2025 |
| `model_reference` | Exact `model_id`, `training_token_sha256`, `training_receipt_sha256`; deployment pins the approved reference |
| `scoring_source` | Either `{"mode":"reuse","source":<explicit 2026 cloud reference>}` or `{"mode":"capture","capture_token":<stable token>}` |
| `previous_run` | Null or exact `run_token_sha256` and `summary_sha256` for a prior run of this same season/week |
| `allow_retrospective_demo` | Boolean true; this grants no operational approval |

A source reference contains `season`, a 32-character snapshot identifier plus
`.manifest.json` as `manifest_name`, and four lowercase SHA-256 identities:
`raw_sha256`, `manifest_sha256`, `capture_token_sha256`, `capture_receipt_sha256`.
The manifest and original capture checkpoint/completion are verified against
actual bytes. Weekly scoring checks the manifest's exact requested week. History
must use full seasons; existing captures are read, never fetched again.

## Durable identity and stage contracts

`weekly_contract.identity` hashes the token separately from the canonical request
and implementation identity. The claim at
`initial-demo/weekly/runs/<token_sha256>/claim.json` binds the full request and
code. A changed week, cutoff, source, model, revision reference or implementation
cannot reuse that token. Same-name Standard executions also have AWS's own
execution identity rules; the durable S3 claim remains the processing guard.

`cloud_weekly.advance` advances at most one stage per invocation:

1. **Ingestion:** reuse an explicit capture, or write a conditional invocation
   intent before calling only the existing ingestion function. Only its owner
   invokes. Ambiguous responses are followed by S3 receipt/status checks, never
   another invocation, token or API fetch. The ingestion ledger independently
   protects one HTTP attempt per capture token.
2. **Preparation:** download and verify all six sources, reuse
   `games.normalize_snapshot` and `dataset.build_dataset`, and publish normalized
   records/exclusions/quality, six dataset files, schedule, eligibility, selected
   rows and provenance. This is a separate Python weekly-preparation interface;
   it does not call or reconfigure recovery-only Athena preparation.
3. **Inference:** reuse `cloud_modeling.trusted_model` before deserialization.
   Verify the original protected training identity/runtime and all model hashes.
   Require byte-identical train, holdout and aggregate files relative to the
   original model metadata. Use `baseline.feature_frame`, `home_probabilities`
   and `prediction_csv` for the new scoring rows. Never fit a model/scaler.
4. **Summary:** verify every stage artifact, stage receipt, source pair/capture,
   protected model artifact and original training claim/completion before the
   terminal receipt is published. Scoring-input provenance and the model's
   training provenance have separate identities.

The legacy prediction CSV's `cutoff` column still means scheduled kickoff. The
weekly `forecast_cutoff` is separately bound in request, eligibility and prediction
provenance; these two times must not be confused.

Each stage publishes immutable bytes with a final `complete.json` marker and
artifact hashes. Matching partial publication may resume; completed missing or
conflicting artifacts are never repaired. Pure normalization/build/scoring may
be recomputed during explicitly reviewed publication recovery, without fetching,
querying or fitting. Completion replay verifies the entire recorded hash closure
without invoking ingestion, model reload, query or training. Failed attempts
have sanitized stage/type receipts under `failures/`; an ambiguous capture intent
remains visible even if no failure receipt could be written.

## Eligibility is not approval

Technical row selection requires all selected source observations to be strictly
before the cutoff, any known publication time to be strictly before it, the
weekly schedule observation to be at most 24 hours old, and scheduled kickoff to
be strictly after the cutoff. Completed/started-by-schedule games, missing prior
history and prior-game scheduled starts at/after the cutoff are excluded. TBD or
malformed rows retain normalization quarantine reasons. No rows are fabricated
to replace exclusions; zero eligible rows produce zero predictions.

When `previous_run` is selected, the earlier summary and its evidence are hash
verified. An earlier recorded kickoff at/before the new cutoff or changed
opponents quarantines the revised matchup, even if the new schedule moves it
later. Both observations and summaries are preserved. Without a selected prior
version, absence of revisions or actual kickoff cannot be established. Explicit
UTC offsets are normalized; neither schedule chronology nor observation time is
substituted for historical publication/completion evidence.

All current sources/models remain retrospective and unapproved. Even technically
eligible rows produce **retrospective demonstration predictions only**. A finished
workflow reports `state=withheld`, `workflow_completed=true`, technical counts,
`operational_forecast_approved=false`, and explicit withheld reasons. The four
existing status fields remain retrospective/false. This is a successful processing
outcome with operational publication withheld, not a live forecast approval.

`state=pending` identifies the next unfinished stage. The Standard workflow waits
15 seconds between advances, permits at most eight advances and has an 1,800-second
overall timeout; each Lambda task is bounded to 310 seconds (worker timeout 300).
There is no Task retry policy. Failed stages stop the workflow; pending work at
the bound remains incomplete and requires reviewed recovery. Local clients start
the explicit execution and inspect progress; they do not perform preparation or
prediction. Alerts may request investigation, never automatic retraining.
