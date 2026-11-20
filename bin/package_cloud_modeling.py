"""Build a bounded Linux Python 3.14 Lambda ZIP without data or production fitting."""

import argparse
import ast
import importlib.metadata
import json
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ('src/__init__.py','src/models/__init__.py','src/features/__init__.py',
 'src/ingestion/__init__.py','src/pipeline/__init__.py','src/evaluation/__init__.py',
 'src/models/baseline.py','src/models/predict.py','src/evaluation/metrics.py',
 'src/features/dataset.py','src/features/games.py','src/ingestion/storage.py',
 'src/ingestion/cfbd.py','src/ingestion/s3_storage.py','src/pipeline/cloud_ingestion.py',
 'src/pipeline/run_contract.py','src/pipeline/model_contract.py','src/pipeline/cloud_modeling.py')
LIMIT = 250 * 1024 * 1024


def include_dependency(name):
    """Exclude only bundled tests/bytecode and pip-created command entry points."""
    parts = Path(name).parts
    return not any(p in ('tests','test','__pycache__') for p in parts) and not name.endswith('.pyc') and not name.startswith('bin/')


def validate_template():
    template = json.loads((ROOT/'infra/cloud-modeling.yaml').read_text())
    resources = template['Resources']
    assert len(resources) == 8
    for name in ('Training','Inference'):
        props = resources[name]['Properties']
        assert props['Runtime']=='python3.14' and props['Architectures']==['x86_64']
        assert props['ReservedConcurrentExecutions']==1 and props['Timeout']<=180
        assert resources[name+'Async']['Properties']['MaximumRetryAttempts']==0
    for name in SOURCE_FILES: ast.parse((ROOT/name).read_text())
    return template


def build(output, dependencies=None):
    if sys.version_info[:2] != (3,14): raise ValueError('Use Python 3.14.')
    validate_template()
    output = Path(output).absolute()
    if (any(p.is_symlink() for p in (output,*output.parents)) or output.exists()
            or not output.resolve().is_relative_to((ROOT/'data/processed').resolve())
            or output.resolve()==(ROOT/'data/processed').resolve()):
        raise ValueError('Select a new non-symlink ignored output directory under data/processed.')
    output.mkdir(parents=True,exist_ok=False)
    target = Path(dependencies) if dependencies else output/'dependencies'
    if dependencies is None:
        subprocess.run([sys.executable,'-m','pip','install','--only-binary=:all:',
            '--platform','manylinux_2_28_x86_64','--platform','manylinux2014_x86_64',
            '--implementation','cp','--python-version','3.14','--abi','cp314','--no-compile',
            '--target',str(target),'-r',str(ROOT/'infra/cloud-modeling-requirements.txt')],check=True)
    versions = {d.metadata['Name'].lower().replace('_','-'):d.version
                for d in importlib.metadata.distributions(path=[str(target)])}
    expected = dict(line.split('==') for line in (ROOT/'infra/cloud-modeling-requirements.txt').read_text().splitlines())
    if versions != expected: raise ValueError('Dependency closure differs from exact pins.')
    files = sorted(p for p in target.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in files): raise ValueError('Dependency links are not supported.')
    selected = [p for p in files if include_dependency(p.relative_to(target).as_posix())]
    native = []
    for path in selected:
        if '.so' in path.name:
            header = path.read_bytes()[:20]
            if header[:4]!=b'\x7fELF' or header[4:6]!=b'\x02\x01' or struct.unpack('<H',header[18:20])[0]!=62:
                raise ValueError('Native extension is not ELF64 little-endian Linux x86_64.')
            native.append(path.relative_to(target).as_posix())
    if not native: raise ValueError('Expected Linux native numeric dependencies.')
    size = sum(p.stat().st_size for p in selected)+sum((ROOT/n).stat().st_size for n in SOURCE_FILES)
    if size > LIMIT: raise ValueError('ZIP plus dependencies exceed Lambda uncompressed limit; do not deploy.')
    archive_path = output/'cloud-modeling.zip'
    with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCE_FILES: archive.write(ROOT/name,name)
        for path in selected: archive.write(path,path.relative_to(target).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert sum(i.file_size for i in archive.infolist())==size
        assert all(archive.read(n)==(ROOT/n).read_bytes() for n in SOURCE_FILES)
    import hashlib
    report={'runtime':'python3.14','architecture':'Linux x86_64','versions':versions,
        'source_files':SOURCE_FILES,'full_dependency_bytes':sum(p.stat().st_size for p in files),
        'uncompressed_bytes':size,'limit_bytes':LIMIT,'zip_bytes':archive_path.stat().st_size,
        'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),'native_elf_files':native,
        'excluded_bundled_test_bytecode_bytes':sum(p.stat().st_size for p in files if p not in selected),
        'linux_execution':'not established by static ELF checks','deployed':False}
    (output/'package-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_elf_files','source_files','versions')},indent=2))
    return archive_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--dependencies-dir',type=Path,help='Reuse a measured Linux dependency directory after verifying pins and ELF headers.')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    if args.validate_only:
        validate_template(); print('Local modeling template/source validation: OK (not cloud execution)')
    elif args.output_dir: build(args.output_dir,args.dependencies_dir)
    else: parser.error('Select --validate-only or --output-dir.')


if __name__=='__main__': main()
