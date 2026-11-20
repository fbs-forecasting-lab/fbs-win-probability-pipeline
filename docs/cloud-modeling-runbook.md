# Cloud baseline training and inference (PM-04)

**Deployed and verified in AWS Linux on November 20, 2026 (PM-04C).**
The verified ingestion and recovery-only preparation deployments are unchanged.
No real project dataset was trained or scored on the controlling computer.
Local model tests use fictional synthetic fixtures only.
The [verification summary](cloud-modeling-verification.md) separates local checks
from the completed bounded cloud smoke test and remaining operational limitations.

## Architecture and trust boundary

Two private, independently invocable Python 3.14 x86_64 Lambda functions share
one pinned ZIP: `fbs-model-training` and `fbs-model-inference`. There are no public
URLs, endpoints, schedules, persistent servers, new model families or new features.
The controller submits explicit references and inspects results; production
fitting, evaluation, model reload and scoring execute inside AWS.

`cloud_modeling.training_handler` validates a version-one request with
`training_token`, `dataset_id`, `preparation_selection_id`,
`preparation_receipt_sha256`, and `allow_retrospective_demo=true`. The deployment
pins the three preparation references in environment/IAM. It verifies the exact
completed preparation receipt and all six dataset hashes, then reuses
`S3Store.download_dataset` and `baseline.train_baseline`. The existing scaler and
logistic regression fit only on 2022–2024. The 2025 holdout is evaluated without
tuning/refitting, against the training-derived constant home-win rate. Existing
metrics, ten calibration bins, predictor order and model settings are unchanged.

A stable token claim binds request, code identity and actual library/Python
versions before fitting. Only the atomic claim owner may fit. After fitting,
the adapter reloads the trusted just-created model and writes a single immutable
checkpoint containing the exact model bundle. If interrupted after checkpointing,
same-token recovery republishes those bytes without refitting. If a claim exists
without a durable checkpoint, the run stops as ambiguous; it must not fit again
or choose a fresh token automatically. Completed replay verifies the dataset,
claim and every published artifact and returns the original receipt without
training or S3 mutation. Runtime/version changes fail closed instead of causing
an implicit retrain. No token means "latest."

Model identity hashes the canonical training request and implemented code bytes.
The claim also binds runtime/library versions. The nine-file bundle is published
conditionally under `initial-demo/cloud-modeling/models/<model_id>/`:

- `model.joblib`, `model_metadata.json`
- `evaluation.json`, `calibration.json`
- `holdout_predictions.csv`, `sample_predictions.csv`, `exclusions.json`
- `interpretation.json`, `training_provenance.json`

The existing seven model artifacts remain compatible with local loaders.
Interpretation records coefficients per training standard deviation, means,
scales, original-unit log-odds changes and intercepts. These are conditional
associations, not causal effects or causal feature-importance rankings. Win
percentage is a fraction, margin is points/game, and home_field is binary.
Provenance records actual platform/runtime/library versions, request, code,
dataset identity, settings via metadata, and all artifact hashes. The final
training completion receipt is under
`cloud-modeling/training/<training_token_sha256>/complete.json` and binds all
nine files. Partial matching writes can resume; conflicting or missing completed
artifacts cannot be repaired silently. All application writes use conditional
creation, readback verification and final completion markers.

`cloud_modeling.inference_handler` accepts only a model ID, training-token hash,
exact training-receipt hash, demo permission and mode. It verifies the completion
receipt, original claim, implementation identity, fixed dataset reference,
runtime/library versions and every model artifact **before deserialization**.
The model write domain belongs to the trainer; the inference role cannot write
models or training receipts. Hashes do not make arbitrary pickle/joblib files
safe. Trust depends on this protected producer domain and approved deployment;
an account administrator able to replace both code and evidence remains trusted.
No arbitrary URL, serialized payload, path or newest-model lookup is accepted.

- `saved_sample` reuses `predict.predict_saved_sample`, reloads the model and
  re-verifies its exact S3 dataset. Its predictions must match the training
  sample CSV byte-for-byte. Three prediction artifacts and a completion receipt
  are conditionally published under `cloud-modeling/inference/<inference_id>/`.
- `hypothetical` validates exactly the three finite numeric predictors, rejects
  booleans/strings and invalid domains, then reuses `predict.predict_vector`.
  It returns finite complementary P(home wins)/P(away wins), explicit model and
  dataset identity, hypothetical context and status. It is not a real matchup.

Every result retains retrospective mode and false historical-availability,
point-in-time-forecasting and predictor-use approval flags. Cloud execution does
not establish historical publication times. The saved 2026 Week 12 sample is a
snapshot, not an operational forecast. Empty eligible samples remain empty.

## Runtime/package assessment

The full pinned Linux dependency installation measured 267,091,940 bytes, above
the 262,144,000-byte ZIP/layer uncompressed limit. Excluding only bundled
`test`/`tests` directories, bytecode/cache directories and generated command
entry points yields a **224,068,011-byte** package including project code.
The compressed ZIP is **79,009,499 bytes**: upload via S3, not Lambda's direct
50 MiB upload API. It fits without containers, ECR, persistent compute or an
account upgrade. All actual runtime modules, native libraries, licenses and
distribution metadata are retained. No arbitrary runtime-library trimming or
model implementation changes are used.

