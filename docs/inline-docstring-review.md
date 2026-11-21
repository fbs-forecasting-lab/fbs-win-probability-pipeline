# Inline docstring review - no producer edits

AST inventory as of PM-10, November 21, 2026. All 22 source classes and all function/method definitions were inspected without importing pipeline code. This lists absent inline docstrings, not missing external contracts or necessarily undocumented implementation. Nested local functions are not included; module-level functions and class methods are included.

**Four classes** and **127 functions/methods** lack inline docstrings. There are existing external class/function guides, but that does not make the inline omissions complete. Earlier coursework/peer reviews remain complete.

## Smallest safe correction

Add concise behavior, inputs/outputs and refusal semantics to each listed major public helper/class; use shorter intent/invariant docstrings for private helpers where useful. The four class docstrings belong to `OddsResponse`, `WeeklyStore`, `InsightsStore` and `MonitorStore`. Do not change signatures, control flow, model settings, request schemas or statuses. A text-only patch is necessary but not sufficient for compatibility.

Producer identities hash source bytes, including comments/docstrings. In particular, ingestion, preparation, modeling, weekly, monitoring and insights contracts bind overlapping source closures. A docstring patch can therefore alter derived model/request/stage identities and invalidate automatic replay assumptions even if the Python AST behavior is unchanged.

Prepare the smallest separate coordinated documentation-only source patch, map every affected `implementation_hash` closure, record old/new producer hashes and an explicit read/replay compatibility policy. Preserve original receipts and old package/runtime bindings. Run affected offline integrity/replay/packaging tests. Rebaseline and seek separate approval for any deployment or compatibility adaptation; never rewrite historical receipts or silently accept arbitrary old/new hashes. PM-10 makes no such producer patch.

Prioritize the four classes and externally used undocumented orchestration/verification helpers before private boilerplate. The full inventory below prevents calling that priority pass a complete inline-docstring cleanup.

## First minimal patch to prepare later (not applied)

| Definition | Suggested concise class-docstring content |
| --- | --- |
| `OddsResponse` | Exact provider bytes, request/observation times and quota metadata for one bounded capture. |
| `WeeklyStore` | Read protected training/source receipts and isolate immutable weekly-stage outputs. |
| `InsightsStore` | Isolate explanation/market claims, one-attempt checkpoints and verified replay. |
| `MonitorStore` | Read verified monitoring sources and publish private immutable reports, alerts and review records. |

Then document `cloud_weekly.checked_stage`, `publish_stage`, `advance` and
`cloud_modeling.verify_bundle`: expected receipt/input identities, return shape,
completion-last/no-refit behavior and integrity/conflict failures. These are
concrete priority omissions already covered externally. This small first patch
would not resolve every absent docstring in the inventory. In particular,
undocumented public API/market/monitoring contract helpers still need review.
Preserve the distinction between the proposed words above and actual existing
docstrings. Even this first patch requires the producer-identity compatibility
process above and a new reviewed package/baseline; do not apply it casually.

## Complete absent-inline-docstring inventory

