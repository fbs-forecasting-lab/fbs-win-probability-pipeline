"""Explicit source selection and fail-closed eligibility for cloud preparation."""

from datetime import datetime
import json
from pathlib import Path
import re

from src.features import dataset, games
from src.pipeline.run_contract import ContractError, digest, encode

SQL_PATH = Path(__file__).with_name("prior_season_features.sql")
COMPATIBILITY_PATH = Path(__file__).with_name("preparation_identity_v1.json")
LEGACY_IMPLEMENTATION_SHA256 = "e583b79e8bef1e2c1d13adf25a6c595eb67ae569bd9a190a86b9c48f46d18725"
DATA_FILES = ("train.csv", "holdout.csv", "prediction.csv", "team_season_aggregates.csv",
              "exclusions.json", "dataset_report.json")


def validate(event):
    """Select exactly one hashed manifest per season; reject unknown request fields."""
    required = {"schema_version", "sources", "allow_retrospective_demo", "require_cloud_sources"}
    if not isinstance(event, dict) or not required <= event.keys() or event.keys() - required - {"forecast_cutoff"}:
        raise ContractError("Expected explicit sources, schema version and retrospective/cloud-source permissions.")
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ContractError("Expected preparation schema version 1.")
    if event["allow_retrospective_demo"] is not True:
        raise ContractError("Explicit retrospective-demo permission is required.")
    if type(event["require_cloud_sources"]) is not bool:
        raise ContractError("Cloud-source requirement must be a boolean.")
    if "forecast_cutoff" in event:
        games._utc_timestamp(event["forecast_cutoff"])
    if not isinstance(event["sources"], list) or len(event["sources"]) != 6:
        raise ContractError("Missing required seasons: select exactly one source for each season 2021–2026.")
    selected = {}
    for source in event["sources"]:
        fields = {"season", "manifest_name", "raw_sha256", "manifest_sha256"}
        if (not isinstance(source, dict) or not fields <= source.keys()
                or source.keys() - fields - {"capture_token_sha256", "capture_receipt_sha256"}):
            raise ContractError("Source must identify a season, manifest and both expected SHA-256 hashes.")
        season = source["season"]
        if type(season) is not int or season not in dataset.SEASONS or season in selected:
            raise ContractError("Duplicate or unsupported season; select exactly one snapshot per season 2021–2026.")
        if not isinstance(source["manifest_name"], str) or not re.fullmatch(r"[0-9a-f]{32}\.manifest\.json", source["manifest_name"]):
            raise ContractError("Select a manifest filename, not a path.")
        has_receipt = "capture_token_sha256" in source
        if has_receipt != ("capture_receipt_sha256" in source) or (event["require_cloud_sources"] and not has_receipt):
            raise ContractError("Graded cloud preparation requires a verified ingestion receipt for every season.")
        for field in fields - {"season", "manifest_name"} | (source.keys() - fields):
            if not isinstance(source[field], str) or not re.fullmatch(r"[0-9a-f]{64}", source[field]):
                raise ContractError("Expected lowercase SHA-256 source identities.")
        selected[season] = dict(source)
    return {**event, "sources": [selected[year] for year in dataset.SEASONS]}


def implementation_hash():
    """Retain v1 identity only for the explicitly pinned query-verification correction.

    Runtime source bytes must match the packaged compatibility record. Original
    source hashes remain anchored to the deployed implementation, so request,
    selection and query-token identities do not change during this recovery.
    A later source change must not silently inherit this compatibility bridge.
    """
    root = Path(__file__).resolve().parents[1]
    paths = [Path(dataset.__file__), Path(games.__file__), Path(__file__), SQL_PATH,
             Path(__file__).with_name("cloud_preparation.py"), Path(__file__).with_name("run_contract.py"),
             Path(__file__).with_name("cloud_ingestion.py"), root / "ingestion/s3_storage.py",
             root / "ingestion/storage.py"]
    actual = {p.name: digest(p.read_bytes()) for p in paths}
    record = json.loads(COMPATIBILITY_PATH.read_bytes(), object_pairs_hook=games._unique_keys)
    original = record.get("identity_source_sha256")
    runtime = record.get("runtime_source_sha256")
    if (record.get("compatibility_version") != 1 or not isinstance(original, dict)
            or not isinstance(runtime, dict) or original.keys() != actual.keys()
            or runtime != actual or digest(encode(original)) != LEGACY_IMPLEMENTATION_SHA256
            or {name for name in actual if actual[name] != original[name]}
            != {"cloud_preparation.py", "preparation_contract.py"}):
        raise ContractError("Preparation source compatibility check failed; no query identity can be reused.")
    return LEGACY_IMPLEMENTATION_SHA256


def selection_id(request, database, table, workgroup):
    return digest(encode({"request": request, "implementation_sha256": implementation_hash(),
                          "database": database, "table": table, "workgroup": workgroup}))


def eligibility(source, cutoff):
    """A cutoff is a request to assess operational eligibility, never an approval switch."""
    if cutoff is None:
        return
    instant = datetime.fromisoformat(games._utc_timestamp(cutoff))
    observed = datetime.fromisoformat(games._utc_timestamp(source["retrieved_at"]))
    available = source["source_availability"].get("available_at")
    if observed >= instant or (available and datetime.fromisoformat(games._utc_timestamp(available)) >= instant):
        raise ContractError("Operational input was observed or published at/after the forecast cutoff.")
    # Even early capture is not evidence of actual completion/publication or schedule versions.
    raise ContractError("Operational eligibility is unverified; only retrospective preparation is supported.")


def query(selection, database, table):
    for name in (database, table):
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
            raise ContractError("Select fixed lowercase catalog identifiers.")
    if not re.fullmatch(r"[0-9a-f]{64}", selection):
        raise ContractError("Invalid selection identity.")
    return SQL_PATH.read_text().replace("__TABLE__", f"{database}.{table}").replace("__SELECTION__", selection)
