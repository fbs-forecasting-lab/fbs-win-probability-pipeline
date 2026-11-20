# Cloud ingestion: deployment and recovery

**PM-02C deployed and cloud-verified on November 20, 2026.** This is only the cloud capture
foundation. Athena, cloud training/inference, operational forecast eligibility,
scheduling, drift/performance monitoring, and alerts remain separate work. The
existing notebook, retrospective CLIs, and synthetic quickstart still work.

The PM-02B preparation and command-reference sections below retain their original
review context. The completed PM-02C execution record at the end supersedes their
"not deployed"/"not run" statements. Do not rerun creation or smoke commands merely
to reproduce this report; an additional invocation requires its own authorized
scope. No acceptance result below applies to Athena, training or inference.

For the concise public record, see the
[sanitized verification summary](cloud-ingestion-verification.md).

## Request and identity

A synchronous invocation takes only:

```json
{"schema_version":1,"season":2026,"week":12,"idempotency_token":"capture-20261120-take01"}
```

Choose the actual desired season/week explicitly before an authorized smoke test;
this example is not a claim about the current schedule. Week 0–99 is accepted;
omit week for a full regular season. Null week, booleans, unknown fields, secret
values in extra fields, and malformed tokens fail before SDK client creation.
Tokens contain 8–64 lowercase letters/digits/hyphens. Never use secrets as tokens.

The canonical identity is SHA-256 of sorted compact JSON plus newline for:
`schema_version`, `season`, `week` (null when omitted), `endpoint=cfbd/games`,
`season_type=regular`, `classification=fbs`. Token SHA-256 selects the ledger
folder; its immutable claim binds that token to one canonical request. JSON
key ordering does not change identity. This namespace is the configured project
prefix; changing the prefix creates a different namespace, not a retry.

The secret and bucket come only from deployment configuration. Events cannot
upload raw data. The notebook/control script initiates and reads receipts;
ingestion and temporary files execute inside Lambda.

## Durable objects and times

The existing raw layout stays `<prefix>/raw/cfbd/games/season=<year>/`.
The ledger is separate: `<prefix>/cloud-ingestion/runs/<token_sha256>/`.
Every ledger/raw write is conditional `If-None-Match: *`; nothing is overwritten.

| Object | Meaning |
| --- | --- |
| `claim.json` | Atomic fetch ownership, canonical request/hash, token hash, run start, diagnostic deadline |
| `capture.json` | One atomic checkpoint containing base64 original raw bytes and the unchanged existing manifest format |
| `failure.json` | First caught failure, stage, safe message and failure time; it does not prevent recovery from a capture |
| `complete.json` | Winning version-one success receipt, after verification of both final objects |

`started_at` is claim preparation time (it can precede a losing concurrent claim).
`retrieved_at` is when the existing HTTP client received the response.
`completed_at` is receipt preparation time after final readback, not kickoff or
publication time. `failed_at` is the caught failure observation. A 210-second
claim diagnostic deadline is 30 seconds beyond the configured 180-second Lambda
timeout. It distinguishes a recent `in_progress` claim from `interrupted`; it
**never** grants permission to take over or refetch. Injected clocks in tests
must return UTC ISO timestamps in the same canonical format as production.

Every receipt carries `receipt_version=1`, token/request hashes, a state and the
existing retrospective/unapproved flags. Completed receipts additionally contain
raw/manifest S3 keys and SHA-256 hashes, capture SHA-256, record count, source
availability, and the three run times. They contain no raw records, bucket name,
secret value, authorization headers or API error details. A failure response
contains only a fixed safe message and stage; do not expect original SDK errors.
Hard termination may prevent `failure.json`; the claim remains evidence.

The checkpoint duplicates the response privately for recovery (raw size limit
16 MiB; generic S3 transfer object limit 64 MiB). It is deliberately a single
conditional S3 object rather than two files with an interruption gap. It retains
source bytes until a separate, explicitly reviewed retention decision. Do not
apply automatic expiration to claims or completion receipts: deleting them would
allow token reuse. No ledger cleanup or bucket lifecycle policy is installed.

