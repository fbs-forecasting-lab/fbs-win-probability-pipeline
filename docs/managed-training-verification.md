# PM-13 managed-training deployment — stopped before training

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
