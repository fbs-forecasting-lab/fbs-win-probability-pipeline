# Private monitoring and human-review contract

PM-06B deployed the fourteen approved resources; the tested PM-06C continuation
completed seven monitor/four review invocations in AWS without repeating the
first report. Replay, historical application-failure detection, simulated review
and the expected error alarm passed. Both functions are at concurrency one, with
automatic delivery disabled and the display private. Genuine alerts were not
reviewed or closed. Monitoring does not train, score, refresh data,
approve forecasts, or alter a predecessor. See the [runbook](cloud-monitoring-runbook.md)
and [verification summary](cloud-monitoring-verification.md).

## Explicit inputs and immutable identity

`monitor_contract.validate_report` accepts only version 1 `operation="report"`
requests with these fields:

| Field | Meaning and validation |
| --- | --- |
| `run_token` | Stable lowercase/digit/hyphen token, 8–64 characters; conflicting reuse fails. |
| `weekly_reference` | Exact `run_token_sha256` and `summary_sha256`; no latest-run lookup. |
| `model_reference` | Exact `model_id`, `training_token_sha256`, `training_receipt_sha256`; must equal both the weekly request and deployed approved model. |
| `outcome_sources` | Zero to ten explicit 2026 manifest/capture references, each with season, fixed manifest name, raw/manifest hashes and capture token/receipt hashes. No automatic capture. |
| `as_of` | Explicit timezone-aware observation boundary, canonicalized to UTC; source observations must not follow it. |
| `windows` | One to twelve ordered, nonoverlapping `[start,end)` kickoff windows; `start < end <= as_of`. |
| `review_reference` | Null, or exact alert ID, transition sequence and hash belonging to this same analysis. No mutable latest-review lookup. |
| `allow_retrospective_demo` | Must be `true`; does not grant operational approval. |
| `evidence_mode` | `saved_retrospective`, or explicitly `synthetic_test` in offline tests. Synthetic reports are disabled in the proposed deployment. |

`cloud_monitoring.inputs` verifies the weekly completion bytes and full artifact
closure with the existing stage verifier. Required feature/prediction rows must
match in game, season, week, teams and kickoff cutoff. The training CSV must match
the original model's recorded training hash. `model_evidence` verifies the trusted
producer claim, request/code/runtime identity, completion and all nine model
artifacts with existing model verification functions. It **does not deserialize
or execute the model**. Existing model/runtime compatibility remains mandatory.

The claim binds the canonical request, six-module monitoring implementation hash
and fixed policy. Reports are written under
`<prefix>/monitoring/runs/<token-sha256>/` as `report.json`, `stakeholder.json`,
`display.html`, then `complete.json` containing every artifact hash. All writes
are conditional `IfNoneMatch="*"`. Replay recomputes against the same verified
inputs, checks every published hash and returns the same completion. Identical
partial publication can finish; conflicting bytes or a damaged completed bundle
fail rather than repairing or overwriting evidence. Stable content-derived alert
IDs prevent duplicate alerts across replay and review-only report refreshes.

## Quality and distribution policy

Each private report contains source identities, as-of time, windows, sample sizes,
thresholds, measured values and limitations. Quality accounting checks raw =
retained + excluded + quarantined, feature eligibility and prediction counts.
Rejection reasons remain visible, including missing history and cutoff failures.
Features must be finite and in the existing domains; probabilities must be finite,
within [0,1], complementary, and unique by game ID. Invalid values are critical
indicators. A valid zero-row or withheld workflow is not a processing failure.

The versioned `monitor-policy-v1` uses investigation heuristics, not fitted alarm
thresholds or statistical tests:

| Indicator | Investigation threshold / minimum |
| --- | --- |
| Quarantined / raw | Greater than 10% |
| (Normalization exclusions + feature rejections) / raw | Greater than 20% |
| Missing-history rejections / retained | Greater than 5% |
| Observation age at explicit `as_of` | Greater than 86,400 seconds, or existing stale-schedule rejection |
| Numeric feature population stability index (PSI) | Greater than 0.20; training decile boundaries, unique cuts and 0.5 pseudocount smoothing |
| Constant training numeric feature | More than 10% of scoring values outside the reference, absolute tolerance 1e-12 |
| Binary `home_field` | Absolute scoring-minus-training rate difference greater than 0.15 |
| Distribution minimum | At least 30 valid rows in **both** reference and scoring sets |