The existing `save_snapshot` generates a snapshot ID. Only the winning fetch
invocation creates it. Recovery reconstructs those exact files, calls
`load_snapshot`, and uses the existing `S3Store.upload_raw`. Final raw/manifest
bytes are read back before success. Completed-token replay revalidates the
capture, receipt and both final objects without reading the secret or fetching.
Different-request token reuse fails at the claim stage.

## Recovery matrix

| Observed condition | Safe action |
| --- | --- |
| Completed receipt and all hashes match | Same token returns the original receipt; no new observation |
| Capture exists, publication partially failed | Repeat exactly the same event; resume existing bytes only |
| Capture PUT committed but response was lost | Same token finds that checkpoint and resumes without a fetch |
| Completion response was lost | Same token verifies and returns the winning receipt |
| Claim exists without capture, invocation might still run | Wait; retry only observes status, never fetches |
| Claim expired or caught failure, still no capture | Original observation cannot be recovered; investigate, then explicitly choose a new token for a NEW observation |
| 409 or ambiguous claim timeout | Retry the same event to inspect any claim/capture; never retry unconditionally or delete ledger objects |
| Hash mismatch, conflicting objects, corrupt receipt | Stop and investigate; do not overwrite, delete, or silently choose a new source |
| Same token with different request | Reject; use a deliberately new token only for a separate observation |

The original owner makes at most **one HTTP attempt**. A timeout, 429, 5xx or
authentication failure is not automatically retried; do not assume no quota was
consumed. Existing local CLI retry behavior remains unchanged. S3 SDK clients
also use one attempt in this handler: read retries by reinvocation are harmless,
but token/claim rules prevent them from turning into a new fetch. Recovery can
run concurrently; all publishers use the identical checkpoint and conditional
writes, and return the same first winning completion receipt.

A synchronous Lambda invocation returning HTTP 200 is not proof of success:
inspect the payload `state == "completed"`. Handled failures return structured
receipts. Async retries are disabled; use synchronous invocation only in this
slice. No schedule, event trigger, public URL, or invocation permission is created.

## Packaging and local validation

Keep the existing `.venv` on Python 3.14. The raw-transfer path now lazily imports
model/dataset dependencies only when their dataset methods are called. Raw
capture imports no NumPy, pandas, scikit-learn or Jupyter. A subprocess test
checks this transitive boundary. No project-wide requirement versions changed.

```bash
.venv/bin/python -B bin/package_cloud_ingestion.py --validate-only
.venv/bin/python -B bin/package_cloud_ingestion.py \
  --output-dir data/processed/pm02-package-take-01
```

The second command installs pinned ingestion-only wheels into that NEW ignored
directory, targeting CPython 3.14/manylinux2014 x86_64, then creates
`cloud-ingestion.zip` and `package-report.json`. It does not modify `.venv` or
upload anything. Output-directory reuse is refused, even after a failed build.
Pip needs network/cache access. The complete transitive requirements are pinned
in `infra/cloud-ingestion-requirements.txt`; source files are allowlisted.
`.env`, private data, tests and model/training modules are excluded.

`infra/cloud-ingestion.yaml` uses JSON syntax, which is valid YAML/CloudFormation.
The helper validates local structure and parses source syntax; that is not
CloudFormation service validation or a Linux runtime smoke test. If available,
run `cfn-lint infra/cloud-ingestion.yaml` before deployment. Never claim that
merely producing the ZIP verifies the managed runtime.

AWS lists Python 3.14 on Amazon Linux 2023. Dependencies must be Linux-compatible,
and AWS recommends packaging the SDK with its dependencies to avoid runtime SDK
misalignment. This package includes the pinned boto3/botocore closure.
[Python runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html),
[ZIP packaging](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html),
[S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).

## Resources, secret and access boundaries

Prepared CloudFormation resources only:

- Lambda, Python 3.14, x86_64, 512 MiB memory, 512 MiB scratch storage, timeout
  180 seconds, reserved concurrency 1. The account must have quota available.
- Execution role `${FunctionName}-execution`, trusted only by Lambda. No broad managed administrator policy. Deployment requires `CAPABILITY_NAMED_IAM`.
- Dedicated log group, retention 14 days, retained when deleting the stack.
- Async invoke configuration: zero retries, maximum event age 60 seconds.

