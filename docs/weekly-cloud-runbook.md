# Weekly cloud orchestration runbook (PM-05)

**Local implementation and validation only; no PM-05 workload is deployed.**
Read the [request/evidence contract](weekly-cloud-contract.md) and
[verification summary](weekly-cloud-verification.md) before deployment review.

## Preserved restrictions and new interface

The verified ingestion, recovery-only preparation and modeling deployments stay
unchanged. Preparation still denies StartQueryExecution. Existing saved-sample
inference still requires the exact original dataset. The new weekly worker does
not weaken either contract: it uses the existing Python normalization/builder
for a separate scoring input, then reloads the trusted original model. It checks
unchanged training/holdout/aggregate bytes, records scoring provenance separately
and never invokes training. There is no new Athena dependency or query permission.

Current support is explicit weeks in season 2026 with the approved PM-04 model,
not a generalized future-season forecast system. Historical availability remains
unknown. Technical eligibility and operational publication approval are separate;
all completed runs currently end withheld/unapproved, including zero-row runs.

## Proposed resources and permissions

Region us-east-1; stack `fbs-weekly-pipeline`; eight new resources:

- Python 3.14 x86_64 Lambda `fbs-weekly-pipeline`, role
  `fbs-weekly-pipeline-execution`, retained 14-day log group
  `/aws/lambda/fbs-weekly-pipeline`, and async retry configuration (zero retries).
- Standard Step Functions workflow `fbs-weekly-pipeline` and role
  `fbs-weekly-workflow-execution` (invoke only the new worker).
- EventBridge Scheduler schedule `fbs-weekly-pipeline`, initially **DISABLED**,
  and role `fbs-weekly-schedule-execution` (start only this workflow).

The worker has 1,536 MiB memory, 512 MiB temporary storage, 300-second timeout,
reserved concurrency one and single-thread numeric libraries. Runtime updates
occur on function update. It shares the existing 20 pinned modeling dependencies.
Before any smoke, compare its runtime-version ARN with the protected model
deployment and verify code hash, exact role policies, concurrency and retry
settings. The loader also checks actual Python/library versions. Stop on mismatch;
do not bypass loading checks, update predecessors or refit to force compatibility.

Worker reads are limited to project raw/capture history, its weekly ledger, the
explicit protected model/claim/completion and original approved dataset/preparation.
Only `initial-demo/weekly/runs/` permits worker writes, with conditional creation.
Only the existing ingestion function can be invoked. No secret access, model/data
overwrite, deletion, bucket-setting mutation, Athena query or training permission
is added. Prefix-conditioned list probes use MaxKeys=1; 403 stays fatal.

The recurring schedule is Tuesday 12:00 UTC with a fixed explicit request and
execution name, not a moving week/latest lookup. Its universal StartExecution
target receives a JSON-string input through `ScheduleInput`; the private parameters
encode that string inside the outer target JSON. It has zero retries. The smoke
payload is historical/fixed and must **not** be activated as a production schedule.
Future activation requires separate review of timing, cutoff, source/model
evidence, run token and execution name. A repeated fixed execution does not create
a new weekly forecast. No schedule is enabled in this task or proposed smoke.

## Local evidence and package

```bash
.venv/bin/python -B -m unittest tests.test_cloud_weekly tests.test_weekly_packaging -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B bin/package_cloud_weekly.py --validate-only
.venv/bin/python -B bin/package_cloud_weekly.py \
  --output-dir data/processed/weekly-package-new
```

The packager reuses the modeling packager's exact dependency/native checks and
source allowlist approach. Output must be a new ignored directory. It excludes
only dependency tests/bytecode/command entry points, keeps runtime libraries and
licenses, and enforces Lambda's 250 MiB uncompressed limit. Actual new worker
Linux imports, durations and end-to-end behavior still need the approved cloud
smoke; previous PM-04 execution is not proof for this new workflow.

## Concrete proposal (awaiting approval)

The final ignored proposal and approval hashes are in
`data/processed/pm05-readiness-20261120-final/`. Exact account/bucket/profile,
parameters, reviewed artifact location and six smoke events are private there.
Artifact key: `initial-demo/cloud-artifacts/cloud-weekly/<ZIP_SHA256>.zip` in
`<FBS_S3_BUCKET>`. The schedule stays disabled. No existing resource/permission
changes are proposed. Recompute proposal/template/ZIP/dependency/implementation
hashes and source equality before any approved write.

