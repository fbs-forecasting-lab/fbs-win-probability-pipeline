"""Cloud S3 normalization and Athena feature parity; no API fetch or model training."""

import base64
import csv
from datetime import datetime, timezone
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

import boto3

from src.features import dataset, games
from src.ingestion.s3_storage import S3Store
from src.pipeline.cloud_ingestion import CLIENT_CONFIG
from src.pipeline import preparation_contract as contract
from src.pipeline.run_contract import ContractError, STATUS, digest, encode

MAX_QUERYABLE_BYTES = 16 * 1024 * 1024
MAX_RESULT_ROWS = 20000
REASONS = ("target_uncompleted", "prediction_target_completed", "missing_home_history",
           "missing_away_history", "home_history_not_before_cutoff", "away_history_not_before_cutoff")


def queryable_row(row):
    """Preserve microsecond chronology without engine-specific timestamp truncation."""
    delta = datetime.fromisoformat(row["start_date"]) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    micros = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    return row | {"start_epoch_us": micros}


class PreparationStore(S3Store):
    """Exact-key list probes within the role's narrowly allowed preparation prefixes."""
    def _get(self, key, *, optional=False):
        allowed = tuple(f"{self.prefix}/{part}/" for part in
                        ("raw/cfbd/games", "cloud-ingestion/runs", "cloud-preparation", "datasets"))
        if not isinstance(key, str) or not key.startswith(allowed):
            raise ContractError("Read is outside preparation prefixes.")
        if optional:
            result = self.client.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
            if not any(item.get("Key") == key for item in result.get("Contents", [])):
                return None
        return super()._get(key, optional=False)


def verify_origin(store, reference, source, raw, manifest):
    """Verify the capture checkpoint and its completed receipt; caller labels are not evidence."""
    token = reference.get("capture_token_sha256")
    if token is None:
        return {"origin": "legacy_upload_unverified", "cloud_capture_verified": False}
    base = f"{store.prefix}/cloud-ingestion/runs/{token}"
    receipt_bytes = store._get(f"{base}/complete.json")
    if digest(receipt_bytes) != reference["capture_receipt_sha256"]:
        raise ContractError("Cloud capture receipt hash mismatch.")
    receipt = json.loads(receipt_bytes)
    capture_bytes = store._get(f"{base}/capture.json")
    capture = json.loads(capture_bytes)
    request = capture["request"]
    params = source["request_parameters"]
    expected_request = {"schema_version": 1, "season": params["year"], "week": params.get("week"),
                        "endpoint": "cfbd/games", "season_type": "regular", "classification": "fbs"}
    raw_base = f"{store.prefix}/raw/cfbd/games/season={params['year']}"
    expected = {"raw_key": f"{raw_base}/{source['raw_file']}",
                "manifest_key": f"{raw_base}/{reference['manifest_name']}",
                "raw_sha256": digest(raw), "manifest_sha256": digest(manifest),
                "capture_sha256": digest(capture_bytes), "token_sha256": token,
                "request_sha256": digest(encode(request)), "state": "completed", **STATUS}
    if (capture.get("capture_version") != 1 or request != expected_request
            or any(receipt.get(k) != v for k, v in expected.items())
            or base64.b64decode(capture["raw"], validate=True) != raw
            or base64.b64decode(capture["manifest"], validate=True) != manifest
            or receipt.get("record_count") != json.loads(manifest)["record_count"]
            or receipt.get("retrieved_at") != source["retrieved_at"]
            or receipt.get("source_availability") != source["source_availability"]):
        raise ContractError("Cloud capture lineage does not match the selected source.")
    return {"origin": "cloud_ingestion", "cloud_capture_verified": True,
            "receipt_key": f"{base}/complete.json", "receipt_sha256": digest(receipt_bytes)}


def load_sources(request, store, root):
    manifests, origins = [], {}
    for reference in request["sources"]:
        season = reference["season"]
        path = store.download_raw(season, reference["manifest_name"], root / "raw" / str(season))
        source = games.load_snapshot(path).source
        if any(source[field] != reference[field] for field in ("raw_sha256", "manifest_sha256")):
            raise ContractError("Selected raw/manifest hash mismatch.")
        if season <= 2025 and "week" in source["request_parameters"]:
            raise ContractError("Historical seasons require full-season captures, not weekly samples.")
        contract.eligibility(source, request.get("forecast_cutoff"))
        origins[str(season)] = verify_origin(store, reference, source,
                                            (path.parent / source["raw_file"]).read_bytes(), path.read_bytes())
        manifests.append(path)
    return manifests, origins