Twenty dependencies are pinned separately in `infra/cloud-modeling-requirements.txt`;
the project's normal requirements are unchanged. Static checks verified 250
ELF64 Linux x86_64 native files and a maximum referenced GLIBC symbol version
2.27, compatible with the intended AL2023 ABI baseline. Static checks are not
dynamic-link/import proof. Docker's service was unavailable locally. The subsequent
approved AWS smoke test verified imports and execution on Linux x86_64 with Python
3.14.10, including actual cold-start, duration and memory measurements below.
No macOS model check is presented as Linux execution.

Training uses 1,536 MiB memory / 180 seconds; inference 1,024 MiB / 90 seconds.
Both use 512 MiB temporary storage, reserved concurrency one, zero async retries,
and single-thread numeric libraries. Runtime updates occur on function update;
verify both functions' runtime-version ARNs match before fitting/inference.
The existing loader requires actual Python/library version equality on reload;
never bypass it. The predeployment region check had 398 unreserved executions
available; the two reserved slots fit that observed quota.

## Approved deployment (executed November 20, 2026)

Region `us-east-1`; stack `fbs-cloud-modeling`. Eight new resources: the two
functions, roles `fbs-model-training-execution`/`fbs-model-inference-execution`,
14-day retained log groups `/aws/lambda/fbs-model-training` and
`/aws/lambda/fbs-model-inference`, and two async retry configurations.

Use existing `<FBS_S3_BUCKET>` and `initial-demo`. The private readiness proposal
records exact references to the verified dataset (2,194/740/59 input rows),
preparation completion and immutable artifact key. Training reads only that
dataset/preparation receipt and its modeling state; inference reads trusted
model/claim/completion objects and the same fixed dataset. Training writes only
model/training prefixes; inference writes only its output prefix. Optional
absence probes use prefix-conditioned ListBucket with MaxKeys=1; a 403 remains
fatal. Both policies forbid nonconditional writes. Neither role gets CFBD
secrets, Lambda invocation, Athena, catalog mutation, deletion or bucket-setting
permissions. The policy validator's literal-asterisk warning is intentional:
`If-None-Match: *` requires that literal value, not a pattern.

Read-only metadata confirmed an active Free plan with eligible credits and unused
function names. Use its existing coverage; do not upgrade, purchase, subscribe,
enroll in Organizations or activate a paid plan. Stop if required service access
needs an upgrade. Storage, requests, Lambda runtime and retained logs consume
allowances/credits; this is not a promise of unlimited free usage. No Cost
Explorer API calls, CFBD requests or Athena queries are required. Ingestion and
recovery-only preparation configuration must remain unchanged.

Build/validate locally (fresh ignored output directory each time):

```bash
.venv/bin/python -B bin/package_cloud_modeling.py --validate-only
.venv/bin/python -B bin/package_cloud_modeling.py \
  --output-dir data/processed/pm04-package-new
```

The measured Linux dependency directory can be reused with `--dependencies-dir`;
the packager verifies the exact pinned closure and native headers. It refuses
existing output directories and packages exceeding the uncompressed limit.

For any separately approved subsequent deployment, recompute proposal/template/ZIP hashes and source
equality. Check proposed names, stable token, bucket privacy, predecessor settings
and quota without changing them. Upload with `s3api put-object --if-none-match '*'`
to the proposal's exact key; stream/hash the whole ZIP on readback (it exceeds
the application's 64 MiB object-transfer bound). Never overwrite an artifact.

```bash
aws cloudformation validate-template --region us-east-1 \
  --template-body file://infra/cloud-modeling.yaml
aws cloudformation create-stack --region us-east-1 --stack-name fbs-cloud-modeling \
  --template-body file://infra/cloud-modeling.yaml \
  --parameters file://"$REVIEW/stack-parameters.json" \
  --capabilities CAPABILITY_NAMED_IAM --on-failure DO_NOTHING
aws cloudformation wait stack-create-complete --region us-east-1 \
  --stack-name fbs-cloud-modeling
```

Record both functions' code hashes, architecture, runtime versions, environment,
concurrency and exact role policies. There are no automatic workload invocations.

### Bounded smoke procedure (all six checks passed November 20)

Maximum **two training invocations and four inference invocations**, with at most
**one fit**, **zero CFBD requests and zero Athena queries**:

1. Train once using the exact prepared `training-request.json` and stable token
   `pm04-model-smoke-20261120-01`. Verify receipt, nine model artifacts,
   evaluation/calibration, interpretation, counts and status. Record actual
   metrics; do not substitute or promise September results.
2. Replay that identical training event. Verify unchanged receipt/object bytes,
   ETags, sizes/times and no second `model_fit_start` in CloudWatch.
