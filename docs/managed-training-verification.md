# Managed-training verification — PM-13B measured result

**PM-13C update:** [Inference-only recovery preparation](managed-inference-recovery.md) now passes native timestamp-archive verification locally. The original training is complete; a separate consumer image and unpublished candidate receipt are pinned. Cloud inference and independent fit-count corroboration remain unverified. Earlier sections below preserve dated evidence.

## November 22, 2026: job completed; native verification remains incomplete

The original single SageMaker job completed in AWS Linux using the unchanged
reviewed image, six-file dataset and canonical request. The measured artifacts,
split counts, holdout scores and calibration passed independent inspection.
**This verifies actual SageMaker training execution; it does not establish full
PM-13 acceptance or native inference compatibility.** No historical metrics were
substituted, no model was trained locally and no predecessor model was retrained.

### Equivalent-scope ECR policy correction

The one corrected candidate omitted only the statement's explicit `Resource`.
Its attachment request pinned the existing registry and repository; ECR repository
policies apply only to that attachment repository. The Lambda service principal,
only `ecr:BatchGetImage` / `ecr:GetDownloadUrlForLayer`, and exact function/account
source conditions were unchanged. No wildcard principal, public access or new
object permission was introduced. Original rejected payload/baselines remain intact.

Corrected policy-file SHA-256:
`847fbb68c689d1835dd706eb254bb1c055a3accffaadd8ad73e80bb894d1aafb`.

Generic Access Analyzer reported `MISSING_RESOURCE`; its validator has no ECR
resource-type option. That limitation was recorded, not reported as a pass.
The documented Lambda repository-policy representation supports omission of this
field. ECR then accepted this **single** candidate and its read-back matched
exactly. Acceptance after this sole representation change supports the diagnosis;
AWS did not explicitly identify the original offending field. No successive
speculative service variants were tried.

Retained repository, role IDs/trust/inline scopes and log groups were reconciled
rather than recreated. A temporary Docker credential configuration initially
lost the daemon connection at a local tag step, before any push. Four offline
controller tests verified the explicit-existing-endpoint correction and no-retry
behavior. The subsequent single push preserved the reviewed manifest digest:
`sha256:52832ca633d3cc49864feb5946b34aa9526d327991a874633ecbc0d9d6b3be00`.
No image rebuild or producer-byte change occurred.

### Training result versus independent inference

| Check | Actual result |
| --- | --- |
| Submission / original jobs | **1 / 1**, original name/request; original directory-wide durable journal consumed |
| Job status | **Completed**; no configured RetryStrategy or replacement submission |
| Instance / runtime setting | One ml.m5.large; 300-second training-runtime setting |
| AWS measured training / billable time | **53 / 53 seconds**; not a total wall-clock billing cap |
| Actual split counts | **2,194 train (2022–2024) / 740 holdout (2025) / 59 saved prediction rows (2026)** |
| Model files | Seven files; companion hashes, dataset/report/preparation links and immutable image/source pins verified |
| Probabilities | All saved holdout/sample probabilities finite, in [0,1] and complementary; row identities/order verified |
| Fit observations | One exclusive fit-attempt record, one completion record and one Training phase; no job attempt-count field or CloudWatch stream available |
| Private native receipt | **Not published**; the reviewed native archive contract rejects the genuine service archive |
| Independent bridge | Not deployed; **0 of at most 3** synchronous calls used; hypothetical result not measured |
| Protected state | Six input ETags/sizes/modification times, protected model objects, predecessor functions, bucket protections and disabled rules unchanged |

The scaler/logistic pipeline's pinned implementation fits only the training
split. Holdout labels remain evaluation-only. The job's internal serialization
round-trip gate completed before artifact publication. Independent bridge reload
and saved-prediction byte equality have **not** been established for this model.

Measured holdout scores, with differences against the historical Lambda result:

| Metric | SageMaker model | Constant training-rate baseline | Maximum absolute difference from historical Lambda |
| --- | --- | --- | --- |
| Brier score | 0.21061287148858282 | 0.24163577488303326 | 0 |
| Log loss | 0.6096025525960278 | 0.6763272181260667 | 0 |
| Accuracy | 0.6648648648648648 | 0.5918918918918918 | 0 |

Calibration uses the existing ten fixed equal-width bins, with no calibration
fitting. Values below are rounded to six decimals; empty bins remain unavailable.
The last bin includes 1.0. Counts sum to the actual 740 holdout rows.

| Model probability bin | Games | Mean prediction | Observed home-win rate |
| --- | --- | --- | --- |
| 0.0–0.1 | 2 | 0.080122 | 0.000000 |
| 0.1–0.2 | 6 | 0.169721 | 0.333333 |
| 0.2–0.3 | 34 | 0.258127 | 0.235294 |
| 0.3–0.4 | 72 | 0.359678 | 0.291667 |
| 0.4–0.5 | 118 | 0.454581 | 0.491525 |
| 0.5–0.6 | 158 | 0.549126 | 0.506329 |
| 0.6–0.7 | 154 | 0.649144 | 0.733766 |
| 0.7–0.8 | 135 | 0.752029 | 0.770370 |
| 0.8–0.9 | 59 | 0.845292 | 0.847458 |
| 0.9–1.0 | 2 | 0.934775 | 1.000000 |

