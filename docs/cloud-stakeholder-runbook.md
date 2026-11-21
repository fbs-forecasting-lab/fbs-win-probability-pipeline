# Private stakeholder adapters: deployment and verification runbook

**PM-07A deployed and verified Phase A.** The original four explanation/one
refusal invocation allowance and single provider request are exhausted. The
commands below preserve the reviewed procedure, not permission to run it again;
further workloads require separate authorization. See the
[contract](stakeholder-insights-contract.md) and
[actual verification record](cloud-stakeholder-verification.md).

## Concrete candidate

Stack `fbs-stakeholder-insights`, `us-east-1`, uses
`infra/cloud-stakeholder.yaml` and `CAPABILITY_NAMED_IAM`: exactly eight resources.

| Logical resources | Exact identity / configuration |
| --- | --- |
| `Explanation`, `ExplanationRole`, `ExplanationLogs`, `ExplanationAsync` | Function `fbs-stakeholder-explanation`; role `fbs-stakeholder-explanation-execution`; log group `/aws/lambda/fbs-stakeholder-explanation`; 512 MiB, 90 seconds |
| `Benchmark`, `BenchmarkRole`, `BenchmarkLogs`, `BenchmarkAsync` | Function `fbs-sportsbook-benchmark`; role `fbs-sportsbook-benchmark-execution`; log group `/aws/lambda/fbs-sportsbook-benchmark`; 1,536 MiB, 180 seconds |

Both functions use Python 3.14/x86_64, `FunctionUpdate` runtime management,
reserved concurrency one, fourteen-day logs and zero asynchronous retries.
There are no schedules, public endpoints, rules, subscriptions, alarm actions
or public hosting. Existing monitoring/weekly delivery remains disabled.

Artifact key within the existing private project bucket:

```text
initial-demo/cloud-artifacts/cloud-stakeholder/55b0ec8af283dab3a9ae67ca47f0ca528a7c87e2810bb89333530625463afdd7.zip
```

Exact private account/bucket, pinned source/model identities, parameters and
fixed tokens are in `data/processed/pm07-readiness-20261120/deployment-proposal.json`
and its `approval-baselines.json`. Do not copy private evidence into Git.
Bucket ownership, encryption, policies, ACLs and privacy settings must not change.

The explanation role alone receives `bedrock:InvokeModel` for
`arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0`.
`Converse` uses that permission. No cross-region profile, other model or provider
secret is needed. `MarketSecretArn` stays **empty**: no secret is created/read,
no secret-read permission is included, and market HTTP is refused before calls.

## Preflight and frozen hashes

Before writes, verify the baseline's own hash against the review record, then
every recorded file/source, dependency pins, template and ZIP. Reject material
drift rather than rebuilding and substituting a different artifact.

```bash
.venv/bin/python -B - <<'PY'
import hashlib, json, zipfile
from pathlib import Path
root = Path.cwd()
ready = root / 'data/processed/pm07-readiness-20261120'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = ready / 'approval-baselines.json'
assert sha(baseline) == 'bf4897cd77547a5372ba4dbf5f5e1fe8b95b362e11ed222848d542660edf3993'
b = json.loads(baseline.read_text())
p = json.loads((ready / 'deployment-proposal.json').read_text())
for name, expected in b['files'].items():
    assert sha(root / name) == expected, name
assert sha(root / p['template']) == b['template_sha256']
assert sha(root / p['application_zip']) == b['zip_sha256']
assert sha(root / p['requirements']) == b['requirements_sha256']
with zipfile.ZipFile(root / p['application_zip']) as z:
    assert z.testzip() is None
    for name, expected in b['source_sha256'].items():
        content = (root / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected, name
        assert z.read(name) == content, name
print('Approved files, dependency pins and packaged source match.')
PY
```

Recheck account/region/owner, active Free-plan status and eligible service coverage
against the proposal; do not repeat a broad billing investigation. Stop if a paid
upgrade, agreement activation, subscription, purchase or Organizations enrollment
is required. Direct regional Nova Micro must still be available with positive
quota. Metadata is not invocation evidence; AWS credits do not establish
third-party coverage.

Require all four bucket-level public-access blocks, expected encryption/ownership
and any existing policy's nonpublic status. Only exact `NoSuchBucketPolicy` means
policy absent, not proof of privacy; other errors/malformed responses stop.
Check stack, role, function and log names for collisions. Snapshot predecessors,
disabled controls and selected source/model object bytes/metadata. Validate the
template and resolved policies with the exact reviewed parameters.

## Upload and deploy only after approval

Use a fresh ignored evidence directory. Keep tracing/debug logs off; use the
reviewed AWS profile if one is recorded. Variables below are not printed.

