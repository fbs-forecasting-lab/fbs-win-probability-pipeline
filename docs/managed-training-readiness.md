# PM-09A managed-training readiness — no cloud execution

November 21, 2026. This closes local preparation gates, not the syllabus's actual
SageMaker/EC2 execution requirement. No real project data was trained locally.
The verified Lambda system, protected model and original producer bytes remain
unchanged. Private evidence and exact requests are ignored under
`data/processed/pm09a-readiness-20261121/`; none is a deployment authorization.

## PM-13 current status — November 21, 2026

The PM-09A preparation below is historical. PM-12/13 resolved the applied-quota
and eligible-credit gates: ml.m5.large quota 15, FREE/ACTIVE and $119.973485
estimated eligible credits. Under the later execution authorization, PM-13 created
only the reviewed repository, roles and logs, then stopped when ECR rejected the
original repository policy. No image upload, job, fit, private receipt or inference
call occurred. [Actual deployment verification](managed-training-verification.md)
records retained resources, cost assumptions and the unresolved policy gate.
The original image, request and approval baselines remain unchanged. Actual
SageMaker training is still missing; waiting on the old quota case is no longer
the execution blocker.

## Historical PM-09A locally verified gates

| Gate | New evidence | Remaining boundary |
| --- | --- | --- |
| Linux runtime | Existing OrbStack was stopped; started without installation/configuration changes. Docker executed Linux x86_64 on the local ARM host using `--platform linux/amd64`. | Emulated local Linux is not a SageMaker service execution. Existing local containers resumed with the runtime; no unrelated container was edited/deleted. |
| Immutable image | Base manifest `sha256:bbe0b5c9f1b049d9b0a77b742cfd252b2c0ccfb153f259df4d830c798dd63dd3`; final local image manifest `sha256:52832ca633d3cc49864feb5946b34aa9526d327991a874633ecbc0d9d6b3be00`. | No ECR upload; verify the identical manifest after an approved push. |
| Launch/storage | Actual `image train` launch, File channel `/opt/ml/input/data/dataset`, seven model files in `/opt/ml/model`, diagnostics in `/opt/ml/output/data`, sanitized `/opt/ml/output/failure`. Synthetic counts 18/6/6. | Real managed input staging, output compression and permissions still require the single approved job. |
| Failure/interruption | Bad input hash: exit 1 before fit/attempt. Existing output rerun: exit 1 and prior bytes preserved. SIGTERM after attempt consumption: exit 143, failure recorded, no completion/model. | Hard kill cannot promise a final diagnostic write. Preserve partial outputs; never infer completion from a tar object alone. |
| Controller | Exact canonical request approval, installed SDK shape, one total SDK attempt, exclusive fsynced directory-wide journal before submission. Timeout/interruption/malformed response consumes the journal; new filename/job name cannot retry in that directory. | A local guard cannot prevent deliberate deletion/use of another directory; both are forbidden. No submission was made. |
| IAM | Six policy/trust documents received zero Access Analyzer findings; 18 exact-context allow/deny simulations matched. | Documents were not attached. Simulation is not effective deployed-role/service verification. |
| Storage | Expected owner, four bucket-level public-access blocks enabled, SSE-S3/AES256 and exactly six files in the selected dataset prefix verified through metadata. | No bucket setting or stored object changed. |
| Native model lineage | 23 focused tests passed both on the host and inside the final pinned image; separate reload reproduces six synthetic saved predictions and hypothetical probabilities. | Real job-origin evidence/receipt must be verified and independently pinned after the job. No synthetic service evidence is cloud proof. |
| Regression | Full network-blocked suite: **365 passed** (342 previous + 23 new). | No historical cloud demonstration was repeated. |

The image contains Python **3.14.10**, scikit-learn 1.9.0, NumPy 2.5.2,
SciPy 1.18.1, pandas 3.0.5 and joblib 1.6.0. **PM-09B correction:** the actual
protected cloud model also records Python 3.14.10, verified against its original
training receipt's metadata hash. The earlier 3.14.2 claim confused local-environment
metadata with cloud evidence. Exact version checks remain intact. A matching
runtime does not make SageMaker a Lambda producer: retain the separate native
receipt/adapter and do not rewrite protected model metadata.

## Access, credits and the unresolved decision

Read-only account evidence is FREE / ACTIVE, **$119.99 USD** remaining credits,
with plan expiration February 25, 2027 at 15:08:26 UTC. This is a dated observation,
not a reservation of credits or a quote for a job. The five CPU training quotas
checked once in `us-east-1` were all zero: `ml.m5.large`, `ml.m5.xlarge`,
`ml.c5.xlarge`, `ml.t3.large` and `ml.m6i.xlarge`. SageMaker listing works; that
alone does not establish CreateTrainingJob access/capacity.