PSI summarizes how two binned distributions differ; numeric means, bin cutpoints,
sample counts and binary counts are retained. Empty/small samples have descriptive
summaries and `insufficient_data`, without a measured-change claim. These coarse
thresholds support initial triage and need human assessment against sample size,
seasonality and selection changes. They do not establish concept drift, causation,
or a reason to retrain automatically.

## Later outcomes and probabilistic performance

`later_outcomes` downloads selected snapshots with the existing raw verifier and
checks their cloud-capture provenance. Observations must be later than the scoring
snapshot and forecast cutoff, and no later than `as_of`. The existing normalizer
validates them; these records go only to evaluation, **never** feature building.

`monitoring_metrics.performance` joins by immutable game ID and also requires the
same season, week, teams and scheduled kickoff. Schedule revisions, ties or
mismatched identities are not silently relabeled. Among explicitly selected later
observations it uses the latest timestamp; contradictory same-time outcomes fail.
Missing/uncompleted outcomes remain pending. Extra outcome games and mismatches
are counted separately. No label is invented and no source is selected implicitly.

Each chronological window needs at least 30 matched completed games and 80%
coverage of that window's predictions. Only then does the existing
`evaluate_probabilities` compute Brier score, log loss, accuracy and ten-bin
calibration. Otherwise metrics are null with `pending` or `insufficient_data`.
An empty label set is not zero error. A Brier increase over 0.05 or log-loss
increase over 0.10 versus the separate retrospective holdout reference requests
investigation; different populations and small windows limit that comparison.
No thresholds are tuned on the rolling outcomes.

The executed report selected no outcomes: all 53 labels remain pending, while
the existing holdout is clearly labeled retrospective. Even a
later measured window retains unknown historical availability and unapproved
status; matching later results alone does not prove prospective forecasting.

## Failure detection and durable alerts

`operation="execution"` takes only schema version 1 and a fixed workflow
`execution_arn`. `execution_run` reads that workflow's description/history; no
execution is started. Failed, timed-out and aborted executions create critical
alerts. It also inspects `LambdaFunctionSucceeded` output for `state="failed"`,
covering application failures that Lambda's Errors metric alone misses.
Successful `withheld` processing is not an incident. Running executions are
pending; terminal evidence is immutable and versioned by execution/history hash,
so a deliberately later redrive observation cannot replace the old one.

Alerts are immutable `monitoring/alerts/<content-id>/alert.json` objects with code,
severity, evidence, recommended investigation, simulation marker and explicit
denials of retraining/publication authorization. Processing failures attempt a
durable critical alert, and the handler raises a sanitized exception for its own
Errors metric. A hard timeout or inability to access S3 cannot guarantee an S3
alert: independent health alarms and operator reconciliation remain necessary.
The proposed EventBridge rule is **disabled**, and all four alarms have no
actions. See the runbook for best-effort delivery and activation limits.

`operation="simulate_alert"` is separately gated, strictly bounded and always
marked simulated. It tests review/deduplication without classifying a genuine
event as investigated. It does not enable synthetic reports or source capture.

## Human review and stakeholder draft

`cloud_review.review_run` requires an exact alert ID/hash, previous sequence/hash,
stable transition token, configured reviewer, actual UTC timestamp, structured
reason, evidence hashes and explicit `simulation` boolean. The chain is:

`unreviewed → acknowledged → investigating → closed`

Closing requires an explicit disposition: confirmed issue, false positive,
expected withholding or follow-up needed. Timestamps increase; the first must
not precede a timestamped alert. Conditional numbered slots reject concurrent
branches. Token claims and slots make identical replay safe and conflicting
replay fail. A simulated review cannot dispose of a genuine alert.

Reviewer identity is **attested by the private IAM invoker**, matched to the
configured name; this handler is not a separate human authentication system.
Evidence hashes are recorded, not independently fetched or adjudicated. The
operator must retain the actual investigation evidence privately. Acknowledgment,
investigation and closure never grant retraining or forecast approval.

`monitoring_view.stakeholder` creates a separate strict allowlist of status,
freshness, counts, distribution indicators, performance availability and selected
review state. It omits raw rows, teams, hashes, bucket/account/ARN references and
reviewer identity. HTML escapes every value. These files remain a **private draft**;
no hosting, public endpoint or publication is included. A selected review state
describes that one alert, not resolution of all alerts.

All dataset/report/review outputs preserve `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`, `approved_for_predictor_use=false` and
`approved_for_point_in_time_forecasting=false`.
