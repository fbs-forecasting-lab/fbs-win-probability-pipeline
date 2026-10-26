# Major-function guide

For a first pass through the model and its call sequence, start with the
[code-reading guide](code-reading-guide.md), then use this page for detailed
inputs, outputs, and failure conditions.

These are implemented names, not proposed services. Paths are relative to the
repository root. CLI entry points expose `main(argv=None)` and return nonzero on
failure. See the [architecture](architecture.md) for the full flow.

## Ingestion and local storage

| Function | Inputs and outputs | Validation / important failures |
| --- | --- | --- |
| `src.ingestion.cfbd.fetch_games(season, week=None)` | Season and optional week → `GamesResponse` containing original bytes, request parameters, retrieval time, HTTP status | Requires CFBD key from environment or project `.env`; validates parameters; bounded HTTP retries, timeout, authentication/rate-limit/server failures are sanitized. Makes real network calls. |
| `src.ingestion.storage.parse_games(raw_response)` | Bytes → list of game objects | Rejects malformed JSON, non-object rows, and non-JSON numeric constants. |
| `coverage_report(records)` | Game objects → field/null/classification/duplicate counts | Describes coverage; does not approve leakage or repair rows. |
| `save_snapshot(result, output_dir=None)` | `GamesResponse` → `(raw_path, manifest_path)` | Preserves bytes, records SHA-256 and coverage; exclusive publication refuses overwrite. Manifest is published last; an orphan raw file is incomplete after failure. |

## Normalization and dataset construction

| Function | Inputs and outputs | Validation / important failures |
| --- | --- | --- |
| `src.features.games.load_snapshot(manifest_path)` | Manifest and sibling raw JSON → `Snapshot(records, source)` | Checks schema, source/request metadata, timestamps, SHA-256, count, coverage, and unapproved status. Missing, tampered, malformed, or mismatched files fail. |
| `normalize_snapshot(manifest_path, output_root=None)` | Verified snapshot → output directory named by snapshot ID | Publishes `games.csv`, `exclusions.json`, `quality_report.json`; excludes non-FBS pairs, quarantines invalid/TBD rows, preserves null uncompleted scores. Conflicting output fails; identical output can be reused. |
| `src.features.dataset.build_dataset(manifest_paths, output_dir, *, allow_retrospective_demo=False, normalized_root=...)` | Exactly one manifest per 2021–2026 season plus normalized artifacts → report and six dataset files | Requires demo acknowledgement, full historical seasons, matching normalized artifacts and hashes. Builds Y−1 aggregates and three explicit predictors; excludes missing histories, inappropriate completion status, or chronology failures. Conflicting outputs fail. |

Dataset files: `train.csv` (2022–2024), `holdout.csv` (2025), `prediction.csv`
(eligible uncompleted 2026 sample), `team_season_aggregates.csv`, `exclusions.json`,
and `dataset_report.json`. The dataset ID is SHA-256 of the canonical identity
(schema version, source metadata/hashes, predictor columns, mode), not just the
prediction rows. Target-game scores form training labels only. The 2021 season supplies
history, not training targets. A new retrieval time/manifest changes identity.

## Training, loading, evaluation, and prediction

| Function | Inputs and outputs | Validation / important failures |
| --- | --- | --- |
| `src.models.baseline.load_dataset(directory, *, allow_retrospective_demo=False)` | Six dataset artifacts → verified report and split arrays/rows | Checks report identity, file hashes, schema, predictor order, flags, seasons, finite features, nonempty train/holdout, and both training labels. |
| `train_baseline(dataset_dir, output_dir, *, allow_retrospective_demo=False)` | Verified dataset → `(metadata, evaluation)` and seven model artifacts | Fits scaler/logistic regression only on training rows; evaluates untouched holdout and constant training home-win rate; serialization must preserve predictions. Nonconvergence, bad input, or conflicting output fails. |
| `load_trusted_model(directory, *, allow_retrospective_demo=False)` | Trusted saved model directory → `(model, metadata)` | Checks versions, schema, model structure and artifact hashes before deserialization. Version mismatch or tampering fails. Hashes do not make untrusted joblib safe. |
| `src.evaluation.metrics.evaluate_probabilities(labels, probabilities)` | Matching binary labels and probabilities → `(scores, calibration)` | Requires nonempty 1-D arrays, binary labels, finite probabilities in [0, 1]. Computes Brier score, log loss, accuracy at 0.5, and ten descriptive bins. |
| `src.models.predict.predict_saved_sample(model_dir, dataset_dir, output_dir, *, allow_retrospective_demo=False)` | Reloaded model + exact verified training-run dataset → report and three prediction artifacts | Requires matching dataset ID and report hash; refuses mismatches/conflicting output. Writes `predictions.csv`, `prediction_report.json`, `exclusions.json`. |
| `predict_vector(model, values)` | Loaded model + ordered dict of the three named predictors → hypothetical home/away probabilities and status | Enforces feature names/order, finite values and valid feature domains; probability is binary classification output, not a predicted score. |

