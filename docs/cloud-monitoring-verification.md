# PM-06 monitoring verification — bounded AWS smoke complete

On November 20, 2026, PM-06 implemented private monitoring, failure alerts, human
review and a sanitized stakeholder draft. The original PM-06 round performed only
local tests and read-only AWS validation. PM-06B then deployed the fourteen
approved resources and successfully executed **one** saved-report monitoring
invocation. A local HTML comparison initially stopped the controller, followed
by a separate recovery-wrapper metadata parsing stop. Both failures and shutdown
evidence remain preserved. The authorized tested PM-06C continuation then passed
read-only verification, restored only the two functions and completed steps 2–11
without repeating step 1 or changing the application/deployment.

Final cumulative counts are **seven monitoring and four review invocations**.
There were zero CFBD requests, outcome captures, Athena queries, model fits,
inference invocations or weekly executions. No subscriptions, notifications or
stakeholder publication occurred. Predecessors, protected objects, bucket settings
and disabled delivery controls were preserved.

## PM-06C completed continuation (November 20, 2026, Eastern time)

The continuation rechecked all original/recovery/continuation hashes, the tested
controller/wrapper, all thirty packaged source files against the approved commit,
twenty dependency pins and the preserved report/claim/alerts/completion. The
fourteen resource identities, deployed code, role policies, runtime ARN, bucket
protections and predecessor evidence matched. Runtime update mode was verified
through `GetRuntimeManagementConfig`; the actual reviewed runtime ARN was checked
through `GetFunctionConfiguration`, without inventing a manual ARN.

Only `fbs-pipeline-monitoring` and `fbs-monitoring-review` were restored to
reserved concurrency **one**. The stack remains CREATE_COMPLETE. The continuation
made no artifact upload, redeployment, new resource or permission change. Its
private evidence is `data/processed/pm06c-recovery-20261121T021113Z/`; the UTC path
date is November 21 while local execution was November 20.

| Step | Verified outcome |
| --- | --- |
| 1: original report | Accepted from verified preserved evidence; **not invoked again** |
| 2: report replay | Same completion, report, private JSON/HTML and alerts; all seven existing object bytes/metadata unchanged |
| 3: historical application failure | Read the selected existing failed execution; detected one `state=failed` output from a successful Lambda task and published a critical alert with verified evidence |
| 4: execution-report replay | Same result, alert and evidence; object bytes/metadata unchanged |
| 5: simulated alert | Created one informational alert explicitly marked simulated |
| 6: simulated-alert replay | Same alert bytes/metadata; no duplicate |
| 7: simulated acknowledgment | Verified numbered review 001, actual timestamp, factual automated-test evidence and token claim |
| 8: acknowledgment replay | Same review 001 and token; no duplicate transition or metadata change |
| 9: simulated investigation | Verified review 002 and exact preceding review hash |
| 10: simulated closure | Verified review 003, explicit simulated disposition and exact preceding hash; no forecast/retraining authorization |
| 11: invalid request | Expected RuntimeError FunctionError; no report, alert or stored-object mutation |

This continuation used exactly **six additional monitor and four review calls**;
no allowance remains from the cumulative seven/four bound. CloudWatch corroborated
seven monitor invocations with **one expected error**, four review invocations
with zero errors, and zero invocations of all five predecessor functions during
the evidence window. Eleven REPORT lines independently matched these counts.
No workload was automatically retried.

The invalid request completed at 03:24:55.925215Z on November 21 UTC. Its Errors
metric reached one and the monitoring alarm was observed in **ALARM** at
03:26:09.527586Z, **73.602371 seconds** later, within the unchanged 600-second
deadline. No alarm state was forced. All four alarms retained disabled actions;
there was no notification. The alarm can subsequently return to OK naturally.

| Function | AWS execution | REPORT duration range | Maximum memory / configured |
| --- | --- | ---: | ---: |
| Monitoring | Seven calls, Python 3.14 / Linux x86_64 | 4.78–5,760.78 ms | 303 / 1,536 MiB |
| Review | Four calls, Python 3.14 / Linux x86_64 | 244.51–831.43 ms | 98 / 512 MiB |

The protected runtime remains Python 3.14.10 with unchanged pinned libraries.
The saved report retained 53 pending labels and exactly the quality/distribution
findings below; holdout values remain historical reference metrics, not new
evaluation. Report replay did not create a second report or change freshness's
explicit as-of boundary.

All four alert hashes, both completion bundles, three review records and three
review-token claims were verified. Exactly **eighteen monitoring objects** remain.
Only the simulated informational alert has a review chain. Its private evidence
explicitly records automated smoke actions, not personal participation or genuine
incident investigation/closure. The configured reviewer name is authorization
context; invocation timestamps and evidence hashes were independently checked.
The historical critical alert describes a previously stopped execution, not a
new failure. All three genuine saved-data/historical alerts remain unreviewed.

All 84 protected predecessor object metadata snapshots and predecessor
configurations/execution lists remained identical. Both functions remain at
concurrency one; the weekly schedule and monitoring rule remain DISABLED, all
alarm actions are disabled, and the allowlisted stakeholder display remains a
private report-specific draft. It does not imply that genuine alerts were reviewed.
The account remained ACTIVE on the Free plan with eligible credits; no upgrade,
purchase, subscription, Organizations enrollment or personal-payment action ran.

## PM-06B first report (historical, before continuation)

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