3. Invoke inference in saved_sample mode with explicit model/token identities and
   the SHA-256 of the exact completed training receipt read from S3. Verify model
   reload, 59 saved-sample rows, finite complementary probabilities, context and
   byte equality with the trainer's sample predictions.
4. Invoke hypothetical inference with `(0.2, 7, 1)`. Record its actual probability,
   never an expected historical number.
5. Invoke an invalid hypothetical vector (home_field=2); require rejection before
   S3/model load.
6. Invoke a wrong training-receipt hash; require rejection before deserialization.

All calls are synchronous, with SDK automatic retries disabled. Write each event,
response and metadata to a new ignored evidence directory. Inference templates
in the private proposal need their receipt hash filled only from the successful
training receipt; it cannot be known before execution. Nothing selects latest.

```bash
aws lambda invoke --region us-east-1 --function-name fbs-model-training \
  --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
  --payload file://"$REVIEW/training-request.json" "$EVIDENCE/train-01.json"
```

Collect actual runtime/library versions, original dataset/receipt identity,
all artifact hashes, six holdout metrics, both calibration tables, coefficient
interpretation, saved/hypothetical outputs, and one fit-start across training and
replay. Verify originals and bucket privacy/settings remain unchanged. Publish
only a sanitized summary. Real-data training/inference must stay in AWS.

### Observed AWS execution

The reviewed ZIP was uploaded once with conditional creation and verified on
readback. All eight stack resources reached CREATE_COMPLETE. Both functions used
the reviewed code hash and matching `python:3.14.mainline.v118` runtime versions;
their deployed inline policies matched the approved template. No application,
dependency or infrastructure artifact changed during recovery of the controller.

Exactly two training and four inference invocations completed, with one
CloudWatch `model_fit_start`, zero CFBD requests and zero Athena queries.
Training/evaluation used 2,194/740 rows and independent inference scored 59 saved
Week 12 rows. All nine model artifacts, three inference artifacts and completion
receipts passed integrity checks. The training replay preserved all 12 model and
ledger objects' bytes and metadata. Independent saved predictions matched the
training sample byte-for-byte. Both invalid-input checks passed, including
receipt-hash rejection before deserialization.

| Invocation | Duration (ms) | Init (ms) | Max memory reported (MiB) |
| --- | ---: | ---: | ---: |
| Training | 2135.64 | 6888.02 | 314 |
| Training replay | 934.12 | warm | 317 |
| Saved-sample inference | 1955.57 | 6916.07 | 312 |
| Hypothetical inference | 416.87 | warm | 312 |
| Invalid vector | 1.64 | warm | 312 |
| Invalid receipt hash | 82.16 | warm | 312 |

These are Lambda REPORT measurements; memory is the reported execution-environment
high-water mark. Cold-start billed durations were 9024 ms for training and 8872 ms
for inference. These six calls establish this bounded run, not a capacity benchmark.
Both functions remain Active with reserved concurrency one; neither is disabled.
Source objects, original dataset hashes, ingestion/preparation configuration,
bucket encryption and public-access blocks remained unchanged.

The first PM-04B read-only preflight stopped on `NoSuchBucketPolicy` before any
upload, deployment or invocation. Its evidence remains preserved. The corrected
local controller uses `deployment_preflight.inspect_private_bucket`, which records
only that exact response as policy absence without fabricating PolicyStatus.
Owner-scoped reads, encryption and all four true public-access blocks remain
mandatory; a public policy, access error or malformed required response fails.
Six focused tests and the full 239-test offline suite passed. This deployment-only
helper is outside the reviewed Lambda ZIP and does not change its implementation
hash. Private controller configuration and detailed execution evidence remain ignored.

See the [verification summary](cloud-modeling-verification.md) for the newly
measured evaluation, calibration, interpretation and probability results. No
personal-payment activation, upgrade, purchase, subscription or Organizations
enrollment occurred; the preflight confirmed the existing active Free plan with
eligible credits. Continuing storage/log/request usage is not unlimited free usage.

### Failure, recovery and cleanup

On any deployment or smoke failure, stop and set reserved concurrency to zero
for whichever **new modeling functions** exist. Leave ingestion/preparation
unchanged. No fresh-token retry, refit, permission expansion, new model setting
or automatic invocation is permitted to force success. Preserve checkpoint,
models, results and logs. A claim without checkpoint remains ambiguous; recovery
needs review, not a lease timeout. Matching checkpoint publication can be resumed
only after separate authorization, without retraining.

Cleanup commands are documented, not authorized in this implementation task:

```bash
aws lambda put-function-concurrency --region us-east-1 \
  --function-name fbs-model-training --reserved-concurrent-executions 0
aws lambda put-function-concurrency --region us-east-1 \
  --function-name fbs-model-inference --reserved-concurrent-executions 0
aws cloudformation delete-stack --region us-east-1 --stack-name fbs-cloud-modeling
```

Stack deletion removes only new modeling resources; retained logs and every S3
artifact remain. No source, model, result or evidence deletion is proposed.

Official references: [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html),
[Python native packaging](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html),
[Python 3.14/AL2023 runtime](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).
