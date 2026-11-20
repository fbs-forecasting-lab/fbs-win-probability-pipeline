# PM-04 local readiness verification — November 20, 2026

Cloud modeling is implemented but **not deployed or cloud-runtime verified**.
The previously verified ingestion and recovery-only preparation deployments are
unchanged. This work makes no claim that the whole serverless system is complete.

## Newly executed local checks

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

## Pending cloud evidence

Docker's service was unavailable, so static checks do **not** establish Linux
imports, dynamic linking, memory use, cold-start duration or model execution.
Those checks, actual evaluation metrics and hypothetical probabilities remain
pending the separately approved AWS smoke test. No earlier model score is used
as a promised result for this dataset/runtime.

The proposed smoke budget is two training and four inference invocations, at
most one fit, zero CFBD requests and zero Athena queries. It must establish
trusted model reload, completed replay without retraining, saved prediction
equality, invalid-input rejection and unchanged source objects/bucket privacy.
Any failure stops the sequence and disables only the new modeling functions.

The source dataset's 2,194/740/59 counts are **prior PM-03D preparation evidence**,
not newly observed PM-04 training results. Historical availability remains unknown;
retrospective mode and all false approval/availability flags remain unchanged.
See the [runbook](cloud-modeling-runbook.md) for scope, IAM, failure handling and
the concrete deployment procedure.
