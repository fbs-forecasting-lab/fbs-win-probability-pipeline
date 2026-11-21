# PM-07C: bounded genuine sportsbook verification

## Result: capture, comparison and replay verified

On **November 21, 2026**, the approved PM-07B procedure captured a fresh Week 13
input, scored it inside AWS with the protected saved model, captured genuine
The Odds API moneylines and compared five strictly aligned games. Operational
publication remained withheld. No outcomes were selected: this verifies
probability comparison and coverage, **not market outperformance**.

All recorded approval hashes, local helpers and packaged sources matched commit
`60c95d167836f8dc71a31d2bd715e0f841d4a38e`. The operator confirmed Starter FREE
access and available credit, then created one secret through the reviewed hidden
Terminal procedure. Only secret metadata was read locally. The existing stack
was updated once with the unchanged template/ZIP; no artifact upload or new
CloudFormation resource was needed. Actual secret ARN/parameter/policy hashes
are preserved privately as approved response bindings.

Only the benchmark role's exact-secret `GetSecretValue` statement and benchmark
environment's `MARKET_SECRET_ARN` changed. All physical resource IDs, code,
runtime identities, explanation resources and predecessor configurations were
preserved. The role has no permission to change the secret, models or source data.

## Actual sequence and limits

| Step | Verified outcome |
| --- | --- |
| Fresh weekly execution | Four worker calls; one ingestion/CFBD attempt; one saved-model scoring batch; `workflow_completed=true`, state `withheld` |
| Market capture | One genuine current NCAAF US h2h request; 15 events, 22 normalized bookmaker markets, zero normalization exclusions |
| Capture replay | Same receipt, raw bytes, manifest, normalized outputs and metadata; no second HTTP request |
| Comparison | Five aligned DraftKings games from 53 eligible predictions; explicit reviewed identities and identical UTC kickoffs |
| Comparison replay | Same result and artifact bytes/metadata; no capture, scoring or additional secret read |
| Completed weekly replay | One worker call; same summary and all weekly artifacts/metadata; no ingestion or scoring |

Totals: **two state-machine executions, five weekly-worker calls, one ingestion
invocation/CFBD HTTP attempt, four benchmark invocations, one odds HTTP request
and one provider credit**. No automatic retries. Zero fits, Athena queries, LLM
requests, outcome captures or separate model-inference-function calls. All
allowances are exhausted; further workloads need separate authorization.

CloudWatch independently recorded five worker, one ingestion and four benchmark
invocations, with zero Lambda Errors. Ingestion logs contain exactly one
`cfbd_fetch_start`. There were no invocation datapoints for explanation,
preparation, training, separate inference, monitoring or review, and no Bedrock
invocation/token datapoints during the execution window. Completed stage receipts
and unchanged inference objects corroborate one scoring batch, without a refit.

## Observation times and counts

All times below are UTC on November 21. The approved common cutoff remained
**18:00:00Z**, latest start **17:20:00Z**. Nothing moved the cutoff or replaced tokens.

| Observation | Actual time |
| --- | --- |
| Fresh execution attempt | 05:26:07.064583Z |
| CFBD retrieval, HTTP 200 | 05:26:18.005397Z |
| Prediction object `LastModified` | 05:27:00Z |
| Odds request started | 05:28:17.344033Z |
| Odds retrieval completed, HTTP 200 | 05:28:17.412027Z |
| Frozen comparison `as_of` | 05:29:53.341099Z |
| Completed weekly replay attempt | 05:31:06.471938Z |
| Final protection checks completed | 05:31:58.022288Z |

CFBD returned **65** rows: **55 retained**, **10 quarantined for TBD kickoff**,
zero normalization exclusions. Two feature exclusions lacked away-team history;
**53** rows were technically eligible and scored. Historical training/holdout/
aggregate files and the protected model stayed unchanged. All original capture,
manifest and output hashes and source identities were verified.

