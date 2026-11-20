# Cloud preparation and Athena (PM-03)

**Cloud preparation recovered and verified on November 20, 2026 (PM-03D).**
The function is enabled at reserved concurrency one in **recovery-only mode**;
new query creation is explicitly denied. Parity and six-file dataset publication
completed using the original query and captures. PM-02 ingestion is unchanged.
This slice does not train models, issue forecasts or complete the serverless ML
system.

## PM-03D verified recovery — November 20, 2026

The approved proposal, template, package, compatibility-record and original-event
hashes matched before cloud changes, as did all 15 packaged project files. The
corrected immutable artifact was uploaded/read back and the existing stack
updated with `CAPABILITY_NAMED_IAM`. All seven physical resource identities were
preserved. The deployed role exactly matched the narrowed policy, with no
managed policies attached; recovery-only mode and the explicit query-start
denial were verified before concurrency was restored to one.

| Additional invocation | Observed result |
| --- | --- |
| Resume original selection | Completed in AWS Python 3.14 x86_64 Linux; original successful query reused; all parity checks passed |
| Completed replay | Identical completion receipt; all 61 checked source/normalized/dataset/query-result objects retained hashes, ETags, sizes and modification times |
| Missing season | Rejected before source/query operations |
| Post-cutoff input | Rejected at source eligibility |

Recovery used **four additional preparation invocations**, five total including
PM-03B, with **zero additional CFBD requests and zero new Athena executions**.
CloudWatch showed no ingestion fetch-start during recovery. The original query
remained the sole execution, `SUCCEEDED`, with unchanged **15,540,870 scanned
bytes**; the workgroup's 128 MiB limit is unchanged. The 54 objects preserved
from the failed attempt, including original provenance/query identity, were
unchanged after recovery and negative tests.

The cloud Python/SQL gate verified **3,065 normalized targets**, including
eligibility exclusions, prior counts, labels and predictors (`1e-12` tolerance).
The split counts are now parity-verified, rather than diagnostic:

| Split | Target rows | Published rows | Excluded |
| --- | ---: | ---: | ---: |
| Train, 2022–2024 | 2,237 | **2,194** | 43 |
| Holdout, 2025 | 762 | **740** | 22 |
| Prediction, 2026 Week 12 | 66 | **59** | 7 |

Dataset fingerprint: `f2f55540`. All six files (`train.csv`, `holdout.csv`,
`prediction.csv`, `team_season_aggregates.csv`, `exclusions.json`,
`dataset_report.json`) were published and hash-verified, with the run completion
receipt last. The existing baseline dataset loader also passed without fitting
a model. The six sources account for 4,403 raw records, 3,797 retained normalized
rows, 605 exclusions and one quarantine; per-season counts are preserved below.

Deployed corrected ZIP SHA-256:
`3fe91ccce611465c3033979cf657501589eb0ccaa957ac336c3ef38191edb43e`.
Recovery template SHA-256:
`c2e28624c5f00b965d5816617a9f0445a187e53eaca4291a8974fdede2f314ea`.
The packaged runtime/identity record matches the implementation. Final local
verification passed **216 offline tests** with network blocked. Bucket
privacy/encryption and ingestion configuration remained unchanged. The confirmed
Free plan remained active; no upgrade, purchase, subscription, Organizations
enrollment or additional service was used.

Historical availability remains unknown. Retrospective mode and all three false
availability/approval flags are unchanged. These are prepared saved-snapshot
rows, not approved operational forecasts. Private receipts, raw/data artifacts,
packages, source identities and detailed execution evidence remain outside Git.

### Recovery-only limitation

The current function may inspect/finalize its existing successful query but
**cannot create a query for a subsequent weekly selection**. Application mode
and the execution role's explicit Start denial both enforce this. Future weekly
preparation requires deliberate reviewed reconfiguration of both controls and
separate authorization, plus appropriate identity/version review. Changing only
the mode flag does not remove the IAM denial. Do not invoke captures or alter
selections to work around it. Cloud training/inference, operational eligibility
and the rest of the serverless system remain unfinished.

## PM-03C local correction and recovery proposal — historical preparation

This section records preparation before PM-03D approval/execution. Its commands
describe the recovery that subsequently succeeded above.

The local fix compares `returned_sql.strip()` with `submitted_sql.strip()` only
when verifying Athena's returned query. It does not alter the SQL file, submitted
SQL, internal whitespace, literals, comments, database/workgroup checks, source
selection, client token or query-argument hash.

