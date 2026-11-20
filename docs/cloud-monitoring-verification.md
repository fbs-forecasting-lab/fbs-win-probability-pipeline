# PM-06 monitoring verification — prepared, not deployed

On November 20, 2026, PM-06 added private monitoring, failure alerts, human review
and a sanitized stakeholder draft on top of the verified weekly pipeline.
**No monitoring function has been deployed or executed in AWS.** There were no
cloud writes, CFBD requests, queries, fits, inference invocations, weekly
executions, subscriptions, notifications or public publications in this round.
Read-only AWS validation was separately authorized. Prior deployments and the
disabled weekly schedule were preserved.

## Newly executed local checks

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
installed, but its configured local daemon socket was absent), and the two new handlers
still require the approved deployment smoke. Previous AWS Linux weekly/modeling
success is predecessor evidence, not a monitoring-runtime result.

## Newly executed read-only AWS checks

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
predictions. PM-06 read back the selected completion to bind its hash; it did not
run the new monitor over that real dataset locally or in AWS.

The proposed report selects those immutable predictions and no later outcome
captures. Expected result: zero matched labels, 53 pending across the selected
batch, no rolling metrics, and no claim of prospective performance. Its fixed
past observation window ends before these games; window eligibility is separate
from the batch-wide pending count. These are smoke expectations, not measured
PM-06 cloud results. A separately authorized later capture is needed before
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

The [proposal/runbook](cloud-monitoring-runbook.md) bounds approval to 14 new
resources and eleven synchronous invocations: seven monitor and four review,
with zero predecessor workloads. It tests real saved-input verification, replay,
historical application-failure detection, explicit simulated-alert review and an
expected invalid-request Errors metric. It does not verify new weekly failure/
timeout alarm transitions, prospective outcomes, automatic rule delivery, external
notifications or public hosting. The failure-event rule and weekly schedule stay
disabled; alarms have no delivery actions. Acknowledgment never approves a model
or forecast. This slice does not complete operational forecasting.