PM-06B invocation totals were **one monitoring, zero review**. CloudWatch recorded
one monitor invocation, zero monitor Errors, one REPORT line and no review or
predecessor invocations during the task window. The configured monitor executed
inside AWS Linux x86_64, with Python 3.14.10 and the protected producer's exact
numeric-library versions. Its REPORT measured 5,335.87 ms execution, 6,845.48 ms
initialization, 12,182 ms billed duration, and 301 MiB maximum memory of 1,536 MiB.
The review function had not executed then; its subsequent execution is recorded above.

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

PM-06B published seven immutable objects: one claim, three report/display artifacts,
one completion and two alerts. These are retained within the final eighteen objects.
Hash/readback checks passed; stakeholder JSON is
the exact allowlist, and HTML matches the producer's original allowlist order.
No raw records, private identifiers or source hashes appear in the display.
All 84 protected predecessor object metadata snapshots remained identical, as
did predecessor configurations, execution history selection and bucket settings.

## Historical local controller failure and shutdown

Canonical JSON sorts object keys. The private controller incorrectly re-rendered
the parsed `stakeholder.json` in that sorted order and compared it byte-for-byte
with HTML built in the allowlist's intentional insertion order. The field values
and original HTML were correct. This was a **local verifier assertion**, not a
Lambda exception, source/model integrity failure or alert-worthy new incident.

The required failure procedure ran immediately: both new functions temporarily
had reserved concurrency **zero**. The stack was retained at CREATE_COMPLETE,
with template concurrency one. The later authorized continuation restored that setting.
The failure-event rule and weekly schedule remain DISABLED; all four alarms have
actions disabled and no notifications. No invocation was retried or continued.
Evidence is preserved privately in
`data/processed/pm06b-deployment-20261120T233040Z/`.

The private controller comparison was corrected locally to validate fields and
render from the allowlist order. Three offline regression checks passed: sorted
JSON remains valid, extra fields fail, and altered HTML fails. No packaged
application, dependency, infrastructure or request identity changed. The original
approved hashes still apply. The prepared recovery proposal preserved the two
functions and original request identities. The completed continuation above used
the remaining six monitor and four review invocations without upload,
redeployment or repetition of step 1.

The account remained ACTIVE on the Free plan. No upgrade, purchase, subscription,
Organizations enrollment or personal payment was requested. Logs had no detected
credential patterns, and no secret retrieval was needed. Raw reports, detailed
logs, resource identifiers, packages and private proposals remain excluded from Git.

## Initial PM-06C recovery preflight stop (historical)

On November 20, 2026 (Eastern time), the approved recovery attempt stopped in its
read-only preflight. Original approval/recovery hashes, the corrected controller
hash, all thirty packaged source files and twenty dependency pins matched. The
new private recovery wrapper then incorrectly required `RuntimeVersionArn` from
`GetRuntimeManagementConfig`. For `FunctionUpdate`, AWS documents that this
manual-mode field is null; the SDK response omitted it. This caused a local
`KeyError`, not an AWS invocation failure or evidence of runtime drift. See the
[AWS API contract](https://docs.aws.amazon.com/lambda/latest/api/API_GetRuntimeManagementConfig.html).

No function was enabled or invoked. The failure procedure reasserted reserved
concurrency zero for **only** monitor and review, with successful shutdown
responses. That initial attempt added **zero monitor and zero review invocations**;
cumulative totals then remained one monitor and zero review. Original step 1 was
not repeated. Full deployed-state/S3 re-verification did not finish in that attempt;
the later explicitly authorized continuation completed it as reported above.

The private wrapper was corrected locally: require `FunctionUpdate`, accept only
the documented absent/null manual ARN, and still require the actual runtime ARN
from `GetFunctionConfiguration` to equal the preserved reviewed runtime identity.
It does not fabricate an ARN, suppress an AWS error, change runtime settings or
permit a different runtime. Seven new runtime-metadata tests and three complete
read-only-guard tests passed offline, including rejection of runtime and policy
drift. The three approved display regressions also passed: **13 private offline
checks**, separate from the prior 281-test project suite.

This attempt changed no packaged application, original approved controller,
template, dependency, IAM policy, artifact, request or token. There were no
uploads, deployments, new resources, captures, queries, fits, inference calls or
weekly executions. There were no upgrades, purchases, subscriptions or
Organizations enrollment. The private failed preflight and tested continuation
proposal are preserved under `data/processed/pm06c-recovery-20261121T015808Z/`.
This path uses UTC; the attempt was on November 20 locally. Its failure evidence
was retained unchanged when the later continuation restored the functions.

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
PM-06B/PM-06C executions establish both handlers' AWS runtime and the bounded
smoke acceptance above. The original 281-test suite was not rerun for these
documentation/private-controller-only changes; the thirteen offline private
controller checks are reported separately from that project suite.

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

## Bounded acceptance and remaining gaps

The [proposal/runbook](cloud-monitoring-runbook.md) bounded the deployment to 14
resources and eleven synchronous invocations. All those bounded checks completed:
saved-data reporting, replay preservation, historical application-failure detection,
simulated review and the expected error metric/alarm. No invocation allowance
remains; any further workload needs separate authorization.

The smoke does not establish measured rolling/prospective performance: later
outcomes were not captured, and historical availability remains unknown. It also
does not verify new weekly failure/timeout alarm transitions, automatic rule
delivery, external notifications or public hosting. The failure-event rule and
weekly schedule stay disabled; alarms have no delivery actions. Review automation
is explicitly simulated, not personal investigation or independent human
authentication. Acknowledgment never approves a model or forecast. This slice
does not complete operational forecasting.
