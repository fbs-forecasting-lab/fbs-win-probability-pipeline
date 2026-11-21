"""Offline PM-09A builders and an explicitly invoked, single-attempt controller.

Nothing here creates an SDK client, loads credentials, or runs on import. Policies
are standalone allowlists, not permission boundaries against other attached grants.
The log group must already exist. Image/runtime, quota, bucket freshness, IAM and
service-side retry behavior still need separate verification before approval.
"""

from dataclasses import dataclass
from functools import lru_cache
import hmac
import json
import os
from pathlib import Path
import re

from botocore.config import Config
from botocore.exceptions import ParamValidationError
from botocore.session import Session
from botocore.validate import validate_parameters

from src.pipeline.run_contract import ContractError, digest, encode

REGION = "us-east-1"
JOURNAL_GUARD = ".pm09a-submission-consumed.json"
DATA_FILES = ("train.csv", "holdout.csv", "prediction.csv",
              "team_season_aggregates.csv", "exclusions.json", "dataset_report.json")


def _match(value, pattern, field):
    """Reject placeholders, wildcards and non-string resource identities."""
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise ContractError(f"Invalid explicit {field}.")
    return value


@dataclass(frozen=True)
class TrainingSpec:
    """Pinned resources; image_digest is ``sha256:<64 lowercase hex digits>``.

    prefix is a nonempty, normalized S3 project prefix without a trailing slash.
    report_sha256 binds the container's existing dataset-report integrity guard.
    Role and repository names can be supplied explicitly; no resource is created.
    """

    account: str
    bucket: str
    prefix: str
    dataset_id: str
    image_digest: str
    job_name: str
    report_sha256: str
    role_name: str = "fbs-final-managed-training"
    repository: str = "fbs-final-training"

    def __post_init__(self):
        _match(self.account, r"[0-9]{12}", "account")
        # Deliberately support simple DNS bucket names only.
        _match(self.bucket, r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", "bucket")
        _match(self.prefix, r"[A-Za-z0-9][A-Za-z0-9._/-]*", "prefix")
        if any(part in ("", ".", "..") for part in self.prefix.split("/")):
            raise ContractError("Use a normalized project prefix.")
        for name in ("dataset_id", "report_sha256"):
            _match(getattr(self, name), r"[0-9a-f]{64}", name)
        _match(self.image_digest, r"sha256:[0-9a-f]{64}", "image digest")
        _match(self.job_name, r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", "job name")
        _match(self.role_name, r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", "role name")
        _match(self.repository, r"[a-z0-9]+(?:[._/-][a-z0-9]+)*", "repository")
        if len(self.repository) > 256 or len(self.prefix) > 512:
            raise ContractError("Resource path exceeds the contract limit.")

    @property
    def job_arn(self):
        """Return the single job resource authorized by this contract."""
        return f"arn:aws:sagemaker:{REGION}:{self.account}:training-job/{self.job_name}"

    @property
    def role_arn(self):
        """Return the one execution role that the caller may pass."""
        return f"arn:aws:iam::{self.account}:role/{self.role_name}"

    @property
    def dataset_prefix(self):
        """Return the exact File-channel listing prefix, including its slash."""
        return f"{self.prefix}/datasets/{self.dataset_id}/"

    @property
    def output_root(self):
        """Return the root to which SageMaker appends job/output artifact paths."""
        return f"{self.prefix}/final-readiness/managed-training"


def training_role_trust(spec):
    """Trust SageMaker only for this account and exact training-job source ARN."""
    return {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "sagemaker.amazonaws.com"},
        "Action": "sts:AssumeRole", "Condition": {
            "StringEquals": {"aws:SourceAccount": spec.account},
            "ArnEquals": {"aws:SourceArn": spec.job_arn}}}]}


def _allow(actions, resources, condition=None):
    """Build one allow statement with explicit resource scope."""
    statement = {"Effect": "Allow", "Action": actions, "Resource": resources}
    if condition is not None:
        statement["Condition"] = condition
    return statement


