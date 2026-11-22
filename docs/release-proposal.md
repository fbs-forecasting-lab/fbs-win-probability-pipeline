# PM-08 proposed release, training and publication actions

**PM-13C update:** [Inference-only recovery preparation](managed-inference-recovery.md) now passes native timestamp-archive verification locally. The original training is complete; a separate consumer image and unpublished candidate receipt are pinned. Cloud inference and independent fit-count corroboration remain unverified. Earlier sections below preserve dated evidence.

**Nothing below authorizes deployment or publication.** The candidate is locally
prepared, not requirement-complete. Private exact references and approval hashes
are in ignored `data/processed/pm08-readiness-20261121/`. No old workload allowance
can be reused. Preserve Free/Active status, eligible coverage and zero personal
payment; stop if a required service needs paid activation or an upgrade.

**PM-11 update:** the separately authorized static monitoring publication is
complete; its verification is linked below. This does not authorize training,
recurrence, delivery, provider work or main integration.

## 1. Named-service training executed — PM-13B native verification gaps

**Current PM-13B result:** one corrected equivalent-scope ECR policy was accepted;
the unchanged reviewed image and original request produced a Completed SageMaker
job (2,194/740/59 rows, 53 training/billable seconds). Measured scores/calibration
and seven artifact payloads passed inspection. [Verification](managed-training-verification.md)
separates actual training from native receipt/inference acceptance: PAX timestamps
are rejected by the original native parser: no receipt was published, bridge
deployed or inference call executed.
Exact fit-count corroboration from logs is also missing. Preserve the completed
job and raw outputs; no retraining, silent image change or broader IAM is approved
by this document. Further compatibility work needs a concrete reviewed change.

**Historical PM-13 result:** applied ml.m5.large quota 15 and FREE/ACTIVE eligible
credits resolved the old access gate. The authorized attempt created only the
new repository/roles/logs; ECR rejected the original reviewed repository policy
before any upload or job. [Measured deployment status](managed-training-verification.md)
records zero jobs/fits/inference calls and the policy blocker. Original pins and
predecessors remain unchanged. The PM-09A/09B paragraphs below describe the
historical preparation/access state, not today's applied quota.

Syllabus p.5 explicitly names SageMaker or EC2; Lambda has no established exemption.
[PM-09A readiness](managed-training-readiness.md) supersedes the earlier unverified
container and unresolved adapter proposal. Existing OrbStack now executes the
immutable Linux x86_64 image; actual `train` launch, channel/output paths, failures,
SIGTERM, native trusted reload and synthetic parity passed. All 23 focused tests
passed inside that image; 365 offline tests passed on the host. No real-data local
training or cloud job occurred.

The preferred one-job plan stays `us-east-1`, `fbs-final-training-20261121`,
one `ml.m5.large`, 5 GiB, training limit 300 seconds, network isolation, no Spot,
profiling or configured service retries. Five small CPU quotas remain zero.
Free/Active and $119.99 in remaining credits are independently evidenced; service
inclusion/credits do not establish quota, job capacity or service execution.
Do not seek execution approval until a Free-plan-compatible CPU quota/access
resolution is established. PM-09B submitted the single authorized quota request
for zero to one; status is CASE_OPENED, awaiting AWS decision, and the applied
quota is zero. No GPU
substitution, region change or Paid activation was made. Quota approval alone
does not authorize execution.

Exact input/request, scoped training/caller/native-inference policies and trust
are prepared privately. Six validation documents had no Access Analyzer findings;
18 IAM simulations matched. Policy validation is not deployed-role verification.
The immutable base/image/source/dependency bindings and bounded execution plan
are in [the detailed proposal](managed-training-readiness.md). The request omits
the optional RetryStrategy (explicit zero is invalid); SDK resubmission is disabled
and a durable consumed-directory journal prevents ambiguous-response retries.
Infrastructure restart/exactly-once behavior remains a cloud observation, not a
local-test guarantee. SIGTERM grace/upload time means 300 seconds is not a total
billable wall-clock cap.

PM-09B corrected the runtime evidence: both the image and receipt-verified
protected cloud model record Python 3.14.10; 3.14.2 was a local-environment value.
The minimum native adapter verifies an independently approved SageMaker
job/receipt/archive before unchanged baseline deserialization/prediction. A
separate native bridge is required by the different producer origin, not a
verified runtime mismatch; no Lambda claim is forged or runtime check relaxed. The proposal bounds this to three synchronous future invocations and
keeps predecessor deployments/model references unchanged. Its result-bound receipt
hash can only be populated after the single genuine job. No bridge was deployed.