def compare_sql(rows, directory):
    """Gate publication on every accepted target, exclusion reason, label and predictor."""
    expected = {}
    for split in dataset.SPLIT_SEASONS:
        for row in csv.DictReader(io.StringIO((directory / f"{split}.csv").read_text())):
            expected[(int(row["season"]), int(row["game_id"]))] = (row | {"split": split}, [])
    for row in json.loads((directory / "exclusions.json").read_bytes())["rows"]:
        expected[(row["season"], row["game_id"]) ] = (row, row["reasons"])
    seen = set()
    for actual in rows:
        key = (int(actual["season"]), int(actual["game_id"]))
        if key in seen or key not in expected:
            raise ContractError("SQL produced duplicate or unexpected targets.")
        seen.add(key)
        reference, reasons = expected[key]
        if actual["split"] != reference["split"] or games._utc_timestamp(actual["cutoff"]) != reference["cutoff"]:
            raise ContractError("SQL target provenance or split differs from the existing builder.")
        actual_reasons = {name for name in REASONS if int(actual[name]) == 1}
        if actual_reasons != set(reasons) or any(int(actual[name]) not in (0, 1) for name in REASONS):
            raise ContractError("SQL eligibility differs from the existing builder.")
        for side in ("home", "away"):
            field = f"{side}_prior_game_count"
            if int(actual[field]) != int(reference[field]):
                raise ContractError("SQL prior-season counts differ from the existing builder.")
        if not reasons:
            for field in dataset.PREDICTOR_COLUMNS:
                number = float(actual[field])
                if not math.isfinite(number) or not math.isclose(number, float(reference[field]), rel_tol=1e-12, abs_tol=1e-12):
                    raise ContractError("SQL predictor differs from the existing builder.")
            label = None if reference["split"] == "prediction" else int(reference["home_win"])
            if (None if actual.get("home_win") in (None, "") else int(actual["home_win"])) != label:
                raise ContractError("SQL label differs from the existing builder.")
    if seen != expected.keys():
        raise ContractError("SQL omitted required targets.")
    return {"verified_target_rows": len(seen), "tolerance": 1e-12}


def query_rows(client, query_id):
    rows, names, token = [], None, None
    while True:
        response = client.get_query_results(QueryExecutionId=query_id, MaxResults=1000,
                                            **({"NextToken": token} if token else {}))
        result = response["ResultSet"]
        columns = [item["Name"] for item in result["ResultSetMetadata"]["ColumnInfo"]]
        if names is None:
            names = columns
        elif names != columns:
            raise ContractError("Athena result columns changed between pages.")
        for row in result["Rows"]:
            values = [cell.get("VarCharValue") for cell in row["Data"]]
            if not rows and values == names:
                continue
            if len(values) != len(names):
                raise ContractError("Athena result row has an invalid shape.")
            rows.append(dict(zip(names, values, strict=True)))
            if len(rows) > MAX_RESULT_ROWS:
                raise ContractError("Athena result exceeds the bounded row limit.")
        token = response.get("NextToken")
        if not token:
            return rows