def training_role_policy(spec):
    """Allow six reads, exact dataset listing, quarantined puts, ECR and logs.

    Only GetAuthorizationToken requires a global resource. No CreateLogGroup,
    bucket-wide listing, input/protected-model writes, secrets or query/provider
    actions are granted. Log streams are limited to this job's sole instance.
    """
    bucket = f"arn:aws:s3:::{spec.bucket}"
    return {"Version": "2012-10-17", "Statement": [
        _allow(["s3:GetObject"], [bucket + "/" + spec.dataset_prefix + name for name in DATA_FILES]),
        _allow(["s3:ListBucket"], [bucket], {"StringEquals": {"s3:prefix": spec.dataset_prefix}}),
        _allow(["s3:GetBucketLocation"], [bucket]),
        _allow(["s3:PutObject"], [f"{bucket}/{spec.output_root}/{spec.job_name}/output/*"]),
        _allow(["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
               [f"arn:aws:ecr:{REGION}:{spec.account}:repository/{spec.repository}"]),
        _allow(["ecr:GetAuthorizationToken"], ["*"]),
        _allow(["logs:CreateLogStream", "logs:PutLogEvents"],
               [f"arn:aws:logs:{REGION}:{spec.account}:log-group:/aws/sagemaker/TrainingJobs:"
                f"log-stream:{spec.job_name}/algo-1-*"]),
    ]}


def caller_submission_policy(spec):
    """Allow only exact-job create/describe/stop and exact-role service PassRole."""
    return {"Version": "2012-10-17", "Statement": [
        _allow(["sagemaker:CreateTrainingJob", "sagemaker:DescribeTrainingJob", "sagemaker:StopTrainingJob"],
               [spec.job_arn], {"StringEquals": {"aws:RequestedRegion": REGION}}),
        _allow(["iam:PassRole"], [spec.role_arn],
               {"StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"}}),
    ]}


def managed_inference_policy(spec):
    """Read only this managed result and dataset; no trainer/legacy write access.

    The verifier receipt is outside the training role's writable output prefix.
    Its externally approved hash is bound by the new function configuration.
    Log groups must be created separately before deployment.
    """
    bucket = f"arn:aws:s3:::{spec.bucket}"
    base = f"{bucket}/{spec.output_root}/{spec.job_name}"
    return {"Version": "2012-10-17", "Statement": [
        _allow(["s3:GetObject"], [bucket + "/" + spec.dataset_prefix + n for n in DATA_FILES]
               + [base + "/output/model.tar.gz", base + "/verified/receipt.json"]),
        _allow(["s3:GetBucketPublicAccessBlock"], [bucket]),
        _allow(["logs:CreateLogStream", "logs:PutLogEvents"],
               [f"arn:aws:logs:{REGION}:{spec.account}:log-group:/aws/lambda/"
                "fbs-final-managed-inference:log-stream:*"]),
    ]}


def sdk_config():
    """Return offline SDK configuration: one total HTTP attempt in us-east-1."""
    return Config(region_name=REGION, retries={"mode": "standard", "total_max_attempts": 1})


def _request(spec):
    """Render the only supported training configuration from pinned identities."""
    return {
        "TrainingJobName": spec.job_name,
        "RoleArn": spec.role_arn,
        "AlgorithmSpecification": {
            "TrainingImage": f"{spec.account}.dkr.ecr.{REGION}.amazonaws.com/"
                             f"{spec.repository}@{spec.image_digest}",
            "TrainingInputMode": "File"},
        "InputDataConfig": [{"ChannelName": "dataset", "InputMode": "File", "DataSource": {
            "S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": f"s3://{spec.bucket}/{spec.dataset_prefix}",
                             "S3DataDistributionType": "FullyReplicated"}}}],
        "OutputDataConfig": {"S3OutputPath": f"s3://{spec.bucket}/{spec.output_root}"},
        "ResourceConfig": {"InstanceType": "ml.m5.large", "InstanceCount": 1, "VolumeSizeInGB": 5},
        "StoppingCondition": {"MaxRuntimeInSeconds": 300},
        "EnableNetworkIsolation": True,
        "EnableManagedSpotTraining": False,
        "ProfilerConfig": {"DisableProfiler": True},
        "Environment": {"EXPECTED_DATASET_ID": spec.dataset_id,
                        "EXPECTED_REPORT_SHA256": spec.report_sha256,
                        "ALLOW_RETROSPECTIVE_DEMO": "true"},
    }


@lru_cache(maxsize=1)
def _training_shape():
    """Load installed botocore metadata only; never create a client or credentials."""
    return Session().get_service_model("sagemaker").operation_model("CreateTrainingJob").input_shape


def _canonical(value):
    """Use the project's sorted compact UTF-8 JSON plus newline, with strict types."""
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ContractError("JSON object keys must be strings.")
        for item in value.values():
            _canonical(item)
    elif type(value) is list:
        for item in value:
            _canonical(item)
    elif type(value) not in (str, int, bool, type(None)):
        raise ContractError("Training requests require plain JSON without floating-point values.")
    return encode(value)


def request_sha256(request):
    """Hash exact canonical request bytes; this does not grant execution approval."""
    return digest(_canonical(request))