Because v1 selection identity includes implementation hashes, simply editing
the adapter would select a different run. `preparation_identity_v1.json` records
the original identity-source hashes and the exact corrected runtime hashes.
`implementation_hash` verifies all nine relevant files, anchors the original
hash to the deployed version, and permits differences only in the adapter and
contract files. It then returns that original v1 identity. Missing/stale or
unreviewed compatibility data fails closed; callers cannot supply an identity
override. The deployment ZIP hash separately identifies the corrected runtime.

Offline comparison with preserved PM-03B evidence confirmed the original request,
selection, SQL bytes/hash, client token, query-argument hash and exact saved
`query.json` hash. Recovery therefore uses the existing successful execution,
not a replacement. The same six source references and existing normalized
objects are retained. No cloud API was called during PM-03C.

Recovery-only mode requires an existing query receipt and `SUCCEEDED` execution;
it refuses to call `StartQueryExecution` if either is absent. The corrected
template sets `PREPARATION_RECOVERY_ONLY=true`, removes the Start permission,
and explicitly denies that action for the existing workgroup. Database,
workgroup, SQL-body, source integrity and mandatory parity checks remain in
force. Source/history/status semantics and normalization are unchanged.

New verification: **28 focused tests and 216 full offline tests passed**, with
network connections blocked in the full suite. Local template lint/structure,
ZIP CRC/source equality, runtime identity and isolated packaged import checks
passed. The corrected package has two changed Python files and one new identity
record; the SQL and 2,286 dependency files are byte-identical to the deployed ZIP.
An isolated macOS import is not corrected-package AWS Linux verification.

The ignored `data/processed/pm03c-recovery-20261120/` directory contains
`recovery-proposal.json`, `approval-baselines.json`, exact event files and stack
parameters. The corrected ZIP is in `data/processed/pm03c-package-20261120-1/`.
The baselines bind the proposal, template, ZIP, compatibility record and original
event bytes. Prior approvals and failure evidence are preserved; do not replace
their hashes with these new baselines.

### Proposed recovery sequence — requires one new approval

Use the same account/region/stack and the confirmed active Free plan with eligible
credits. Do not repeat the billing investigation or wait for reporting to settle.
No Paid-plan upgrade, purchase, subscription, Organizations enrollment or new
service is permitted. Stop if a required action needs an upgrade. No Cost Explorer
API calls are needed. Existing evidence/storage remains preserved.

1. Recompute the new approval hashes and check packaged sources. Read-only guards
   must confirm the deployed predecessor code and reserved concurrency zero,
   the original successful query/receipt and six source references. Stop on
   material drift. No CFBD fetch or Athena submission is permitted.
2. Upload the corrected ZIP with `If-None-Match: *` to the exact artifact key in
   the private proposal; read back and verify its SHA-256. Reuse an existing
   object only if its bytes match. Never replace an artifact.
3. **Update the existing stack**, using the corrected template and prepared
   parameters; do not create another stack or directly update Lambda code outside
   CloudFormation. This updates CodeKey, recovery-only environment and narrowed
   IAM while retaining all seven resource identities and existing limits:

   ```bash
   aws cloudformation update-stack --region us-east-1 \
     --stack-name fbs-data-preparation \
     --template-body file://infra/cloud-preparation.yaml \
     --parameters file://data/processed/pm03c-recovery-20261120/stack-parameters.json \
     --capabilities CAPABILITY_NAMED_IAM --disable-rollback
   aws cloudformation wait stack-update-complete --region us-east-1 \
     --stack-name fbs-data-preparation
   ```

4. Verify corrected CodeSha256, recovery-only mode, the Start denial and unchanged
   resource settings. Restore concurrency to the template's desired value of one;
   this explicitly resolves the previous failure-shutdown drift:

   ```bash
   aws lambda put-function-concurrency --region us-east-1 \
     --function-name fbs-data-preparation --reserved-concurrent-executions 1
   ```