| Source | Definition | Kind |
| --- | --- | --- |
| [src/features/dataset.py:71](../src/features/dataset.py) | `_json` | function |
| [src/features/dataset.py:75](../src/features/dataset.py) | `_csv` | function |
| [src/features/dataset.py:144](../src/features/dataset.py) | `_source_audit` | function |
| [src/features/dataset.py:195](../src/features/dataset.py) | `_target_audit` | function |
| [src/features/games.py:47](../src/features/games.py) | `_json_bytes` | function |
| [src/features/games.py:51](../src/features/games.py) | `_utc_timestamp` | function |
| [src/features/games.py:65](../src/features/games.py) | `_integer` | function |
| [src/features/games.py:69](../src/features/games.py) | `_unique_keys` | function |
| [src/features/games.py:164](../src/features/games.py) | `_validate_row` | function |
| [src/features/games.py:208](../src/features/games.py) | `_normalize` | function |
| [src/features/markets.py:12](../src/features/markets.py) | `instant` | function |
| [src/features/markets.py:14](../src/features/markets.py) | `implied` | function |
| [src/features/markets.py:20](../src/features/markets.py) | `fair_probabilities` | function |
| [src/features/markets.py:27](../src/features/markets.py) | `normalize` | function |
| [src/features/markets.py:71](../src/features/markets.py) | `compare` | function |
| [src/ingestion/cfbd.py:40](../src/ingestion/cfbd.py) | `_api_key` | function |
| [src/ingestion/cfbd.py:48](../src/ingestion/cfbd.py) | `_validate_key` | function |
| [src/ingestion/cfbd.py:56](../src/ingestion/cfbd.py) | `_retry_delay` | function |
| [src/ingestion/odds.py:14](../src/ingestion/odds.py) | `OddsResponse` | class |
| [src/ingestion/odds.py:22](../src/ingestion/odds.py) | `parameters` | function |
| [src/ingestion/odds.py:26](../src/ingestion/odds.py) | `validate_key` | function |
| [src/ingestion/odds.py:29](../src/ingestion/odds.py) | `fetch_moneylines` | function |
| [src/ingestion/odds.py:58](../src/ingestion/odds.py) | `manifest` | function |
| [src/ingestion/s3_storage.py:29](../src/ingestion/s3_storage.py) | `__getattr__` | function |
| [src/ingestion/s3_storage.py:81](../src/ingestion/s3_storage.py) | `_sha` | function |
| [src/ingestion/s3_storage.py:85](../src/ingestion/s3_storage.py) | `_dataset_id` | function |
| [src/ingestion/s3_storage.py:107](../src/ingestion/s3_storage.py) | `S3Store.__init__` | function |
| [src/ingestion/s3_storage.py:116](../src/ingestion/s3_storage.py) | `S3Store._private_bucket` | function |
| [src/ingestion/s3_storage.py:129](../src/ingestion/s3_storage.py) | `S3Store._get` | function |
| [src/ingestion/s3_storage.py:151](../src/ingestion/s3_storage.py) | `S3Store._put` | function |
| [src/ingestion/s3_storage.py:170](../src/ingestion/s3_storage.py) | `S3Store._upload` | function |
| [src/ingestion/storage.py:30](../src/ingestion/storage.py) | `_reject_non_json_constant` | function |
| [src/pipeline/cloud_benchmark.py:17](../src/pipeline/cloud_benchmark.py) | `capture` | function |
| [src/pipeline/cloud_benchmark.py:40](../src/pipeline/cloud_benchmark.py) | `market_input` | function |
| [src/pipeline/cloud_benchmark.py:58](../src/pipeline/cloud_benchmark.py) | `benchmark` | function |
| [src/pipeline/cloud_benchmark.py:82](../src/pipeline/cloud_benchmark.py) | `run` | function |
| [src/pipeline/cloud_benchmark.py:93](../src/pipeline/cloud_benchmark.py) | `handler` | function |
| [src/pipeline/cloud_explanation.py:16](../src/pipeline/cloud_explanation.py) | `verified_facts` | function |
| [src/pipeline/cloud_explanation.py:34](../src/pipeline/cloud_explanation.py) | `provider_call` | function |
| [src/pipeline/cloud_explanation.py:47](../src/pipeline/cloud_explanation.py) | `run` | function |
| [src/pipeline/cloud_explanation.py:85](../src/pipeline/cloud_explanation.py) | `handler` | function |
| [src/pipeline/cloud_ingestion.py:37](../src/pipeline/cloud_ingestion.py) | `CloudS3Store._get` | function |
| [src/pipeline/cloud_modeling.py:29](../src/pipeline/cloud_modeling.py) | `ModelingStore.__init__` | function |
| [src/pipeline/cloud_modeling.py:33](../src/pipeline/cloud_modeling.py) | `ModelingStore._get` | function |
| [src/pipeline/cloud_modeling.py:72](../src/pipeline/cloud_modeling.py) | `check_reference` | function |
| [src/pipeline/cloud_modeling.py:99](../src/pipeline/cloud_modeling.py) | `verify_bundle` | function |
| [src/pipeline/cloud_modeling.py:126](../src/pipeline/cloud_modeling.py) | `train_run` | function |
| [src/pipeline/cloud_modeling.py:245](../src/pipeline/cloud_modeling.py) | `infer_run` | function |
| [src/pipeline/cloud_modeling.py:286](../src/pipeline/cloud_modeling.py) | `failure` | function |
| [src/pipeline/cloud_modeling.py:292](../src/pipeline/cloud_modeling.py) | `handler` | function |
| [src/pipeline/cloud_modeling.py:307](../src/pipeline/cloud_modeling.py) | `training_handler` | function |
| [src/pipeline/cloud_modeling.py:311](../src/pipeline/cloud_modeling.py) | `inference_handler` | function |
| [src/pipeline/cloud_monitoring.py:26](../src/pipeline/cloud_monitoring.py) | `csv_rows` | function |
| [src/pipeline/cloud_monitoring.py:48](../src/pipeline/cloud_monitoring.py) | `inputs` | function |
| [src/pipeline/cloud_monitoring.py:73](../src/pipeline/cloud_monitoring.py) | `later_outcomes` | function |
| [src/pipeline/cloud_monitoring.py:90](../src/pipeline/cloud_monitoring.py) | `selected_review` | function |
| [src/pipeline/cloud_monitoring.py:100](../src/pipeline/cloud_monitoring.py) | `report_run` | function |
| [src/pipeline/cloud_monitoring.py:193](../src/pipeline/cloud_monitoring.py) | `handler` | function |
| [src/pipeline/cloud_preparation.py:37](../src/pipeline/cloud_preparation.py) | `PreparationStore._get` | function |
| [src/pipeline/cloud_preparation.py:83](../src/pipeline/cloud_preparation.py) | `load_sources` | function |
| [src/pipeline/cloud_preparation.py:137](../src/pipeline/cloud_preparation.py) | `query_rows` | function |
| [src/pipeline/cloud_review.py:15](../src/pipeline/cloud_review.py) | `review_run` | function |
| [src/pipeline/cloud_review.py:60](../src/pipeline/cloud_review.py) | `handler` | function |
| [src/pipeline/cloud_weekly.py:22](../src/pipeline/cloud_weekly.py) | `WeeklyStore` | class |
| [src/pipeline/cloud_weekly.py:23](../src/pipeline/cloud_weekly.py) | `WeeklyStore._get` | function |
| [src/pipeline/cloud_weekly.py:34](../src/pipeline/cloud_weekly.py) | `checked_stage` | function |
| [src/pipeline/cloud_weekly.py:45](../src/pipeline/cloud_weekly.py) | `publish_stage` | function |
| [src/pipeline/cloud_weekly.py:53](../src/pipeline/cloud_weekly.py) | `scoring_reference` | function |
| [src/pipeline/cloud_weekly.py:169](../src/pipeline/cloud_weekly.py) | `advance` | function |
| [src/pipeline/cloud_weekly.py:232](../src/pipeline/cloud_weekly.py) | `handler` | function |
| [src/pipeline/explanation_facts.py:8](../src/pipeline/explanation_facts.py) | `number` | function |
| [src/pipeline/explanation_facts.py:12](../src/pipeline/explanation_facts.py) | `count` | function |
| [src/pipeline/explanation_facts.py:16](../src/pipeline/explanation_facts.py) | `catalog` | function |
| [src/pipeline/explanation_facts.py:57](../src/pipeline/explanation_facts.py) | `validate_selection` | function |
| [src/pipeline/insights_contract.py:19](../src/pipeline/insights_contract.py) | `decode` | function |
| [src/pipeline/insights_contract.py:31](../src/pipeline/insights_contract.py) | `reference` | function |
| [src/pipeline/insights_contract.py:35](../src/pipeline/insights_contract.py) | `validate` | function |
| [src/pipeline/insights_contract.py:69](../src/pipeline/insights_contract.py) | `implementation_hash` | function |
| [src/pipeline/insights_storage.py:7](../src/pipeline/insights_storage.py) | `InsightsStore` | class |
| [src/pipeline/insights_storage.py:8](../src/pipeline/insights_storage.py) | `InsightsStore._get` | function |
| [src/pipeline/insights_storage.py:15](../src/pipeline/insights_storage.py) | `InsightsStore._put` | function |
| [src/pipeline/insights_storage.py:20](../src/pipeline/insights_storage.py) | `claim` | function |
| [src/pipeline/insights_storage.py:26](../src/pipeline/insights_storage.py) | `external_once` | function |
| [src/pipeline/insights_storage.py:43](../src/pipeline/insights_storage.py) | `replay` | function |
| [src/pipeline/managed_contract.py:56](../src/pipeline/managed_contract.py) | `TrainingSpec.__post_init__` | function |
| [src/pipeline/managed_lineage.py:37](../src/pipeline/managed_lineage.py) | `_require` | function |
| [src/pipeline/managed_lineage.py:42](../src/pipeline/managed_lineage.py) | `_json` | function |
| [src/pipeline/managed_lineage.py:88](../src/pipeline/managed_lineage.py) | `_evidence` | function |
| [src/pipeline/managed_lineage.py:203](../src/pipeline/managed_lineage.py) | `_metadata` | function |
| [src/pipeline/managed_lineage.py:235](../src/pipeline/managed_lineage.py) | `_receipt` | function |
| [src/pipeline/model_contract.py:15](../src/pipeline/model_contract.py) | `hex_id` | function |
| [src/pipeline/model_contract.py:21](../src/pipeline/model_contract.py) | `validate` | function |
| [src/pipeline/model_contract.py:56](../src/pipeline/model_contract.py) | `implementation_hash` | function |
| [src/pipeline/model_contract.py:65](../src/pipeline/model_contract.py) | `identities` | function |
| [src/pipeline/monitor_contract.py:17](../src/pipeline/monitor_contract.py) | `token` | function |
| [src/pipeline/monitor_contract.py:23](../src/pipeline/monitor_contract.py) | `weekly_reference` | function |
| [src/pipeline/monitor_contract.py:29](../src/pipeline/monitor_contract.py) | `validate_report` | function |
| [src/pipeline/monitor_contract.py:81](../src/pipeline/monitor_contract.py) | `validate_review` | function |
| [src/pipeline/monitor_contract.py:106](../src/pipeline/monitor_contract.py) | `implementation_hash` | function |
| [src/pipeline/monitor_storage.py:9](../src/pipeline/monitor_storage.py) | `MonitorStore` | class |
| [src/pipeline/monitor_storage.py:10](../src/pipeline/monitor_storage.py) | `MonitorStore._get` | function |
| [src/pipeline/monitor_storage.py:19](../src/pipeline/monitor_storage.py) | `MonitorStore._put` | function |
| [src/pipeline/monitor_storage.py:27](../src/pipeline/monitor_storage.py) | `verified_object` | function |
| [src/pipeline/monitor_storage.py:33](../src/pipeline/monitor_storage.py) | `completion` | function |
| [src/pipeline/monitor_storage.py:41](../src/pipeline/monitor_storage.py) | `publish` | function |
| [src/pipeline/monitor_storage.py:47](../src/pipeline/monitor_storage.py) | `alert` | function |
| [src/pipeline/monitoring_metrics.py:16](../src/pipeline/monitoring_metrics.py) | `instant` | function |
| [src/pipeline/monitoring_metrics.py:19](../src/pipeline/monitoring_metrics.py) | `feature_values` | function |
| [src/pipeline/monitoring_metrics.py:30](../src/pipeline/monitoring_metrics.py) | `probability_errors` | function |
| [src/pipeline/monitoring_metrics.py:42](../src/pipeline/monitoring_metrics.py) | `quality` | function |
| [src/pipeline/monitoring_metrics.py:70](../src/pipeline/monitoring_metrics.py) | `distributions` | function |
| [src/pipeline/monitoring_view.py:7](../src/pipeline/monitoring_view.py) | `stakeholder` | function |
| [src/pipeline/monitoring_view.py:20](../src/pipeline/monitoring_view.py) | `render` | function |
| [src/pipeline/notebook_views.py:46](../src/pipeline/notebook_views.py) | `StepFailed._render_traceback_` | function |
| [src/pipeline/notebook_views.py:180](../src/pipeline/notebook_views.py) | `_parse` | function |
| [src/pipeline/notebook_views.py:194](../src/pipeline/notebook_views.py) | `_signed` | function |
| [src/pipeline/notebook_views.py:198](../src/pipeline/notebook_views.py) | `_size` | function |
| [src/pipeline/notebook_views.py:202](../src/pipeline/notebook_views.py) | `_s3_folder` | function |
| [src/pipeline/notebook_views.py:209](../src/pipeline/notebook_views.py) | `_status` | function |
| [src/pipeline/notebook_views.py:244](../src/pipeline/notebook_views.py) | `_plain_reason` | function |
| [src/pipeline/preparation_contract.py:80](../src/pipeline/preparation_contract.py) | `selection_id` | function |
| [src/pipeline/preparation_contract.py:98](../src/pipeline/preparation_contract.py) | `query` | function |
| [src/pipeline/run_contract.py:16](../src/pipeline/run_contract.py) | `encode` | function |
| [src/pipeline/run_contract.py:20](../src/pipeline/run_contract.py) | `digest` | function |
| [src/pipeline/run_contract.py:24](../src/pipeline/run_contract.py) | `now` | function |
| [src/pipeline/run_contract.py:47](../src/pipeline/run_contract.py) | `receipt` | function |
| [src/pipeline/weekly_contract.py:14](../src/pipeline/weekly_contract.py) | `instant` | function |
| [src/pipeline/weekly_contract.py:18](../src/pipeline/weekly_contract.py) | `validate` | function |
| [src/pipeline/weekly_contract.py:62](../src/pipeline/weekly_contract.py) | `implementation_hash` | function |
| [src/pipeline/weekly_contract.py:71](../src/pipeline/weekly_contract.py) | `identity` | function |
| [src/pipeline/weekly_contract.py:96](../src/pipeline/weekly_contract.py) | `publication_status` | function |
