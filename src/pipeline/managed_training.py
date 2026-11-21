"""Candidate managed-job entrypoint; reuses baseline training, never replaces a release."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

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
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
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
        f.flush()
        os.fsync(f.fileno())
    return baseline.train_baseline(dataset_dir, model_dir, allow_retrospective_demo=True)


def main(argv=None):
    """Accept SageMaker's appended ``train`` argument and fail without a traceback.

    File-channel paths are fixed; SDK-specific SM_* variables are unnecessary.
    SIGTERM produces a nonzero exit and a sanitized failure description. A
    completion is written only after successful training/reload verification.
    The retained attempt prevents another fit after an interrupted local run;
    the separate submission journal prevents resubmitting the managed job.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='train', choices=('train',))
    parser.parse_args(argv)
    output = Path('/opt/ml/output')
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    old_handler = signal.signal(signal.SIGTERM, terminate)
    try:
        metadata, evaluation = run(
            '/opt/ml/input/data/dataset', '/opt/ml/model', output/'data/fit-attempt.json',
            os.environ['EXPECTED_DATASET_ID'], os.environ['EXPECTED_REPORT_SHA256'],
            allow_retrospective_demo=os.environ.get('ALLOW_RETROSPECTIVE_DEMO') == 'true')
        model_dir = Path('/opt/ml/model')
        completion = dict(STATUS, state='completed', dataset_id=metadata['dataset_id'],
                          versions=metadata['versions'], counts=metadata['counts'],
                          artifact_sha256={p.name: digest(p.read_bytes()) for p in sorted(model_dir.iterdir())})
        with (output/'data/training-complete.json').open('x') as f:
            json.dump(completion, f, sort_keys=True)
        print('Managed training completed; retrospective approval remains withheld.')
        return 0
    except BaseException as exc:
        message = 'Managed training stopped: ' + type(exc).__name__ + '; evidence preserved.'
        output.mkdir(parents=True, exist_ok=True)
        try:
            with (output/'failure').open('x') as f:
                f.write(message)
        except FileExistsError:
            pass
        print(message, file=sys.stderr)
        return 143 if isinstance(exc, SystemExit) and exc.code == 143 else 1
    finally:
        signal.signal(signal.SIGTERM, old_handler)


if __name__ == '__main__':
    raise SystemExit(main())