Use the existing private project bucket, without changes to its four Block
Public Access flags, policy, encryption or visibility. Runtime permissions are
`GetBucketPublicAccessBlock`, `GetObject`/`PutObject` only for raw and ledger
prefixes, prefix-constrained `ListBucket` capped at one key, `GetSecretValue` on one configured
secret, and writing to the named log group. `CloudS3Store` probes optional objects with `ListObjectsV2(Prefix=<exact key>,
MaxKeys=1)` before GET. The role supplies `s3:prefix` and caps `s3:max-keys` at 1.
A successful list proves absence only when the exact key is not returned. For
these general-purpose buckets, lexicographic ordering puts an exact match before
longer keys sharing its prefix. A listed object is then read through the existing
byte-verifying helper; deletion or denial at GET fails closed. There is no 403
fallback and no broad bucket-list grant. The original CLI `S3Store` remains unchanged.

The old optional-GET assumption was unsafe: GET has no Prefix parameter, while
AWS documents `s3:prefix` as a ListObjectsV2 request condition. IAM simulation of
the exact proposed role denies listing without that context. We therefore do
not claim a missing GET will return 404 under that role. The explicit list probe
removes that dependency. Read-only simulation verifies the identity policy,
not SCPs, future trust relationships, or live execution under a not-yet-created role.
[GetObject permission semantics](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html),
[prefix and max-keys conditions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html),
[ListObjectsV2 ordering](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html). No delete or policy-mutation permissions.

Hampton must supply an existing Secrets Manager ARN containing only the plain
API key in `SecretString`, not JSON or `Bearer ...`. Set it off screen; never
put the value in a command, event, template or log. If a new secret is necessary,
its creation requires separate authorization. The template creates no secret.
Optional KMS ARN parameters add only necessary runtime decrypt/generate-data-key
permissions for existing customer-managed encryption; associated key policies
must already permit the role. Code artifact encryption/deployment permissions
are separate from execution-role data access.

Deployment identity needs CloudFormation/Lambda/log/IAM resource operations,
`iam:PassRole` scoped to the execution role, and code-artifact upload access.
After creation, operators need only named-function invoke and selected receipt
reads. Do not change existing bucket/key policies as a workaround for denial.

Costs can include CFBD quota, Lambda requests/duration, S3 requests and duplicate
checkpoint storage, Secrets Manager, KMS and logs. No exact prices are assumed.
Concurrency 1, synchronous-only operation, one HTTP attempt, and no schedule bound
this slice; agree a smoke-test invocation budget before deployment.

## PM-02B proposal and preparation evidence (historical)

Read-only discovery on November 20, 2026 verified the configured AWS account
(identifier withheld; suffix 0237) and **us-east-1**. The project bucket is the
existing configured bucket, not a replacement; its exact name is bound in the
ignored proposal below rather than copied into public documentation. Encryption
is AES256 (SSE-S3), all four public-access blocks are enabled, and no bucket
policy is present. No bucket policy, encryption or visibility changes are proposed.

| Resource / setting | Exact proposed choice |
| --- | --- |
| Stack and function | `fbs-cloud-ingestion` |
| Execution role | `fbs-cloud-ingestion-execution` |
| Log group | `/aws/lambda/fbs-cloud-ingestion`, 14 days, retained on stack deletion |
| Project prefix | `initial-demo` |
| Raw keys | `initial-demo/raw/cfbd/games/season=<year>/<snapshot_id>.json` and sibling manifest |
| Ledger | `initial-demo/cloud-ingestion/runs/<token_sha256>/` |
| Code bucket | Same inspected existing project bucket |
| Code key | `initial-demo/cloud-ingestion-code/pm02b-20261120/30d6373d4e619b150ee86d3efe415aae5c5d5cd64c7c96f7025c02dfa63cfa74.zip` |
| API secret name | `fbs/cfbd-api-key` (not found; proposed creation requires approval) |
| Secret KMS | Default Secrets Manager AWS-managed key; no customer-managed key parameter |
| Bucket KMS | None; SSE-S3 requires no KMS permissions |
| Smoke request | season 2026, week 12, token `pm02b-20261120-smoke-01` |
| Conflicting request | Same token, week 13; expected claim-stage rejection |

