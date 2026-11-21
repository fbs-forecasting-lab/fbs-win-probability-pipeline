# Stakeholder explanation and sportsbook benchmark contract

PM-07 adds two private cloud adapters. They are implemented and tested offline,
but neither external integration has been executed. See the
[verification record](cloud-stakeholder-verification.md) and
[deployment runbook](cloud-stakeholder-runbook.md). The original predictor,
training procedure, operational approval controls and deployed predecessors are
unchanged.

## Shared request and storage rules

`insights_contract.validate` requires schema version 1, a stable `run_token`,
`allow_retrospective_demo=true` and exactly the fields for the selected operation.
There is no arbitrary prompt, free-text explanation, endpoint, model selection,
credential or operational action in the request. Artifact references contain
explicit SHA-256 identities. Unknown fields, invalid types and duplicate JSON
keys fail; nonfinite numbers are rejected.

`InsightsStore` reuses existing source verification and private-bucket checks.
Token claims bind the canonical request, implementation and configuration.
Writes are conditional and confined to the adapter's own `stakeholder/` domain.
Every write checks all four bucket public-access blocks. Missing optional
objects use exact-key `ListObjectsV2` probes with `MaxKeys=1`; access denial is
never absence. A conflicting request/code/configuration cannot reuse a token.

Before external work, an immutable attempt marker consumes the token's one
attempt. A completed response is checkpointed with its claim and content hashes.
An interrupted publication reuses that checkpoint. A marker without a response
returns `attempt_unresolved`: the call may already have occurred, so another
call or guessed completion is forbidden. Completed replay verifies artifact
hashes; it does not invoke either provider. Existing bytes are never repaired
or overwritten to manufacture success.

All result paths retain `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`,
`approved_for_point_in_time_forecasting=false` and
`approved_for_predictor_use=false`. Operational approval remains false.

## Explanation: `operation=explain`

The input is one `monitor_reference` with `run_token_sha256`,
`completion_sha256` and `report_sha256`. The adapter verifies the monitoring
producer implementation, original claim, completion, report, stakeholder JSON
and private HTML before building an allowlist of facts. It does not send these
objects wholesale to the provider.

The provider receives only bounded factual sentences about:

- Retrospective status, unknown historical availability and withheld publication.
- Quality counts and technical scoring-row count.
- Distribution-check state, measured sample sizes and investigation indicators.
- Pending/matched outcome counts and performance state.
- Historical holdout model and constant-baseline metrics, explicitly labeled as
  historical references, when present in the verified report.
- Limitations: distribution changes are not concept drift or authorization for
  retraining, forecast approval or alert closure.

Private identifiers, resource names, raw games, team names, keys, free-text
review evidence and unrestricted user text are excluded. Failed or undersized
measurements remain unavailable; they are not presented as zero measured change.

The selected provider is **Amazon Bedrock, Amazon Nova Micro**,
`amazon.nova-micro-v1:0`, direct regional on-demand inference in `us-east-1`.
The application calls `Converse` with a fixed instruction and the fact catalog:
at most 6,144 input bytes including that instruction, 128 output tokens,
temperature zero, a 5-second connection timeout, a 20-second read timeout and
one total SDK attempt. The response checkpoint is bounded to 8,192 bytes.
There is no cross-region profile or fallback model. IAM authorizes only this
foundation-model ARN; the application needs no provider secret.

This is deliberately an **extractive LLM summary**. A genuine model call selects
and orders three to seven verified fact identifiers. `status`, `performance`
and `limits` are mandatory. Only exact corresponding source sentences are
rendered, never free-form provider prose or provider-supplied numbers. Unknown
facts, duplicates, extra fields, incomplete output, invalid token usage or a
non-`end_turn` response make the explanation unavailable. The factual report
remains available. A deterministic or mocked selection is not substituted for
a failed real call, and an unavailable explanation is not reported as generated.

Outputs are `facts.json`, `explanation.json`, private `display.html`,
`provenance.json` and a hash-bound completion receipt, beneath
`stakeholder/explanations/<token fingerprint>/`. Provenance records the actual
provider request ID, returned usage/latency when present, response identity,
model/region, input identity and fixed limits. Absence is not filled with invented
usage or timing. Explanation text cannot change metrics/probabilities, review
alerts, publish forecasts or trigger training.

## Market capture: `operation=capture_market`

The source is The Odds API v4 **current** NCAAF moneyline endpoint. Request fields
are `window_start`, `window_end` and `odds_format` (`american` or `decimal`). The
window is positive and at most fourteen days. Sport, US region and `h2h` market
are fixed; there is no arbitrary URL, historical endpoint, retry or redirect.