[Supported Free-plan services](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html)
include SageMaker. [AWS's plan comparison](https://aws.amazon.com/free/) separates
Free-plan access/credits from Paid billing. Neither establishes an instance quota
or grants a legacy SageMaker free-hours trial. No GPU, alternate region, service
activation, subscription or upgrade was selected/made. No quota increase was
requested during PM-09A; the separately authorized PM-09B request is recorded below.

**PM-09B access request:** Hampton authorized and one Service Quotas request
was submitted for `L-611FA074` (`ml.m5.large for training job usage`) in `us-east-1`,
from zero to one. Preflight found no equivalent pending/open/approved request.
The latest check is **CASE_OPENED** (awaiting AWS decision), with applied quota still zero and FREE/ACTIVE
unchanged. AWS created a related case through the quota route; no separate inquiry was
submitted. The API has no justification
field; the truthful student-project explanation is preserved privately for any
related support handling. No personal-payment commitment was made.

Await the existing request; do not duplicate it. If unavailable/denied, the approved
fallback is one Basic account/billing inquiry about retaining Free/zero personal
payment, not paid technical support or an upgrade. If AWS requires payment, stop
and prepare an unsent instructor clarification. Approval of quota alone never
authorizes an image upload, resource deployment or workload execution.

## Exact execution contract prepared, not authorized

`managed_contract.TrainingSpec` renders the private `training-request.json`,
training trust/policy, caller submission policy and native inference read policy.
The exact selected PM-03D dataset/preparation/report identities are pinned from
preserved verification evidence. Input listing is confined to that dataset prefix;
object reads are only its six names. No raw-history/model/secret/provider access
is added. Output is separate from all protected model domains.

Proposed identities and ceilings:

- Region `us-east-1`; job `fbs-final-training-20261121`; training role
  `fbs-final-managed-training`; private ECR repository `fbs-final-training`.
- One `ml.m5.large`, one instance, 5 GiB, `MaxRuntimeInSeconds=300`;
  File input, network isolation on, Spot and profiling off; no warm pool,
  debugger, checkpoints, tuning, pipelines or automatic controller resubmission.
- Input: `<FBS_S3_BUCKET>/initial-demo/datasets/<pinned-dataset-id>/`.
  Expected historical splits are 2,194/740/59; actual job counts/metrics must be
  measured, not substituted with these expectations.
- Output root: `initial-demo/final-readiness/managed-training`; service artifacts
  resolve to `fbs-final-training-20261121/output/model.tar.gz` and `output.tar.gz`
  beneath it. Refuse an existing job/output namespace before any future write.
- The training role can put only this job's `output/*`; it cannot write the
  separate `verified/receipt.json` or any protected model/input. SageMaker's
  training log group must exist before execution; stream writes are job-scoped.
- New optional-to-deploy **native inference bridge**, required for the proposed
  independent API scoring proof: `fbs-final-managed-inference`, a new role of
  the same name, x86_64, 2,048 MiB, 60-second timeout, concurrency one. Use this
  exact image with `ImageConfig.EntryPoint=["/lambda-entrypoint.sh"]` and
  `Command=["src.pipeline.managed_inference.handler"]`. No existing function,
  model, weekly reference or runtime is changed. Its role can read only the
  pinned six dataset files, exact managed archive/verified receipt and bucket
  public-access settings; log writes are confined to its own precreated group.
  Exact-function ECR service retrieval policy/trust are prepared and validated.

### Retry and stop semantics

The [RetryStrategy API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_RetryStrategy.html)
configures retries for InternalServerError; it is optional and its minimum, when
supplied, is **one**, not zero. This request **omits it**, does not use Pipelines
and opts into no service retry strategy. The [SDK retry contract](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
is separately enforced through `total_max_attempts=1` and a consumed submission
journal. This is not an undocumented guarantee against every AWS infrastructure
restart. A replacement container does not share a durable local fit marker;
verify actual job transitions/logs and stop on ambiguity rather than asserting
that local tests established service-level exactly-once behavior.

[Runtime limits](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_StoppingCondition.html)
and [signal delivery](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-dockerfile.html)
allow a SIGTERM grace period up to 120 seconds before SIGKILL. The candidate exits
promptly on tested SIGTERM. The 300-second training setting is **not a 300-second
billable wall-clock cap**: provisioning, input staging, compression/upload,
ECR/S3/log retention can consume credits too. Recheck Free/Active status, remaining
eligible coverage and expiry before approval/execution; never upgrade to proceed.

### Provenance and independent scoring

`managed_lineage.build_verified_receipt` accepts only separately reviewed exact
job evidence: completed DescribeTrainingJob, approved request/image/source,
preparation/dataset/report/file pins, output object and runtime. An arbitrary
self-consistent manifest or matching coefficients do not establish producer trust.
The verifier/controller must collect authentic AWS metadata and bind it to the
reviewed image/source manifest and original preparation receipt before approving
the evidence digest. The receipt's digest then comes from protected configuration,
not from the caller or archive supplier.

Bound compressed/expanded tar sizes and exactly seven canonical regular files;
reject traversal, links, duplicate aliases, extra members, invalid metadata,
runtime mismatch and changed hashes **before deserialization**. Plain USTAR and
benign `./` root spellings are tested; unsupported archive extensions fail closed.
Actual service archive compatibility remains part of the first-job verification.

`managed_inference` retrieves only configured keys, requires all public-access
blocks and injects the approved receipt pin. `managed_lineage.infer` delegates to
unchanged `baseline.load_trusted_model`, `predict_saved_sample` and `predict_vector`.
The producer stays `sagemaker_training`; no Lambda training claim is fabricated.
The old Lambda/weekly contract intentionally does not accept this new origin.

## Bounded future verification plan (requires separate approval)

After the CPU/access/cost gate closes and private hashes are reviewed:

1. Create only the proposed private repository/roles/log groups; upload the exact
   reviewed image and verify its digest. Preserve all predecessor resources and
   bucket settings. No paid activation or public endpoint.
2. Recheck the exact six-file input selection and fresh job/output namespace.
   Use one protected submission directory and the pinned request hash; one SDK
   CreateTrainingJob attempt, one job/fit, maximum training runtime 300 seconds.
   Poll Describe only within a bounded observation period; never resubmit an
   ambiguous/failed request or choose a replacement name.
3. Require Completed status, unchanged request/image, no configured retry, one
   observed training attempt, runtime/source match and valid output/diagnostic
   hashes. Verify all seven files, train-only fitting, counts, holdout metrics and
   calibration, preserving actual measured results. A tar alone is not completion.
4. Build a native receipt from authenticated read-only job/object evidence, bind
   its exact hash independently, and publish it only to the verifier-owned
   `verified/receipt.json` key with exclusive/no-overwrite semantics. Keep detailed
   evidence private. This response-bound hash is necessarily unknown before a job;
   its verification/pinning procedure must be included in the later authorization.
5. Deploy only the separate native bridge using the identical reviewed image and
   result-bound receipt configuration. At most **three synchronous invocations**:
   saved sample (byte-equal to training sample), hypothetical (finite complementary
   probabilities), invalid receipt pin (rejected before any AWS read/model load).
   No legacy inference invocation, API capture, Athena query or second fit.
6. On failure, stop; preserve journal, objects and logs. Stop only the new job if
   active, disable only the new bridge if it exists; no repair, deletion, expanded
   permission, new job name or retry. Schedules/delivery stay disabled.

Quota/access and genuine cloud-origin verification remain unresolved; this plan
is not an execution approval request. All four retrospective/unapproved status
flags remain unchanged throughout.

## Reproduce the local verification

The ignored final build context contains the preserved reviewed Linux dependency
ZIP and exactly four `managed_*.py` candidate modules, with source/dependency/base/
image hashes in the private build manifest. A future rebuild must reproduce or
review a new digest; never substitute a mutable image tag silently.

```bash
docker build --platform linux/amd64 --provenance=false \
  -t fbs-managed-training:pm09a-final \
  data/processed/pm09a-readiness-20261121/build-context-final
PYTHONPATH=/tmp/fbs-pm03-work/network-guard:. \
  .venv/bin/python -B -m unittest discover -s tests -v
```

The network guard is a local verification helper, not an installation dependency.
Focused tests also block network directly. Linux checks mount synthetic fixtures
only and use `--network none`, a read-only container root and fixed paths. Exact
executed arguments, outputs, policy simulations, request and approval hashes remain
in ignored evidence; credentials and local proposals/packages are never committed.

## PM-09B documentation-only follow-through

The one quota request has a related case open; identifiers and raw responses remain only in
ignored evidence. No application or package changed. The final-documentation
source now links [checked research references](research-references.md), separates
legacy Lambda and proposed SageMaker receipt contracts, and explains artifact
inspection, evaluation and stop conditions without suggesting that old cloud
allowances can be reused. All remaining managed execution gates above persist.
The historical PM-09A 365-test result was not rerun for documentation changes.
