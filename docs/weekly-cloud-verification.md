# PM-05 weekly cloud verification — November 20, 2026

**Deployed and verified in AWS; operational publication remains withheld.**
The approved PM-05C recovery completed all six smoke events after the original
PM-05B failure. The weekly schedule stays DISABLED. Ingestion, recovery-only
Athena preparation and the protected PM-04C model deployments remain unchanged.

## Local evidence and preserved history

Original PM-05 readiness passed 16 focused tests and 255 offline tests, template
lint/validation, Step Functions definition validation and IAM policy validation.
Those were local/read-only checks, not deployed success. Synthetic fixtures used
real normalization/features and a mocked saved-model boundary without fitting.

PM-05B uploaded the reviewed ZIP once and created eight resources. Its first
execution used two worker calls: ingestion-reference publication succeeded, then
preparation failed because download_raw's exact-key manifest list probe was
outside the original worker list allowance. The worker was disabled. That failed
execution and its four run objects were preserved; no ingestion invocation,
fetch, query or fit occurred in the failed attempt.

PM-05C added only raw listing prefixes for seasons 2021–2026, keeping the same
bucket and max-keys <= 1. No object permission or write domain changed. The full
S3 call trace found no other mismatch. **19 focused tests and all 258 offline
tests passed**, plus template lint/validation and **94 exact-context IAM
simulations** covering allowed probes, denied unrelated/oversized listings and
unauthorized writes. The earlier baselines and failure evidence remain preserved.

The original resource-count guard stopped before executing the change set.
After review, its semantic replacement accepted exactly WeeklyRole.Policies as
the direct change and Weekly.Role, WorkflowRole.Policies, and
Workflow.Definition/RoleArn as dependent ARN reevaluations. All entries were
Modify/Replacement=False. Seven local guard cases rejected additions, removals,
replacements, other direct changes and expanded listing limits.

The saved change set was executed once. The deployed policy matched the scoped
correction; all six raw probes simulated allowed under the actual role. Every
physical resource identity was unchanged. Application ZIP, source bytes, runtime,
environment, requests, run tokens, model references, cutoff and schedule were
unchanged. Worker concurrency was restored to one only after these checks.
Recovery used a distinct execution name with the original token and resumed
preparation without repeating ingestion or changing the four prior run objects.

## Actual cloud smoke outcomes

| Event | Outcome | Additional worker calls | Technical rows / predictions |
| --- | --- | ---: | ---: |
| Resume Week 12 | SUCCEEDED; withheld, workflow_completed=true | 3 | 59 / 59 |
| Completed replay | SUCCEEDED; same result, unchanged bytes/metadata | 1 | 59 / 59 |
| Conflicting week under original token | Expected FAILED at run_claim | 1 | not scored |
| Missing history | Expected FAILED at request/configuration | 1 | not scored |
| Observation at cutoff | SUCCEEDED; withheld, workflow_completed=true | 4 | 0 / 0 |
| Fresh Week 13 | SUCCEEDED; withheld, workflow_completed=true | 4 | 53 / 53 |

Recovery totals: **six additional executions and 14 worker invocations**.
Including the original failed attempt: **seven executions and 16 worker
invocations**, within the seven/20 cumulative limits. CloudWatch corroborated
exactly **one ingestion invocation, one CFBD fetch-start and zero model-fit
starts**. The existing Athena query-ID list was unchanged: **zero new queries**.
No automatic failure retry, recapture, replacement run token or cutoff change
occurred. All model reuse and processing took place in AWS, not locally.

| Scoring input | Raw | Retained | Normalization excluded | Quarantined | Feature/cutoff rejected | Eligible/predicted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Week 12 | 70 | 66 | 4 | 0 | 7 | 59 |
| Cutoff equality | 70 | 66 | 4 | 0 | 66 | 0 |
| Fresh Week 13 | 65 | 55 | 0 | 10 | 2 | 53 |

Week 12 normalization excluded four non-FBS-vs-FBS records. Feature selection
rejected six completed targets and one missing home-team history. At cutoff
equality, all 59 remaining candidates had schedule observation at cutoff and
all five historical observations after cutoff. Each of these six observation
reasons had count 59; the reason counts overlap. The other seven rejections
were the same six completed targets and one missing history. Zero eligible rows
remained exactly zero predictions.

Fresh Week 13 quarantined **10 unresolved kickoff times** and excluded two
retained targets for missing away-team history. No rows were substituted. The
UTC precheck was **2026-11-20T22:15:17.181688Z**; source retrieval was
**2026-11-20T22:15:28.666663Z**, before the fixed **2026-11-20T23:59:00Z** cutoff.
The same protected model scored this distinct source/feature identity without
retraining. This is a retrospective demonstration, not an approved live forecast.

Each processing completion verified **69 linked hashes** binding raw sources,
captures, normalized data, selected features, cutoff, protected model and training
claim/completion, stage receipts and predictions. Scoring provenance is separate
from model training provenance. All probabilities were finite, in [0,1] and
complementary. Original train/holdout/aggregate bytes matched model metadata.
All 22 protected model/dataset objects retained their verified bytes/metadata;
95 original source objects retained their checked metadata. Completed replay
preserved the run's bytes/metadata without ingestion or scoring work. Bucket
settings and all four predecessor deployments remained unchanged.

## Runtime and remaining boundaries

Actual execution was AWS Linux x86_64 with Python 3.14.10 and matching runtime
version python:3.14.mainline.v118. Trusted loading verified the original model's
NumPy 2.5.2, pandas 3.0.5, SciPy 1.18.1, scikit-learn 1.9.0 and joblib 1.6.0
versions before deserialization. Worker REPORT durations ranged from 1.74 to
6811.30 ms, with maximum reported memory 326 MiB out of 1536 MiB configured.
Cold initialization was 6876.88 ms for recovery and 7202.92 ms for the fresh run.
Memory values are execution-environment high-water marks, not independent
per-request allocation measurements; this is not a capacity benchmark.
The single ingestion invocation reported 1432.74 ms execution, 978.44 ms cold
initialization, and 98 MiB maximum memory out of 512 MiB configured.

The reviewed package is unchanged: 20 pinned dependencies, 24 project sources,
79,026,549 compressed bytes and 224,119,679 uncompressed bytes. Prior static checks
passed archive/source equality, 250 ELF64 Linux x86_64 files and maximum referenced
GLIBC symbol version 2.27. The cloud results above provide the subsequent runtime
proof; earlier static checks or the previous model deployment alone did not.

The worker remains Active with reserved concurrency one and the schedule
DISABLED. All four mode/availability/approval status fields remain
retrospective/false. Operational publication is withheld because historical
publication/schedule revision evidence is unverified and the saved model remains
retrospective/unapproved. The Free plan was active with eligible credits; no
upgrade, purchase, subscription, Organizations enrollment or personal-payment
action occurred. Storage/logs still consume covered allowances or credits.
Detailed evidence, data, packages, models and private proposals remain ignored;
credential-pattern scans found no hits. No public endpoint, alert infrastructure,
automatic retraining or active recurrence was added. Operational approval,
scheduling activation, monitoring and later weeks require separate review. See
the [runbook](weekly-cloud-runbook.md) and [contract](weekly-cloud-contract.md).