5. Allow **at most four additional preparation invocations**, using the prepared
   event files below. One was used in PM-03B, so success would total five out of
   the original twelve, within the eleven remaining. There are no automatic
   pending loops or failure retries.

   | Additional call | Event file | Required evidence |
   | --- | --- | --- |
   | 1 | `original-selection.json` | Existing successful query ID; mandatory Python/SQL parity; six verified dataset files; completion last |
   | 2 | `original-selection.json` | Same completed receipt/query; unchanged source, normalized, dataset and query-result object hashes/metadata |
   | 3 | `missing-season.json` | Refused before source/query operations; query count unchanged |
   | 4 | `post-cutoff.json` | Refused at source eligibility; no new query or capture |

   For each, invoke synchronously and save results separately in a new ignored
   evidence directory:

   ```bash
   aws lambda invoke --region us-east-1 --function-name fbs-data-preparation \
     --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
     --payload file://data/processed/pm03c-recovery-20261120/original-selection.json \
     "$EVIDENCE/recovery-01.json"
   ```

The hard recovery limits are **zero additional CFBD requests and zero new Athena
executions**. The original single execution remains the only query. Missing or
changed query evidence is a stop, not permission to submit a replacement. The
2,194/740/59 split counts remain diagnostic until the deployed parity gate and
publication actually complete. Do not change zero/missing eligibility to force
a prediction example.

On any unexpected failure, stop and set only preparation concurrency to zero,
preserving all resources, captures, query results, logs and partial publication.
No retry/new token/query or permission expansion is authorized. The temporary
shutdown drift is intentional and must be recorded. No cloud recovery occurred
in PM-03C; the function remains disabled and the prior failure unresolved in AWS.

## PM-03B actual result — November 20, 2026

The approved proposal/template/ZIP hashes matched, and all 14 packaged source/SQL
files matched the implementation. The reviewed ZIP was uploaded conditionally
and read back. All seven approved resources reached `CREATE_COMPLETE` in
us-east-1; deployed code matched the ZIP. The workgroup enforces the approved
134,217,728-byte (128 MiB) scan cutoff.

Five sequential full-season backfills completed with HTTP 200 using the approved
stable tokens. CloudWatch recorded exactly five fetch-starts, one per token;
each deployed fetch permits one HTTP attempt. The existing 2026 Week 12 capture
was reused. All six cloud-receipt identities and raw/manifest hashes were
verified. No secret value was retrieved into the controller.

Normalization ran inside AWS Linux Lambda and published verified CSV, exclusion
and quality artifacts, provenance and selected JSON-lines input:

| Season | Raw | Retained | Excluded | Quarantined |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 849 | 732 | 117 | 0 |
| 2022 | 854 | 734 | 120 | 0 |
| 2023 | 868 | 750 | 118 | 0 |
| 2024 | 874 | 753 | 120 | 1 |
| 2025 | 888 | 762 | 126 | 0 |
| 2026 Week 12 | 70 | 66 | 4 | 0 |
| Total | 4,403 | 3,797 | 605 | 1 |

There was **one preparation invocation and one unique Athena execution**.
Athena reached `SUCCEEDED`, scanning **15,540,870 bytes**. However,
`GetQueryExecution.Query` omitted the SQL's final newline (2,758 requested
characters versus 2,757 returned). Workgroup/database matched and SQL matched
after trimming boundary whitespace. The adapter's exact comparison returned
`failed` at `athena_query`, before the Python/SQL parity gate.

Read-only inspection of that same query produced these diagnostic counts;
they are **not a completed or parity-approved dataset**:

| Split | Normalized targets | SQL-eligible | Excluded |
| --- | ---: | ---: | ---: |
| Train, 2022–2024 | 2,237 | 2,194 | 43 |
| Holdout, 2025 | 762 | 740 | 22 |
| Prediction, 2026 Week 12 | 66 | **59** | 7 |

No six-file dataset or completion receipt was published. Replay and the two
negative invocations were **not run**, because the failure procedure stopped
the sequence. The new function's reserved concurrency was set to zero and
verified; no other resource was disabled or deleted. Captures, normalized
objects, query results and logs were retained. Bucket privacy/encryption and
the deployed ingestion configuration stayed unchanged, as did all unknown
historical-availability and retrospective/unapproved flags.

A preliminary controller paginator issue was corrected before cloud writes or
workload invocations, with its separate record preserved; no execution allowance
was consumed. Application source, template, ZIP and baselines were unchanged.
Detailed receipts, query comparison, hashes and metadata remain in ignored
evidence. A reviewed fix and fresh authorization are needed before updating or
re-enabling preparation or submitting another query. Reuse the six captures;
no new CFBD fetch is needed. Code changes affect selection identity, so do not
assume they automatically reuse this execution. See the
[verification summary](cloud-preparation-verification.md).

## Implemented flow

