"""Package the weekly worker with the reviewed modeling dependency closure; never deploy."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('model_packaging', ROOT/'bin/package_cloud_modeling.py')
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)
SOURCE_FILES = (*packaging.SOURCE_FILES, 'src/pipeline/cloud_preparation.py', 'src/pipeline/preparation_contract.py',
                'src/pipeline/prior_season_features.sql', 'src/pipeline/preparation_identity_v1.json',
                'src/pipeline/weekly_contract.py', 'src/pipeline/cloud_weekly.py')


def validate_template():
    template = json.loads((ROOT/'infra/cloud-weekly.yaml').read_text())
    resources = template['Resources']
    assert len(resources) == 8
    assert resources['Schedule']['Properties']['State'] == 'DISABLED'
    assert resources['Schedule']['Properties']['Target']['RetryPolicy']['MaximumRetryAttempts'] == 0
    assert resources['Weekly']['Properties']['Runtime'] == 'python3.14'
    assert resources['Weekly']['Properties']['RuntimeManagementConfig']['UpdateRuntimeOn'] == 'FunctionUpdate'
    assert resources['WeeklyAsync']['Properties']['MaximumRetryAttempts'] == 0
    states = resources['Workflow']['Properties']['Definition']['States']
    assert 'Retry' not in states['Advance'] and states['Budget']['Choices'][0]['NumericGreaterThanEquals'] == 7
    assert states['Wait']['Seconds'] == 15 and states['Advance']['TimeoutSeconds'] == 310
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--dependencies-dir', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    validate_template()
    if args.validate_only:
        print('Weekly template invariants: OK; not deployed')
    elif args.output_dir:
        packaging.SOURCE_FILES = SOURCE_FILES
        packaging.validate_template = validate_template
        archive = packaging.build(args.output_dir, args.dependencies_dir)
        archive.rename(archive.with_name('cloud-weekly.zip'))
    else:
        parser.error('Select --validate-only or a new --output-dir.')


if __name__ == '__main__':
    main()