Read-only service access and official coverage support Step Functions on the
active Free plan; Scheduler metadata access also succeeded. No billing
investigation was reopened. Resource creation and execution remain unverified.
Use existing credits/allowances only; stop if an upgrade is required. No Paid-plan
activation, purchase, subscription or Organizations enrollment is authorized.
Billable scope is bounded workflow transitions, Lambda runtime/requests, S3
storage/requests and retained logs. Storage continues after the smoke; this is
not a promise of unlimited free operation.

After explicit approval, conditionally upload the reviewed ZIP once and verify
its full streamed readback hash, then deploy the eight-resource stack:

```bash
aws s3api put-object --region us-east-1 --bucket "$PROJECT_BUCKET" \
  --key "$REVIEWED_ARTIFACT_KEY" --body "$REVIEWED_ZIP" --if-none-match '*'
aws cloudformation create-stack --region us-east-1 \
  --stack-name fbs-weekly-pipeline --template-body file://infra/cloud-weekly.yaml \
  --parameters file://"$REVIEW/parameters.json" \
  --capabilities CAPABILITY_NAMED_IAM --on-failure DO_NOTHING
```

Verify all eight resources and runtime/IAM gates before execution. The controller
may submit the exact prepared event to StartExecution and inspect DescribeExecution;
all stage coordination and processing happen in AWS. Keep SDK automatic retries
disabled. Execution names and stable request/capture tokens come from the proposal.

```bash
aws stepfunctions start-execution --region us-east-1 \
  --state-machine-arn "$REVIEWED_WORKFLOW_ARN" --name "$REVIEWED_EXECUTION_NAME" \
  --input file://"$REVIEW/replay-event.json"
```

### Proposed smoke scope

| Execution | Worker-call limit | Expected evidence |
| --- | ---: | --- |
| Week 12 replay of explicit existing captures/model | 4 | Complete stage chain; verified technically selected rows and withheld summary |
| Completed replay with identical request/token | 1 | Unchanged bytes/metadata; no ingestion invocation or model reload |
| Conflicting week under original token | 1 | Claim rejection, no external work |
| Missing historical season | 1 | Request rejection before stage I/O |
| Observation exactly at cutoff | 4 | Zero technically eligible rows, zero predictions, withheld summary |
| Fresh explicit 2026 Week 13 capture | 8 | At most one ingestion invocation/HTTP attempt; distinct scoring identity; same protected model |

Maximum: **six executions, 19 worker invocations, one ingestion invocation, one
CFBD HTTP attempt, zero Athena queries and zero fits**. Each execution also has
the template's eight-advance cap and overall timeout. Expected negative refusals
are successful checks; any unexpected failure stops the sequence. If preparation
is pending, only bounded same-request progress/publication checks are permitted.
An ambiguous capture response is never followed by another ingestion invocation.

The fresh-event cutoff is fixed at **2026-11-20T23:59:00Z**. If capture occurs at
or after that cutoff, observations remain ineligible; do not move the cutoff,
refetch or choose a fresh token automatically. No prediction-count promise is
made. The replay cutoff is 2026-11-20T12:00:00Z; its Week 12 snapshot is historical.
The minimum new-path proof is one fresh Week 13 capture and **no** query, because
the weekly feature adapter calls the existing Python builder directly. Even a
successful run remains retrospective/unapproved and may have zero eligible rows.

Collect execution history, all stage/summary hashes, exact model/source/feature/
cutoff identities, technical/quarantine reasons, prediction counts/complementary
probabilities, code/runtime versions, invocation counts and source/object metadata
before/after replay. Verify no model-fit/query start and no duplicate capture.
Record actual values, not historical metric substitutions. Keep private detailed
evidence ignored and publish only a sanitized summary.

## Failure and recovery

On an unexpected deployment/smoke failure, stop the workflow, set only the new
weekly worker's reserved concurrency to zero, and leave the schedule disabled.
Preserve execution history, captures, stage receipts, partial results and logs.
Do not disable ingestion/preparation/modeling, change settings, expand permissions,
refetch, query, train or choose new tokens to obtain success. A still-running
ingestion call may finish its original capture; preserve it and inspect receipts.
Workflow timeout does not cancel an already running Lambda; no replacement call
is permitted while the outcome is ambiguous. Reviewed recovery may use a new
execution name with the same request/token; completed evidence is never rewritten.

Alerts must request investigation and an approval/evidence review, never retrain.
Cleanup requires separate authorization; no deletion or recurring activation is
included in this proposal.

Official references: [Free-plan serverless coverage](https://aws.amazon.com/free/serverless/),
[Standard execution identity](https://docs.aws.amazon.com/step-functions/latest/apireference/API_StartExecution.html),
[Scheduler universal targets](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-targets-universal.html).
