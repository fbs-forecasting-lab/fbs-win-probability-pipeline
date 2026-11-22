# Submitted source and deployed revisions

All 22 public source classes have inline descriptions. The four store/response classes and four major weekly/model verification helpers received docstrings only. Source-byte identities change wherever a producer closure includes these files. Use the original deployment image, package and receipt pin for historical replay. The pre-edit revision is `82396197c9ee894422182d84810cd2e9ab78e15c`. No receipt or verifier policy was updated.

| Source | Pre-edit SHA-256 | Candidate SHA-256 |
|---|---|---|
| `src/ingestion/odds.py` | `4e9cf4e7290c5fd91d05f8f00c0cccd21a9f7ef4e7e7564a5c680dc78d7012ac` | `acdd590a3a62147d4eaffeeb602cfcfce8dbb988c4aee32d0a944ffa79ded39f` |
| `src/pipeline/cloud_modeling.py` | `eeb37020e8e9fa7373492e82f63847bd1cf463a8cfe589ee6bc38325916f5ecd` | `0aa7599edf7b232070773318eb504fc3dc70535a9fab64ae0c34160fb8c238e6` |
| `src/pipeline/cloud_weekly.py` | `03f895d633a07d544c9beb71209ad70eb49134a666d441b28786f8ff7f301645` | `7bcc28390987d026b1ad807fb2aad1ba4fd620897ac0e72fcb625ae1745d48bc` |
| `src/pipeline/insights_storage.py` | `4c200ae6197c6ad461adecbf95d1f634a0cf45b56ef0ff00d0696dada5cdc2c0` | `2242ed05cc7cd1dcb82936330fc8d59cd659fa27e4b7592580bf90c3a6dd5788` |
| `src/pipeline/monitor_storage.py` | `50a653759a7bd5087068a4305dce90230cde766dbc09bdd6a491be6ab565dcec` | `9ea69ec7472bf838439f6e18f3e75d79908a95eeb74502c03fa738872e2a7d94` |

## Runtime implementation identities

| Contract | Pre-edit | Candidate |
|---|---|---|
| `model_contract` | `8d27677fa88b206577b518a0d709a48ff09a1676e6644f859ae20445ce06a0e4` | `49c6f901690f79eb657fe92b48f53f046b86cad20ad0d9e4ae020dcb342def73` |
| `weekly_contract` | `a65c04a5b0eff4f7f0ec5314ae0d142fbebcee511a56bdf816c03503f4fda8b2` | `2760d2f635cc8979cf99e598de3c5d6693f623a8a5c1eb83baef507b8a2225fb` |
| `monitor_contract` | `1d7e9e4886fcd24336339e8ab96f44a821793c14cdebaccaec19bf79c5564310` | `e28513329f327a5f2003b20b3b5e3074ff0c62d2e7174bf404fb65ff69bcd072` |
| `insights_contract` | `d97e96a0cad2364d5ab82dcde8c1ff8862c231cd15395f6efa1cd4b28eb07d70` | `537a0e276ecb0d081cacf1b6cf8e54710fb7db44f83058c4d805cf7a1fd969e2` |
| `preparation_contract` | `e583b79e8bef1e2c1d13adf25a6c595eb67ae569bd9a190a86b9c48f46d18725` | `e583b79e8bef1e2c1d13adf25a6c595eb67ae569bd9a190a86b9c48f46d18725` |

The comparison uses the pre-edit repository revision above. For an individual historical run, use its recorded implementation identity and original package or image digest as the authority. Candidate-generated identities must not be used to replay historical writes.

## Remaining definitions without inline docstrings