`src.pipeline.cloud_preparation.handler` runs in Python 3.14 Lambda:

1. Require explicit retrospective permission and exactly one version per season
   2021–2026, each identified by a manifest filename and expected raw/manifest
   SHA-256 hashes. Historical seasons must be full-season requests.
2. Check all four bucket public-access blocks; use `S3Store.download_raw` and
   `games.load_snapshot` to verify selected pairs in cloud temporary storage.
   No CFBD request, secret lookup or local-history discovery occurs.
3. With `require_cloud_sources=true`, verify ingestion completion receipts,
   their capture checkpoints, requests, exact final bytes and hashes for all six
   seasons. Otherwise label missing receipt lineage `legacy_upload_unverified`;
   that mode is for reference checks, not the graded cloud-ingress path.
4. Reuse `games.normalize_snapshot`, preserving FBS inclusion, exclusions,
   duplicates and quarantine. Reuse `dataset.build_dataset` as the existing
   baseline-compatible reference serializer and independent SQL parity oracle.
5. Publish normalized CSV/exclusions/quality/provenance under
   `initial-demo/cloud-preparation/runs/<selection_id>/`. One JSON-lines file
   contains only the selected versions under
   `cloud-preparation/queryable/selection_id=<selection_id>/games.jsonl`.
   `prepared.json` binds their hashes; it is not dataset completion.
6. A normal run submits `prior_season_features.sql` to the dedicated Athena workgroup. It
   aggregates completed Y-1 games from each team's perspective, joins team IDs,
   separates labels, and reproduces completion/missing-history/chronology
   exclusions. An injected partition equality isolates the selected versions.
   The current recovery-only deployment reads the existing successful execution
   and cannot submit another query.
7. Return `query_pending` for queued/running queries. Invoke the **same event**
   to finalize. A stable Athena client token recovers a lost start response;
   `query.json` binds execution ID to exact arguments. Never change selection
   to work around a failed query.
8. Compare every SQL target, split, exclusion reason, prior-game count, label
   and eligible predictor with the Python reference (`1e-12` numeric tolerance).
   Only then publish the six existing dataset files under
   `initial-demo/datasets/<dataset_id>/` and write `complete.json` last. The
   compatible CSV bytes use the existing Python serializer, gated by actual
   Athena feature equivalence; this does not introduce a second model path.

The original v1 selection identity hashes the canonical request, approved
implementation/SQL bytes and catalog/workgroup names. The PM-03C compatibility
record attests corrected runtime bytes while preserving that existing identity;
it is not a general exemption for future code changes. Dataset identity retains existing source/normalizer
hash logic. Changed source versions get new identities. Application writes use
`If-None-Match: *`, readback and conflict refusal. Matching partial publication
resumes safely. A completed bundle with missing/corrupt artifacts fails rather
than silently repairing evidence. Completed replay re-verifies sources,
normalization, query results and all six dataset files without another query or
CFBD fetch. Athena's uniquely named result objects use service writes in a
separate results prefix; those do not support the application conditional-write
protocol.

## PM-03 predeployment coverage — read-only, November 20, 2026

| Season | Raw records | Observation | Origin |
| --- | ---: | --- | --- |
| 2021 | 849 | September 23 | Full-season legacy local upload |
| 2022 | 854 | September 23 | Full-season legacy local upload |
| 2023 | 868 | September 23 | Full-season legacy local upload |
| 2024 | 874 | September 23 | Full-season legacy local upload |
| 2025 | 888 | September 23 | Full-season legacy local upload |
| 2026 Week 12 | 70 | November 20, 06:56:17 UTC | Verified cloud capture |

At that inspection the ingestion ledger contained one completed cloud capture: 2026 Week 12. That
is target coverage, not training history. Minimum graded-path backfill is five
full-season cloud requests, 2021–2025, through existing ingestion. **None were
executed in PM-03; all five completed in PM-03B, as recorded above.** Fresh history may differ from September; do not promise old
dataset IDs or metrics. A November sample may contain completed games and few
or zero prediction rows; do not fabricate history or future eligibility.

## Leakage and operational refusal