Actual provider headers: `x-requests-last=1`, `x-requests-used=1`,
`x-requests-remaining=499`. This is quota consumption under the operator-confirmed
free account, not AWS credit coverage of a third-party service. The returned
markets comprised 14 FanDuel and eight DraftKings rows; the fixed bookmaker was
not substituted. All quote update/retrieval and model observation times passed
the strict pre-cutoff gate, with matched kickoffs after cutoff.

## Matching, coverage and limitations

A reviewed literal team-ID/provider-name crosswalk was constructed only from
the two genuine captured sources. The deterministic mapper then required exact
home/away orientation and UTC kickoff, with duplicate/reuse rejection. The
crosswalk, mapping, input identities, detailed review reasons and completed request
were hashed and frozen before comparison. No fuzzy matching, invented provider
IDs, time adjustment or second fetch was used.

**Five of 53** prediction-eligible games aligned: **9.433962264150944% coverage**.
Of eight DraftKings markets, five matched, one had a different scheduled kickoff
and two lacked prediction-eligible rows because the CFBD kickoffs were TBD.
The 48 unshared model rows remained explicit exclusions from the comparison;
missing quote coverage was never interpreted as a probability or label.

The five shared labels are pending, with zero matched outcomes and null paired
performance metrics. The observation window ended at the actual `as_of`, before
the games; its kickoff eligibility/coverage is separate from shared market
coverage. No Brier/log-loss advantage or betting-return claim is made. Individual
comparison rows, exact event IDs, raw odds and stakeholder output stay private.

Historical publication and schedule-revision availability remain unknown. All
four retrospective/unapproved flags and false operational approval persist.
This bounded observation neither validates future market coverage nor completes
rolling outcome evaluation, forecasting approval or recurring/public delivery.

## Runtime, preservation and remaining work

All work ran in the reviewed AWS Linux/Python 3.14 x86_64 runtime.

| Function | REPORT duration range | Maximum memory |
| --- | ---: | ---: |
| Weekly worker, five calls | 1,854.27–9,404.25 ms | 324 MiB |
| Ingestion, one call | 1,344.35 ms | 98 MiB |
| Benchmark, four calls | 319.94–4,774.53 ms | 304 MiB |

Benchmark capture billed duration was 8,353 ms including cold initialization;
handler duration alone was 1,216.93 ms. Timing/memory/usage records are measured,
not estimates. All 87 protected object bytes/metadata and all existing explanation
objects remained unchanged. Both insights functions remain active at concurrency
one; market access is now configured to the single secret. This is not permission
for additional calls. Schedules/rules, alarm actions, notifications and public
display remain disabled; bucket ownership, encryption, versioning and privacy
settings are unchanged. No resource was left disabled for failure.

One controller-only semantic assertion stopped before stack execution: CloudFormation
reported dynamic direct reevaluations alongside the two parameter-driven property
changes. The original stop was preserved. Eight private offline guard tests passed;
the correction accepts only those same properties, the exact secret parameter and
dependent role ARN. Read-only template/parameter/protection checks passed before
the same change set executed once. There was no workload failure or ambiguous
invocation, permission expansion, application change or redeployment.

The previous **336-test** offline application suite remains historical PM-07B
evidence; it was not repeated for these documentation/private-controller changes.
Whitespace, local documentation links, secret/private-identifier and attribution
checks passed before publication. AWS remained Free/Active, reporting $119.99
eligible credits; reporting can lag actual credit consumption. No paid activation,
upgrade, purchase or Organizations enrollment occurred.

Private evidence is ignored under
`data/processed/pm07c-execution-20261121T051251Z/`. It includes original failures,
response bindings, requests, complete responses, hashes, metadata, quota, source
lineage, mappings, replay snapshots and runtime logs. No key value was retrieved
into the local controller or committed. Later outcomes and any new observation
require a new bounded proposal/authorization; expired cutoffs must not be reused.
