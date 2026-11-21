"""Candidate managed-job entrypoint; reuses baseline training, never replaces a release."""
import json
import os
from pathlib import Path

from src.models import baseline
from src.pipeline.run_contract import STATUS, digest


def run(dataset_dir, model_dir, attempt_file, dataset_id, report_sha256, *, allow_retrospective_demo=False):
    """Verify a pinned SageMaker File channel and fit the existing baseline once.

    Inputs are the six dataset files already downloaded by the managed service,
    expected dataset/report identities, a fresh output and an exclusive attempt
    marker. Outputs are the normal model/evaluation artifacts. Holdout stays
    evaluation-only. A consumed attempt or existing output refuses another fit;
    failures preserve evidence. No SDK, network, credentials or dotenv is used.
    This candidate does not publish into the trusted cloud-modeling domain.
    """
    baseline.require_demo(allow_retrospective_demo)
    dataset_dir, model_dir, attempt_file = map(Path, (dataset_dir, model_dir, attempt_file))
    for value in (dataset_id, report_sha256):
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Select exact dataset and report identities.')
    if model_dir.is_symlink() or (model_dir.exists() and (not model_dir.is_dir() or any(model_dir.iterdir()))):
        raise ValueError('Model output must be a fresh empty directory.')
    if digest((dataset_dir/'dataset_report.json').read_bytes()) != report_sha256:
        raise ValueError('Pinned report hash differs; no fit.')
    data = baseline.load_dataset(dataset_dir, allow_retrospective_demo=True)
    if data['report']['dataset_id'] != dataset_id:
        raise ValueError('Pinned dataset identity differs; no fit.')
    attempt_file.parent.mkdir(parents=True, exist_ok=True)
    with attempt_file.open('x') as f:
        json.dump(dict(STATUS, dataset_id=dataset_id, report_sha256=report_sha256, attempt_consumed=True), f)
    return baseline.train_baseline(dataset_dir, model_dir, allow_retrospective_demo=True)


def main():
    """Use explicit reviewed job environment and standard SageMaker container paths."""
    run('/opt/ml/input/data/dataset', '/opt/ml/model', '/opt/ml/output/data/fit-attempt.json',
        os.environ['EXPECTED_DATASET_ID'], os.environ['EXPECTED_REPORT_SHA256'],
        allow_retrospective_demo=os.environ.get('ALLOW_RETROSPECTIVE_DEMO') == 'true')


if __name__ == '__main__':
    main()
