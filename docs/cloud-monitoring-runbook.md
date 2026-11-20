# PM-06 private monitoring deployment runbook

Status: implementation, offline tests, package and read-only AWS validation
complete; **deployment and smoke execution require approval**. No new monitor or
review handler has run in AWS. Use the [contract](monitoring-contract.md) for
strict fields and the [verification summary](cloud-monitoring-verification.md)
for completed evidence. This slice does not complete operational forecasting.

## Concrete candidate

The private proposal is
`data/processed/pm06-readiness-20261120/deployment-proposal.json`, with
`approval-baselines.json`, exact CloudFormation parameters and smoke templates in
the same ignored directory. Bucket/account/model/execution references belong
there, not in this document. The proposal selects the existing private project
bucket, prefix `initial-demo`, region `us-east-1`, and stack `fbs-cloud-monitoring`.
No bucket setting, predecessor resource or weekly schedule is changed.

Package: `data/processed/pm06-package-20261120-3/cloud-monitoring.zip`;
SHA-256 `d502b32bafcc9a612a9550052f909c4a09acd07cc6cce613c9edda7ed306f2c0`.
Artifact key:
`initial-demo/cloud-artifacts/cloud-monitoring/d502b32bafcc9a612a9550052f909c4a09acd07cc6cce613c9edda7ed306f2c0.zip`.
Template: `infra/cloud-monitoring.yaml`, SHA-256
`175f08714be166390c0f473791967d32cc940079190d9666c8ccb1b7e71ff59b`.
The private baselines also bind all 30 packaged source files, 20 pinned
dependencies, six-module monitoring identity, request templates and parameters.

Exactly fourteen new resources are proposed:

| Logical resource(s) | Exact name / configuration |
| --- | --- |
| `Monitor` | `fbs-pipeline-monitoring`; Python 3.14, x86_64, 1,536 MiB, 180 s, concurrency 1, 512 MiB temp |
| `Review` | `fbs-monitoring-review`; Python 3.14, x86_64, 512 MiB, 60 s, concurrency 1, 512 MiB temp |
| `MonitorRole` | `fbs-pipeline-monitoring-execution`; scoped reads and monitor-only conditional writes |
| `ReviewRole` | `fbs-monitoring-review-execution`; alert reads, review-slot/token conditional writes only |
| `MonitorLogs`, `ReviewLogs` | `/aws/lambda/fbs-pipeline-monitoring`, `/aws/lambda/fbs-monitoring-review`; 14-day retention, retain on replacement/deletion |
| `MonitorAsync`, `ReviewAsync` | `$LATEST` invocation configs; zero function-error retries, event age 60 s |
| `FailureRule` | `fbs-monitoring-workflow-failures`; existing weekly FAILED/TIMED_OUT/ABORTED events; **DISABLED**, target retry count zero |
| `FailurePermission` | Lambda permission bound to that rule/account; no public endpoint |
| `FailedAlarm`, `TimeoutAlarm` | `fbs-weekly-execution-failures`, `fbs-weekly-execution-timeouts`; existing workflow metrics |
| `MonitorErrorsAlarm`, `ReviewErrorsAlarm` | `fbs-monitoring-errors`, `fbs-monitoring-review-errors`; respective Lambda Errors metrics |

All four alarms use one 60-second Sum period, threshold at least one, missing
data not breaching, no actions, and `ActionsEnabled=false`. No custom metrics,
SNS topic, subscription, email/SMS, public hosting, schedule or pipeline start
permission is introduced. `AllowAlertSimulation=true` is proposed only to test
the explicitly simulated private alert/review path. Synthetic report inputs stay
disabled. Runtime management is `FunctionUpdate`; compare the selected Lambda
runtime and numeric-library versions with the protected model before any smoke
invocation. Stop on incompatibility; do not update the model to force success.

## Actual calls and least privilege

| Path | Calls and exact boundary |
| --- | --- |
| Preflight | `GetBucketPublicAccessBlock`; all four controls required; no setting writes |
| Weekly/report verification | `GetObject` of the explicit weekly completion and its hash-bound closure; training/model claim, completion and nine artifacts; no model deserialization |
| Optional absence | `ListObjectsV2(Prefix=exact_key, MaxKeys=1)`, then `GetObject` when present; 403 and unexpected errors remain errors |
| Later outcomes | Existing `download_raw`: exact 2026 manifest list probe and GETs; raw SHA/manifest/capture provenance and normalizer; no CFBD call |
| Publication/replay | Exact-key probes; `PutObject(IfNoneMatch="*")`, GET readback; complete last; no delete or overwrite |
| Execution inspection | `DescribeExecution` and paginated `GetExecutionHistory` for only `fbs-weekly-pipeline` executions; no `StartExecution` or Lambda invocation |
| Human review | Exact alert/previous-slot hash reads; optional numbered slot/token probes; conditional new slot/claim writes |

