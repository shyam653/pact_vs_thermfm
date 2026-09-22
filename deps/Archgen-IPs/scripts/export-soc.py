#!/usr/bin/env python3
"""Archive original generated RTL, compact metadata, source pins and licenses."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError('Hardware validation requires assertions enabled; remove -O/PYTHONOPTIMIZE')

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--chipyard-root', type=Path, required=True)
p.add_argument('--ip', type=Path, required=True)
p.add_argument('--config', required=True)
a = p.parse_args()
cy, ip = a.chipyard_root.resolve(), a.ip.resolve()
name = 'chipyard.harness.TestHarness.' + a.config
gen = cy / 'sims/verilator/generated-src' / name
rtl, artifacts = ip / 'rtl', ip / 'docs/artifacts'
if rtl.exists() or artifacts.exists():
    p.error('RTL or artifact destination already exists')
hw = json.loads((gen / (name + '.json')).read_text())
assert sorted(k for k in hw['cpus'] if k.startswith('cpu@')) == ['cpu@0', 'cpu@1']
(rtl / 'gen-collateral').mkdir(parents=True)
artifacts.mkdir(parents=True)
sources = sorted(f for f in (gen / 'gen-collateral').iterdir()
                 if f.suffix in {'.v', '.sv', '.vh', '.svh'})
required = set()
for listname in [name + '.all.f', 'sim_files.common.f']:
    for line in (gen / listname).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith(('+', '-')):
            candidate = Path(line)
            if candidate.suffix in {'.v', '.sv', '.vh', '.svh'}:
                required.add(candidate.resolve())
missing = required - {f.resolve() for f in sources}
if missing:
    raise RuntimeError(f'Source list requires files outside snapshot: {sorted(map(str, missing))}')
for f in sources:
    shutil.copyfile(f, rtl / 'gen-collateral' / f.name)
for suffix in ['dts', 'json', 'memmap.json', 'l2.json', 'top.mems.conf', 'd']:
    shutil.copyfile(gen / (name + '.' + suffix), artifacts / (name + '.' + suffix))
for f in gen.glob('*.regmap.json'):
    shutil.copyfile(f, artifacts / f.name)
for f in [gen / 'top_module_hierarchy.json', gen / (name + '.top.mems.conf')]:
    shutil.copyfile(f, rtl / f.name)
licenses = ip / 'third_party/licenses'
components = ['.', 'generators/rocket-chip', 'generators/rocket-chip-inclusive-cache',
              'generators/testchipip', 'generators/rocket-chip-blocks', 'generators/diplomacy',
              'generators/hardfloat', 'tools/cde']
if 'FFT' in a.config:
    components += ['generators/fft-generator', 'tools/dsptools', 'tools/fixedpoint', 'tools/rocket-dsp-utils']
else:
    components += ['generators/nvdla', 'generators/nvdla/src/main/resources/hw']
pins = {}
for component in components:
    source = cy / component
    if not source.exists():
        raise RuntimeError(f'Missing component {source}')
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    status = subprocess.check_output(['git', '-C', str(source), 'status', '--short'], text=True)
    pins[component] = {'commit': commit, 'status_at_export': status}
    dest = licenses / ('chipyard' if component == '.' else component.replace('/', '__'))
    dest.mkdir(parents=True, exist_ok=True)
    for f in source.iterdir():
        if f.is_file() and (f.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))):
            shutil.copyfile(f, dest / f.name)
shutil.copyfile(cy / 'generators/rocket-chip/LICENSE.SiFive', rtl / 'gen-collateral/LICENSE.SiFive')
def hashes(directory):
    return {str(f.relative_to(directory)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(directory.rglob('*')) if f.is_file()}
(artifacts / 'rtl.sha256').write_text(''.join(
    f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n' for f in sources))
(artifacts / 'generation.json').write_text(json.dumps({
    'config': 'chipyard.' + a.config, 'chipyard_commit': pins['.']['commit'],
    'sources': len(sources), 'dut_top': 'ChipTop',
    'includes_simulation_resources': True,
    'required_source_files_checked': len(required),
    'rtl_unmodified_after_generation': True, 'components': pins,
    'config_sha256': hashlib.sha256((ip / 'config' / (a.config + '.scala')).read_bytes()).hexdigest(),
    'rtl_files': hashes(rtl), 'license_files': hashes(licenses),
}, indent=2) + '\n')
print(f'Exported {len(sources)} RTL sources to {rtl}')
