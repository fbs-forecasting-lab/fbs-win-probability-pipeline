"""Package the private explanation/benchmark adapters; no deployment or external calls."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('monitor_package',ROOT/'bin/package_cloud_monitoring.py')
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)
SOURCE_FILES=(*monitor.SOURCE_FILES,'src/pipeline/insights_contract.py','src/pipeline/insights_storage.py','src/pipeline/explanation_facts.py',
 'src/pipeline/cloud_explanation.py','src/ingestion/odds.py','src/features/markets.py','src/pipeline/cloud_benchmark.py')

def validate_template():
    t=json.loads((ROOT/'infra/cloud-stakeholder.yaml').read_text());r=t['Resources'];assert len(r)==8
    assert not any(v['Type'].startswith(('AWS::Events','AWS::Scheduler','AWS::SNS')) for v in r.values())
    for n in ('Explanation','Benchmark'):
        p=r[n]['Properties'];assert p['Runtime']=='python3.14' and p['Architectures']==['x86_64'] and p['ReservedConcurrentExecutions']==1
        assert r[n+'Async']['Properties']['MaximumRetryAttempts']==0
    for n in SOURCE_FILES:
        if n.endswith('.py'):ast.parse((ROOT/n).read_text())
    return t

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--dependencies-dir',type=Path)
    a=parser.parse_args();validate_template()
    if a.validate_only:print('Eight-resource stakeholder template and 37 project files validated; not deployed.')
    elif a.output_dir:
        pack=monitor.weekly.packaging;pack.SOURCE_FILES=SOURCE_FILES;pack.validate_template=validate_template
        path=pack.build(a.output_dir,a.dependencies_dir);path.rename(path.with_name('cloud-stakeholder.zip'))
    else:parser.error('Select --validate-only or a new --output-dir.')
if __name__=='__main__':main()
