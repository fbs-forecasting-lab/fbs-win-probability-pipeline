# PM-05 local verification — November 20, 2026

**Not deployed; no new end-to-end cloud success is claimed.** PM-04C remains the
separately verified modeling baseline, with ingestion and recovery-only Athena
preparation unchanged. PM-05 ran no cloud workload, CFBD request, Athena query,
schedule activation or production model fit. New weekly tests use synthetic
snapshots and a mocked saved-model boundary, without fitting a new model.

Sixteen focused tests and the complete **255-test offline suite passed**, with
network transports blocked and a socket guard during the full suite. The tests
exercise existing normalization/features, a distinct week with unchanged model
and training/holdout bytes, complementary predictions, zero-row behavior,
observation/kickoff equality and offsets, stale data, TBD/completed/started games,
missing history, conflicts, pending progress, ambiguous ingestion responses,
partial publication/recovery, altered artifacts and prior schedule revisions.
Template tests enforce the eight-advance budget, no Task retries, disabled fixed
schedule, scoped IAM and package source allowlist. Mocks do not prove AWS execution.

CloudFormation lint and read-only ValidateTemplate passed. Step Functions
ValidateStateMachineDefinition returned OK with no diagnostics. Read-only Step
Functions and Scheduler metadata APIs were accessible and proposed names unused.
IAM policy validation found zero errors; the worker's single literal-asterisk
warning is intentional for `If-None-Match: *`. Workflow/schedule policies had no
findings. No cloud resources were created or changed by these validation calls.

The package uses the previously pinned 20 Linux dependencies plus 24 project
source files. The final ZIP is 79,026,549 bytes compressed and 224,119,679 bytes
uncompressed, below the 262,144,000-byte Lambda limit. Archive CRC, source equality,
exact dependency closure and 250 ELF64 Linux x86_64 files passed; maximum referenced
GLIBC symbol version was 2.27. Final hashes are recorded in the ignored proposal.
New worker imports, runtime-version equality with the
protected model, effective deployed IAM, performance, source selection and full
asynchronous execution remain pending the approved smoke. Local Docker was
unavailable during the preceding packaging assessment; previous Lambda execution
of shared libraries is not execution evidence for this new worker.

The proposed minimum distinct-week verification is one fresh capture and zero
queries/fits. Publication remains withheld regardless of technical row counts:
unknown historical availability, model approval and schedule revisions are not
resolved by adding orchestration. No automatic retraining, alert infrastructure,
public endpoint or active schedule was added. See the
[runbook](weekly-cloud-runbook.md) and [contract](weekly-cloud-contract.md).
