# PM-06 monitoring verification — deployed, smoke sequence stopped

On November 20, 2026, PM-06 implemented private monitoring, failure alerts, human
review and a sanitized stakeholder draft. The original PM-06 round performed only
local tests and read-only AWS validation. PM-06B then deployed the fourteen
approved resources and successfully executed **one** saved-report monitoring
invocation. A local HTML comparison failed after Lambda returned completed;
the sequence stopped and both new functions were disabled as required.

There were zero review invocations, CFBD requests, outcome captures, Athena
queries, model fits, inference invocations or weekly executions. No subscriptions,
notifications or stakeholder publication occurred. Predecessors, protected
objects, bucket settings and the disabled weekly schedule were preserved.

## PM-06B actual AWS results

The approved proposal, template, ZIP, requirements, implementation and every
recorded file hash matched before cloud writes. All thirty packaged source files
equaled commit `e5143543c433eaac74f6803a91b19b06dc217479`; twenty dependency pins
matched. The artifact was uploaded once with a conditional write and read-back
hash verification. CloudFormation reached CREATE_COMPLETE with exactly fourteen
resources. Deployed code hashes, scoped role policies, runtime compatibility and
disabled delivery settings matched the proposal.

| Smoke step | Actual outcome |
| --- | --- |
| 1: saved Week 13 report | Lambda returned completed with no FunctionError; report, completion, both warning alerts and allowlisted JSON/HTML verified read-only after the controller stopped |
| 2: report replay | NOT RUN |
| 3–4: historical application-failure inspection/replay | NOT RUN; no new incident or failure-history alert claimed |
| 5–6: simulated alert/create replay | NOT RUN |
| 7–10: simulated acknowledgment/replay/investigation/closure | NOT RUN; no review records or personal investigation attestations written |
| 11: invalid request and metric/alarm observation | NOT RUN; no negative-test alarm transition claimed |

Actual invocation totals are **one monitoring, zero review**. CloudWatch records
one monitor invocation, zero monitor Errors, one REPORT line and no review or
predecessor invocations during the task window. The configured monitor executed
inside AWS Linux x86_64, with Python 3.14.10 and the protected producer's exact
numeric-library versions. Its REPORT measured 5,335.87 ms execution, 6,845.48 ms
initialization, 12,182 ms billed duration, and 301 MiB maximum memory of 1,536 MiB.
The review function did not execute, so its runtime/memory behavior is unverified.

The published saved-input report measured:

| Quality measure | Actual result |
| --- | ---: |
| Raw / retained / quarantined | 65 / 55 / 10 |
| Normalization exclusions / missing-history feature rejections | 0 / 2 (missing away history) |
| Technical scoring rows | 53 |
| Invalid features / invalid probabilities | 0 / 0 |
| Quarantine rate | 15.3846%; warning above 10% |
| Total exclusion rate / missing-history rate | 3.0769% / 3.6364%; below their thresholds |
| Source age at the fixed report as-of | 871.333337 seconds; below 86,400 seconds |

The as-of remains the approved **2026-11-20T22:30:00Z**; this is a saved observation,
not a claim about current wall-clock freshness. Distribution samples were 2,194
training rows versus 53 scoring rows, above the 30-row minimum:

| Feature | Indicator | Investigation threshold | Result |
| --- | ---: | ---: | --- |
| `prior_win_pct_diff` | PSI 0.2529945485983902 | > 0.20 | Warning |
| `prior_avg_margin_diff` | PSI 0.12048550080608399 | > 0.20 | No warning |
| `home_field` | Absolute rate difference 0.034184138559708255 | > 0.15 | No warning |

These descriptive differences do not establish concept drift or authorize
retraining. The two durable warning alerts are `quarantine_rate` and
`distribution_change_prior_win_pct_diff`. They describe the selected saved data,
not a newly occurring application failure. Neither alert was reviewed or closed.

With no outcomes selected, the report has **zero matched, 53 pending, zero
mismatched** labels and null rolling metrics/calibration. Batch-wide observed
label coverage is 0/53; the fixed past window contains zero eligible kickoffs,
so its coverage is null, not a measured 0% performance result. Historical holdout
metrics below remain a separate reference, not a new evaluation. All four
retrospective/unapproved flags persist, with no operational forecast approval.

Seven new immutable objects remain: one claim, three report/display artifacts,
one completion and two alerts. Hash/readback checks passed; stakeholder JSON is
the exact allowlist, and HTML matches the producer's original allowlist order.
No raw records, private identifiers or source hashes appear in the display.
All 84 protected predecessor object metadata snapshots remained identical, as
did predecessor configurations, execution history selection and bucket settings.

## Local controller failure and shutdown

Canonical JSON sorts object keys. The private controller incorrectly re-rendered
the parsed `stakeholder.json` in that sorted order and compared it byte-for-byte
with HTML built in the allowlist's intentional insertion order. The field values
and original HTML were correct. This was a **local verifier assertion**, not a
Lambda exception, source/model integrity failure or alert-worthy new incident.

The required failure procedure ran immediately: both new functions now have
reserved concurrency **zero**. The stack is retained at CREATE_COMPLETE, its
template concurrency remains one, and this temporary shutdown is intentional.
The failure-event rule and weekly schedule remain DISABLED; all four alarms have
actions disabled and no notifications. No invocation was retried or continued.
Evidence is preserved privately in
`data/processed/pm06b-deployment-20261120T233040Z/`.

The private controller comparison was corrected locally to validate fields and
render from the allowlist order. Three offline regression checks passed: sorted
JSON remains valid, extra fields fail, and altered HTML fails. No packaged
application, dependency, infrastructure or request identity changed. The original
approved hashes still apply. Further cloud work is stopped pending recovery
review; a prepared local recovery proposal would restore only the two new
functions and continue steps 2–11, with at most six remaining monitor and four
review invocations. It requires no upload, deployment or repeat of step 1.