One HTTPS attempt uses a 5-second connection timeout, 15-second read timeout,
25-second response-body deadline and 4 MiB body limit, bounded additionally by
the Lambda timeout. A credential is read only from the exact configured Secrets
Manager ARN. It is never accepted in events, written to provenance, displayed,
or included in logged errors. Error bodies and request URLs containing the key
are not retained. An unset secret is refused before client creation or HTTP;
credential retrieval failure consumes the token's attempt slot but makes no
HTTP request. Ambiguous HTTP outcomes never permit a fresh attempt automatically.

Successful capture preserves exact `raw.json` bytes and a `manifest.json` with
request parameters excluding the key, request/retrieval times, status, count,
raw SHA-256, numeric provider quota headers when supplied, and safeguards.
`markets.json`, `quality.json` and a completion receipt follow normalization.
All are private beneath `stakeholder/market-captures/<token fingerprint>/`.

`markets.normalize` preserves provider event/team identities, bookmaker, two
prices, kickoff, market-level `last_update`, retrieval time and source identity.
The deprecated bookmaker-level update time is retained only as metadata; it
cannot replace a missing market timestamp. Duplicate identities, ambiguous
bookmakers/moneylines, non-two-way markets, malformed prices, missing timestamps
and timestamps after retrieval are excluded with reasons.

Decimal odds greater than one imply `q=1/price`. American odds imply
`q=100/(price+100)` for positive prices, or
`q=(-price)/((-price)+100)` for negative prices; absolute price must be at least
100. For a two-way market, the documented overround removal is proportional:
`p_home=q_home/(q_home+q_away)`, `p_away=1-p_home`.
`q_home+q_away-1` is retained as the overround, including a possible underround.
This is a comparison convention, not a betting-return or market-efficiency claim.

## Comparison: `operation=benchmark`

The request pins `weekly_reference`, `model_reference`, `market_reference`,
`as_of`, evaluation `windows`, separately selected `outcome_sources`, bookmaker
`draftkings`, and an explicit `event_map`. Each mapping supplies CFBD game/home/
away IDs plus provider event ID and exact provider home/away names. Duplicate,
ambiguous, reversed or unrelated matches fail or are excluded; there is no fuzzy
team-name matching or retrospective selection of a better bookmaker.

The adapter reuses `cloud_monitoring.inputs` to verify saved weekly predictions,
the protected model/training lineage, input hashes and completion. It never
reloads or executes the prediction model. Capture artifacts and normalization
are independently reverified. Prediction-object S3 `LastModified` supplies the
recorded model observation time; it is not proof of historical publication.

A shared row requires identical game/team orientation and scheduled kickoff,
model observation **before** the original verified weekly forecast cutoff,
market retrieval **before** cutoff, market update **before** cutoff, and cutoff
**before** kickoff. Observation times must also be at or before `as_of`.
Equality at cutoff is ineligible. The event cannot replace the source cutoff.
An older quote timestamp does not make a newly retrieved quote available in the
past. Historical/closing prices cannot be certified without matching evidence.

Without later outcomes, report only aligned probability differences, coverage
and pending/insufficient performance states. Later labels use the existing
verified outcome-selection branch solely for evaluation. Paired Brier/log-loss
metrics use the exact same shared games and windows for model and bookmaker,
with the existing minimum of thirty matched labels and 80% window coverage.
No shared rows means `no_aligned_market_data`, zero shared coverage when model
rows exist, and unavailable paired metrics. No missing probability or label is
invented. Zero aligned rows is not evidence of model superiority.

`benchmark.json`, a scalar-allowlisted private `stakeholder.json` and a completion
receipt preserve identities, timing, rejection reasons and outcomes lineage.
Market values never enter predictors, training labels, fitting, model selection
or operational approval.

## Access and external evidence still required

Read-only AWS metadata reports the selected first-party model authorized and
available with positive on-demand quotas under the active Free plan. This is
readiness evidence, **not a completed model call or a guarantee of future access**.
Phase A can verify one real explanation, replay and refusals without market access.

No project market key is configured; the third-party account plan/quota and
bookmaker/event availability are unverified. Historical odds require paid access
and are excluded. The saved Week 13 cutoff has passed: current odds retrieved
later must yield zero aligned rows for that cutoff. Genuine nonzero benchmarking
needs separately approved, aligned future observations or existing eligible
capture evidence. Synthetic tests cannot fill either external-evidence gap.

Primary references: [Bedrock Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html),
[Nova Micro](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-micro.html),
[AWS Free-plan services](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html),
and [The Odds API v4](https://the-odds-api.com/liveapi/guides/v4/).