Every artifact retains `dataset_mode=retrospective_demo`,
`historical_availability_verified=false`,
`approved_for_point_in_time_forecasting=false`, and
`approved_for_predictor_use=false`. Capture establishes observation then, not
historical publication. `forecast_cutoff` requests an eligibility assessment:
observation/publication at or after it is rejected; earlier observations still
fail because historical availability, actual completion and schedule versions
are unverified. No operational request is currently approved. Future forecasts
need version-specific publication/completion evidence before the issued cutoff,
historical schedules/reschedules and explicit eligibility approval. Splits stay
train 2022–2024, holdout 2025, unlabeled eligible 2026 sample; downstream fitting
must remain train-only. No fitting occurs in this slice.

## Original deployment proposal — approved and deployed in PM-03B

The specification and commands below record the approved scope, not permission
to rerun the stopped sequence or replace its single query.

Region `us-east-1`; stack/function/workgroup `fbs-data-preparation`; role
`fbs-data-preparation-execution`; retained log group
`/aws/lambda/fbs-data-preparation`; Glue database `fbs_preparation`, table
`selected_games`. Use existing `<FBS_S3_BUCKET>` and `initial-demo`. Encryption
observed SSE-S3/AES256; all four public-access blocks enabled. No bucket,
secret, KMS key, bucket-policy, ingestion-permission or schedule changes.

Seven new resources: Lambda, role, 14-day log group, async retry policy (zero
retries), Glue database/table, Athena workgroup. Lambda uses Python 3.14 x86_64,
1 GiB memory/temp storage, 180 seconds, concurrency 1. The role reads selected
project raw/ingestion data and writes preparation artifacts, datasets and Athena
results. No secret access, object deletion, ingestion invocation, catalog mutation
or bucket-setting permissions. Artifact writes require the exact conditional
header. Access Analyzer's wildcard-without-Like warning is intentional: `*` in
`s3:if-none-match` is a **literal required header value**, not a wildcard pattern.

Workgroup results enforce SSE-S3 in
`initial-demo/cloud-preparation/athena-results/` with a **128 MiB per-query scan
cutoff**. JSON-lines input is capped at 16 MiB and targets at 20,000. CTE references
can rescan data: input size does not equal billed scan size. Inspect actual
statistics; never raise limits automatically. Billable scope: up to five CFBD
attempts, Lambda runtime/invocations, S3 storage/requests, Athena scans, Glue
catalog storage beyond applicable allowances, and retained logs. No cost-free
claim is made.

The ignored readiness directory holds concrete private values and exact artifact
location `initial-demo/cloud-artifacts/cloud-preparation/<ZIP_SHA256>.zip`.
`approval-baselines.json` separately records the final template/ZIP/proposal
hashes, avoiding a circular proposal hash. Recompute all three before approved
actions and stop on drift. Do not put private account/bucket references in Git.
Read-only probes found no preparation Lambda/database; a bounded workgroup
listing confirmed that name is unused. The five proposed backfill tokens are
unclaimed. Recheck these identities immediately before deployment/capture.

### Validate/upload/deploy after approval

These commands describe proposed actions, not completed cloud execution:

```bash
.venv/bin/python -B bin/package_cloud_preparation.py --validate-only
/private/tmp/fbs-pm02b-validation-tools/bin/cfn-lint infra/cloud-preparation.yaml
aws cloudformation validate-template --region us-east-1 \
  --template-body file://infra/cloud-preparation.yaml
```

Read `bucket`, `artifact_key`, `profile`, and reviewed ZIP path from the private
proposal off screen. Use the standard credential chain. Recheck privacy,
encryption and unused resource names. Do not display `.env` or credential values.

```bash
aws s3api put-object --region us-east-1 --bucket "$PROJECT_BUCKET" \
  --key "$ARTIFACT_KEY" --body "$REVIEWED_ZIP" --if-none-match '*'
aws cloudformation deploy --region us-east-1 \
  --stack-name fbs-data-preparation --template-file infra/cloud-preparation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectBucket="$PROJECT_BUCKET" ProjectPrefix=initial-demo \
    CodeBucket="$PROJECT_BUCKET" CodeKey="$ARTIFACT_KEY"
```

On an existing artifact, verify exact bytes/hash before reuse; a mismatch is a
stop. Never replace it. The preparation function has no API key/secret access.

### Backfill and synchronous smoke scope after approval

| Season | Week | Stable token |
| --- | --- | --- |
| 2021 | omitted (full season) | `pm03-backfill-2021-v1` |
| 2022 | omitted (full season) | `pm03-backfill-2022-v1` |
| 2023 | omitted (full season) | `pm03-backfill-2023-v1` |
| 2024 | omitted (full season) | `pm03-backfill-2024-v1` |
| 2025 | omitted (full season) | `pm03-backfill-2025-v1` |

