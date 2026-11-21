# Class and docstring reference

Source inventory for the final documentation. Existing deployed source bytes are preserved; changing even a docstring in a hashed producer requires compatibility/repackaging review. No signature or implementation claim is inferred from a proposed interface.

| Class | Source | Responsibility / failures | Existing class docstring |
| --- | --- | --- | --- |
| `DatasetError` | [src/features/dataset.py:58](../src/features/dataset.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | Invalid inputs, missing explicit demo permission, or conflicting output. |
| `SeasonInput` | [src/features/dataset.py:63](../src/features/dataset.py) | Verified season metadata and normalized rows consumed by chronological dataset construction. | Verified inputs for one season: source metadata, typed normalized rows, counts, artifact hashes. |
| `NormalizationError` | [src/features/games.py:36](../src/features/games.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A snapshot-integrity, metadata, or output-conflict error. |
| `Snapshot` | [src/features/games.py:41](../src/features/games.py) | A hash/coverage-verified raw capture and its manifest/source metadata. | A verified raw snapshot: the parsed game records and their source metadata. |
| `CFBDError` | [src/ingestion/cfbd.py:26](../src/ingestion/cfbd.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | An actionable error that contains no request, response body, or credentials. |
| `GamesResponse` | [src/ingestion/cfbd.py:31](../src/ingestion/cfbd.py) | Exact CFBD response bytes plus request/retrieval/status metadata. | One raw CFBD /games response: original bytes, request parameters, retrieval time, HTTP status. |
| `OddsResponse` | [src/ingestion/odds.py:14](../src/ingestion/odds.py) | Exact current-odds response bytes, request times/parameters and quota metadata. | Absent; module/function contracts documented externally; inline addition deferred for hashed-producer compatibility. |
| `S3StorageError` | [src/ingestion/s3_storage.py:38](../src/ingestion/s3_storage.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | Sanitized transfer, configuration, or integrity failure. |
| `S3Store` | [src/ingestion/s3_storage.py:91](../src/ingestion/s3_storage.py) | Private-bucket raw/dataset transfer, exact-byte reuse and verified new-directory downloads. | Explicit, no-overwrite transfers between verified local artifacts and one private bucket/prefix. |
| `SnapshotError` | [src/ingestion/storage.py:26](../src/ingestion/storage.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A sanitized response-validation or snapshot-storage error. |
| `BaselineError` | [src/models/baseline.py:41](../src/models/baseline.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A demo input, model artifact, or output failed validation. |
| `CloudS3Store` | [src/pipeline/cloud_ingestion.py:30](../src/pipeline/cloud_ingestion.py) | Ingestion ledger exact-key optional probes and immutable capture/publication. | Resolve optional absence through a prefix-scoped, exact-key list probe. |
| `ModelingStore` | [src/pipeline/cloud_modeling.py:27](../src/pipeline/cloud_modeling.py) | Protected model/preparation read domains and separated trainer/inference write domains. | Use exact-key absence probes; a 403 always stays a failure. |
| `PreparationStore` | [src/pipeline/cloud_preparation.py:35](../src/pipeline/cloud_preparation.py) | Explicit source verification, scoped normalized/dataset/query-state artifacts. | Exact-key list probes within the role's narrowly allowed preparation prefixes. |
| `WeeklyStore` | [src/pipeline/cloud_weekly.py:22](../src/pipeline/cloud_weekly.py) | Pinned original training/model references, weekly source/stage reads and isolated writes. | Absent; module/function contracts documented externally; inline addition deferred for hashed-producer compatibility. |
| `InsightsStore` | [src/pipeline/insights_storage.py:7](../src/pipeline/insights_storage.py) | Isolated explanation/market claims, attempts, response checkpoints and output domains. | Absent; module/function contracts documented externally; inline addition deferred for hashed-producer compatibility. |
| `MonitorStore` | [src/pipeline/monitor_storage.py:9](../src/pipeline/monitor_storage.py) | Monitoring source reads and private immutable reporting/review domains. | Absent; module/function contracts documented externally; inline addition deferred for hashed-producer compatibility. |
| `StepFailed` | [src/pipeline/notebook_views.py:43](../src/pipeline/notebook_views.py) | Stops dependent notebook stages and displays the documented saved-dataset fallback. | A notebook step failed. The message is shown with ``say``; the error box shows one short line. |
| `ContractError` | [src/pipeline/run_contract.py:12](../src/pipeline/run_contract.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A safe error with no event or credential contents. |
| `DemoError` | [src/pipeline/s3_demo.py:36](../src/pipeline/s3_demo.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A demo stage failed; the message names the stage and never includes secrets. |
| `RefreshError` | [src/pipeline/week_refresh.py:52](../src/pipeline/week_refresh.py) | Typed validation/stage exception; callers stop rather than continue with invalid evidence. | A refresh stage failed; the message names the stage and never includes secrets. |

## Existing function docstring excerpts

The [major-function guide](major-functions.md) covers implemented inputs, outputs, validation and failure conditions. These are actual docstrings, not proposed names.

### `src/models/baseline.py:load_dataset`

```text
Load and fully verify a six-file retrospective demo dataset.

Checks the report's schema version, demo flags, predictor contract, identity hash, and every
artifact's SHA-256, then the split seasons and counts, exclusion reasons, unique game IDs,
completion status, binary labels, and feature domains before returning anything.

Args:
    directory: Folder containing dataset_report.json and the five data artifacts.
    allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

Returns:
    Dict with ``report`` (parsed report), ``report_sha256``, ``artifacts`` (bytes by file name), and
    ``splits`` mapping train/holdout/prediction to ``{"rows", "x", "y"}``: the CSV rows, the
    three-column predictor frame, and the 0/1 labels (``None`` for prediction rows).

Raises:
    BaselineError: If permission is missing or any file, hash, count, or field fails validation.
```

### `src/models/baseline.py:train_baseline`

```text
Fit the fixed scaler + logistic regression and evaluate it on the 2025 holdout.

The pipeline is fitted on the 2022–2024 training rows only. Holdout rows are scored, never used
for fitting, and compared with a constant baseline that always predicts the training home-win
rate. The saved 2026 prediction rows are also scored. The fitted pipeline is serialized and
reloaded, and its predictions must be unchanged before anything is published.

Args:
    dataset_dir: Verified dataset directory (see ``load_dataset``).
    output_dir: New or matching directory for the seven model artifacts.
    allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

Returns:
    ``(metadata, evaluation)``: the metadata written to model_metadata.json, and the holdout
    evaluation with Brier score, log loss, and accuracy for the model and the constant baseline.

Raises:
    BaselineError: If the dataset is invalid, the model does not converge, serialization changes
        predictions, or existing output conflicts.
```

### `src/models/baseline.py:load_trusted_model`

```text
Reload a trusted, locally generated model after verifying its saved artifacts.

Checks the metadata's demo flags, schema, predictor and class order, and library versions, then
every artifact's SHA-256, before deserializing model.joblib. The restored pipeline must match the
recorded structure and settings. Hashes detect changes but do not make an untrusted joblib file
safe: joblib can execute code, so load only model directories this project created.

Args:
    directory: Model directory written by ``train_baseline``.
    allow_retrospective_demo: Must be True to acknowledge unverified historical availability.

Returns:
    ``(model, metadata)``: the restored scikit-learn pipeline and its parsed metadata.

Raises:
    BaselineError: If permission is missing, versions or hashes do not match, or the model fails
        validation.
```

### `src/pipeline/managed_training.py:run`

```text
Verify a pinned SageMaker File channel and fit the existing baseline once.

Inputs are the six dataset files already downloaded by the managed service,
expected dataset/report identities, a fresh output and an exclusive attempt
marker. Outputs are the normal model/evaluation artifacts. Holdout stays
evaluation-only. A consumed attempt or existing output refuses another fit;
failures preserve evidence. No SDK, network, credentials or dotenv is used.
This candidate does not publish into the trusted cloud-modeling domain.
```

### `src/pipeline/public_monitoring.py:build_view`

```text
Extract allowlisted measurements from a hash-pinned private report.

Returns a new public-safe dictionary. Raw rows, references, free text,
alerts/reviewer details and individual predictions are never copied.
Invalid state/count/identity fails; missing measurements stay unavailable.
Hash verification alone does not establish trust: use a verified producer.
```
