# Cloud ingestion verification — November 20, 2026

**The ingestion slice was deployed and verified in AWS. The complete serverless
ML pipeline is not finished.** This summary records PM-02C observations without
requiring private local files, credentials, raw responses or deployment ZIPs.

## Cloud execution evidence

The reviewed application ran in AWS Lambda's Python 3.14 x86_64 Linux runtime in
us-east-1. The API capture and raw/manifest publication executed inside AWS;
the controlling machine supplied requests and inspected evidence only.

| Synchronous invocation | Observed result |
| --- | --- |
| Fresh capture: 2026 regular-season Week 12 | Completed; CFBD HTTP 200; **70 records** |
| Identical request and token | Original completed receipt and payload digest returned unchanged |
| Same token, conflicting Week 13 request | Rejected at the claim stage; no new capture |

CloudWatch corroborated **one fetch-start across exactly three invocations**.
The deployed fetch path permitted one HTTP attempt and received HTTP 200.
No fresh-token retry was performed. Replay and conflict handling did not refetch.

Raw response, manifest and durable checkpoint bytes/hashes agreed. Record count,
coverage, request parameters and timestamps were checked. All five capture/run
objects retained identical hashes, ETags, lengths and modification times after
replay and conflict rejection. Bucket encryption remained AES256, and all four
Block Public Access settings remained enabled.

- Run start: `2026-11-20T06:56:17.230238Z`
- API observation: `2026-11-20T06:56:17.567041Z`
- Completion: `2026-11-20T06:56:17.867207Z`
- Raw fingerprint: `5ccd0696`; manifest: `bb56fd45`; checkpoint: `d6c19066`

No secret value was printed, saved locally, or included in receipts/documentation.
Observed logs contained only Lambda lifecycle records and a sanitized fetch-start
record. Private operational references and detailed execution evidence remain
outside Git. No raw CFBD records are redistributed by this summary.

## Implementation identity and validation

Deployed ZIP SHA-256:
`30d6373d4e619b150ee86d3efe415aae5c5d5cd64c7c96f7025c02dfa63cfa74`

Deployed template SHA-256:
`217b6bf6c84419ec81e9bc352ede74e30b8431252372b36640e4c8d7bace3258`

The ten packaged project source files match this implementation byte-for-byte.
Documentation and tests are outside the deployment ZIP. Proposal/template hash
baselines were explicitly established during PM-02C authorization, not verified
against an earlier recorded hash baseline.

Separate local verification passed **188 offline tests**. Template linting,
CloudFormation template validation and scoped IAM policy simulation passed in
PM-02B. These local/service checks are distinct from the successful PM-02C
Linux execution. The deployed role policy matched the approved template; no
broader managed policies were attached. No failure shutdown was required.

## Limits and remaining work

Historical availability remains unknown. The capture retains
`dataset_mode=retrospective_demo`, `historical_availability_verified=false`,
`approved_for_point_in_time_forecasting=false`, and
`approved_for_predictor_use=false`. Observation time does not certify historical
publication time or operational forecast eligibility.

Athena transformation, cloud model training/inference, automatic scheduling,
drift/performance monitoring and alerts remain unfinished. This result verifies
only ingestion, durable run identity, integrity and replay/conflict behavior.
See the [architecture](architecture.md) and
[deployment/recovery runbook](cloud-ingestion-runbook.md). Repeating live capture
or changing infrastructure requires explicit authorization.
