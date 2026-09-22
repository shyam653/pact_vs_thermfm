#!/usr/bin/env python3
"""Independently map a verified pre-ABC SoC checkpoint with explicit ABC commands.

This reuses, and labels, the origin's RTL elaboration and SRAM simulation evidence.
It never resumes or modifies the origin run. Outputs must be a fresh directory.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--platform', type=Path, required=True)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--openroad', type=Path, required=True)
    parser.add_argument('--openroad-native', type=Path, required=True)
    parser.add_argument('--allow-changed-document', type=Path, action='append', default=[])
    args = parser.parse_args()
    origin = args.origin.resolve(strict=True)
    platform = args.platform.resolve(strict=True)
    suite = args.suite.resolve(strict=True)
    output = args.output.resolve()
    require(not output.exists(), f'Output already exists: {output}')
    provenance = json.loads((origin / 'provenance.json').read_text())
    inventory = json.loads((origin / 'macro-map/inventory.json').read_text())
    checkpoint = origin / 'ChipTop-before-abc.il'
    checkpoint_hash = digest(checkpoint)
    status = (origin / 'run-status.txt').read_text().strip() if (origin / 'run-status.txt').exists() else 'IN_PROGRESS'
    if status != 'IN_PROGRESS':
        require(status == 'exit_status=0', f'Origin failed: {status}')
        require(json.loads((origin / 'summary.json').read_text())['status'] == 'PASS', 'Origin is not PASS')
        require(json.loads((origin / 'artifact-sha256.json').read_text())['ChipTop-before-abc.il'] == checkpoint_hash,
                'Historical checkpoint hash mismatch')
    allowed = {p.resolve(strict=True) for p in args.allow_changed_document}
    require(all(p.name == 'README.md' for p in allowed), 'Only explicitly identified README.md mismatches may be recorded')
    changed = []
    observed_inputs = []
    for record in provenance['inputs']:
        path = Path(record['path']).resolve(strict=True)
        actual = digest(path)
        observed_inputs.append({'path': str(path), 'sha256': actual})
        if actual != record['sha256']:
            require(path in allowed, f'Origin input changed: {path}')
            changed.append({'path': str(path), 'historical_sha256': record['sha256'], 'observed_sha256': actual,
                            'scope': 'Explicitly permitted documentation-only historical mismatch'})
    for name in ['preflight.log', 'elaborate.log', 'prepare.log']:
        log = (origin / name).read_text()
        require('Found and reported 0 problems.' in log and 'ERROR:' not in log, f'Origin gate incomplete: {name}')
    sram_log = (origin / 'macro-map/test_sram.log').read_text()
    require('FAIL' not in sram_log, 'Origin SRAM comparisons failed')
    seeds = re.findall(r'^SEED=(\d+)$', sram_log, re.M)
    require(seeds == ['1', '827361', '2147483647'], 'Incomplete origin SRAM seeds')
    matches = re.findall(r'^PASS kind=(\d+) .* compared_cycles=(\d+)$', sram_log, re.M)
    require(Counter(k for k, _ in matches) == Counter({str(i): 3 for i in range(len(inventory['memories']))}),
            'Incomplete origin SRAM interface comparisons')
    cycles = sum(int(n) for _, n in matches)
    expected_cycles = 3 * sum(10002 + 6 * ((m['depth'] + 510) // 511) + 4 * m['mask_bits'] for m in inventory['memories'])
    require(cycles == expected_cycles, 'Unexpected origin SRAM cycle coverage')
    if (origin / 'memory-audit.json').exists():
        require(json.loads((origin / 'memory-audit.json').read_text())['status'] == 'PASS', 'Origin memory audit failed')
    output.mkdir(parents=True)
    (output / 'inputs').mkdir()
    (output / 'inherited').mkdir()
    scripts = Path(__file__).resolve().parent
    shutil.copyfile(__file__, output / 'run.py')
    for name in ['direct.abc', 'check.tcl']:
        shutil.copyfile(scripts / name, output / name)
    for name in ['provenance.json', 'preflight.log', 'elaborate.log', 'prepare.log', 'memory-audit.json',
                 'macro-map/inventory.json', 'macro-map/test_sram.log', 'macro-map/chipyard-sram-macros.v',
                 'macro-map/test_sram.sv', 'summary.json', 'artifact-sha256.json', 'source-plan.json']:
        source = origin / name
        if source.exists():
            target = output / 'inherited' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    prefix = (origin / 'map.log').read_text().split('Executing ABC pass')[0]
    require('ChipTop-before-abc.il' in prefix, 'Origin log does not show checkpoint writing')
    (output / 'inherited/map-prefix.log').write_text(prefix)
    linked = {'checkpoint.il': checkpoint, 'cell.lib': platform / 'lib/NangateOpenCellLibrary_typical.lib',
              'sram.lib': platform / 'lib/fakeram45_512x64.lib'}
    for name, source in linked.items():
        (output / 'inputs' / name).symlink_to(source)
    native = {name: suite / 'libexec' / name for name in ['yosys', 'yosys-abc', 'iverilog', 'vvp']}
    native['openroad'] = args.openroad_native.resolve(strict=True)
    tools = {'yosys': str(suite / 'bin/yosys'), 'openroad': str(args.openroad.resolve(strict=True))}
    files = [*linked.values(), *native.values(), *(Path(p) for p in tools.values()),
             platform / 'lef/NangateOpenCellLibrary.tech.lef', platform / 'lef/NangateOpenCellLibrary.macro.lef',
             platform / 'lef/fakeram45_512x64.lef', scripts / 'run.py', scripts / 'direct.abc', scripts / 'check.tcl']
    observed_inputs.extend({'path': str(path), 'sha256': digest(path)} for path in files)
    macros = inventory['physical_macro_instances']
    (output / 'map.ys').write_text('read_rtlil inputs/checkpoint.il\nread_liberty -lib inputs/cell.lib\n'
        'hierarchy -check -top ChipTop\n'
        f'select -assert-count {macros} t:fakeram45_512x64\n'
        'abc -liberty inputs/cell.lib -script direct.abc\nclean\nwrite_rtlil ChipTop-after-abc.il\n')
    (output / 'finalize.ys').write_text('read_rtlil ChipTop-after-abc.il\nread_liberty -lib inputs/cell.lib\n'
        'clean -purge\nhierarchy -check -top ChipTop\ncheck -assert -mapped\nselect -assert-none t:$*\n'
        f'select -assert-count {macros} t:fakeram45_512x64\n'
        'tee -o statistics.json stat -json -liberty inputs/cell.lib -liberty inputs/sram.lib\n'
        'write_verilog -noattr -noexpr ChipTop-mapped.v\nwrite_json ChipTop-mapped.json\n')
    observed_inputs.extend({'path': str(output / name), 'sha256': digest(output / name)} for name in ['map.ys', 'finalize.ys', 'direct.abc', 'check.tcl'])
    run_provenance = {'started_utc': now(), 'configuration': inventory['configuration'], 'top': 'ChipTop',
        'mapping_mode': 'abc-direct', 'abc_commands': ['strash', '&get -n', '&nf', '&put'],
        'checkpoint_reuse': {'origin': str(origin), 'checkpoint_sha256': checkpoint_hash,
                            'origin_status_at_fork': status, 'historical_document_mismatches': changed,
                            'scope': 'Reuse original RTL elaboration, SRAM simulations and pre-ABC synthesis; rerun ABC, mapped checks and OpenROAD link independently'},
        'tools': tools, 'inputs': observed_inputs,
        'native_tools_before': {'observed_utc': now(), 'files': {n: {'path': str(p), 'sha256': digest(p)} for n, p in native.items()}}}
    write_json(output / 'provenance.json', run_provenance)
    code = 1
    try:
        for stage in ['map', 'finalize']:
            print(f'{inventory["configuration"]}: starting {stage} at {now()}', flush=True)
            with (output / f'{stage}.console.log').open('w') as log:
                subprocess.run([tools['yosys'], '-Q', '-T', '-q', '-l', f'{stage}.log', '-s', f'{stage}.ys'],
                               cwd=output, stdout=log, stderr=subprocess.STDOUT, check=True)
        env = dict(os.environ, PLATFORM_ROOT=str(platform), OUTPUT_ROOT=str(output), CONFIG=inventory['configuration'],
                   EXPECTED_SRAM_MACROS=str(macros))
        with (output / 'openroad.console.log').open('w') as log:
            subprocess.run([tools['openroad'], '-exit', '-log', str(output / 'openroad.log'), str(output / 'check.tcl')],
                           cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        statistics = json.loads((output / 'statistics.json').read_text())
        design = statistics['design']
        counts = design['num_cells_by_type']
        link = json.loads((output / 'openroad-link.json').read_text())
        require(link['linked'] and link['sram_macros'] == macros and link['instances'] == design['num_cells'], 'OpenROAD/Yosys mismatch')
        library_cells = set(re.findall(r'\bcell\s*\(\s*"?([^\s"()]+)"?\s*\)', linked['cell.lib'].read_text())) | {'fakeram45_512x64'}
        require(set(counts) <= library_cells, f'Unmapped cells: {set(counts) - library_cells}')
        require(counts['fakeram45_512x64'] == macros and design['num_memories'] == 0 and design['num_processes'] == 0,
                'Residual memories/processes or SRAM count mismatch')
        for record in observed_inputs:
            require(digest(record['path']) == record['sha256'], f'Input changed during independent mapping: {record["path"]}')
        write_json(output / 'native-tools-after.json', {'observed_utc': now(), 'files': {n: {'path': str(p), 'sha256': digest(p)} for n, p in native.items()}})
        write_json(output / 'summary.json', {'completed_utc': now(), 'configuration': inventory['configuration'], 'top': 'ChipTop',
            'status': 'PASS', 'synthesis_mode': 'mapped', 'mapping_mode': 'abc-direct', 'abc_commands': run_provenance['abc_commands'],
            'checkpoint_reuse': run_provenance['checkpoint_reuse'], 'mapped_design': design, 'yosys_creator': statistics['creator'],
            'standard_cell_instances': design['num_cells'] - macros, 'openroad_link': link, 'memory_inventory': inventory,
            'sram_comparison': {'evidence': 'inherited', 'seeds': [1, 827361, 2147483647], 'interfaces': len(inventory['memories']), 'compared_cycles': cycles},
            'limitations': ['Exploratory Nangate45/fakeram45 mapping; no timing constraints, placement, routing or timing closure',
                            'Finite SRAM simulation is inherited from the checkpoint origin; no full-SoC formal equivalence',
                            'Original default ABC run is independent and is not completed by this run',
                            'Same direct ABC optimization mode is required for comparable cell area']} )
        write_json(output / 'artifact-sha256.json', {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*'))
                    if p.is_file() and p.name not in ['artifact-sha256.json', 'run-status.txt']})
        code = 0
        print(f'{inventory["configuration"]}: PASS at {now()}', flush=True)
    finally:
        (output / 'run-status.txt').write_text(f'exit_status={code}\n')


if __name__ == '__main__':
    main()