The constant baseline has all 740 rows in the 0.5–0.6 bin, mean prediction
0.5829535095715588 and observed home-win rate
0.5918918918918918. These are descriptive historical
holdout results, not rolling performance or proof of operational forecasting.

Runtime metadata from the actual job matches the reviewed image: Python
3.14.10, scikit-learn 1.9.0, NumPy 2.5.2, SciPy 1.18.1, pandas 3.0.5 and
joblib 1.6.0. All retrospective/unapproved flags remain unchanged.

### Why native receipt/inference verification stopped

SageMaker packaged the seven files using PAX timestamp headers (`atime`, `ctime`,
`mtime`, `LIBARCHIVE.creationtime`). The unchanged native loader accepts bounded
USTAR files and rejects these extension headers. The raw archive and its hashes
were preserved; it was not repacked or overwritten to force acceptance.

A tested **controller-only inspection** permits only those inert numeric timestamps,
while refusing path/link/size overrides, unknown metadata, duplicate aliases,
missing/extra files, symlinks/hardlinks, truncation, trailing data and compressed/
expanded size overruns. It performs no extraction, model deserialization or fit.
This enabled artifact/evaluation inspection, **not a bypass of native trust**.
The reviewed image and its native verifier were not modified. Consequently the
native completion receipt was not published and an incompatible bridge was not
invoked. A separately reviewed inference/archive compatibility correction is
needed; the completed model/job need not be retrained.

Bounded read-only checks also found **zero CloudWatch streams** under the exact
job prefix, including the final check. CloudTrail inspection did not establish
a logging failure cause. One fit is observed through diagnostics and the single
Training phase, but independent corroboration of the exact service fit count is
unavailable; that acceptance gap is not marked complete. No permissions were
broadened or workload repeated to manufacture log evidence. No new active job or
bridge existed to stop/disable at the final check.

### Credits, retained resources and checks

Account remained **FREE / ACTIVE**. Estimated eligible credits before and after
this task were **$119.963146** and **$119.963146**, covering
training, Lambda, ECR, S3 and logs. The 50-hour promotion was not relied on.
At the previously checked $0.115/hour training rate, the 53 billable seconds imply
approximately **$0.00169306 compute before credits**. This is a rate-based
estimate, not settled billing; the unchanged account balance may reflect reporting
lag. No paid Cost Explorer query or plan/subscription change was made.

Retained: one private image (373,404,225 compressed bytes), the two scoped
roles and two log groups, the Completed job, and its two original S3 archives
(47,138 bytes combined). No endpoint or native inference function exists.
Image storage is approximately $0.04/month at $0.10/GB-month before credits;
S3/log retention and other account resources remain separate. The prior $0.4094
30-day plan estimate was conservative and is not claimed as actual expenditure.
No automatic deletion, new recurring work, schedule/delivery activation or public
publication was configured. Main and Pages remain untouched.

**379 full offline tests passed** with network blocked, including 14 new ECR/policy
and safe archive-inspection regressions; four additional private upload-controller
tests passed. Original application/source/dependency/request/private-artifact pins
remain unchanged. Detailed policy comparison, genuine job/diagnostic/artifact
bytes, input preservation, calibration, log checks and cost responses are ignored
under `data/processed/pm13b-execution-20261122T070838Z/`. Private identifiers/model files are excluded from Git.

Only actual named-service training execution and measured artifacts are newly
verified. Native receipt/inference, exact-fit corroboration, genuine human review,
recurrence/delivery, pending outcomes and operational approval remain separate gaps.

---

## Historical PM-13 first attempt — stopped before training

November 21, 2026, `us-east-1`. **Training and independent inference remain
unverified.** Deployment stopped at ECR's validation of the original reviewed
repository policy, before image upload or SageMaker submission. Historical
Lambda measurements are not results of this attempt.

## Cloud and local evidence collected November 21, 2026

- Started from `feature/final-readiness` at `d824724decb46a2c4435d7e626112185a2290190`
  with a clean working tree. Original executable, dependency/build context,
  canonical request, IAM and private-artifact pins matched. Intervening documentation
  changes were identified separately; original PM-09A baselines were preserved.
- The existing immutable Linux x86_64 image passed read-only source-byte and
  runtime verification in a network-disabled container. No real data was trained
  locally. Python is 3.14.10 with the originally pinned dependencies.
- Current applied `ml.m5.large for training job usage` quota was **15** through
  `GetServiceQuota`, code `L-611FA074`. PM-12 separately established positive
  m4.xlarge/m5.xlarge quotas; no quota request or Support action was repeated.