```bash
export AWS_MAX_ATTEMPTS=1
PM07_READY=data/processed/pm07-readiness-20261120
PM07_RUN="data/processed/pm07-deployment-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$PM07_RUN"
PM07_BUCKET="$(.venv/bin/python -B -c 'import json; print(json.load(open("data/processed/pm07-readiness-20261120/deployment-proposal.json"))["bucket"])')"
PM07_KEY=initial-demo/cloud-artifacts/cloud-stakeholder/55b0ec8af283dab3a9ae67ca47f0ca528a7c87e2810bb89333530625463afdd7.zip
PM07_ZIP=data/processed/pm07-package-20261120-final/cloud-stakeholder.zip
aws cloudformation validate-template --region us-east-1 \
  --template-body file://infra/cloud-stakeholder.yaml \
  > "$PM07_RUN/template-validation.json"
aws s3api put-object --region us-east-1 --bucket "$PM07_BUCKET" \
  --key "$PM07_KEY" --body "$PM07_ZIP" --if-none-match '*' \
  > "$PM07_RUN/artifact-upload.json"
```

Read uploaded bytes back and compare with the approved ZIP before deployment.
If an object exists, stop the upload path and verify it read-only; never overwrite
it or blindly retry an ambiguous write. No bucket setting is changed.

```bash
aws s3api get-object --region us-east-1 --bucket "$PM07_BUCKET" \
  --key "$PM07_KEY" "$PM07_RUN/reviewed-upload.zip" \
  > "$PM07_RUN/artifact-readback.json"
.venv/bin/python -B -c 'import hashlib,sys; assert hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()=="55b0ec8af283dab3a9ae67ca47f0ca528a7c87e2810bb89333530625463afdd7"' \
  "$PM07_RUN/reviewed-upload.zip"
aws cloudformation create-stack --region us-east-1 \
  --stack-name fbs-stakeholder-insights \
  --template-body file://infra/cloud-stakeholder.yaml \
  --parameters "file://$PM07_READY/cloudformation-parameters.json" \
  --capabilities CAPABILITY_NAMED_IAM > "$PM07_RUN/create-stack.json"
aws cloudformation wait stack-create-complete --region us-east-1 \
  --stack-name fbs-stakeholder-insights
aws cloudformation describe-stack-resources --region us-east-1 \
  --stack-name fbs-stakeholder-insights > "$PM07_RUN/resources.json"
```

Before invoking, verify eight physical resources, deployed code hash, resolved
policies, configured limits, empty secret parameter and unchanged predecessors.
Get runtime update mode through `GetRuntimeManagementConfig`; get the actual
runtime ARN from `GetFunctionConfiguration`. Do not require or fabricate a
manual-mode ARN for `FunctionUpdate`. Record actual Python/library versions;
static ELF/macOS imports are not AWS Linux execution proof.

## Exact Phase A smoke sequence

Execute sequentially and accept each result before continuing. Maximum: **four
explanation and one benchmark Lambda invocations**, **one** Converse attempt,
6,144 input bytes, 128 output tokens, one SDK attempt. **Zero** odds/CFBD requests,
secret reads, outcome captures, Athena queries, fits, model-inference invocations
or weekly executions. Never retry an ambiguous invocation.

1. Genuine explanation using the fixed saved report:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-stakeholder-explanation \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload "file://$PM07_READY/explain-request.json" \
     "$PM07_RUN/01-explain.json" > "$PM07_RUN/01-invoke.json"
   ```

   Require a real valid fact selection. Verify four artifacts, claim, attempt,
   checkpoint, completion hashes, allowlisted input, provider/model/region and
   actual response ID/usage. Invalid/truncated/denied output means unavailable:
   preserve it and stop, without a new token/model or substitute explanation.
   A completed-but-unavailable result is not successful LLM verification.

2. Snapshot output bytes/metadata, then replay:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-stakeholder-explanation \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload "file://$PM07_READY/explain-request.json" \
     "$PM07_RUN/02-replay.json" > "$PM07_RUN/02-invoke.json"
   ```

   Require the original completion and identical stored bytes/metadata, with no
   second provider call.

3. Changed source hash must fail at `verified_facts` before provider work:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-stakeholder-explanation \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload "file://$PM07_READY/invalid-source-request.json" \
     "$PM07_RUN/03-invalid-source.json" > "$PM07_RUN/03-invoke.json"
   ```

   Its separate claim may exist, but no external attempt/completion may be created.

4. Reject changed input with the original token before provider work:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-stakeholder-explanation \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload "file://$PM07_READY/conflicting-request.json" \
     "$PM07_RUN/04-conflict.json" > "$PM07_RUN/04-invoke.json"
   ```

   Original artifacts must remain unchanged.