Model artifacts: `model.joblib`, `model_metadata.json`, `evaluation.json`,
`calibration.json`, `holdout_predictions.csv`, `sample_predictions.csv`,
`exclusions.json`. The home and away probabilities sum to one. All model/dataset
paths retain retrospective/unapproved flags and require explicit demo consent.

## S3 transfers

`src.ingestion.s3_storage.configuration()` reads local nonsecret S3 settings;
`make_client(region=None, profile=None)` creates the SDK client. These are not
used by the synthetic example. `S3Store(client, bucket, prefix)` validates the
bucket/prefix. Its existing `_private_bucket()` check requires all four Block
Public Access controls before transfers; it changes no settings.

| Method | Inputs and outputs | Validation / important failures |
| --- | --- | --- |
| `upload_raw(manifest_path)` | Verified local raw/manifest pair → S3 receipt | Uses `<prefix>/raw/cfbd/games/season=<year>/`; identical objects are reused, conflicting objects refused. Conditional writes and readback protect integrity. |
| `upload_dataset(directory, *, allow_retrospective_demo=False)` | Verified dataset → S3 receipt | Uses dataset-ID-specific prefix; uploads six artifacts with report as completion marker. Demo flag and private-bucket check required. |
| `download_dataset(identifier, output_dir, *, allow_retrospective_demo=False)` | S3 dataset ID → verified local files and receipt | Verifies SHA-256 and dataset semantics before publication. Missing object, tampering, invalid ID, access error, or conflicting local output fails. Files are downloaded, not streamed into training. |
| `download_raw(season, manifest_name, output_dir)` | S3 season/manifest name → local manifest path | Verifies the manifest and referenced raw bytes with `load_snapshot` before publication. Unsafe names, missing objects, hash mismatch, or output conflict fails. |

AWS exceptions are sanitized; no permissions or bucket policies are modified.
S3 stores data, not a hosted model. The assignment's offline checks do not
establish current AWS connectivity.

## Orchestration and examples

- `src.pipeline.week_refresh.discover_history(root)` reads the **local** reference
  dataset report and finds its five 2021–2025 manifest paths.
  `history_sources(report)` extracts the expected history metadata;
  `verify_history(paths, expected=None)` validates the exact season set, complete
  seasons, raw hashes, and expected source identity when provided.
- `download_history(store, directory, reference_dataset_id=...)` reads the
  reference dataset **from S3**, downloads five raw snapshots, then verifies them
  against that report. The notebook's Step 2b uses these downloaded manifests;
  its setup does not require a local raw-history copy.
- `week_refresh.main` validates season/week/tag, demo consent, bucket/prefix,
  output paths, history and key presence before requests. `run(store, week, tag,
  history, *, root=None, extra_args=())` executes private-bucket preflight,
  fetch/save, raw upload, normalization, dataset build and upload. Errors name
  their stage; output includes the next `s3_demo` command. The CLI defaults to
  local history; it does not automatically use the notebook's S3 history path.
- `src.pipeline.s3_demo.run(store, dataset_id, run_dir, *,
  allow_retrospective_demo=False, vector=None)` downloads/verifies, trains locally,
  predicts the saved sample, and optionally predicts a vector. `main` refuses
  unsafe inputs before client creation. Download/training identity mismatch,
  invalid directory, or stage failure stops the chain.
- `src.pipeline.notebook_views` formats tables and messages and provides the
  notebook's stage/error context. It does not implement another model.
- `bin/synthetic_demo.py:run` generates fixed fictional fixtures and chains
  `normalize_snapshot`, `build_dataset`, `train_baseline`,
  `predict_saved_sample`, `load_trusted_model`, and `predict_vector`. It requires
  a new ignored output directory and explicit retrospective consent. Synthetic
  compatibility manifests are labeled as simulations, never real API evidence.

The fixed Week 5 sample is historical. Fetching it again can remove completed
rows from prediction eligibility and cannot reproduce the September snapshot.
Use saved artifacts for historical reproduction, and treat prior rehearsal
counts as dated observations rather than guarantees for a fresh request.