IAM pins the project bucket and model/training domains. Monitor listing is
limited to monitoring outputs, weekly outputs and 2026 raw prefixes; all listings
require `s3:max-keys <= 1`. Review listing is limited to review slots and token
claims. It cannot rewrite an alert; the monitor cannot write review transitions.
Neither role can write original raw, weekly, preparation or model data, fetch
secrets, query Athena, invoke training, start workflows or send notifications.
The saved weekly closure was traced, and all 133 exact IAM simulation contexts
passed. Actual deployed role enforcement still needs smoke verification.

## Checks before a separately approved deployment

Local checks already completed; repeat only after material changes:

```bash
PYTHONPATH=/tmp/fbs-pm03-work/network-guard:. .venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B bin/package_cloud_monitoring.py --validate-only
cfn-lint infra/cloud-monitoring.yaml
git diff --check
```

The temporary network guard was local verification tooling, not a repository
dependency. Existing test fixtures also block network access. The packager reuses
the reviewed Linux dependency directory, verifies exact pins/ELF headers and
refuses an existing output directory. A clean build can instead install pinned
binary wheels into a **new ignored directory**:

```bash
.venv/bin/python -B bin/package_cloud_monitoring.py \
  --output-dir data/processed/pm06-monitoring-package-new
```

A new ZIP requires new approval hashes, not silent replacement of this candidate.
Static checks are not Linux execution. Before cloud writes, recompute every
`approval-baselines.json` file hash, source hash, template/requirements/ZIP hash,
and verify the ZIP source equals the reviewed checkout. Confirm an ACTIVE Free
plan with eligible credits and permitted service coverage; stop if a required
service needs a paid upgrade. Never enroll in Organizations, buy, subscribe or
upgrade. The [AWS plan documentation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
describes actions that can change account-plan status. Read-only service access
was checked; creation restrictions can still surface at deployment.

Verify the proposed stack/resource names are not occupied, owner/encryption and
all four bucket access blocks remain correct, and the weekly schedule is still
disabled. Preserve predecessor object hashes/metadata and resource identities.
Keep private config and command output off screen. Do not retrieve a secret.

## Approved-only upload and creation procedure

The following is a **future procedure, not an action taken in PM-06**. A controller
must enforce baselines before using these steps; do not paste private values into
tracked files or display them. The CLI parameters file contains no secret values,
but does contain private resource references.

```python
# Run from the repository root only after deployment approval and digest checks.
import hashlib, json
from pathlib import Path
import boto3
from botocore.config import Config

ready = Path("data/processed/pm06-readiness-20261120")
p = json.loads((ready / "deployment-proposal.json").read_text())
b = json.loads((ready / "approval-baselines.json").read_text())
for name, expected in b["files"].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
for name, expected in b["source_sha256"].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
for name, expected in ((p["template"], b["template_sha256"]),
                       (p["application_zip"], b["zip_sha256"]),
                       (p["requirements"], b["requirements_sha256"])):
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
session = boto3.Session(profile_name=p["profile"], region_name=p["region"])
config = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=30)
s3 = session.client("s3", config=config)
with Path(p["application_zip"]).open("rb") as body:
    s3.put_object(Bucket=p["bucket"], Key=p["artifact_key"], Body=body,
                  IfNoneMatch="*", ExpectedBucketOwner=p["account"])
# Read back and hash the exact artifact before creating any resource.
uploaded = s3.get_object(Bucket=p["bucket"], Key=p["artifact_key"],
                         ExpectedBucketOwner=p["account"])["Body"]
try:
    assert hashlib.sha256(uploaded.read()).hexdigest() == b["zip_sha256"]
finally:
    uploaded.close()
cf = session.client("cloudformation", config=config)
cf.validate_template(TemplateBody=Path(p["template"]).read_text())
cf.create_stack(StackName=p["stack_name"], TemplateBody=Path(p["template"]).read_text(),
                Parameters=json.loads((ready / p["parameters_file"]).read_text()),
                Capabilities=p["capabilities"], OnFailure="DO_NOTHING")
```

No silent retry after upload/deployment ambiguity. Observe stack events using
read-only calls and preserve evidence. Verify exactly fourteen physical resources,
role policy equality, code SHA, both concurrency settings, runtime configuration,
disabled rule, non-delivering alarms and unchanged predecessors before smoke.

## Bounded smoke: eleven synchronous calls maximum

Create a new ignored evidence directory. Invoke each event once with
`InvocationType="RequestResponse"`, recording request/response hashes, request ID,
FunctionError, duration, maximum memory and runtime INIT evidence. Check the
response body, not just transport status. Do not use automatic controller retries.

| Order | Function/event | Required evidence |
| --- | --- | --- |
| 1 | Monitor: `report-request.json` | Saved Week 13 summary/model and source closure verify; report/three artifacts/completion verify; withholding remains expected; no outcome capture selected |
| 2 | Same monitor request bytes | Same completion and alerts; artifact bytes, ETags, sizes, LastModified and other recorded metadata unchanged |
| 3 | Monitor: `execution-request.json` | Reads the preserved PM-05B failed execution; catches application-level failed task output; durable critical alert and terminal evidence; no weekly execution |
| 4 | Same execution request bytes | Same evidence/alert identities and metadata; no duplicate publication |
| 5 | Monitor: `simulation-request.json` | Explicit simulated informational alert with `simulated=true` |
| 6 | Same simulation request bytes | Same alert bytes/metadata |
| 7 | Review: simulated acknowledgment | Slot 001, selected alert hash, configured human attestation, actual time and retained evidence hash |
| 8 | Exact acknowledgment replay | Same transition and hash; no duplicate slot |
| 9 | Review: simulated investigation | Slot 002, exact preceding hash and increasing time |
| 10 | Review: simulated closure | Slot 003, exact preceding hash, explicit reason and evidence; no operational/retraining approval |
| 11 | Monitor: `invalid-monitor-request.json` | Expected FunctionError for missing required fields; monitor Errors metric visible, no successful report |

Use `review-template.json` and the corresponding investigation/closure templates.
Populate only their dependent alert/previous hashes from verified earlier
responses, plus genuine human-attested timestamps and evidence. Simulation
remains true; never fabricate a genuine investigation or dispose of the real
failure alert during this test. Each transition has its own prepared stable token;
the replay uses identical bytes. AWS authorizes the private IAM invocation; the
handler only matches the attested name, not an independently authenticated person.
Retain that attestation limitation.

For a synchronous call, use the existing configured session, one-attempt SDK
config and an evidence file (do not print private result payloads):

```python
result = session.client("lambda", config=Config(
    retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=210
)).invoke(FunctionName="fbs-pipeline-monitoring",
          InvocationType="RequestResponse",
          Payload=(ready / "report-request.json").read_bytes())
# Save result["Payload"].read() and response metadata into fresh ignored evidence.
# Validate every receipt/artifact hash before using dependent references.
```

Totals: **seven monitor + four review invocations**, zero CFBD requests, Athena
queries, model fits, inference calls, weekly executions, outcome captures,
notifications and public publications. Stop at the bound. Read-only observation
of alarm/metric propagation is bounded to ten minutes; no workload retry to force
an alarm. The expected malformed-input rejection is a negative test, not an
unexpected deployment failure.

The rule stays DISABLED and all alarm actions stay false. This smoke checks
failure-history interpretation and the monitor's own error metric. It cannot
claim real-time EventBridge delivery or new States failure/timeout alarm
transitions. Step Functions status events are delivered on a
[best-effort basis](https://docs.aws.amazon.com/step-functions/latest/dg/eventbridge-integration.html);
even a separately enabled rule needs manual explicit-execution reconciliation.
Lambda async retry configuration does not provide exactly-once delivery; durable
alert/report identities handle duplicates when an event is delivered.

## Performance, cost and failure boundaries

No outcomes are selected in this smoke: expected rolling metrics are null/pending,
not zero error. Prior holdout evaluation remains a separate retrospective
reference. A later, separately approved 2026 Week 13/full-season outcome capture
after games complete must preserve source identity, teams and kickoff, be later
than scoring/cutoff and no later than the new as-of, and meet 30-label/80%-coverage
limits. It needs a new explicit report request/window, not a modified completed
request. No later capture is authorized by this runbook alone.

Potential credit-consuming resources are Lambda requests/GB-seconds, S3 artifact
and report storage/requests, log ingestion/storage and four standard alarms;
CloudFormation/IAM configuration does not eliminate underlying service costs.
At maximum configured duration the eleven calls bound Lambda execution to
7 × 1.5 × 180 + 4 × 0.5 × 60 = **2,010 GB-seconds**, excluding service overhead.
The ~79 MB artifact and retained evidence persist. No public endpoint, NAT,
always-running compute, paid subscription or notification delivery is proposed.
Credits and the Free plan must remain valid; do not interpret student status or
metadata access as unlimited free service coverage. Stop if upgrade/payment is
required, and leave evidence intact.

On any unexpected failure or ambiguous invocation: stop, preserve all requests,
logs, receipts and partially published evidence, disable **only the two new
functions** with `put_function_concurrency(..., ReservedConcurrentExecutions=0)`,
and retain the disabled rule/no-action alarms. Do not retry, alter thresholds,
broaden permissions or invoke a predecessor. Do not delete captured data or
silently complete a failed report. Hard timeouts may leave no S3 failure alert;
the function-health alarms are the independent backstop.

Teardown requires separate approval. The non-destructive stop commands are:

```bash
aws lambda put-function-concurrency --function-name fbs-pipeline-monitoring --reserved-concurrent-executions 0 --region us-east-1
aws lambda put-function-concurrency --function-name fbs-monitoring-review --reserved-concurrent-executions 0 --region us-east-1
aws events disable-rule --name fbs-monitoring-workflow-failures --region us-east-1
```

Use the approved private profile, without printing it or changing configuration.
No stack/object/log deletion is authorized; logs and S3 evidence are retained.
After success, publish only a sanitized verification summary. Automatic rule
activation, notification delivery, human identity integration and public hosting
are separate decisions, not acceptance shortcuts.