Project/name-filtered and CFBD-keyword secret metadata searches found no candidate;
DescribeSecret confirmed the proposed name absent. No GetSecretValue call was made.
The new secret's exact ARN is the only unresolved deployment parameter: it will
be returned by approved creation and inserted into the local parameter file.
Do not infer the ARN suffix or use a wildcard secret in the execution role.

The proposed stack, function, role and exact log group were absent at inspection.
Lambda reported 400 unreserved concurrent executions, sufficient for the proposed
one reserved slot at inspection time. Recheck names/HEAD before an approved
execution; stop rather than update any newly conflicting resource.

### Evidence and remaining verification

- `cfn-lint 1.61.0`, run in a separate temporary environment: no findings.
- AWS CloudFormation `ValidateTemplate`: passed; reports `CAPABILITY_NAMED_IAM`.
- AWS IAM `SimulateCustomPolicy`, resolved proposed identity policy: raw/ledger
  list probes allowed; unrelated prefixes, missing prefix, and max-keys 2 denied.
- Linux-targeted CPython 3.14 wheel installation and isolated package import are
  local packaging checks. They are **not Linux execution evidence**.
- Docker cannot connect to its daemon; no Podman, Colima, QEMU user-mode or Lima
  command was available. The actual Lambda Linux runtime remains unverified.
- No function has been deployed or invoked. Live role authorization, source
  capture and receipts still require the approved smoke test below.

The handler emits one sanitized `cfbd_fetch_start` log with only request/token
hashes immediately before the single HTTP attempt. Replay does not emit a new
fetch-start record. This supports the smoke-test evidence without logging keys,
request bodies or API responses; it is not a monitoring implementation.

### Local proposal files

The following NEW ignored directory holds inspected identifiers, not secret values:

```text
data/processed/pm02b-readiness-20261120-adc24f78/
  deployment-proposal.json
  parameters.json
  smoke-request.json
  conflict-request.json
  metadata-summary.json
  validation-summary.json
```

The proposal binds the actual account, bucket and optional configured profile.
Do not commit it or print it on screen. `parameters.json` intentionally contains
`<CREATED_SECRET_ARN>` until authorized secret creation fills it. The final local
ZIP is `data/processed/pm02b-package-20261120-1/cloud-ingestion.zip`; its SHA-256 is
`30d6373d4e619b150ee86d3efe415aae5c5d5cd64c7c96f7025c02dfa63cfa74`.
These paths describe this concrete approval proposal. A future rebuild needs a
new output directory/key and renewed review of its digest.

### Reviewed command reference (SDK equivalents executed in PM-02C)

Run from the repository root in a fresh shell. No project data is uploaded by
these commands: only application code and cloud-generated data from invocation.
All bucket values come from the inspected local proposal; no literal private
bucket/account identifiers are copied into this tracked runbook.

```bash
set -e
export PM02B_REVIEW_DIR=data/processed/pm02b-readiness-20261120-adc24f78
export AWS_DEFAULT_REGION=us-east-1
PM02B_PROFILE=$(.venv/bin/python -B -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())["profile"] or "")')
if [ -n "$PM02B_PROFILE" ]; then export AWS_PROFILE="$PM02B_PROFILE"; fi
```

First create only the approved secret, using a hidden terminal prompt. The key
never enters command history, a file, or stdout. A noninteractive prompt fails
rather than echoing. This command needs explicit creation authorization; it has
not been run. If creation fails, stop; do not overwrite an existing secret.

```bash
.venv/bin/python -B - <<'PYSECRET'
import getpass, json, os, re, warnings
from pathlib import Path
import boto3
root=Path(os.environ["PM02B_REVIEW_DIR"])
p=json.loads((root/"deployment-proposal.json").read_text())
try:
    warnings.simplefilter("error",getpass.GetPassWarning)
    key=getpass.getpass("CFBD API key (hidden): ")
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]+",key):
        raise ValueError("Invalid key format")
    session=boto3.Session(profile_name=p["profile"],region_name=p["region"])
    arn=session.client("secretsmanager").create_secret(Name=p["secret_name"],SecretString=key)["ARN"]
    key=None
    params=json.loads((root/"parameters.json").read_text())
    for item in params:
        if item["ParameterKey"]=="CfbdSecretArn":item["ParameterValue"]=arn
    (root/"parameters.json").write_text(json.dumps(params,indent=2)+"\n")
    p["secret_arn"]=arn;p["secret_creation_required"]=False
    (root/"deployment-proposal.json").write_text(json.dumps(p,indent=2)+"\n")
except Exception as exc:
    print("Secret setup stopped:",type(exc).__name__)
    raise SystemExit(1)
print("Secret created; local parameters updated. Value withheld.")
PYSECRET
```

