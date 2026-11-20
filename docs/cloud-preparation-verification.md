# Cloud preparation verification — November 20, 2026

## PM-03D cloud recovery: all acceptance criteria passed

**The corrected package ran successfully in AWS Lambda's Python 3.14 x86_64
Linux runtime. Data preparation is verified; cloud training/inference and
operational forecasting remain unfinished.**

Before changes, the proposal/template/ZIP/compatibility-record/original-request
hashes matched, along with all 15 packaged project files. The reviewed corrected
ZIP was uploaded without replacement and read back. The existing stack reached
`UPDATE_COMPLETE`; all seven physical resource identities were retained.
Recovery-only mode, the exact narrowed IAM policy and explicit denial of
`StartQueryExecution` were verified before concurrency was restored to one.

| Recovery invocation | Actual result |
| --- | --- |
| Resume original event | Completed; original query reused; Python/SQL parity passed for all 3,065 target rows at tolerance `1e-12` |
| Completed replay | Identical receipt; hashes, ETags, lengths and last-modified times unchanged for all 61 checked objects |
| Missing-season event | Rejected before source/query operations |
| Post-cutoff event | Rejected at source eligibility |

There were **four additional preparation invocations**, five total across
PM-03B/PM-03D, **zero new CFBD requests and zero new Athena executions**.
CloudWatch corroborated zero ingestion fetch-starts during recovery. The sole
original query remained successful, with **15,540,870 bytes scanned** and the
128 MiB cutoff unchanged. Original request, selection, SQL, query receipt/ID,
six source versions and provenance were preserved. All 54 pre-existing source,
normalized and query-result objects retained their bytes and metadata.

| Split | Targets | Parity-verified published rows | Excluded |
| --- | ---: | ---: | ---: |
| Train | 2,237 | **2,194** | 43 |
| Holdout | 762 | **740** | 22 |
| Prediction | 66 | **59** | 7 |

These counts are now verified through the cloud parity/publication gate, not
just diagnostic SQL inspection. Dataset fingerprint: `f2f55540`. All six
baseline-compatible files and the final completion receipt were published and
hash-verified. The existing dataset loader passed without training a model.
Raw/retained/excluded/quarantined totals remain **4,403 / 3,797 / 605 / 1**;
the per-season accounting from PM-03B below is unchanged.

The deployed corrected ZIP matches the implementation, SHA-256:
`3fe91ccce611465c3033979cf657501589eb0ccaa957ac336c3ef38191edb43e`.
Template SHA-256:
`c2e28624c5f00b965d5816617a9f0445a187e53eaca4291a8974fdede2f314ea`.
Final offline verification passed **216 tests, zero failures**, with network
blocked. No model settings or normalization semantics were changed.

The function remains enabled at **reserved concurrency one, recovery-only mode**.
The explicit IAM Start denial remains active. Subsequent weekly preparation
cannot create a query without deliberate reviewed configuration/IAM changes
and separate authorization; changing only the mode flag is insufficient.

Bucket privacy/encryption, the verified ingestion deployment and all historical
availability/status safeguards remained unchanged. Sources are still unknown
historically; datasets remain retrospective and unapproved. No paid-plan upgrade,
purchase, subscription or Organizations enrollment occurred. No recovery failure
or shutdown was required. Private execution details, raw/data artifacts,
deployment packages and proposals remain ignored and outside Git.

The historical PM-03B failure and PM-03C local checks below are retained as the
record of how recovery was prepared; their incomplete status is superseded by
the verified PM-03D result above. See the [runbook](cloud-preparation-runbook.md).

## PM-03C local recovery preparation — not executed in AWS

The boundary-whitespace correction is prepared locally. The deployed function
is still the PM-03B package at reserved concurrency zero. No AWS/CFBD calls,
uploads, updates, enables, queries or workload invocations occurred in PM-03C.
The confirmed Free-plan/credit investigation was not repeated.

The query comparison now trims only leading/trailing whitespace for verification.
Submitted SQL bytes and their hashes are unchanged. SQL-body spacing, literals,
comments, database/workgroup and selected source versions remain exact checks.
A pinned compatibility record verifies the corrected runtime source bytes while
retaining the original implementation/selection identity; unreviewed changes
fail closed rather than selecting a replacement run.

