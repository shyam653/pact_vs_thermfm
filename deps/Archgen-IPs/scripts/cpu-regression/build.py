#!/usr/bin/env python3
"""Rebuild the frozen 422-test RV64 CPU inventory against a prepared toolchain."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError('Inventory validation requires assertions enabled; remove -O/PYTHONOPTIMIZE')

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--chipyard-root', type=Path, required=True)
p.add_argument('--config', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
cy, out = a.chipyard_root.resolve(), a.output.resolve()
if out.exists():
    p.error('output already exists')
out.mkdir(parents=True)
templates = Path(__file__).resolve().parent / 'templates'
pins = json.loads((templates.parent / 'source-pins.json').read_text())
for component, directory in [('riscv-tests', cy / 'toolchains/riscv-tools/riscv-tests'),
                             ('riscv-test-env', cy / 'toolchains/riscv-tools/riscv-tests/env')]:
    revision = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != pins[component]:
        p.error(f'Unexpected {component} revision: {revision}')
    subprocess.run(['git', '-C', str(directory), 'diff', 'HEAD', '--exit-code'], check=True)
shutil.copytree(templates / 'bench', out / 'bench')
shutil.copyfile(templates / 'dual-hart-smoke.S', out / 'dual-hart-smoke.S')
env = os.environ.copy()
env.update(CHIPYARD_ROOT=str(cy), CONFIG=a.config, CPU_ENV=str(out / 'env.sh'))
envfile = '''export CY="$CHIPYARD_ROOT"
export RISCV="${RISCV:-$CY/.conda-env/riscv-tools}"
export PATH="$RISCV/bin:$CY/.conda-env/bin:$PATH"
export LD_LIBRARY_PATH="$RISCV/lib:$CY/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
'''
(out / 'env.sh').write_text(envfile)
env['RISCV'] = env.get('RISCV', str(cy / '.conda-env/riscv-tools'))
env['PATH'] = f"{env['RISCV']}/bin:{cy}/.conda-env/bin:" + env['PATH']
tests = cy / 'toolchains/riscv-tools/riscv-tests'
commands = []
def run(command, cwd, log):
    commands.append({'argv': [str(x) for x in command], 'cwd': str(cwd)})
    with (out / log).open('w') as f:
        subprocess.run(command, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)

targets = (templates / 'isa-targets.txt').read_text().splitlines()
isa = out / 'isa'
isa.mkdir()
run(['make', '--no-print-directory', '-f', str(tests / 'isa/Makefile'),
     f'src_dir={tests}/isa', 'XLEN=64', '-j2', *targets], isa, 'isa-build.log')
rows = [{'test': n, 'binary': str(isa / n), 'suite': 'isa', 'required_stdout': '[]'} for n in targets]
for script in ['build.sh', 'build-chipyard.sh', 'corrected/build.sh']:
    run(['bash', str(out / 'bench' / script)], out, script.replace('/', '-') + '.log')
for manifest in ['manifest.tsv', 'chipyard-manifest.tsv', 'corrected/manifest.tsv']:
    for row in csv.DictReader((out / 'bench' / manifest).open(), delimiter='\t'):
        rows.append({**row, 'required_stdout': '[]'})
markers = {'chipyard-hello': ['Hello world'], 'chipyard-cpp-hello': ['Hello World!'],
           'chipyard-mt-hello-dual': ['Hello world from core 0, a rocket', 'Hello world from core 1, a rocket']}
for row in rows:
    row['required_stdout'] = json.dumps(markers.get(row['test'], []))
smoke = out / 'dual-hart-smoke.riscv'
run(['riscv64-unknown-elf-gcc', '-march=rv64imafdc_zicsr_zifencei', '-mabi=lp64d',
     '-mcmodel=medany', '-nostdlib', '-nostartfiles', '-static', '-Wl,--no-relax',
     '-T', str(tests / 'env/p/link.ld'), str(out / 'dual-hart-smoke.S'), '-o', str(smoke)], out, 'smoke-build.log')
rows.append({'test': 'dual-hart-smoke', 'binary': str(smoke), 'suite': 'dual-hart-smoke',
             'required_stdout': json.dumps(['PASS dual-hart: hart0+hart1, peer data visible, 256 atomic increments'])})
assert len(rows) == len({r['test'] for r in rows}) == 422, 'Frozen inventory mismatch'
fields = ['test', 'binary', 'suite', 'required_stdout']
for name, selected in [('all', rows), ('isa', [r for r in rows if r['suite'] == 'isa']),
                       ('bench', [r for r in rows if r['suite'] != 'isa'])]:
    with (out / f'{name}.tsv').open('w') as f:
        writer = csv.DictWriter(f, fields, delimiter='\t')
        writer.writeheader()
        writer.writerows(selected)
for row in rows:
    row['sha256'] = hashlib.sha256(Path(row['binary']).read_bytes()).hexdigest()
(out / 'inputs.json').write_text(json.dumps(rows, indent=2) + '\n')
(out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
print(f'Built {len(rows)} tests in {out}')