Validate, verify the ZIP digest, upload one immutable application artifact, then
deploy only the four template resources and their scoped role policy:

```bash
aws cloudformation validate-template --template-body file://infra/cloud-ingestion.yaml
.venv/bin/python -B - <<'PYHASH'
import hashlib,json,os
from pathlib import Path
p=json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())
assert p["secret_arn"] and not p["secret_creation_required"]
assert hashlib.sha256(Path(p["zip_path"]).read_bytes()).hexdigest()==p["code_sha256"]
PYHASH
PM02B_BUCKET=$(.venv/bin/python -B -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())["bucket"])')
PM02B_CODE_KEY=$(.venv/bin/python -B -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())["code_key"])')
aws s3api put-object --bucket "$PM02B_BUCKET" --key "$PM02B_CODE_KEY" \
  --body data/processed/pm02b-package-20261120-1/cloud-ingestion.zip --if-none-match '*'
aws cloudformation create-stack --stack-name fbs-cloud-ingestion \
  --template-body file://infra/cloud-ingestion.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameters "file://$PM02B_REVIEW_DIR/parameters.json"
aws cloudformation wait stack-create-complete --stack-name fbs-cloud-ingestion
```

`create-stack` intentionally refuses an existing stack rather than updating it.
The deployment identity needs resource creation, named-role creation/PassRole,
and code-artifact put/get access. This does not broaden the Lambda runtime policy.
If a create/wait step fails, inspect sanitized stack events and stop; do not
change bucket/IAM protections or retry with broader permissions.

Perform three synchronous invocations; save each response in a NEW evidence
folder. The expected budget is **at most one CFBD HTTP attempt**, one secret read
by the function, and three Lambda invocations. A full-success first invocation
normally creates five S3 objects: claim, checkpoint, raw, manifest and completion.
Replay/conflict attempts use conditional claims and do not replace those objects.

```bash
mkdir data/processed/pm02b-smoke-evidence-01
aws lambda invoke --function-name fbs-cloud-ingestion --invocation-type RequestResponse \
  --cli-read-timeout 210 --cli-binary-format raw-in-base64-out \
  --payload "file://$PM02B_REVIEW_DIR/smoke-request.json" \
  data/processed/pm02b-smoke-evidence-01/first.json
.venv/bin/python -B -c 'import json; from pathlib import Path; r=json.loads(Path("data/processed/pm02b-smoke-evidence-01/first.json").read_text()); assert r["state"]=="completed"; assert r["approved_for_point_in_time_forecasting"] is False; print(r["state"], r["record_count"], r["raw_sha256"][:8])'
aws lambda invoke --function-name fbs-cloud-ingestion --invocation-type RequestResponse \
  --cli-read-timeout 210 --cli-binary-format raw-in-base64-out \
  --payload "file://$PM02B_REVIEW_DIR/smoke-request.json" \
  data/processed/pm02b-smoke-evidence-01/replay.json
cmp data/processed/pm02b-smoke-evidence-01/first.json data/processed/pm02b-smoke-evidence-01/replay.json
aws lambda invoke --function-name fbs-cloud-ingestion --invocation-type RequestResponse \
  --cli-read-timeout 210 --cli-binary-format raw-in-base64-out \
  --payload "file://$PM02B_REVIEW_DIR/conflict-request.json" \
  data/processed/pm02b-smoke-evidence-01/conflict.json
.venv/bin/python -B -c 'import json; from pathlib import Path; r=json.loads(Path("data/processed/pm02b-smoke-evidence-01/conflict.json").read_text()); assert r["state"]=="failed" and r["stage"]=="claim"'
PM02B_TOKEN_HASH=$(.venv/bin/python -B -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())["token_sha256"])')
aws logs filter-log-events --log-group-name /aws/lambda/fbs-cloud-ingestion \
  --filter-pattern "\"cfbd_fetch_start\" \"$PM02B_TOKEN_HASH\"" --query 'length(events)'
```