First exact event:
`{"schema_version":1,"season":2021,"idempotency_token":"pm03-backfill-2021-v1"}`.
The private proposal contains all five. Invoke one at a time synchronously,
saving each result and CLI metadata in a new ignored evidence directory:

```bash
aws lambda invoke --region us-east-1 --function-name fbs-cloud-ingestion \
  --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
  --payload file://"$EVIDENCE/backfill-2021.json" "$EVIDENCE/backfill-2021-result.json"
```

Check both transport status and returned state. Repeat only for the other four
listed seasons after success: **at most five CFBD attempts total**. On failure
or interruption preserve the ledger, stop, and do not choose a new token.
Existing completed tokens are verified/reused, never refetched. Week 12 needs
no additional request.

Build `selected-sources.json` from those five completed receipts plus the existing
Week 12 receipt. Request fields: `schema_version=1`,
`allow_retrospective_demo=true`, `require_cloud_sources=true`, and six `sources`.
Each source has `season`, `manifest_name`, `raw_sha256`, `manifest_sha256`,
`capture_token_sha256`, `capture_receipt_sha256` (SHA-256 of exact receipt bytes).
Read future snapshot identities from successful receipts; never guess them.
The private proposal includes the existing 2026 reference. The local controller
reads metadata only; normalization/features run inside AWS.

```bash
aws lambda invoke --region us-east-1 --function-name fbs-data-preparation \
  --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
  --payload file://"$EVIDENCE/selected-sources.json" "$EVIDENCE/preparation-01.json"
```

Bound smoke to **12 preparation invocations and one unique Athena execution**:
initial call, up to eight same-event pending/finalization calls, one completed
replay, one missing-season refusal, one post-cutoff refusal. Wait briefly between
pending calls and save separate evidence. A failed query is not retried with a
new selection. If pending at the limit, preserve evidence and stop.

Collect exact event/template/ZIP/proposal hashes, Lambda configuration, six
source origins, normalized accounting/reasons, prepared/query/complete receipts,
Athena SQL/engine/status/scan statistics, parity and six dataset hashes. Verify
unchanged object hashes/ETags/lengths/times on completed replay, no query from
negative requests, and no more than five fetch-starts in ingestion logs. Check
bucket privacy/encryption before and after. Publish only a sanitized summary.

### Failure and cleanup

On deployed preparation smoke failure, disable only the new function and stop:

```bash
aws lambda put-function-concurrency --region us-east-1 \
  --function-name fbs-data-preparation --reserved-concurrent-executions 0
```

Do not expand permissions, delete evidence or fetch again to force success.
Backfill failure pauses the sequence without altering verified ingestion;
follow its [recovery runbook](cloud-ingestion-runbook.md).

Cleanup only when separately requested removes the new stack, not project data:

```bash
aws cloudformation delete-stack --region us-east-1 --stack-name fbs-data-preparation
aws cloudformation wait stack-delete-complete --region us-east-1 --stack-name fbs-data-preparation
```

Logs are retained; the workgroup has recursive deletion disabled. If query
history blocks removal, leave it disabled for reviewed cleanup, not forced
deletion. Preserve bucket, captures, datasets, artifact and evidence.

## Verification limits and official references

See the [dated local verification summary](cloud-preparation-verification.md) for
executed checks, counts and available-tool limitations.

Tests run the exact SQL with synthetic data in SQLite,
and compare features/eligibility/labels and existing dataset bytes. Fake S3/Athena
tests cover corruption, conflicts, pending/replay, partial publication and
lineage. **SQLite, mocks, template checks and macOS imports do not prove Athena
or Linux Lambda execution.** No PM-03 workload ran in AWS; the local Docker
service was unavailable then. PM-03B subsequently verified AWS Linux normalization
and Athena SQL execution, but did not reach parity or dataset publication because
of the identity-check failure above.

References: [Hive JSON-lines SerDe](https://docs.aws.amazon.com/athena/latest/ug/hive-json-serde.html),
[injected partition selection](https://docs.aws.amazon.com/athena/latest/ug/partition-projection-dynamic-id-partitioning.html),
[idempotent query start](https://docs.aws.amazon.com/athena/latest/APIReference/API_StartQueryExecution.html),
[workgroup limits](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-athena-workgroup-workgroupconfiguration.html),
[S3 conditional-write enforcement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html).