def prepare_run(event, store, athena, *, database="fbs_preparation", table="selected_games",
                workgroup="fbs-data-preparation", recovery_only=False):
    """Repeat the same event to finalize pending SQL or recover matching partial publication.

    A stable Athena client token recovers an ambiguous query-start response without another query.
    No CFBD client or training function is called. All processing is cloud-local when invoked in Lambda.
    """
    stage, selection = "request_validation", None
    try:
        request = contract.validate(event)
        if type(recovery_only) is not bool:
            raise ContractError("Recovery-only configuration must be a boolean.")
        selection = contract.selection_id(request, database, table, workgroup)
        sql = contract.query(selection, database, table)
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", workgroup):
            raise ContractError("Invalid fixed workgroup.")
        base = f"{store.prefix}/cloud-preparation/runs/{selection}"
        stage = "aws_preflight"
        store._private_bucket()
        with tempfile.TemporaryDirectory(prefix="fbs-preparation-") as tmp:
            root = Path(tmp)
            stage = "source_verification"
            manifests, origins = load_sources(request, store, root)
            stage = "normalize"
            normalized = root / "normalized"
            for path in manifests:
                games.normalize_snapshot(path, normalized)
            stage = "build_reference"
            directory = root / "dataset"
            report = dataset.build_dataset(manifests, directory, normalized_root=normalized,
                                           allow_retrospective_demo=True)
            inputs = dataset._load_inputs(manifests, normalized)
            data = b"".join(encode(queryable_row(row)) for item in inputs.values() for row in item.rows)
            if len(data) > MAX_QUERYABLE_BYTES:
                raise ContractError("Queryable selection exceeds the 16 MiB input bound.")
            stage = "publish_normalized"
            artifacts = {}
            for item in inputs.values():
                sid = item.source["snapshot_id"]
                for name in ("games.csv", "exclusions.json", "quality_report.json"):
                    artifacts[f"normalized/{sid}/{name}"] = (normalized / sid / name).read_bytes()
            artifacts["provenance.json"] = encode({"request": request, "origins": origins,
                "sources": report["sources"], "selection_id": selection, **STATUS})
            queryable_key = f"{store.prefix}/cloud-preparation/queryable/selection_id={selection}/games.jsonl"
            # Queryable data must be immutable and verified before any query starts.
            existing_data = store._get(queryable_key, optional=True)
            if existing_data is not None and existing_data != data:
                raise ContractError("Conflicting queryable data; existing objects preserved.")
            artifacts["prepared.json"] = encode({"selection_id": selection, "queryable_key": queryable_key,
                "queryable_sha256": digest(data), "queryable_bytes": len(data),
                "artifact_sha256": {name: digest(content) for name, content in artifacts.items()}, **STATUS})
            # An existing prepared marker is not permission to repair missing queryable bytes.
            if store._get(f"{base}/prepared.json", optional=True) is not None and existing_data is None:
                raise ContractError("Prepared receipt references missing queryable data.")
            if existing_data is None:
                store._put(queryable_key, data)
            store._upload(base, artifacts, "prepared.json")
            stage = "athena_query"
            arguments = {"ClientRequestToken": digest(encode({"selection": selection, "sql": sql,
                                                             "workgroup": workgroup})),
                         "QueryString": sql, "QueryExecutionContext": {"Database": database},
                         "WorkGroup": workgroup, "ResultReuseConfiguration": {"ResultReuseByAgeConfiguration": {"Enabled": False}}}
            query_content = store._get(f"{base}/query.json", optional=True)
            if query_content is None:
                if recovery_only:
                    raise ContractError("Recovery requires the original query receipt; no query was submitted.")
                query_id = athena.start_query_execution(**arguments)["QueryExecutionId"]
                query_content = encode({"query_id": query_id, "arguments_sha256": digest(encode(arguments))})
                store._put(f"{base}/query.json", query_content)
            info = json.loads(query_content)
            if info["arguments_sha256"] != digest(encode(arguments)):
                raise ContractError("Stored query conflicts with selected inputs.")
            query_id = info["query_id"]
            execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
            returned_sql = execution.get("Query")
            # Athena may trim boundary whitespace. Keep all SQL body bytes,
            # literals/comments and the original submitted/idempotency hashes.
            if (not isinstance(returned_sql, str) or returned_sql.strip() != sql.strip()
                    or execution.get("WorkGroup") != workgroup
                    or execution.get("QueryExecutionContext", {}).get("Database") != database):
                raise ContractError("Athena query identity does not match the immutable request.")
            state = execution["Status"]["State"]
            if recovery_only and state != "SUCCEEDED":
                raise ContractError("Recovery requires the original successful query; no replacement was submitted.")
            if state in {"QUEUED", "RUNNING"}:
                return {"state": "query_pending", "selection_id": selection, "query_id": query_id, **STATUS}
            if state != "SUCCEEDED":
                raise ContractError("Athena query failed or was cancelled; inspect private execution evidence.")
            stage = "sql_parity"
            parity = compare_sql(query_rows(athena, query_id), directory)
            stage = "publish_dataset"
            bundle = {name: (directory / name).read_bytes() for name in contract.DATA_FILES}
            dataset_base = f"{store.prefix}/datasets/{report['dataset_id']}"
            completion = {"state": "completed", "selection_id": selection, "dataset_id": report["dataset_id"],
                          "query_id": query_id, "sql_sha256": digest(sql.encode()),
                          "sql_parity": parity, "splits": {name: value["output"] for name, value in report["splits"].items()},
                          "dataset_prefix": dataset_base, "origins": origins,
                          "dataset_artifact_sha256": {name: digest(content) for name, content in bundle.items()}, **STATUS}
            # Completion is verified again on replay. Never repair a missing completed artifact.
            complete = store._get(f"{base}/complete.json", optional=True)
            if complete is not None:
                if json.loads(complete) != completion:
                    raise ContractError("Conflicting preparation completion receipt.")
                for name, content in bundle.items():
                    if store._get(f"{dataset_base}/{name}") != content:
                        raise ContractError("Completed dataset failed replay integrity verification.")
                return completion
            store._upload(dataset_base, bundle, "dataset_report.json")
            store._put(f"{base}/complete.json", encode(completion))
            return completion
    except Exception as exc:
        # Never include exception text: it can contain SDK details, paths, SQL or event contents.
        return {"state": "failed", "stage": stage, "selection_id": selection,
                "error_type": type(exc).__name__,
                "message": str(exc) if isinstance(exc, ContractError) else "Preparation stopped; existing evidence preserved.", **STATUS}


def handler(event, context):
    """Only execution-role clients; no dotenv, CFBD secret or local-history discovery."""
    try:
        contract.validate(event)
        recovery = os.environ.get("PREPARATION_RECOVERY_ONLY", "true")
        if recovery not in {"true", "false"}:
            raise ContractError("Configure recovery-only mode explicitly.")
        store = PreparationStore(None, os.environ.get("FBS_S3_BUCKET"), os.environ.get("FBS_S3_PREFIX"))
        store.client = boto3.client("s3", config=CLIENT_CONFIG)
        return prepare_run(event, store, boto3.client("athena", config=CLIENT_CONFIG),
                           database=os.environ["PREPARATION_DATABASE"], table="selected_games",
                           workgroup=os.environ["PREPARATION_WORKGROUP"], recovery_only=recovery == "true")
    except Exception as exc:
        return {"state": "failed", "stage": "request_or_configuration", "error_type": type(exc).__name__,
                "message": "Invalid request or cloud configuration; preparation not started.", **STATUS}
