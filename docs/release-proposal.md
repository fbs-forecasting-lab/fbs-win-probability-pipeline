# PM-08 proposed release, training and publication actions

**Nothing below authorizes deployment or publication.** The candidate is locally
prepared, not requirement-complete. Private exact references and approval hashes
are in ignored `data/processed/pm08-readiness-20261121/`. No old workload allowance
can be reused. Preserve Free/Active status, eligible coverage and zero personal
payment; stop if a required service needs paid activation or an upgrade.

## 1. Named-service training closure — blocked candidate

Syllabus p.5 explicitly says SageMaker or EC2; the supplied newest serverless
announcement does not establish an exemption for Lambda. Retain the verified
Lambda implementation. Preferred resolution is **one on-demand SageMaker training
job**, not a notebook server, hosted endpoint, tuning job or persistent EC2 host.

- Region `us-east-1`; job `fbs-final-training-20261121`; role
  `fbs-final-managed-training`; private ECR repository `fbs-final-training`.
- Prefer one `ml.m5.large`, 5 GiB volume, 300-second maximum runtime, retry zero,
  Spot/warm pools/debugger/profiling disabled, network isolation enabled. Its
  account quota is **zero**. A no-paid-upgrade quota resolution needs separate
  approval; do not request it now. A positive GPU quota is not permission to use
  a more expensive instance just to bypass this blocker. Any GPU alternative
  needs a revised explicit cost/coverage review and bounded approval.
- Read the existing PM-03D parity-verified dataset via a SageMaker `dataset` File
  channel; exact dataset/report/preparation/model references are privately pinned.
  Preserve 2,194 train / 740 holdout / 59 saved prediction rows. No API capture,
  historical backfill, Athena query or current-model replacement.
- `managed_training.run` checks the report/dataset, explicit demo consent, new
  output and exclusive attempt marker before delegating to existing baseline
  training/evaluation. No new model algorithm/settings or secrets are introduced.
- Output only to a fresh private `initial-demo/final-readiness/managed-training/`
  job prefix. The candidate yields the existing seven baseline artifacts and
  managed-job evidence, **not automatically a trusted nine-artifact release**.
  If the final demonstration must invoke this exact SageMaker-produced artifact,
  a separately reviewed promotion/provenance adapter must bind the job/image/source,
  interpretation/provenance companions and existing trusted inference contract.
  Do not claim byte-equivalent coefficients alone establish producer trust.

### Container and permission gates

The candidate Dockerfile reuses the reviewed Linux ZIP and new entrypoint.
It requires an immutable reviewed `public.ecr.aws/lambda/python:3.14` base digest,
then overrides the Lambda entrypoint with the SageMaker training module. No pip
install/network or key retrieval occurs inside the isolated job. The new image
must be built and run in compatible Linux x86_64 before approval; Docker's local
daemon was unavailable in prior packaging evidence. No image digest or successful
Linux execution is invented. The local build context can be hashed, but is not a
deployable verified image.

Offline SDK shape validation caught that `RetryStrategy.MaximumRetryAttempts=0`
is invalid (the optional strategy's minimum is one). The corrected nonexecutable
request template omits that strategy; explicit SDK resubmission remains forbidden.
Confirm required service-level no-retry behavior before approval rather than
claiming an unexecuted job verified it. The exact dataset report hash is now bound
from preserved, hash-verified model metadata; only the image/role/quota/runtime
and final promotion/retry gates remain unresolved. No job was submitted.

Proposed role: SageMaker service trust restricted to account/source job, exact
six input `GetObject` resources and dataset-prefix listing, conditional output
scope, exact ECR pull resources plus required registry authorization, scoped
CloudWatch logs. No CFBD/odds secret, Bedrock, Athena, predecessor invocation or
protected model writes. A fully resolved image/role policy and CreateTrainingJob
request require a new baseline and read-only IAM/service validation before cloud
approval. Scope is one role, one repository/image upload and one job/fit;
maximum 300 seconds, no retry or fresh-name rerun on ambiguity. No endpoint or
recurring resource is proposed. Model output remains quarantined/private until
integrity, counts, holdout metrics, actual runtime and intended API lineage pass.

Official contracts: [managed training](https://docs.aws.amazon.com/sagemaker/latest/dg/train-model.html),
[File channel/container layout](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-running-container.html),
[CreateTrainingJob](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateTrainingJob.html)
and [Free-plan service scope](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html).
Service inclusion and accessible metadata do not prove a particular instance can
run under this account or that usage consumes no credits.

## 2. Static public monitoring — content ready locally, hosting unverified

Candidate: ignored `public-view/index.html`, built from the verified PM-06 saved
report and its recorded SHA-256 using `public_monitoring.build_view/render`.
It contains only dated scalar counts, measurement states, pending labels and
retrospective flags. It excludes private identifiers, raw data, game predictions,
reviewer text, alert details, model references and secret values. Source age is
explicitly the saved report's age, not current freshness. No JavaScript/external
asset or automatic refresh is required.

Minimal proposed publication is **GitHub Pages from the public repository**,
after content approval and hosting/settings verification. Copy only the approved
HTML into `docs/public-monitoring/index.html` in a separately approved publication
change; choose main `/docs` Pages source only after normal integration. Proposed
URL is `https://fbs-forecasting-lab.github.io/fbs-win-probability-pipeline/public-monitoring/`;
it is **not published or verified now**. Recheck any existing Pages configuration
before changing it; do not replace another site. This requires no AWS resource,
data-bucket policy/ACL/public-access change or public inference endpoint.
Approval must cover the exact reviewed HTML hash and Pages setting. Afterward
verify unauthenticated visibility and absence of excluded fields. Revoke the
publication source on accidental disclosure; preserve private evidence and
never expose the source bucket. No publication ran during PM-08.

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
No slides, final PDF, resource deployment, uploads, publication, activation, API
invocation, new training job or query was performed in this preparation round.
