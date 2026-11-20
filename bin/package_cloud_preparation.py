"""Build the small Python 3.14 preparation Lambda; never deploy or include source data."""

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("capture_packaging", ROOT / "bin/package_cloud_ingestion.py")
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)
SOURCE_FILES = (*packaging.SOURCE_FILES, "src/features/dataset.py", "src/pipeline/preparation_contract.py",
                "src/pipeline/cloud_preparation.py", "src/pipeline/prior_season_features.sql",
                "src/pipeline/preparation_identity_v1.json")


def validate_template():
    """Local invariants only; cfn-lint and service validation are separate checks."""
    template = json.loads((ROOT / "infra/cloud-preparation.yaml").read_text())
    resources = template["Resources"]
    assert len(resources) == 7
    function = resources["Preparation"]["Properties"]
    assert function["Runtime"] == "python3.14" and function["Architectures"] == ["x86_64"]
    assert function["ReservedConcurrentExecutions"] == 1
    assert resources["AsyncPolicy"]["Properties"]["MaximumRetryAttempts"] == 0
    assert resources["Workgroup"]["Properties"]["WorkGroupConfiguration"]["BytesScannedCutoffPerQuery"] == 134217728
    assert function["Environment"]["Variables"]["PREPARATION_RECOVERY_ONLY"] == "true"
    statements = resources["ExecutionRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    assert any(s["Effect"] == "Deny" and "athena:StartQueryExecution" in s["Action"] for s in statements)
    from src.pipeline.preparation_contract import implementation_hash
    implementation_hash()
    for path in SOURCE_FILES:
        if path.endswith('.py'):
            ast.parse((ROOT / path).read_text())
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.validate_only:
        validate_template()
        print('Local preparation template and source syntax: OK (not service validation)')
    elif args.output_dir:
        packaging.build(args.output_dir, source_files=SOURCE_FILES,
                        template_validator=validate_template, archive_name='cloud-preparation.zip')
    else:
        parser.error('Select --validate-only or --output-dir.')


if __name__ == '__main__':
    main()
