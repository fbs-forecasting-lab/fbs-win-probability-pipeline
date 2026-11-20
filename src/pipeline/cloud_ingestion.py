"""Cloud-only capture adapter. No event data upload, dotenv lookup or model imports."""

import base64
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import re
import tempfile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.features.games import load_snapshot
from src.ingestion.cfbd import fetch_games, _validate_key
from src.ingestion.storage import save_snapshot
from src.ingestion.s3_storage import S3Store, MAX_OBJECT_BYTES
from src.pipeline.run_contract import ContractError, digest, encode, now, receipt, validate

# An ingestion request must never be automatically refetched after an ambiguous write.
CLIENT_CONFIG = Config(connect_timeout=5, read_timeout=15,
                       retries={"mode": "standard", "total_max_attempts": 1})
MAX_CAPTURE_BYTES = 16 * 1024 * 1024
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class CloudS3Store(S3Store):
    """Resolve optional absence through a prefix-scoped, exact-key list probe.

    GET has no Prefix request parameter. Do not assume prefix-conditioned
    ListBucket permission makes a missing GET return 404. An authorized list
    gives positive evidence of absence; a 403 from either operation stays fatal.
    """
    def _get(self, key, *, optional=False):
        if optional:
            allowed = (f"{self.prefix}/raw/cfbd/games/", f"{self.prefix}/cloud-ingestion/runs/")
            if not isinstance(key, str) or not key.startswith(allowed):
                raise ContractError("Optional read is outside cloud capture prefixes.")
            result = self.client.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
            if not any(item.get("Key") == key for item in result.get("Contents", [])):
                return None
        # If the listed object disappears or GET is forbidden, fail closed.
        return super()._get(key, optional=False)


def create_once(store, key, content):
    """Atomic creation, never read-then-write. 409/timeouts remain ambiguous failures."""
    if len(content) > MAX_OBJECT_BYTES:
        raise ContractError("Run object exceeds the bounded transfer limit.")
    try:
        store.client.put_object(Bucket=store.bucket, Key=key, Body=content, IfNoneMatch="*",
                                ChecksumSHA256=base64.b64encode(bytes.fromhex(digest(content))).decode(),
                                ContentType="application/json")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"PreconditionFailed", "412"}:
            return False
        raise
    if store._get(key) != content:
        raise ContractError("Run object readback failed integrity verification.")
    return True


def unpack_capture(content, request, directory):
    """Recreate cloud-temp files and use the existing snapshot verifier before use."""
    capture = json.loads(content)
    if capture["capture_version"] != 1 or capture["request"] != request:
        raise ContractError("Capture request does not match the claim.")
    manifest_bytes = base64.b64decode(capture["manifest"], validate=True)
    raw = base64.b64decode(capture["raw"], validate=True)
    manifest = json.loads(manifest_bytes)
    sid = manifest["snapshot_id"]
    if not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{32}", sid):
        raise ContractError("Capture snapshot identifier is invalid.")
    path = directory / f"{sid}.manifest.json"
    (directory / f"{sid}.json").write_bytes(raw)
    path.write_bytes(manifest_bytes)
    source = load_snapshot(path).source
    params = {"year": request["season"], "seasonType": "regular", "classification": "fbs"}
    if request["week"] is not None:
        params["week"] = request["week"]
    if source["request_parameters"] != params:
        raise ContractError("Captured source parameters do not match the request.")
    return path, source


def verified_facts(store, path, source, capture_content):
    """Verify both final objects by actual bytes, including on completed-token replay."""
    base = f"{store.prefix}/raw/cfbd/games/season={source['request_parameters']['year']}"
    raw_key, manifest_key = f"{base}/{source['raw_file']}", f"{base}/{path.name}"
    raw = store._get(raw_key)
    manifest = store._get(manifest_key)
    if raw != (path.parent / source["raw_file"]).read_bytes() or manifest != path.read_bytes():
        raise ContractError("Published pair failed integrity verification.")
    return {"raw_key": raw_key, "manifest_key": manifest_key,
            "raw_sha256": source["raw_sha256"], "manifest_sha256": source["manifest_sha256"],
            "capture_sha256": digest(capture_content), "retrieved_at": source["retrieved_at"],
            "record_count": json.loads(manifest)["record_count"],
            "source_availability": source["source_availability"]}