The account remained ACTIVE on the Free plan. No upgrade, purchase, subscription,
Organizations enrollment or personal payment was requested. Logs had no detected
credential patterns, and no secret retrieval was needed. Raw reports, detailed
logs, resource identifiers, packages and private proposals remain excluded from Git.

## PM-06 local checks (historical implementation evidence)

| Check | Result |
| --- | --- |
| Focused monitoring/package tests | 23 passed (19 behavior/metrics and 4 policy/package tests) |
| Complete offline suite | 281 passed, 0 failures/errors; network blocked |
| Local template invariants and `cfn-lint` | Passed; 14 proposed resources |
| Final package CRC and exact source comparison | Passed; all 30 allowlisted project files equal current source |
| Pinned dependency closure | 20 exact versions; existing modeling requirements unchanged |
| Native binaries | 250 ELF64 little-endian Linux x86_64 files; maximum required GLIBC symbol version 2.27 |
| ZIP size | 79,041,784 bytes compressed; 224,162,981 bytes uncompressed, below 262,144,000-byte limit |

The focused tests exercise shifted/constant/binary features, small/empty/invalid
inputs, delayed/missing/mismatched/revised/future outcomes, chronological coverage,
existing evaluation metrics, withheld-versus-failed processing, successful Lambda
tasks returning failure objects, durable alerts, partial publication/replay,
review chains/races/conflicts/dispositions and strict stakeholder redaction.
The final privacy regression also proves failed Block Public Access preflight
cannot publish either a direct alert or a fallback failure alert; every write
rechecks all four controls.
Synthetic fixtures and stubbed producer verification do not establish live
performance or new-handler cloud execution. No model is fitted by these tests.

The package is
`data/processed/pm06-package-20261120-3/cloud-monitoring.zip`, SHA-256
`d502b32bafcc9a612a9550052f909c4a09acd07cc6cce613c9edda7ed306f2c0`.
It reuses the pinned Linux dependencies of the verified predecessor. Static ELF,
pin, quota and source checks do **not** establish dynamic compatibility: a local
compatible Linux execution environment was unavailable (the Docker CLI was
installed, but its configured local daemon socket was absent). The subsequent
PM-06B report execution above establishes the monitor's AWS runtime, but not the
unexecuted review handler or remaining smoke acceptance. The original 281-test
suite was not rerun for documentation-only PM-06B changes; the three new local
controller checks are reported separately.

## PM-06 read-only AWS checks (historical readiness evidence)

CloudFormation accepted the template. Access Analyzer reported no errors for
either role; each has the expected warning for literal `"*"` used with the
`s3:if-none-match` equality condition, not an unrestricted resource grant.
All **133 exact IAM request-context simulations** passed. They include every
object in the selected weekly closure, all nine protected model artifacts and
their producer claim/completion, exact-key list probes, max-keys one,
conditional output writes, isolated review writes and denial of unrelated
prefixes, oversized listings, original-data writes and pipeline starts.
These are policy simulations, not proof of deployed role behavior.

The account was ACTIVE on the Free plan with eligible credits. Read-only metadata
for required existing services was accessible; proposed named resources were unused,
and the existing weekly schedule remained DISABLED. No paid-only service,
upgrade, purchase, subscription or Organizations enrollment was requested.
Service metadata and plan access are readiness evidence, not a promise that
future resource creation can never encounter an account restriction. Recheck
coverage before deployment and stop if an upgrade is required.

Private parameters, selected references, exact IAM contexts, plan metadata,
package verification, bounded event templates, proposal and approval hashes are
Git-ignored under `data/processed/pm06-readiness-20261120/`. They are intentionally
excluded from this public summary.

## Historical evidence and still-pending measurements

The **previously verified PM-05C** Week 13 source had 65 raw records, 55 retained,
10 TBD-kickoff quarantines, two missing-history exclusions and 53 retrospective
predictions. PM-06 read back the selected completion to bind its hash; PM-06B later
verified those saved inputs in the deployed monitor as reported above.

The proposed report selects those immutable predictions and no later outcome
captures. PM-06B's actual result: zero matched labels, 53 pending across the selected
batch, no rolling metrics, and no claim of prospective performance. Its fixed
past observation window ends before these games; window eligibility is separate
from the batch-wide pending count. No rolling performance was measured.
A separately authorized later capture is needed before
rolling performance can be assessed.

The protected model's **previous PM-04C** retrospective holdout reference remains:

| Metric | Model | Constant baseline |
| --- | ---: | ---: |
| Brier score | 0.21061287148858282 | 0.24163577488303326 |
| Log loss | 0.6096025525960278 | 0.6763272181260667 |
| Accuracy | 0.6648648648648648 | 0.5918918918918918 |

Those values are not newly measured rolling performance. Historical availability
remains unknown; all retrospective/unapproved flags remain unchanged.

## Deployment acceptance still open

The [proposal/runbook](cloud-monitoring-runbook.md) bounded the deployment to 14
resources and eleven synchronous invocations. Deployment and one monitor call
completed; report/execution replay, historical application-failure detection,
simulated-alert/review chains and the invalid-request metric/alarm test remain
unverified in AWS because the sequence stopped. No further invocation is currently
enabled. The smoke also does not verify new weekly failure/
timeout alarm transitions, prospective outcomes, automatic rule delivery, external
notifications or public hosting. The failure-event rule and weekly schedule stay
disabled; alarms have no delivery actions. Acknowledgment never approves a model
or forecast. This slice does not complete operational forecasting.
