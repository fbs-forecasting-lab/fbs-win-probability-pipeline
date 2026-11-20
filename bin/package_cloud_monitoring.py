"""Build the private monitoring/review package; never deploy or include data."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('weekly_packaging',ROOT/'bin/package_cloud_weekly.py')
weekly=importlib.util.module_from_spec(spec);spec.loader.exec_module(weekly)
SOURCE_FILES=(*weekly.SOURCE_FILES,*(f'src/pipeline/{n}.py' for n in
    ('monitor_contract','monitoring_metrics','monitor_storage','monitoring_view','cloud_monitoring','cloud_review')))


def validate_template():
    template=json.loads((ROOT/'infra/cloud-monitoring.yaml').read_text());r=template['Resources']
    assert len(r)==14 and r['FailureRule']['Properties']['State']=='DISABLED'
    for n in ('Monitor','Review'):
        assert r[n]['Properties']['Runtime']=='python3.14' and r[n]['Properties']['ReservedConcurrentExecutions']==1
        assert r[n+'Async']['Properties']['MaximumRetryAttempts']==0
    for item in r.values():
        if item['Type']=='AWS::CloudWatch::Alarm':
            assert item['Properties']['ActionsEnabled'] is False and not item['Properties']['AlarmActions']
    return template


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true');parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--dependencies-dir',type=Path)
    args=parser.parse_args();validate_template()
    if args.validate_only:print('Monitoring template local invariants: OK; not deployed')
    elif args.output_dir:
        packaging=weekly.packaging;packaging.SOURCE_FILES=SOURCE_FILES;packaging.validate_template=validate_template
        path=packaging.build(args.output_dir,args.dependencies_dir);path.rename(path.with_name('cloud-monitoring.zip'))
    else:parser.error('Select --validate-only or a new --output-dir.')


if __name__=='__main__':main()