Local calculations matched preserved PM-03B evidence for the original request,
selection, submitted SQL hash, client token, argument hash, query execution ID
and saved query-receipt hash. All six source references are unchanged. Recovery
requires the existing successful query and never calls Start if its receipt is
missing. The prepared template adds recovery-only mode and an explicit Start
denial; it retains the same seven resources and all runtime/scan limits.

Newly executed checks:

- **28 focused tests passed**, including omitted final newline/boundary whitespace,
  material SQL/comment/literal/source-selection changes, database/workgroup
  mismatch, preserved identity/query reuse without Start, missing/unsuccessful
  query refusal, mandatory parity, interrupted publication, completed replay,
  stale compatibility data and recovery-only IAM/configuration.
- **216 full offline tests passed, zero failures**, with outbound sockets blocked.
- `cfn-lint` and local template/package validation passed. No AWS service
  validation was invoked in this local-only round.
- Corrected ZIP CRC, source equality and isolated import/identity checks passed.
  Compared with the deployed ZIP, only `cloud_preparation.py` and
  `preparation_contract.py` changed; `preparation_identity_v1.json` was added.
  SQL and all 2,286 dependency files remain byte-identical. No data, private
  configuration or model/training packages were included.
- The isolated import ran on macOS; corrected-package Linux/AWS execution remains
  pending. The prior AWS normalization/SQL observations below remain valid.

The new ignored recovery proposal/baselines bind the corrected package and
template. They propose an existing-stack update, concurrency restoration to one,
and **at most four additional preparation invocations** within the eleven
remaining. They permit **zero CFBD requests and zero new Athena executions**.
On failure only preparation is disabled, with evidence preserved. See the
[runbook recovery sequence](cloud-preparation-runbook.md).

Cloud parity, six-file dataset publication, completed replay and the two negative
tests are still unverified. The SQL-derived 2,194/740/59 counts remain diagnostic,
not a completed dataset. Historical availability remains unknown and all
retrospective/unapproved flags are unchanged. No cloud training/inference or
operational forecasting completion is claimed.

## PM-03B cloud outcome: deployed; smoke stopped before parity

**The new preparation function is disabled at reserved concurrency zero.**
The seven-resource stack reached `CREATE_COMPLETE` in us-east-1. Approved
proposal/template/ZIP hashes and 14 packaged source/SQL files matched before
writes; the uploaded artifact and deployed Lambda code matched the reviewed ZIP.
The workgroup enforces a 134,217,728-byte (128 MiB) scan cutoff.

Five approved backfills completed with HTTP 200, one per full season 2021–2025.
CloudWatch corroborated exactly five fetch-starts, one for each stable token;
the verified ingestion code limits each to one HTTP attempt. The existing 2026
Week 12 capture was reused. Six explicit cloud-capture receipts and raw/manifest
hashes were verified; unknown availability stayed unknown. No secret value was
retrieved by the local controller.

Normalization executed in AWS Linux and published verified normalized records,
exclusions, quality reports, provenance and the selected queryable input:

| Season | Raw | Retained | Excluded | Quarantined |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 849 | 732 | 117 | 0 |
| 2022 | 854 | 734 | 120 | 0 |
| 2023 | 868 | 750 | 118 | 0 |
| 2024 | 874 | 753 | 120 | 1 |
| 2025 | 888 | 762 | 126 | 0 |
| 2026 Week 12 | 70 | 66 | 4 | 0 |
| Total | 4,403 | 3,797 | 605 | 1 |

**One preparation invocation started one unique Athena execution.** Athena
succeeded and scanned **15,540,870 bytes**. The adapter nevertheless rejected
query identity at `athena_query`: AWS omitted the final newline from the query
returned by `GetQueryExecution` (2,757 characters versus 2,758 submitted).
Database/workgroup matched, and the SQL matched after boundary-whitespace
trimming. No application fix, replacement query or further invocation followed.

Read-only inspection of that existing successful query found:

| Split | Targets | SQL-eligible | Excluded |
| --- | ---: | ---: | ---: |
| Train | 2,237 | 2,194 | 43 |
| Holdout | 762 | 740 | 22 |
| Prediction | 66 | **59** | 7 |

These are diagnostic SQL counts, not a completed baseline dataset. The cloud
Python/SQL parity gate was **not reached**. No six-file dataset or completion
receipt was published. Replay and missing-season/post-cutoff tests were not run.
Therefore the complete PM-03B acceptance criteria are **not met**.

Failure shutdown was verified. All seven resources remain; only the new
preparation function was disabled. Fifty-two source/preparation objects retained
identical hashes and metadata during read-only follow-up; Athena results and
logs remain preserved. No data or resources were deleted. Existing ingestion
configuration and bucket privacy/encryption were unchanged. Retrospective mode
and all three false approval/availability flags remain unchanged.

Private receipts, SQL results, logs, query statistics, source identities and
object metadata remain in ignored evidence. A controller-only paginator issue
was corrected before writes/workloads and consumed no execution allowance.
The implementation/template/ZIP were not changed. A reviewed correction and
separate recovery authorization are required; all six captures can be reused
without another CFBD request. Implementation changes affect selection identity
and must not silently start a second query under this authorization.

No cloud model training, inference or operational forecasting was performed.
The local tests below are historical PM-03 evidence, not successful cloud parity
evidence. They were not rerun during this documentation-only follow-up.

## PM-03 local readiness (before deployment)

**This section records checks made before PM-03B; preparation/Athena were not
yet deployed/executed at that stage.** PM-02 ingestion was already verified.

- Starting commit: `83c15cdd57ecd6971727aaa4e52e4d9507f30d2f`.
- Full suite: **208 passed, 0 failed**, including 20 new preparation/package
  tests; outbound socket connections blocked for the complete test process.
- Exact feature SQL executed on synthetic SQLite tables: target splits,
  eligibility, prior counts, labels and predictors matched the existing Python
  builder. Published compatible dataset bytes matched that builder. This is
  semantic parity evidence, not proof of Athena syntax/runtime or IAM success.
- Failure tests: required seasons, explicit source versions, cloud receipt and
  checkpoint lineage, corrupt/missing inputs, weekly history refusal, duplicate
  prevention, missing history, quarantine, zero scores, neutral sites, precise
  cutoff ordering, unknown/post-cutoff refusal, changed SQL results, query
  pagination, pending/completed replay, conflicting/missing output, interrupted
  publication and ambiguous query-start recovery.
- `cfn-lint` passed. CloudFormation `ValidateTemplate` accepted the seven-resource
  template and reported `CAPABILITY_NAMED_IAM`. IAM Access Analyzer found no
  errors and one warning for the intentionally literal `*` conditional-write
  header comparison. These are structural/policy checks, not deployed proof.
- A Python 3.14 Linux x86_64-target ZIP was built from pinned dependencies.
  ZIP CRC, source-byte equality, allowlist and native wheel architecture checks
  passed; raw data, private configuration and training packages were absent.
  An isolated macOS handler import/refusal check also passed. **Linux execution
  remains unverified**: the installed Docker client's service was unavailable,
  and no alternative local container/emulation runtime was present.
- Read-only S3 inspection found full-season legacy uploads for 2021–2025
  (849/854/868/874/888 raw records) and exactly one completed cloud capture,
  2026 Week 12 (70 records). Legacy manifest hashes matched the selected
  reference report. No new capture, query, upload or resource change occurred.
- Existing bucket privacy/encryption checks passed; preparation name probes and
  private account/bucket/artifact references are retained only in ignored local
  readiness evidence. Five full-season cloud backfills remain required.
- The proposed Lambda/database/workgroup names were unused; the five stable
  backfill tokens had no existing ledger objects at inspection time.

The ignored readiness directory records final artifact/template/proposal hashes
for a later approval. See the [runbook](cloud-preparation-runbook.md) for exact
resources, bounded smoke/backfill scope and failure/cleanup procedures. Historical
availability remains unknown and all retrospective/unapproved flags are intact.
No cloud training, inference, operational forecast approval or full serverless
completion is claimed.