- Account remained **FREE / ACTIVE** with estimated eligible credits of
  **$119.973485** before resource creation and at the final check. Enabled credits
  explicitly covered SageMaker, Lambda, ECR, S3 and CloudWatch. The unverified
  50-hour promotion was not relied on. No paid activation occurred.
- All six selected S3 dataset files matched the original cloud-preparation receipt
  and report hashes. The existing dataset loader passed. Original job and isolated
  output identities were absent, with no earlier submission journal.
- Reviewed training/inference role documents matched their builders, and the
  exact submission/PassRole policy simulations passed. The existing account
  identity was retained; no caller policy was attached or expanded. The new
  roles' read-back inline policies matched exactly, with no attached managed policies.

## Deployment result and acceptance boundaries

| Check | Actual result |
| --- | --- |
| New resources | One private immutable-tag ECR repository, two scoped IAM roles with one inline policy each, two empty log groups |
| ECR repository policy | One `SetRepositoryPolicy` attempt rejected with `InvalidParameterException`: `Invalid repository policy provided`; no policy installed |
| Image upload | **0 attempts**; repository contains no images |
| SageMaker submission / jobs / fits | **0 / 0 / 0**; original job remains absent and durable submission attempt remains unconsumed |
| Seven model artifacts / private provenance receipt | Not produced or published |
| Actual train/holdout/prediction counts, metrics and calibration | Not measured by SageMaker; no historical or synthetic substitutes |
| Independent inference bridge / test calls | Function not created; **0 of at most 3** calls used |
| Failure shutdown | No active job or new function existed to stop/disable; no deletion, retry or permission expansion |
| Protected predecessors | Function configurations and protected model-object metadata unchanged; bucket privacy/encryption unchanged; event rules unchanged and disabled |

The failed API request contained the exact reviewed repository-policy semantics.
The original generic Access Analyzer validation had no findings; that did **not**
establish acceptance by ECR's service-specific validator. AWS returned no
field-level cause. No speculative policy alteration was applied, and the policy
write was not retried. This is a deployment-readiness blocker, not a failed
training workload or evidence of cloud training completion.

Before a continuation, review a service-compatible repository-policy representation
that retains the exact repository, Lambda service principal, actions and source
conditions. Reconcile the already-created resources rather than recreating them;
preserve all original pins and the rejected payload. The single original job/name,
one fit and three-call inference limit remain unchanged. Never treat an eventual
policy correction as permission to change the image, data, job request or predecessor.

## Cost evidence and retained resources

Current us-east-1 Price List metadata gave training **$0.115/hour**, training volume
**$0.14/GB-month**, Lambda first-tier x86 compute **$0.0000166667/GB-second** plus
**$0.20/million requests**, S3 Standard **$0.023/GB-month**, and logs **$0.50/GB
ingested + $0.03/GB-month retained**. ECR's official pricing examples give
**$0.10/GB-month** and zero same-region transfer charge.

A conservative estimate was **$0.4094 for the proposed job and 30-day retained
artifacts**, using one hour of training/staging allowance, a 5 GiB volume, 2 GB
image allowance (local uncompressed size about 1.31 GB), three 2 GiB Lambda calls
with initialization allowance, 1 GB S3 allowance and 100 MB logs. A $2 planning
allowance and $10 minimum eligible-credit guard were used. These allowances are
estimates, not billing caps; `MaxRuntimeInSeconds=300` limits training runtime
only. Retaining the assumed data/image/log envelope beyond 30 days would cost
approximately $0.226/month at those rates, without additional workloads.

The job, image upload and inference never ran, so that proposed estimate is
**not actual usage**. The before/after estimated credit balance was unchanged;
no settled PM-13-specific charge evidence was available. Billing reporting can
lag. The retained repository/log groups were verified empty and IAM has no
running compute. No endpoint, schedule, automatic deletion or subscription was
created. Resources/evidence were preserved as instructed.

Detailed responses, exact resource identities, controller corrections, rate
metadata and protected-object snapshots remain ignored under
`data/processed/pm13-execution-20261121T172144Z/`.
No CFBD/provider request, Athena query, predecessor retraining, monitoring-review
transition, main/Pages change or recurring activation occurred. Historical
availability remains unknown and retrospective/unapproved flags remain unchanged.
Unchanged application tests were not rerun; checks covered pins, dataset integrity,
Linux image inspection, scoped IAM, actual service responses and final retained state.

Sources: [ECR repository-policy scope](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-policies.html),
[SetRepositoryPolicy errors](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_SetRepositoryPolicy.html),
[ECR rates](https://aws.amazon.com/ecr/pricing/),
[Lambda rates](https://aws.amazon.com/lambda/pricing/),
[SageMaker rates](https://aws.amazon.com/sagemaker/ai/pricing/).

## Documentation closeout — November 22, 2026

The resumed closeout checked the saved failure/verification evidence, original
private/executable pins, unconsumed journal and exact documentation diff. The
cloud observations and prices above are dated November 21; no cloud write,
training submission, inference invocation or new billing check was repeated
during this documentation closeout. No requirement was newly marked complete.