Expect one fetch-start event once logs arrive; record its timestamp/request ID
along with all three invocation IDs, code SHA/runtime, receipt equality, source
hashes/keys, status flags, and the conflict result. Read retries for log delivery
must not invoke Lambda again. A non-completed first result stops this sequence;
apply the recovery matrix, not a fresh token/new pull without renewed approval.
Synchronous API success alone does not establish capture success.

The following read-only verification command checks the two exact object keys
from the receipt and privacy/encryption without printing bucket names or records:

```bash
.venv/bin/python -B - <<'PYVERIFY'
import boto3,json,os
from pathlib import Path
p=json.loads((Path(os.environ["PM02B_REVIEW_DIR"])/"deployment-proposal.json").read_text())
r=json.loads(Path("data/processed/pm02b-smoke-evidence-01/first.json").read_text())
s3=boto3.Session(profile_name=p["profile"],region_name=p["region"]).client("s3")
flags=s3.get_public_access_block(Bucket=p["bucket"])["PublicAccessBlockConfiguration"]
assert all(flags.get(k) is True for k in ["BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets"])
for field in ["raw_key","manifest_key"]:
    obj=s3.head_object(Bucket=p["bucket"],Key=r[field])
    assert obj["ServerSideEncryption"]=="AES256"
    print(field,"present",obj["ContentLength"],"bytes; AES256")
print("All four public-access blocks remain enabled")
PYVERIFY
```

The handler verifies full remote bytes before completion and on replay. Collect
metadata for the two exact keys from the verified receipt, without downloading or
printing private records. Confirm privacy and encryption again, and that replay
kept source hashes and receipt unchanged. These are required deployed smoke-test
observations; no local mock/simulation claims to establish them.

Costs are limited to the approved code upload, one secret, bounded Lambda/S3/
Secrets Manager/log usage, and retained evidence. No schedule, Athena query,
training job, endpoint or monitoring service is created.

### Cleanup / rollback commands (NOT executed)

After a failed smoke test, disable further invocations and stop for review. Only
if rollback is approved for this NEW dedicated stack:

```bash
aws lambda put-function-concurrency --function-name fbs-cloud-ingestion --reserved-concurrent-executions 0
aws cloudformation delete-stack --stack-name fbs-cloud-ingestion
aws cloudformation wait stack-delete-complete --stack-name fbs-cloud-ingestion
```

This removes the dedicated function, invocation configuration and execution role.
The log group is retained. Keep the secret, application ZIP, raw data, checkpoint
and ledger untouched pending separate retention/removal approval. Do not delete
the ledger to enable token reuse. No cleanup was performed during PM-02B.

## PM-02C preflight checkpoint (superseded by completed execution below)

The proposal/template hash baselines were explicitly established by Hampton in
the PM-02C continuation, not verified against an earlier recorded hash baseline.
All three accepted hashes were recomputed and matched before cloud changes.
Read-only preflight confirmed the account, private AES256 bucket settings and
unused proposed resource names. The secure Terminal getpass workflow was opened
for the approved single-secret creation; at this checkpoint it was awaiting input.
No secret creation attempt, artifact upload, stack creation, Lambda invocation or
CFBD HTTP attempt had occurred. This is preflight evidence, not cloud-runtime
verification, and it does not satisfy the pending ingestion acceptance criteria.

Checkpoint evidence: `data/processed/pm02c-deployment-20261120T064607Z-10f5f9/`.
This pending checkpoint was superseded by the successful execution below. Do
not repeat secret creation or deployment from this historical checkpoint.

## PM-02C completed execution — cloud evidence

The three hashes were recomputed immediately before execution and matched the
explicitly accepted PM-02C baselines. The proposal/template baselines were
**established by Hampton's current acceptance**, not matched to an earlier
recorded baseline. The original proposal and template were preserved; execution
parameters with the newly created secret ARN were stored separately.

### Deployed resources and boundaries

- One secret, `fbs/cfbd-api-key`, created through the secure hidden Terminal
  prompt. No secret value was saved locally, printed, or returned to chat.