def capture_run(event, store, get_secret, *, fetch=fetch_games, clock=now):
    """One fetch-owner per token; immutable capture permits safe publication-only retries.

    No lease takeover: a claim without a capture never permits another fetch.
    A hard timeout may leave just that claim. Retry is observation/recovery only.
    """
    token_hash = request_hash = None
    owned = False
    stage = "request_validation"
    base = None
    try:
        request, token_hash, request_hash = validate(event)
        stage = "aws_preflight"
        store._private_bucket()
        base = f"{store.prefix}/cloud-ingestion/runs/{token_hash}"
        stage = "claim"
        started_at = clock()
        deadline_at = (datetime.fromisoformat(started_at.replace("Z", "+00:00")) + timedelta(seconds=210)).isoformat().replace("+00:00", "Z")
        claim_content = encode({"claim_version": 1, "request": request, "request_sha256": request_hash,
                                "token_sha256": token_hash, "started_at": started_at, "deadline_at": deadline_at})
        owned = create_once(store, f"{base}/claim.json", claim_content)
        claim = json.loads(store._get(f"{base}/claim.json"))
        if (claim["claim_version"] != 1 or claim["request"] != request
                or claim["request_sha256"] != request_hash or claim["token_sha256"] != token_hash):
            raise ContractError("Token is already bound to a different request.")
        started = claim["started_at"]
        stage = "capture_checkpoint"
        content = store._get(f"{base}/capture.json", optional=True)
        if content is None:
            if not owned:
                failure = store._get(f"{base}/failure.json", optional=True)
                # No timeout/lease heuristic can prove the original fetch did not happen.
                state = "failed" if failure else ("interrupted" if clock() >= claim["deadline_at"] else "in_progress")
                return receipt(state, token_hash, request_hash,
                               stage="capture_checkpoint", started_at=started,
                               message="No durable capture yet. Do not refetch this token; see recovery runbook.")
            stage = "secret_retrieval"
            key = _validate_key(get_secret())
            if not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", key):
                raise ContractError("SecretString must contain only the API key.")
            stage = "cfbd_fetch"
            LOGGER.info("cfbd_fetch_start token_sha256=%s request_sha256=%s", token_hash, request_hash)
            response = fetch(request["season"], request["week"], api_key=key, max_attempts=1)
            key = None
            if len(response.raw_response) > MAX_CAPTURE_BYTES:
                raise ContractError("Response exceeds the capture size limit.")
            stage = "capture_checkpoint"
            with tempfile.TemporaryDirectory(prefix="fbs-capture-") as tmp:
                raw_path, path = save_snapshot(response, Path(tmp))
                load_snapshot(path)
                content = encode({"capture_version": 1, "request": request,
                                  "raw": base64.b64encode(raw_path.read_bytes()).decode(),
                                  "manifest": base64.b64encode(path.read_bytes()).decode()})
            # A single atomic object contains BOTH files, so interrupted raw publication
            # can resume from exactly the original response, with no new API observation.
            store._put(f"{base}/capture.json", content)
        stage = "verify_capture"
        with tempfile.TemporaryDirectory(prefix="fbs-publish-") as tmp:
            path, source = unpack_capture(content, request, Path(tmp))
            stage = "completion_replay"
            completed = store._get(f"{base}/complete.json", optional=True)
            if completed is not None:
                facts = verified_facts(store, path, source, content)
                value = json.loads(completed)
                expected = receipt("completed", token_hash, request_hash, started_at=started, **facts)
                if value != expected | {"completed_at": value["completed_at"]}:
                    raise ContractError("Completion receipt does not match verified artifacts.")
                return value
            stage = "s3_upload_raw"
            store.upload_raw(path)
            stage = "verify_publication"
            facts = verified_facts(store, path, source, content)
            stage = "complete"
            value = receipt("completed", token_hash, request_hash, started_at=started,
                            completed_at=clock(), **facts)
            create_once(store, f"{base}/complete.json", encode(value))
            # Another recovery invocation may win completion; verify and return that
            # winner rather than report two different success receipts.
            winner = json.loads(store._get(f"{base}/complete.json"))
            if winner != value | {"completed_at": winner["completed_at"]}:
                raise ContractError("Conflicting completion receipt.")
            return winner
    except Exception:
        # Never interpolate events, SDK/HTTP errors, tokens, secret values or URLs.
        failure = receipt("failed", token_hash, request_hash, stage=stage,
                          message="Capture did not complete. Retry this token only to inspect/resume saved bytes; see runbook.")
        if owned and base is not None:
            try:
                create_once(store, f"{base}/failure.json", encode(failure | {"failed_at": clock()}))
            except Exception:
                pass  # The immutable claim still makes ambiguity visible; never refetch.
        return failure


def handler(event, context):
    """Lambda entry point: execution-role secret and SDK clients, no local .env."""
    try:
        validate(event)
        store = CloudS3Store(None, os.environ.get("FBS_S3_BUCKET"), os.environ.get("FBS_S3_PREFIX"))
        secret_id = os.environ.get("CFBD_SECRET_ARN", "")
        if not re.fullmatch(r"arn:[a-z0-9-]+:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:[A-Za-z0-9/_+=.@-]+", secret_id):
            raise ContractError("Configure one explicit CFBD secret ARN.")
        store.client = boto3.client("s3", config=CLIENT_CONFIG)
        def secret():
            client = boto3.client("secretsmanager", config=CLIENT_CONFIG)
            # SecretString must contain only the API key, not JSON or a Bearer header.
            return client.get_secret_value(SecretId=secret_id)["SecretString"]
        return capture_run(event, store, secret)
    except Exception:
        return receipt("failed", stage="request_or_configuration",
                       message="Invalid request or cloud configuration; no capture started.")