- `src/features/dataset.py::_json`
- `src/features/dataset.py::_csv`
- `src/features/dataset.py::_source_audit`
- `src/features/dataset.py::_target_audit`
- `src/features/games.py::_json_bytes`
- `src/features/games.py::_utc_timestamp`
- `src/features/games.py::_integer`
- `src/features/games.py::_unique_keys`
- `src/features/games.py::_validate_row`
- `src/features/games.py::_normalize`
- `src/features/markets.py::instant`
- `src/features/markets.py::implied`
- `src/features/markets.py::fair_probabilities`
- `src/features/markets.py::normalize`
- `src/features/markets.py::compare`
- `src/ingestion/cfbd.py::_api_key`
- `src/ingestion/cfbd.py::_validate_key`
- `src/ingestion/cfbd.py::_retry_delay`
- `src/ingestion/odds.py::parameters`
- `src/ingestion/odds.py::validate_key`
- `src/ingestion/odds.py::fetch_moneylines`
- `src/ingestion/odds.py::manifest`
- `src/ingestion/s3_storage.py::__getattr__`
- `src/ingestion/s3_storage.py::_sha`
- `src/ingestion/s3_storage.py::_dataset_id`
- `src/ingestion/s3_storage.py::S3Store.__init__`
- `src/ingestion/s3_storage.py::S3Store._private_bucket`
- `src/ingestion/s3_storage.py::S3Store._get`
- `src/ingestion/s3_storage.py::S3Store._put`
- `src/ingestion/s3_storage.py::S3Store._upload`
- `src/ingestion/storage.py::_reject_non_json_constant`
- `src/pipeline/cloud_benchmark.py::capture`
- `src/pipeline/cloud_benchmark.py::market_input`
- `src/pipeline/cloud_benchmark.py::benchmark`
- `src/pipeline/cloud_benchmark.py::run`
- `src/pipeline/cloud_benchmark.py::handler`
- `src/pipeline/cloud_explanation.py::verified_facts`
- `src/pipeline/cloud_explanation.py::provider_call`
- `src/pipeline/cloud_explanation.py::run`
- `src/pipeline/cloud_explanation.py::handler`
- `src/pipeline/cloud_ingestion.py::CloudS3Store._get`
- `src/pipeline/cloud_modeling.py::ModelingStore.__init__`
- `src/pipeline/cloud_modeling.py::ModelingStore._get`
- `src/pipeline/cloud_modeling.py::check_reference`
- `src/pipeline/cloud_modeling.py::train_run`
- `src/pipeline/cloud_modeling.py::infer_run`
- `src/pipeline/cloud_modeling.py::failure`
- `src/pipeline/cloud_modeling.py::handler`
- `src/pipeline/cloud_modeling.py::training_handler`
- `src/pipeline/cloud_modeling.py::inference_handler`
- `src/pipeline/cloud_monitoring.py::csv_rows`
- `src/pipeline/cloud_monitoring.py::inputs`
- `src/pipeline/cloud_monitoring.py::later_outcomes`
- `src/pipeline/cloud_monitoring.py::selected_review`
- `src/pipeline/cloud_monitoring.py::report_run`
- `src/pipeline/cloud_monitoring.py::handler`
- `src/pipeline/cloud_preparation.py::PreparationStore._get`
- `src/pipeline/cloud_preparation.py::load_sources`
- `src/pipeline/cloud_preparation.py::query_rows`
- `src/pipeline/cloud_review.py::review_run`
- `src/pipeline/cloud_review.py::handler`
- `src/pipeline/cloud_weekly.py::WeeklyStore._get`
- `src/pipeline/cloud_weekly.py::scoring_reference`
- `src/pipeline/cloud_weekly.py::handler`
- `src/pipeline/explanation_facts.py::number`
- `src/pipeline/explanation_facts.py::count`
- `src/pipeline/explanation_facts.py::catalog`
- `src/pipeline/explanation_facts.py::validate_selection`
- `src/pipeline/insights_contract.py::decode`
- `src/pipeline/insights_contract.py::reference`
- `src/pipeline/insights_contract.py::validate`
- `src/pipeline/insights_contract.py::implementation_hash`
- `src/pipeline/insights_storage.py::InsightsStore._get`
- `src/pipeline/insights_storage.py::InsightsStore._put`
- `src/pipeline/insights_storage.py::claim`
- `src/pipeline/insights_storage.py::external_once`
- `src/pipeline/insights_storage.py::replay`
- `src/pipeline/managed_archive.py::_require`
- `src/pipeline/managed_contract.py::TrainingSpec.__post_init__`
- `src/pipeline/managed_lineage.py::_require`
- `src/pipeline/managed_lineage.py::_json`
- `src/pipeline/managed_lineage.py::_evidence`
- `src/pipeline/managed_lineage.py::_metadata`
- `src/pipeline/managed_lineage.py::_receipt`
- `src/pipeline/model_contract.py::hex_id`
- `src/pipeline/model_contract.py::validate`
- `src/pipeline/model_contract.py::implementation_hash`
- `src/pipeline/model_contract.py::identities`
- `src/pipeline/monitor_contract.py::token`
- `src/pipeline/monitor_contract.py::weekly_reference`
- `src/pipeline/monitor_contract.py::validate_report`
- `src/pipeline/monitor_contract.py::validate_review`
- `src/pipeline/monitor_contract.py::implementation_hash`
- `src/pipeline/monitor_storage.py::MonitorStore._get`
- `src/pipeline/monitor_storage.py::MonitorStore._put`
- `src/pipeline/monitor_storage.py::verified_object`
- `src/pipeline/monitor_storage.py::completion`
- `src/pipeline/monitor_storage.py::publish`
- `src/pipeline/monitor_storage.py::alert`
- `src/pipeline/monitoring_metrics.py::instant`
- `src/pipeline/monitoring_metrics.py::feature_values`
- `src/pipeline/monitoring_metrics.py::probability_errors`
- `src/pipeline/monitoring_metrics.py::quality`
- `src/pipeline/monitoring_metrics.py::distributions`
- `src/pipeline/monitoring_view.py::stakeholder`
- `src/pipeline/monitoring_view.py::render`
- `src/pipeline/notebook_views.py::StepFailed._render_traceback_`
- `src/pipeline/notebook_views.py::_parse`
- `src/pipeline/notebook_views.py::_signed`
- `src/pipeline/notebook_views.py::_size`
- `src/pipeline/notebook_views.py::_s3_folder`
- `src/pipeline/notebook_views.py::_status`
- `src/pipeline/notebook_views.py::_plain_reason`
- `src/pipeline/preparation_contract.py::selection_id`
- `src/pipeline/preparation_contract.py::query`
- `src/pipeline/run_contract.py::encode`
- `src/pipeline/run_contract.py::digest`
- `src/pipeline/run_contract.py::now`
- `src/pipeline/run_contract.py::receipt`
- `src/pipeline/weekly_contract.py::instant`
- `src/pipeline/weekly_contract.py::validate`
- `src/pipeline/weekly_contract.py::implementation_hash`
- `src/pipeline/weekly_contract.py::identity`
- `src/pipeline/weekly_contract.py::publication_status`