5. Unconfigured market access must refuse before clients/HTTP/publication:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-sportsbook-benchmark \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload "file://$PM07_READY/market-unconfigured-request.json" \
     "$PM07_RUN/05-market-unconfigured.json" > "$PM07_RUN/05-invoke.json"
   ```

   Require `unavailable`, `access_refusal`, zero provider attempts and secret
   reads. This is an access guard test, **not genuine odds verification**.

Collect Lambda REPORT duration/max-memory/runtime, invocation responses, immutable
hashes/metadata and actual provider usage/request identity. Inspect available
Bedrock invocation metrics within the bounded test window as corroboration;
report absent evidence rather than inventing it or attributing unrelated calls.
Attempt/checkpoint evidence and single-attempt SDK configuration must also agree
with the one-call bound. Check logs/artifacts for credentials and stakeholder
allowlist violations. Verify protected objects and disabled controls unchanged.

## Market phase: blocked and separately authorized

Confirm a free The Odds API account, usable quota and NCAAF/bookmaker access off
screen first. Do not purchase historical access or change subscription. Future
approval must pin the exact secret ARN/parameter change, request/token/window,
at least one genuine current-odds HTTP attempt, and invocation/credit bounds.

Enter any future key through a real terminal's hidden `getpass` prompt, requiring
`stdin.isatty()`. Never paste it into chat, command arguments/history, reports or
source files; do not pipe it or persist plaintext. A future approved helper can
create one `fbs/the-odds-api-key` secret directly from memory and record only its
ARN privately. Default Secrets Manager encryption needs no customer-managed
key configuration. Confirm storage/request coverage before creation. No such
secret/helper execution is authorized now. Review an exact-ARN conditional IAM
parameter update separately before enabling capture.

Capture once, retain genuine quota headers/raw hashes/timestamps, then construct
explicit mappings from captured events and compare without another fetch. Keep
missing/ambiguous rows. The saved Week 13 cutoff has passed: current retrieval
cannot supply pre-cutoff odds, even with an older quote update. Expected aligned
count is zero, not grounds for retries, paid history, fabricated games or weaker
timing. Nonzero comparison needs separately approved model/market observations
before a common future cutoff, or already captured eligible evidence. Later
outcomes are separately selected evaluation-only inputs with coverage thresholds.

## Cost, failure handling and cleanup

Maintain active Free-plan access and eligible credits. Lambda requests/compute,
S3 storage/requests, fourteen-day logs and the bounded first-party call can consume
credits. Phase A's configured Lambda ceiling is **450 GiB-seconds** across five
invocations; measure actual use. No personal payment, paid upgrade, subscription,
agreement activation, purchase or Organizations enrollment is permitted. Stop if
required. No ongoing schedule or market secret is proposed in Phase A.

On unexpected workload failure, ambiguous response, integrity/runtime drift or
scope change: stop, preserve evidence, and disable **only** the new functions
that exist. Do not expand permissions or retry with new tokens/providers.

```bash
aws lambda put-function-concurrency --region us-east-1 \
  --function-name fbs-stakeholder-explanation --reserved-concurrent-executions 0
aws lambda put-function-concurrency --region us-east-1 \
  --function-name fbs-sportsbook-benchmark --reserved-concurrent-executions 0
```

This is failure shutdown, not deletion. Leave predecessors, data, logs, stack and
reviewed artifact intact. Destructive cleanup needs separate authorization; none
is granted here. After a successful smoke, report function status/evidence gaps
before more workloads. Public display, delivery and operational approval remain
outside this slice.

## Actual PM-07A result

On November 20, 2026 Eastern time (November 21 UTC), the exact approved package
and template deployed eight resources successfully. Both handlers ran in AWS
Linux with the reviewed runtime identity. All five smoke outcomes passed: genuine
available explanation, immutable replay, source-hash and token-conflict rejection,
and zero-call unconfigured-market refusal. Four explanation calls and one market
call consumed exactly one Bedrock request, corroborated by CloudWatch. Actual
usage was 257 input and 42 output tokens; the fact/instruction payload was 1,160
bytes. Validated output preserved pending labels and retrospective/unapproved
status without changing authoritative metrics or predictions.

Eighty-seven protected object bytes/metadata and predecessor settings remained
identical. Both functions remain active at concurrency one. Market secret access,
schedules, delivery, alarm actions, notifications and public display stay disabled.
No other workload ran. Free-plan coverage remained active with $119.99 reported
credits; billing/credit updates can lag consumption. The
[verification record](cloud-stakeholder-verification.md) contains measured duration,
memory, provenance and replay evidence. Private evidence is ignored under
`data/processed/pm07a-deployment-20261121T043424Z/`. The package/template and all
original approval hashes remain unchanged; only sanitized documentation changed.

This verifies the bounded extractive explanation application. It does not verify
genuine sportsbook capture, a nonzero paired benchmark, rolling performance,
public delivery or operational approval. The market prerequisites above still
require separate authorization; do not reexecute Phase A or use a new token.
