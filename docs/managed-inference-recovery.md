# Managed inference recovery — PM-13C local preparation

November 22, 2026. **Training is complete; independent cloud inference remains unverified.**
No cloud writes, fits, workload calls or receipt publication occurred in this round.
Original training evidence and the consumed submission journal remain unchanged.

The native parser formerly rejected SageMaker's per-file PAX timestamp records.
One shared reader now serves native verification and controller inspection. It
accepts only numeric atime, ctime, mtime and LIBARCHIVE.creationtime records;
checks raw lengths/duplicates, checksums, padding, terminators and bounded sizes;
and rejects path/link/size overrides, global/chained extensions, special files,
traversal, duplicates, truncation and trailing content. Seven exact regular
payloads and all companion/provenance/receipt hashes remain mandatory before loading.

- Original producer image: `sha256:52832ca633d3cc49864feb5946b34aa9526d327991a874633ecbc0d9d6b3be00`.
- Corrected consumer image: `sha256:fefa1ed289ce69f05e699178a0ec075bd4ef7626a2a28ed57d3f7e273ba37d94`.
- Unpublished candidate native receipt SHA-256: `fb53bd2e1d6ce2092b17bf06277d23b4010a7d222bb936d4b35ae979ff46225f`.
- Original model archive SHA-256: `05b53455f720e967c6f0cfcfd2a89a828aa6396931242dcf77c4ebd9d36d5254`.

The images are **different**. All original layers, dependencies and Python
3.14.10 are preserved; 4,746 application files are unchanged. Only the native
verifier and inference identity documentation changed, plus the new shared reader.
The receipt continues to name the original producer image. The corrected image
was exported locally and its OCI manifest digest independently verified.

**Verification:** 388 network-blocked regression tests passed; 43 focused host
checks and 23 Linux checks passed. Linux synthetic models reload and reproduce
saved predictions. Genuine archive inspection constructs/verifies the candidate
receipt without real-model deserialization, local training or scoring.
Both S3 archives were read back byte-identically; the original job response and
six input metadata pins match. Twenty-one inference IAM contexts passed; no
permissions changed. The real service bridge remains absent and 0/3 calls used.

The exact us-east-1 job log group exists, but its job-prefix stream count remains
zero. Role simulation allows CreateLogStream/PutLogEvents and implicitly denies
DescribeLogStreams/CreateLogGroup. AWS's [execution-role examples](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html)
include those latter actions; this is a hypothesis, **not confirmed causation**.
One saved fit-attempt/completion and Training phase are observed; independent
service fit-count corroboration remains unavailable. Do not repair IAM or refit.

## Proposed recovery, awaiting approval

Private exact requests, events, compatibility records and approval hashes are in
`data/processed/pm13c-readiness-20261122T074816Z/`. Original approval files are unchanged.

1. Revalidate all new hashes and original producer/job/archive/input pins. Require
   FREE/ACTIVE and sufficient eligible Lambda/ECR/S3/log credits; preserve private
   bucket settings, predecessor objects/configuration and disabled schedules.
2. Upload only the reviewed consumer to existing private `fbs-final-training`
   using tag `pm13c-inference`; verify its immutable digest. Preserve producer image.
3. Publish only the exact candidate to the original job's `verified/receipt.json`
   with `IfNoneMatch=*` and a SHA-256 checksum; verify downloaded bytes. Never overwrite.
4. Create `fbs-final-managed-inference` with the existing same-named scoped role,
   x86_64, 2,048 MiB, 60 seconds, concurrency one, `/lambda-entrypoint.sh`, and
   `src.pipeline.managed_inference.handler`. Pin consumer image and receipt in
   the prepared configuration. No IAM/ECR policy changes, triggers or public URL.
5. At most three synchronous calls: saved-sample byte equality, hypothetical
   finite complementary probabilities, and wrong-receipt rejection before loading.
   Consume each durable attempt marker before invocation; SDK total attempts one.
   No retry after ambiguity or unexpected failure. Stop and disable only this
   bridge on failure; preserve evidence. Zero training/fits/provider/Athena work.
6. Verify receipt/archive hashes, original model/input bytes, predecessor settings,
   schedules and runtime. Report training acceptance separately from inference.

Read-only account evidence remained FREE/ACTIVE with **$119.963146** estimated
eligible credits. The three 2 GiB/60-second calls imply about $0.006 compute before
credits, excluding initialization. A conservative **$1** 30-day planning allowance
covers initialization, image retention, receipt requests/storage and small logs;
this is not a billing cap or settled charge. Recheck coverage before execution.
See [Lambda rates](https://aws.amazon.com/lambda/pricing/),
[ECR storage](https://aws.amazon.com/ecr/pricing/), [S3](https://aws.amazon.com/s3/pricing/)
and [logs](https://aws.amazon.com/cloudwatch/pricing/). No paid plan or subscription.
Retrospective/unapproved flags and unknown historical availability remain unchanged.