- The exact reviewed application ZIP was conditionally uploaded to its proposed
  immutable key; its SHA-256 was verified by remote readback.
- Stack `fbs-cloud-ingestion` reached CREATE_COMPLETE in us-east-1. It contains
  exactly the four approved resources: Lambda, named execution role, log group
  and async retry configuration. The execution role's deployed inline policy
  exactly matches the approved template; no managed policies were attached.
- Function runtime is Python 3.14/x86_64, Active, 512 MiB, 180-second timeout,
  reserved concurrency 1. AWS executed the Linux handler successfully with the
  approved ZIP digest. This is actual cloud-runtime evidence, unlike the earlier
  macOS package-import check.
- Log retention is 14 days; async retries remain zero with maximum age 60 seconds.
- The existing bucket remains AES256 encrypted with all four public-access blocks
  enabled. No bucket policy, IAM permission expansion, schedule, public endpoint,
  training job or monitoring infrastructure was added.

Cloud operations used SDK equivalents of the reviewed commands. Stack creation
used DO_NOTHING on failure to preserve any partial resources, consistent with
the stop-and-preserve instruction; no failure occurred and no rollback ran.

### Smoke invocations and receipt verification

| Invocation | HTTP / receipt result | Verification |
| --- | --- | --- |
| Fresh: 2026 Week 12, reviewed token | Lambda HTTP 200, completed; CFBD HTTP 200 | 70 records; raw, manifest, checkpoint and metadata verified |
| Identical replay | Lambda HTTP 200, completed | Original receipt and payload digest unchanged; no new fetch-start |
| Conflict: same token, Week 13 | Lambda HTTP 200, failed at claim | Expected rejection; no new fetch-start or source mutation |

All five evidence objects (claim, capture, raw, manifest, completion) retained
identical hashes, ETags, lengths and modification times across replay/conflict.
The API response was captured inside Lambda. Independent verification read its
bytes in memory without writing or printing private records. Raw and manifest
bytes exactly matched the durable checkpoint; manifest coverage/count/parameters
and the receipt's source hashes and timestamps agreed.

Run start: `2026-11-20T06:56:17.230238Z`. Response observation: `2026-11-20T06:56:17.567041Z`
(November 20, 2026, 01:56:17 AM EST). Completion: `2026-11-20T06:56:17.867207Z`.
Raw fingerprint: `5ccd0696`; manifest: `bb56fd45`; capture: `d6c19066`.

Historical availability remains unknown. `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`,
`approved_for_point_in_time_forecasting=false`, and
`approved_for_predictor_use=false` are unchanged. This capture does not certify
historical publication time or approve operational forecasts.

### Attempt budget, logs and outcome

Exactly three synchronous invocations were performed, with no invocation retries.
CloudWatch corroborated exactly one `cfbd_fetch_start` for the reviewed token;
the deployed fetch path permits one HTTP attempt and its response was HTTP 200.
Thus the authorized one-attempt CFBD budget was met. Logs contained only Lambda
lifecycle records and the sanitized fetch-start record. Verification evidence
saves log classifications/digests, not full messages or secrets.

All ingestion acceptance checks passed. No function was disabled because no
deployment/smoke/verification failure occurred; concurrency remained 1 at final
verification. No further invocations, fresh tokens, cleanup or API requests were
made during PM-02C. That deployment round made no Git/GitHub mutations; PM-02D
preserves the matching implementation and sanitized result in version control.

Sanitized execution evidence is in `data/processed/pm02c-deployment-20261120T064607Z-10f5f9/`:

- `baseline-verification.json`, `preflight.json`, and `secret-creation.json`;
- `artifact-verification.json`, `stack-resources.json`, `runtime-verification.json`;
- three `invoke-*-receipt.json` and `invoke-*-metadata.json` pairs;
- `capture-verification.json`, object snapshots before and after replay/conflict;
- `cloudwatch-evidence.json`, `final-resource-verification.json`, `deployment-status.json`.

Operational ARN references and resolved parameters are separate ignored files;
never commit or display them. No secret values or raw API records are saved in
this documentation or sanitized execution evidence. The full serverless ML
lifecycle remains unfinished beyond this now-verified ingestion slice.
