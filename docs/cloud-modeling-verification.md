# PM-04 cloud modeling verification — November 20, 2026

Cloud modeling was **deployed and verified in AWS Linux** under the approved
PM-04B scope, resumed through the PM-04C controller correction.
The previously verified ingestion and recovery-only preparation deployments are
unchanged. This work makes no claim that the whole serverless system is complete.

## Local readiness checks (before deployment)

- Focused modeling/package tests: **17 passed**.
- Full offline suite: **233 passed**; requests and AWS transports were blocked,
  with an additional socket-level network guard during the full run.
- Model fits and inference in tests used synthetic fixtures only. No production
  dataset was trained or scored on the controlling computer.
- Tests compare the adapters with the existing baseline, including evaluation,
  calibration, saved-model predictions, train-only fitting and changed holdout
  labels. They cover immutable replay, interrupted publication, ambiguous claims,
  conflicting artifacts, invalid inputs and integrity/origin checks before loading.
- CloudFormation lint and read-only template validation passed for eight proposed
  resources. IAM policy validation returned zero errors and one warning per role
  for the deliberate literal `If-None-Match: *` equality condition.
- The reviewed ZIP contains 20 pinned distributions and 18 allowlisted project
  source files. Archive CRC, source-byte equality and dependency pins passed.
  Compressed size: **79,009,499 bytes**; uncompressed: **224,068,011 bytes**, below
  Lambda's 262,144,000-byte limit. The ZIP requires an S3-backed deployment.
- Static native checks found 250 ELF64 Linux x86_64 files; the highest referenced
  GLIBC symbol version was 2.27. Runtime modules, licenses and distribution
  metadata remain included; bundled dependency tests and bytecode are excluded.

Read-only metadata and validation did not upload artifacts, deploy resources,
invoke workloads, fetch CFBD data or run Athena queries. Detailed metadata,
packages and the concrete deployment proposal remain in ignored local evidence.

## Controller correction and local regression checks (PM-04C)

The original PM-04B attempt stopped during read-only preflight on
`NoSuchBucketPolicy`; no artifact upload, deployment or invocation occurred.
That failure evidence was preserved. The corrected deployment-only helper records
exact policy absence without inventing a nonpublic PolicyStatus. It requires
all four bucket-level Block Public Access flags, owner-scoped reads and valid
encryption. Existing public policies, AccessDenied, unexpected errors and
malformed/missing required settings fail closed. It changes no bucket settings.
Six focused regression tests and the full **239-test offline suite passed**.
The helper is not part of the reviewed Lambda ZIP. Proposal, template, ZIP,
dependency pins and implementation hashes remained unchanged; all 18 packaged
project sources matched implementation commit `44e94af`.

## Newly observed AWS execution (PM-04C)

One reviewed artifact upload and all eight CloudFormation resources completed in
us-east-1. Both private Lambda functions ran the same reviewed package with
matching `python:3.14.mainline.v118` runtime versions. Actual execution was Linux
x86_64, Python 3.14.10, NumPy 2.5.2, pandas 3.0.5, SciPy 1.18.1,
scikit-learn 1.9.0 and joblib 1.6.0. Deployed inline IAM policies matched the
approved template; no public endpoint or schedule was added.

The bounded smoke used **two training and four inference invocations**, with
exactly **one model-fit start** corroborated by CloudWatch and six invocation
REPORT records. There were **zero CFBD requests and zero Athena queries**.
The verified dataset was trained and evaluated inside AWS, not locally.

| Split | Seasons | Verified rows |
| --- | --- | ---: |
| Training | 2022–2024 | 2,194 |
| Holdout | 2025 | 740 |
| Saved prediction sample | 2026 Week 12 | 59 |

The scaler reports 2,194 fitted rows. The original predictors/settings remain
unchanged; holdout data was used only for evaluation, with no tuning/refit.

| Newly measured holdout metric | Model | Training-derived constant baseline |
| --- | ---: | ---: |
| Brier score | 0.21061287148858282 | 0.24163577488303326 |
| Log loss | 0.6096025525960278 | 0.6763272181260667 |
| Accuracy | 0.6648648648648648 | 0.5918918918918918 |

The training home-win rate was 0.5829535095715588. Both calibration tables contain
ten fixed bins; no calibration model was fitted. The model's first bin contains
two games with mean prediction 0.08012209570211601 and observed home-win rate 0.
These are new measurements, although the holdout metrics equal the historical
baseline results; they were not substituted from an earlier report.

| Feature | Coefficient per training standard deviation |
| --- | ---: |
| prior_win_pct_diff | -0.036235058561147705 |
| prior_avg_margin_diff | 0.7902092104150165 |
| home_field | 0.06597967856001555 |

Interpretation artifacts also record training means/scales, original-unit
log-odds changes and intercepts. Coefficients are conditional associations with
correlated predictors, not causal effects or standalone importance rankings.

All nine model artifacts and the training completion receipt passed hash and
provenance checks. Identical training replay returned the same result without
another fit and preserved all 12 model/ledger objects' bytes and metadata.
Independent inference verified the protected trainer origin and artifact hashes
before reloading the model, then produced **59** saved predictions identical to
the trainer's sample CSV. The three inference artifact hashes and completion
receipt were verified. All probabilities were finite, within [0,1], and
complementary. The hypothetical vector `(0.2, 7, 1)` returned:

- P(home wins): **0.662422294285731**
- P(away wins): **0.33757770571426904**

The invalid home_field=2 event was rejected at request/configuration validation.
The invalid training-receipt hash was rejected at trusted-model reload with
"nothing deserialized," before the deserialization branch. These expected
rejections were successful negative checks, not deployment failures.

| Invocation | Duration (ms) | Cold init (ms) | Max memory reported (MiB) |
| --- | ---: | ---: | ---: |
| Training | 2135.64 | 6888.02 | 314 |
| Training replay | 934.12 | warm | 317 |
| Saved-sample inference | 1955.57 | 6916.07 | 312 |
| Hypothetical inference | 416.87 | warm | 312 |
| Invalid vector | 1.64 | warm | 312 |
| Invalid receipt hash | 82.16 | warm | 312 |

Configured memory is 1,536 MiB for training and 1,024 MiB for inference. Memory
values are Lambda REPORT high-water marks for the execution environment, not
independent per-request allocation measurements. First-call billed duration was
9024 ms for training and 8872 ms for saved-sample inference.

## Preserved boundaries and remaining limitations

Before/after checks preserved metadata for 95 source objects and hashes/metadata
for all six original dataset files plus preparation completion. Bucket ownership
checks, encryption, absent policy and all four access blocks were unchanged, as
were ingestion and recovery-only preparation configuration. No bucket policy or
ACL changed, and no permissions beyond the reviewed role policies were added.
Both new functions remain Active with reserved
concurrency one and automatic retries disabled; no resource is left disabled.
CloudWatch credential-pattern scans found no hits; no secret was retrieved by
the controller. Detailed evidence, configuration, packages and models stay ignored.

The Free plan was confirmed active with eligible credits. No paid-plan upgrade,
purchase, subscription or Organizations enrollment occurred. Stored artifacts and
retained logs still consume covered allowances/credits; this is not a claim of
unlimited zero-cost operation. Historical availability remains unknown, and
retrospective mode and all false availability/approval flags remain unchanged.
The 59 predictions describe a saved Week 12 snapshot, not an operational forecast;
the hypothetical output remains hypothetical. This verifies the bounded private
training/evaluation/inference slice, not scheduling, monitoring, a public service
or a complete operational forecasting system. Further workloads require their own
authorization. See the [runbook](cloud-modeling-runbook.md).
