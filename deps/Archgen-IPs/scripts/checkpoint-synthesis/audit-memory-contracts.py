#!/usr/bin/env python3
"""Compare every generic-memory parameter across actual ABC RTLIL checkpoints.

This checks pre-ABC to post-ABC parameter preservation, including INIT and all
clock/transparency/collision/X masks. It does not prove combinational equivalence
around the memory ports or validate RTL-to-pre-ABC memory inference.
"""
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


def parameters(path):
    module = None
    active = None
    result = {}
    with path.open() as stream:
        for line in stream:
            if line.startswith('module '):
                module = line.removeprefix('module ').strip()
            if line.startswith('  cell $mem_v2 '):
                if active is not None or module is None:
                    raise ValueError('Malformed nested memory cell')
                active = module + '/' + line.removeprefix('  cell $mem_v2 ').strip()
                if active in result:
                    raise ValueError(f'Duplicate memory cell: {active}')
                result[active] = {}
            elif active is not None and line.startswith('    parameter '):
                match = re.fullmatch(r'    parameter (signed )?(\\\S+) (.+)\n?', line)
                if not match:
                    raise ValueError(f'Unrecognized memory parameter: {line[:120]}')
                signed, name, value = match.groups()
                if name in result[active]:
                    raise ValueError(f'Duplicate memory parameter: {active}/{name}')
                result[active][name] = {'signed': bool(signed), 'literal': value.strip()}
            elif active is not None and line.rstrip() == '  end':
                active = None
    if active is not None:
        raise ValueError('Truncated memory cell')
    if not result or not all(r'\INIT' in values for values in result.values()):
        raise ValueError('No generic memories or missing INIT parameters')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    before = args.before.resolve(strict=True)
    after = args.after.resolve(strict=True)
    if args.output.exists():
        parser.error('Output must not already exist')
    identities = {'before': {'name': before.name, 'sha256': digest(before), 'bytes': before.stat().st_size},
                  'after': {'name': after.name, 'sha256': digest(after), 'bytes': after.stat().st_size}}
    old, new = parameters(before), parameters(after)
    added, removed = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    changed = {name: sorted(key for key in old[name].keys() | new[name].keys()
                           if old[name].get(key) != new[name].get(key))
               for name in old.keys() & new.keys() if old[name] != new[name]}
    unchanged = not added and not removed and not changed
    cells = []
    for name, params in sorted(old.items()):
        per_parameter = {key: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                         for key, value in sorted(params.items())}
        cells.append({'cell': name, 'parameters': len(params), 'parameter_sha256': per_parameter,
                      'all_parameters_match': name in new and params == new[name]})
    stable = identities['before']['sha256'] == digest(before) and identities['after']['sha256'] == digest(after)
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS' if unchanged and stable else 'FAIL',
              'scope': 'Exact all-parameter $mem_v2 comparison from pre-ABC to post-ABC RTLIL; not RTL inference or surrounding-logic formal equivalence',
              'checkpoints': identities, 'audit_script_sha256': digest(Path(__file__).resolve()),
              'inputs_unchanged_during_audit': stable, 'memory_instances_before': len(old),
              'memory_instances_after': len(new), 'parameters_compared': sum(len(v) for v in old.values()),
              'all_parameters_identical': unchanged, 'added': added, 'removed': removed,
              'changed_parameters': changed, 'cells': cells}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['status']}: {len(old)} memories, {report['parameters_compared']} exact parameters")
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
