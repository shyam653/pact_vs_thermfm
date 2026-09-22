#!/usr/bin/env python3
"""Audit actual-flow or diagnostic cleanup without claiming formal equivalence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def value_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def parse(path):
    modules, current, cell = {}, None, None
    with path.open() as stream:
        for line in stream:
            if line.startswith('module '):
                current = line.strip().split(' ', 1)[1]
                if current in modules:
                    raise ValueError(f'Duplicate module: {current}')
                modules[current] = {'ports': {}, 'memories': [], 'memory_cells': {}}
            elif line.startswith('  wire ') and re.search(r' (input|output|inout) ', line):
                modules[current]['ports'][line.split()[-1]] = line.strip()
            elif line.startswith('  memory '):
                modules[current]['memories'].append(line.strip())
            elif line.startswith('  cell '):
                cell = None
                kind, name = line.strip().split(maxsplit=2)[1:]
                if kind.startswith('$mem'):
                    cell = name
                    if cell in modules[current]['memory_cells']:
                        raise ValueError(f'Duplicate memory cell: {current}/{cell}')
                    modules[current]['memory_cells'][cell] = {'type': kind, 'parameters': {}}
            elif line.startswith('    parameter ') and cell:
                match = re.fullmatch(r'    parameter (signed )?(\\\S+) (.+)\n?', line)
                if not match:
                    raise ValueError(f'Unsupported memory parameter: {line[:120]}')
                signed, key, value = match.groups()
                parameters = modules[current]['memory_cells'][cell]['parameters']
                if key in parameters:
                    raise ValueError(f'Duplicate memory parameter: {current}/{cell}/{key}')
                parameters[key] = {'signed': bool(signed), 'literal': value.strip()}
            elif line == '  end\n':
                cell = None
    return modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--stage', choices=['elaborate'],
                        help='Audit recorded checkpoints from this actual full-flow frontend')
    parser.add_argument('--output', type=Path, help='Optional fresh report path')
    args = parser.parse_args()
    directory = args.probe.resolve(strict=True)
    output = args.output or directory / 'cleanup-audit.json'
    if output.exists():
        parser.error('Refusing to overwrite an audit')
    if args.stage:
        names = [f'{args.stage}-{moment}-clean{suffix}' for suffix in ('.il', '-statistics.json')
                 for moment in ('before', 'after')]
        names += ['elaborated-statistics.json', f'{args.stage}.ys', f'{args.stage}.log',
                  'provenance.json']
        script = (directory / f'{args.stage}.ys').read_text()
        log = (directory / f'{args.stage}.log').read_text()
        check_passed = (re.search(r'^check -assert$', script, re.MULTILINE) is not None and
                        re.search(r'^opt_clean -purge$', script, re.MULTILINE) is not None and
                        'Found and reported 0 problems' in log and 'ERROR:' not in log)
        source_records = json.loads((directory / 'provenance.json').read_text())['inputs']
        source_stable = all(digest(Path(r['path'])) == r['sha256'] for r in source_records)
        context = 'ACTUAL_FULL_FLOW_FRONTEND'
    else:
        names = ['before-clean.il', 'after-clean.il', 'before-clean-statistics.json',
                 'after-clean-statistics.json', 'checked-statistics.json', 'probe.ys',
                 'probe.log', 'provenance.json', 'outcome.json']
        check_passed = json.loads((directory / 'outcome.json').read_text())['status'] == 'PASS_DIAGNOSTIC'
        source_stable = None
        context = 'BOUNDED_DIAGNOSTIC'
    hashes = {name: digest(directory / name) for name in names}
    before, after = [parse(directory / name) for name in names[:2]]
    bstats, astats = [json.loads((directory / name).read_text()) for name in names[2:4]]
    same_modules = before.keys() == after.keys()
    differences = {key: [name for name in before if name not in after or
                         before[name][key] != after[name][key]]
                   for key in ['ports', 'memories', 'memory_cells']}
    monitors = []
    for name in before:
        if name.startswith('\\TLMonitor'):
            monitors.append({'module': name,
                'output_or_inout_ports': sum(' output ' in wire or ' inout ' in wire
                                           for wire in before[name]['ports'].values()),
                'cells_before': bstats['modules'][name]['num_cells'],
                'cells_after': astats['modules'][name]['num_cells'],
                'wire_bits_before': bstats['modules'][name]['num_wire_bits'],
                'wire_bits_after': astats['modules'][name]['num_wire_bits']})
    stable = all(digest(directory / name) == h for name, h in hashes.items())
    if args.stage:
        source_stable = source_stable and all(digest(Path(r['path'])) == r['sha256']
                                               for r in source_records)
    passed = (stable and same_modules and not any(differences.values()) and
              check_passed and source_stable is not False and
              all(m['output_or_inout_ports'] == m['cells_after'] == 0 for m in monitors))
    result = {'status': 'PASS' if passed else 'FAIL',
        'context': context, 'source_inputs_unchanged': source_stable,
        'observed_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Cleanup structural audit: module ports, original memory declarations and memory-cell '
                 'types/all parameters; output-free TileLink monitor internals removed. '
                 'Not formal surrounding-logic equivalence or technology mapping.',
        'audit_script_sha256': digest(Path(__file__).resolve()),
        'input_sha256': hashes, 'inputs_unchanged_during_audit': stable,
        'identical_module_names': same_modules, 'module_count': len(before),
        'top_port_count': len(before['\\ChipTop']['ports']),
        'changed_modules_by_contract': differences,
        'memory_declarations': sum(len(m['memories']) for m in before.values()),
        'memory_cell_count': sum(len(m['memory_cells']) for m in before.values()),
        'contract_before_sha256': value_digest(before),
        'contract_after_sha256': value_digest(after),
        'design_before': {k: v for k, v in bstats['design'].items() if not isinstance(v, dict)},
        'design_after': {k: v for k, v in astats['design'].items() if not isinstance(v, dict)},
        'monitor_count': len(monitors), 'monitors': monitors,
        'same_check_assert_passed': check_passed}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{result["status"]}: {len(monitors)} output-free monitors, '
          f'{result["memory_declarations"]} unchanged memory declarations, '
          f'{result["memory_cell_count"]} unchanged memory-cell parameter sets')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
