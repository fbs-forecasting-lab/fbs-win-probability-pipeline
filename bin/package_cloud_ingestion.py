"""Build an allowlisted Python 3.14 Lambda ZIP; never upload application data."""

import argparse
import ast
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "src/__init__.py", "src/ingestion/__init__.py", "src/features/__init__.py", "src/pipeline/__init__.py",
    "src/ingestion/cfbd.py", "src/ingestion/storage.py", "src/ingestion/s3_storage.py",
    "src/features/games.py", "src/pipeline/run_contract.py", "src/pipeline/cloud_ingestion.py",
)


def validate_template():
    """Validate local structure/policy boundaries; not CloudFormation service validation."""
    template = json.loads((ROOT / "infra/cloud-ingestion.yaml").read_text())
    resources = template["Resources"]
    assert {r["Type"] for r in resources.values()} == {
        "AWS::Lambda::Function", "AWS::IAM::Role", "AWS::Logs::LogGroup", "AWS::Lambda::EventInvokeConfig"}
    fn = resources["Ingestion"]["Properties"]
    assert fn["Runtime"] == "python3.14" and fn["Timeout"] == 180
    assert fn["ReservedConcurrentExecutions"] == 1 and fn["Architectures"] == ["x86_64"]
    assert resources["AsyncPolicy"]["Properties"]["MaximumRetryAttempts"] == 0
    for entry in SOURCE_FILES:
        ast.parse((ROOT / entry).read_text())
    return template


def build(output):
    if sys.version_info[:2] != (3, 14):
        raise ValueError("Use the project's Python 3.14 environment.")
    out = Path(output).absolute()
    allowed = ROOT / "data/processed"
    if any(p.is_symlink() for p in (out, *out.parents)) or not out.resolve().is_relative_to(allowed.resolve()) or out.resolve() == allowed.resolve():
        raise ValueError("Select a new non-symlink output directory beneath data/processed.")
    validate_template()
    out.mkdir(parents=True, exist_ok=False)
    target = out / "dependencies"
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                    "--only-binary=:all:", "--platform", "manylinux2014_x86_64", "--implementation", "cp",
                    "--python-version", "3.14", "--abi", "cp314", "--no-compile", "--target", str(target),
                    "-r", str(ROOT / "infra/cloud-ingestion-requirements.txt")], check=True)
    versions = {d.metadata["Name"].lower().replace('_','-'): d.version
                for d in importlib.metadata.distributions(path=[str(target)])}
    expected = dict(line.split('==') for line in (ROOT / "infra/cloud-ingestion-requirements.txt").read_text().splitlines())
    if versions != expected:
        raise ValueError("Installed package closure does not match the pinned lightweight requirements.")
    zip_path = out / "cloud-ingestion.zip"
    with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCE_FILES:
            archive.write(ROOT / name, name)
        for path in sorted(target.rglob('*')):
            if path.is_file():
                name = path.relative_to(target).as_posix()
                if '__pycache__' not in name and not name.endswith('.pyc') and not name.startswith('bin/'):
                    archive.write(path, name)
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if any(n.startswith(('numpy/','pandas/','scipy/','sklearn/','jupyter/','tests/','data/','src/models/')) or '/.env' in n for n in names):
            raise ValueError("Unexpected private or training contents in package.")
    (out / "package-report.json").write_text(json.dumps({"runtime":"python3.14", "platform":"manylinux2014_x86_64",
        "versions":versions,"source_files":SOURCE_FILES,"zip_bytes":zip_path.stat().st_size,
        "uncompressed_bytes":sum(i.file_size for i in zipfile.ZipFile(zip_path).infolist()),
        "deployed":False}, indent=2)+'\n')
    print(f"Package: {zip_path.relative_to(ROOT)}")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.validate_only:
        validate_template(); print('Local template structure and source syntax: OK (not service validation)')
    elif args.output_dir:
        build(args.output_dir)
    else:
        parser.error('Select --validate-only or --output-dir.')


if __name__ == '__main__':
    main()
