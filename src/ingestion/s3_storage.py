"""Explicit, no-overwrite S3 transfers for raw snapshots and demo datasets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import dotenv_values

from src.features import dataset, games
from src.ingestion.storage import PROJECT_ROOT
from src.models.baseline import DATA_FILES, BaselineError, load_dataset, read_json, require_demo

MAX_OBJECT_BYTES = 64 * 1024 * 1024
PUBLIC_BLOCK_FLAGS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
SDK_CONFIG = Config(connect_timeout=5, read_timeout=30,
                    retries={"mode": "standard", "total_max_attempts": 3})


class S3StorageError(ValueError):
    """Sanitized transfer, configuration, or integrity failure."""


def _aws_error(exc):
    """Never include service messages, request headers, or exception details."""
    code = exc.response.get("Error", {}).get("Code", "") if isinstance(exc, ClientError) else type(exc).__name__
    if code in {"NoCredentialsError", "PartialCredentialsError", "CredentialRetrievalError"}:
        return S3StorageError("AWS credentials are missing or incomplete; configure the standard SDK credential chain.")
    if code in {"ExpiredToken", "ExpiredTokenException", "InvalidToken", "InvalidClientTokenId", "TokenRefreshRequired",
                "SSOTokenLoadError", "UnauthorizedSSOTokenError", "TokenRetrievalError", "InvalidAccessKeyId",
                "SignatureDoesNotMatch"}:
        return S3StorageError("AWS credentials or SSO session expired/invalid; refresh the selected session.")
    if code in {"AccessDenied", "AccessDeniedException", "403", "Forbidden"}:
        return S3StorageError("AWS access denied; check permissions for the selected bucket/prefix and encryption key.")
    if code in {"NoSuchKey", "NotFound", "404"}:
        return S3StorageError("Required S3 object is missing; the upload may be incomplete.")
    if code == "NoSuchBucket":
        return S3StorageError("The selected S3 bucket does not exist; no bucket was created.")
    if code == "ProfileNotFound":
        return S3StorageError("The selected AWS profile is not configured.")
    if code in {"ConditionalRequestConflict", "409"}:
        return S3StorageError("Concurrent S3 write conflict; rerun to verify existing bytes. Nothing is overwritten.")
    if code in {"PermanentRedirect", "AuthorizationHeaderMalformed", "IllegalLocationConstraintException"}:
        return S3StorageError("S3 bucket region does not match the selected region.")
    if code in {"EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError", "ConnectionClosedError"}:
        return S3StorageError("AWS connection or read failed after bounded SDK attempts; check network access.")
    return S3StorageError("AWS operation failed; verify session, region, permissions, and network. Details suppressed.")


def make_client(region=None, profile=None):
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        if not session.region_name:
            raise S3StorageError("Select the project bucket's AWS region with --region or SDK configuration.")
        # SDK handles environment credentials, profiles, SSO, roles and session
        # tokens. Credentials are never copied into application configuration.
        return session.client("s3", config=SDK_CONFIG)
    except (BotoCoreError, ClientError) as exc:
        raise _aws_error(exc) from None


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _dataset_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise S3StorageError("Dataset ID must be a lowercase SHA-256 identifier, not a path.")
    return value


class S3Store:
    def __init__(self, client, bucket, prefix):
        if (not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket)
                or ".." in bucket or bucket.endswith("--x-s3") or re.fullmatch(r"\d+\.\d+\.\d+\.\d+", bucket)):
            raise S3StorageError("Select an explicit general-purpose project bucket name with --bucket.")
        if (not isinstance(prefix, str) or len(prefix) > 400 or not prefix
                or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", part) for part in prefix.split("/"))):
            raise S3StorageError("Select a nonempty project prefix: slash-separated letters, digits, underscores or hyphens.")
        self.client, self.bucket, self.prefix = client, bucket, prefix

    def _private_bucket(self):
        try:
            response = self.client.get_public_access_block(Bucket=self.bucket)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "NoSuchPublicAccessBlockConfiguration":
                raise S3StorageError("Bucket-level Block Public Access is absent; private-storage check failed. No settings changed.") from None
            raise _aws_error(exc) from None
        except BotoCoreError as exc:
            raise _aws_error(exc) from None
        flags = response.get("PublicAccessBlockConfiguration", {})
        if any(flags.get(name) is not True for name in PUBLIC_BLOCK_FLAGS):
            raise S3StorageError("All four bucket-level Block Public Access settings must be enabled. No settings changed.")

    def _get(self, key, *, optional=False):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                if response.get("ContentLength", 0) > MAX_OBJECT_BYTES:
                    raise S3StorageError("Object exceeds this demo's 64 MiB transfer limit.")
                content = body.read(MAX_OBJECT_BYTES + 1)
                if len(content) > MAX_OBJECT_BYTES:
                    raise S3StorageError("Object exceeds this demo's 64 MiB transfer limit.")
                if "ContentLength" in response and len(content) != response["ContentLength"]:
                    raise S3StorageError("Downloaded object length is inconsistent; no local dataset published.")
                return content
            finally:
                body.close()
        except ClientError as exc:
            if optional and exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "NotFound", "404"}:
                return None
            raise _aws_error(exc) from None
        except BotoCoreError as exc:
            raise _aws_error(exc) from None

    def _put(self, key, content):
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content, IfNoneMatch="*",
                                   ChecksumSHA256=base64.b64encode(hashlib.sha256(content).digest()).decode("ascii"),
                                   ContentType="text/csv" if key.endswith(".csv") else "application/json")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"PreconditionFailed", "412"}:
                raise _aws_error(exc) from None
            # Another writer may have created this object after preflight.
            # Reuse only matching actual bytes; never retry unconditionally.
            if self._get(key) != content:
                raise S3StorageError("Conflicting remote content; existing object preserved.") from None
            return "reused"
        except BotoCoreError as exc:
            raise _aws_error(exc) from None
        if self._get(key) != content:
            raise S3StorageError("Uploaded object readback failed integrity verification.")
        return "uploaded"

    def _upload(self, base, artifacts, marker):
        if any(len(content) > MAX_OBJECT_BYTES for content in artifacts.values()):
            raise S3StorageError("Local artifact exceeds this demo's 64 MiB transfer limit.")
        self._private_bucket()
        # Preflight all objects before any write, including the marker. A
        # complete but inconsistent bundle is never silently repaired.
        existing = {name: self._get(f"{base}/{name}", optional=True) for name in artifacts}
        for name, content in existing.items():
            if content is not None and content != artifacts[name]:
                raise S3StorageError("Conflicting remote content; no objects replaced.")
        if existing[marker] is not None and any(content is None for content in existing.values()):
            raise S3StorageError("Existing completion marker references missing objects; bundle is incomplete.")
        result = {}
        for name in [name for name in artifacts if name != marker] + [marker]:
            key = f"{base}/{name}"
            result[f"s3://{self.bucket}/{key}"] = "reused" if existing[name] is not None else self._put(key, artifacts[name])
        return result

    def upload_raw(self, manifest_path):
        try:
            path = Path(manifest_path)
            snapshot = games.load_snapshot(path)
            source = snapshot.source
            raw = (path.parent / source["raw_file"]).read_bytes()
            manifest = path.read_bytes()
            if _sha(raw) != source["raw_sha256"] or _sha(manifest) != source["manifest_sha256"]:
                raise S3StorageError("Local snapshot changed during validation.")
        except (games.NormalizationError, OSError) as exc:
            raise S3StorageError("Local raw snapshot/manifest failed existing integrity validation.") from None
        sid = source["snapshot_id"]
        marker = f"{sid}.manifest.json"
        base = f"{self.prefix}/raw/cfbd/games/season={source['request_parameters']['year']}"
        return self._upload(base, {f"{sid}.json": raw, marker: manifest}, marker)

    def upload_dataset(self, directory, *, allow_retrospective_demo=False):
        try:
            data = load_dataset(directory, allow_retrospective_demo=allow_retrospective_demo)
            report = (Path(directory) / "dataset_report.json").read_bytes()
            if _sha(report) != data["report_sha256"]:
                raise S3StorageError("Local dataset report changed during validation.")
        except (BaselineError, OSError):
            raise S3StorageError("Local dataset failed validation; verify inputs and pass --allow-retrospective-demo.") from None
        identifier = _dataset_id(data["report"]["dataset_id"])
        artifacts = data["artifacts"] | {"dataset_report.json": report}
        return self._upload(f"{self.prefix}/datasets/{identifier}", artifacts, "dataset_report.json")

    def download_dataset(self, identifier, output_dir, *, allow_retrospective_demo=False):
        try:
            require_demo(allow_retrospective_demo)
        except BaselineError:
            raise S3StorageError("Pass --allow-retrospective-demo; historical availability remains unverified.") from None
        identifier = _dataset_id(identifier)
        self._private_bucket()
        base = f"{self.prefix}/datasets/{identifier}"
        report_bytes = self._get(f"{base}/dataset_report.json")
        try:
            report = read_json(report_bytes)
        except BaselineError:
            raise S3StorageError("Remote dataset report is invalid JSON.") from None
        hashes = report.get("artifact_sha256")
        if (report.get("dataset_id") != identifier or not isinstance(hashes, dict) or set(hashes) != DATA_FILES
                or any(not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in hashes.values())):
            raise S3StorageError("Remote dataset identity, artifact filenames, or hashes are unsafe/invalid.")
        # Only fixed allowlisted filenames ever become paths. No directory is
        # published until every byte hash and the existing loader both pass.
        artifacts = {}
        for name in sorted(DATA_FILES):
            content = self._get(f"{base}/{name}")
            if _sha(content) != hashes[name]:
                raise S3StorageError("Downloaded artifact SHA-256 mismatch; no local dataset published.")
            artifacts[name] = content
        artifacts["dataset_report.json"] = report_bytes
        try:
            with tempfile.TemporaryDirectory(prefix="fbs-s3-verify-") as temporary:
                staging = Path(temporary)
                for name, content in artifacts.items():
                    (staging / name).write_bytes(content)
                load_dataset(staging, allow_retrospective_demo=True)
            dataset._publish(Path(output_dir), artifacts)
        except (BaselineError, dataset.DatasetError, OSError):
            raise S3StorageError("Downloaded dataset validation or local publication failed; existing files preserved.") from None
        return {"dataset_id": identifier, "s3_location": f"s3://{self.bucket}/{base}/",
                "output_dir": str(Path(output_dir).resolve()), "verified_files": len(artifacts),
                "dataset_report_sha256": _sha(report_bytes), "dataset_mode": "retrospective_demo",
                "historical_availability_verified": False, "approved_for_point_in_time_forecasting": False}


def configuration():
    # Read only nonsecret project settings. AWS credentials are left entirely
    # to boto3's standard chain, including AWS_SESSION_TOKEN when needed.
    local = dotenv_values(PROJECT_ROOT / ".env")
    return {name: os.environ.get(name, local.get(name)) or None
            for name in ("FBS_S3_BUCKET", "FBS_S3_REGION", "FBS_S3_PREFIX", "FBS_AWS_PROFILE")}


def main(argv=None):
    defaults = configuration()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("upload-raw", "upload-dataset", "download-dataset"):
        command = commands.add_parser(name)
        command.add_argument("--bucket", default=defaults["FBS_S3_BUCKET"])
        command.add_argument("--prefix", default=defaults["FBS_S3_PREFIX"])
        command.add_argument("--region", default=defaults["FBS_S3_REGION"])
        command.add_argument("--profile", default=defaults["FBS_AWS_PROFILE"])
        if name == "upload-raw":
            command.add_argument("--manifest", type=Path, required=True)
        else:
            command.add_argument("--allow-retrospective-demo", action="store_true")
            if name == "upload-dataset":
                command.add_argument("--dataset-dir", type=Path, required=True)
            else:
                command.add_argument("--dataset-id", required=True)
                command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        store = S3Store(None, args.bucket, args.prefix)  # Fail missing configuration without contacting AWS.
        store.client = make_client(args.region, args.profile)
        if args.command == "upload-raw":
            result = store.upload_raw(args.manifest)
        elif args.command == "upload-dataset":
            result = store.upload_dataset(args.dataset_dir, allow_retrospective_demo=args.allow_retrospective_demo)
        else:
            result = store.download_dataset(args.dataset_id, args.output_dir,
                                            allow_retrospective_demo=args.allow_retrospective_demo)
    except S3StorageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