def validate_request(request, spec=None):
    """Validate SDK shape and every knob/identity offline; return a detached copy.

    An optional TrainingSpec pins identities before approval. Without it, identities
    are extracted and cross-checked; submit_once additionally requires the exact
    approved hash. Unknown optional keys are forbidden at every nesting level.
    RetryStrategy is deliberately absent (botocore's optional minimum is one).
    No pipeline, VPC, warm pool, debugger, checkpoint, profiler or Spot opt-in exists.
    """
    if type(request) is not dict:
        raise ContractError("Expected a training request object.")
    snapshot = json.loads(_canonical(request))
    try:
        validate_parameters(snapshot, _training_shape())
    except ParamValidationError:
        raise ContractError("Request fails the installed botocore training shape.") from None
    if spec is None:
        try:
            role = re.fullmatch(r"arn:aws:iam::([0-9]{12}):role/([A-Za-z0-9_-]+)", snapshot["RoleArn"])
            image = re.fullmatch(rf"{role[1]}\.dkr\.ecr\.{REGION}\.amazonaws\.com/"
                                 r"([a-z0-9._/-]+)@(sha256:[0-9a-f]{64})",
                                 snapshot["AlgorithmSpecification"]["TrainingImage"])
            source = snapshot["InputDataConfig"][0]["DataSource"]["S3DataSource"]["S3Uri"]
            location = re.fullmatch(r"s3://([^/]+)/(.+)/datasets/([0-9a-f]{64})/", source)
            spec = TrainingSpec(account=role[1], role_name=role[2], repository=image[1],
                                image_digest=image[2], bucket=location[1], prefix=location[2],
                                dataset_id=location[3], job_name=snapshot["TrainingJobName"],
                                report_sha256=snapshot["Environment"]["EXPECTED_REPORT_SHA256"])
        except (KeyError, IndexError, TypeError):
            raise ContractError("Missing or inconsistent pinned training identities.") from None
    if _canonical(snapshot) != _canonical(_request(spec)):
        raise ContractError("Request differs from the exact managed-training contract.")
    return snapshot


def build_training_request(spec):
    """Build and validate one bounded job, without any API or filesystem access."""
    return validate_request(_request(spec), spec)


def _consume_journal(journal, record):
    """Persist global-directory and named markers durably before any API call.

    Require an absolute, normalized path with existing parents on a durable local
    filesystem. Walk every parent using directory descriptors and O_NOFOLLOW;
    the final directory must be owned by this user and not writable by others.
    The fixed directory guard forbids switching journal filenames after ambiguity.
    Never overwrite, remove or repair either marker, even after write/fsync errors.
    Preserve this single protected directory across job names and restarts.
    """
    raw = os.fspath(journal)
    path = Path(raw)
    if (not path.is_absolute() or str(path) != raw or ".." in path.parts
            or path.name == JOURNAL_GUARD or path == Path("/")):
        raise ContractError("Use an absolute normalized journal path and a dedicated parent directory.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open("/", flags)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        info = os.fstat(directory)
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ContractError("Journal directory must be owned by this user and protected from other writers.")
        for name in (JOURNAL_GUARD, path.name):
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encode(record))
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
    finally:
        os.close(directory)


def submit_once(client, request, journal, approved_request_sha256):
    """Consume one durable journal before one explicit create_training_job call.

    The supplied client must use sdk_config's region and total_max_attempts=1;
    this function never constructs one. Validation/hash/config failures precede
    journal creation. Once created, the marker is consumed on success, exception,
    interruption or ambiguous outcome, including a new job name using that path.
    There is no reconciliation, retry, cleanup, or alternate-name fallback. The
    raw API response/exception is returned/propagated without changing the marker.
    A fixed guard also consumes the whole journal directory, blocking new filenames.
    This cannot prevent deliberate use of another/deleted directory or establish
    service-side no-retry behavior; neither is authorized here.
    """
    snapshot = validate_request(request)
    _match(approved_request_sha256, r"[0-9a-f]{64}", "approved request SHA-256")
    actual = request_sha256(snapshot)
    if not hmac.compare_digest(actual, approved_request_sha256):
        raise ContractError("Exact request hash is not approved; no submission.")
    config = getattr(getattr(client, "meta", None), "config", None)
    retries = getattr(config, "retries", None)
    if (not isinstance(config, Config) or config.region_name != REGION
            or type(retries) is not dict or type(retries.get("total_max_attempts")) is not int
            or retries["total_max_attempts"] != 1):
        raise ContractError("Client must use us-east-1 and total_max_attempts=1.")
    _consume_journal(journal, {"schema_version": 1, "attempt_consumed": True,
                              "request_sha256": actual, "job_name": snapshot["TrainingJobName"]})
    response = client.create_training_job(**snapshot)
    expected_arn = (f"arn:aws:sagemaker:{REGION}:{snapshot['RoleArn'].split(':')[4]}:"
                    f"training-job/{snapshot['TrainingJobName']}")
    if type(response) is not dict or response.get("TrainingJobArn") != expected_arn:
        raise ContractError("Submission returned an unexpected job ARN; attempt remains consumed.")
    return response