## 2. Static public monitoring - saved demonstration published in PM-11

Public URL: [https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/](https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/).
Publication commit: `212a659ceda0a04b76d8917f6435bb0045d7ccb6` on `gh-pages`; HTML SHA-256:
`cd128621a8e5ca88b6ab1dac727546549b8845cf7cedca0efe5fda42f710d975`. Only `public-monitoring/index.html` and empty `.nojekyll` are in that
isolated root tree. [Verification/review history](monitoring-publication-review.md)
records before/after hosting evidence, authorized content diff and rollback.

The approved first branch push automatically enabled legacy branch-root Pages;
the resulting exact configuration/build was verified without replacing settings
or sending an additional build trigger. Unauthenticated HTTPS was 200, served
bytes matched, and desktop/narrow browser checks found no overflow or external
assets. No S3 setting or private stakeholder report changed.

Only the static saved-view commitment is complete. The fixed date, pending
labels, unavailable rolling metrics, investigation-only warnings and false
approval flags remain. No auto-refresh, delivery, review transition or operational
forecasting is enabled. On accidental disclosure/wrong content, disable only the
new Pages site and preserve branches/history/evidence; no rollback was required.

## 3. Delivery, truthful review and recurring inputs

Keep weekly schedule, monitoring rule and alarm actions disabled. The schedule
contains a fixed execution name/input/cutoff, so enabling it is not a weekly
request planner. New recurrence needs date/week selection, fresh deterministic
tokens, pre-call wall-clock expiry guards, source revision policy and durable
per-run/global provider budgets. Current handler eligibility cannot substitute
for refusing an expired new fetch before it happens. Implement/version/test that
coordinated change before proposing activation. No stale-cutoff activation command
is recommended. No final assignment source mandates every lecture notification
service; do not add subscriptions or independent human authentication speculatively.

For genuine human review, Hampton should inspect the saved quality/distribution/
holdout facts and actual alert evidence off screen, then authorize only truthful
existing review transitions. Proposed first step: one acknowledgment of a selected
genuine warning with actual timestamp/evidence hash, not three automatic actions
claiming completed personal investigation. Investigation/closure require actual
findings, not the simulated smoke record. No new review invocation is authorized
now. Later outcomes/rolling performance need their own bounded source selection;
do not recapture to manufacture successful predictions or metrics.

Automatic failure-event delivery remains unverified. Activation would need a
separate, bounded event-delivery test plan accounting for at-least-once delivery,
duplicate invocations, shutdown and cost; there is no indefinite enablement or
forced alarm state in this release proposal. This remains a disclosed project
goal gap, not an invented prerequisite to a static diagnostic page.

## 4. Normal integration and final artifacts

Remote main is `b524cf057b4c5a0a0c56ec6819084c75915e6c62`; PM-07C at
`63670eb89000f2cc7b263347b76b111d4de3e32a` descends from it through all fourteen
PM-02–PM-07 implementation/verification commits. No main reset/merge/PR occurred.
After readiness review and explicit integration approval: fetch/recheck clean
state/ancestry and protection rules, use the repository's normal reviewed merge
workflow without bypassing protections, integrate `feature/final-readiness`,
push normally, and verify remote main and unauthenticated release files. If a PR
is required, seek the already-concrete PR approval then; none is opened now.

Do not mark a final release complete while named-service training, genuine review
or required publication evidence is missing. Existing hashed producer docstrings
and the dataset accounting assertion are deferred to a coordinated compatibility
release, documented in the suggestion disposition; changing source bytes casually
would invalidate existing receipt identities. New candidate modules have inline
docstrings and do not change any deployed producer identity.

Finish the source draft, class appendix, bibliography/citation check and PDF
render/link/length QA after gaps close. Then create about five slides and rehearse
the [five-minute outline](final-demo-outline.md), with no repeated live workload
unless separately budgeted. PDF/code due December 1 at 10 a.m. ET; PPTX at 9 a.m.
The original preparation round performed no slides, final PDF, resource deployment,
uploads, publication, activation, API invocation, new training job or query.
The separately authorized PM-11 static publication is recorded in section 2.
