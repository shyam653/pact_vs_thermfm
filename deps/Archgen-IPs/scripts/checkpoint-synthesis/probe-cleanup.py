#!/usr/bin/env python3
"""Bounded diagnostic: identical SoC frontend, dead-logic cleanup, same CHECK gate."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('origin', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--timeout-seconds', type=int, default=300)
    a = p.parse_args()
    origin = a.origin.resolve(strict=True)
    output = a.output.resolve()
    if output.exists() or a.timeout_seconds <= 0:
        p.error('Output must be fresh and timeout positive')
    original = json.loads((origin / 'provenance.json').read_text())
    for r in original['inputs']:
        if digest(Path(r['path'])) != r['sha256']:
            p.error(f'Original input changed: {r["path"]}')
    frontend, remainder = (origin / 'elaborate.ys').read_text().split('check -assert\n', 1)
    if not frontend.rstrip().endswith('hierarchy -check -top ChipTop'):
        p.error('Unexpected original elaboration sequence')
    output.mkdir(parents=True)
    (output / 'inputs').symlink_to(origin / 'inputs', target_is_directory=True)
    shutil.copyfile(__file__, output / 'probe-cleanup.py')
    script = frontend + (
        'tee -o before-clean-statistics.json stat -json -width\n'
        'write_rtlil before-clean.il\n'
        'opt_clean -purge\n'
        'tee -o after-clean-statistics.json stat -json -width\n'
        'write_rtlil after-clean.il\n'
        'check -assert\n'
        'tee -o checked-statistics.json stat -json -width\n'
        'write_rtlil ChipTop-elaborated.il\n')
    (output / 'probe.ys').write_text(script)
    yosys = original['tools']['YOSYS']['path']
    command = ['timeout', '--signal=TERM', '--kill-after=10', str(a.timeout_seconds),
               yosys, '-Q', '-T', '-q', '-l', 'probe.log', '-s', 'probe.ys']
    metadata = {'started_utc': datetime.now(timezone.utc).isoformat(), 'configuration': original['configuration'],
        'scope': 'Bounded cleanup/CHECK diagnostic only; no technology-mapping or full implementation PASS',
        'origin': str(origin), 'origin_provenance_sha256': digest(origin / 'provenance.json'),
        'inputs': original['inputs'], 'tools': original['tools'], 'command': command,
        'helper_sha256': digest(Path(__file__).resolve()), 'script_sha256': digest(output / 'probe.ys'),
        'identical_frontend_and_hierarchy_prefix': frontend,
        'cleanup': 'opt_clean -purge', 'final_check': 'check -assert'}
    write(output / 'provenance.json', metadata)
    print(f'Starting bounded cleanup diagnostic at {metadata["started_utc"]}', flush=True)
    with (output / 'probe.console.log').open('w') as log:
        process = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT)
    (output / 'run-status.txt').write_text(f'exit_status={process.returncode}\n')
    stable = all(digest(Path(r['path'])) == r['sha256'] for r in original['inputs'])
    write(output / 'outcome.json', {'completed_utc': datetime.now(timezone.utc).isoformat(),
          'exit_status': process.returncode, 'inputs_unchanged': stable,
          'status': 'PASS_DIAGNOSTIC' if process.returncode == 0 and stable else 'FAILED_OR_TIMED_OUT',
          'scope': metadata['scope']})
    print(f'Diagnostic exit {process.returncode}; inputs unchanged {stable}', flush=True)
    raise SystemExit(process.returncode if stable else 1)


if __name__ == '__main__':
    main()
