#!/usr/bin/env python3
"""Run balanced one-worker shards after ISA, admitting extra slots by explicit grant."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

repo = Path(__file__).resolve().parents[2]
work = repo / 'build/IP3'
partition_dir = work / 'cpu-bench-shards'
partition = json.loads((partition_dir / 'partition-provenance.json').read_text())
simulator = repo.parent / 'chipyard/sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig'
expected = 'ac906aabe883e14d65b06669b134ca5079d96ddcd462e82b4d0079b08a6cacf5'
events = partition_dir / 'scheduling-events.jsonl'
grants = partition_dir / 'extra-slot-grants.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def record(event, **details):
    value = {'utc': datetime.now(timezone.utc).isoformat(), 'event': event, **details}
    with events.open('a') as stream:
        stream.write(json.dumps(value) + '\n')
    print(json.dumps(value), flush=True)

def validate_inputs(shard):
    assert sha(simulator) == expected, 'Official simulator bytes changed'
    assert sha(repo / partition['source_manifest']) == partition['source_manifest_sha256']
    assert sha(repo / shard['manifest']) == shard['manifest_sha256']
    for row in partition['original_rows']:
        if row['test'] in shard['ordered_tests']:
            assert sha(Path(row['binary'])) == partition['elf_sha256'][row['test']]

assert not events.exists(), 'Do not restart this scheduler over existing work'
assert not grants.exists(), 'Initial slot grants must be empty'
assert len(partition['shards']) == 4 and sum(shard['tests'] for shard in partition['shards']) == 72
grants.write_text(json.dumps({'extra_slots': 0, 'reason': 'Initial two slots are released by completed ISA; PMP/NVDLA slots require separate coordinated release'}, indent=2) + '\n')
record('waiting_for_isa', baseline_slots_after_isa=2, explicit_extra_slots=0,
       scheduler_sha256=sha(Path(__file__)), partition_sha256=sha(partition_dir / 'partition-provenance.json'))
while not (work / 'cpu-isa/summary.json').is_file():
    time.sleep(15)
isa = json.loads((work / 'cpu-isa/summary.json').read_text())
assert isa['total'] == 349, 'ISA campaign is incomplete'
assert json.loads((work / 'cpu-isa/provenance.json').read_text())['simulator_sha256'] == expected
record('isa_complete', summary_sha256=sha(work / 'cpu-isa/summary.json'), baseline_slots=2)

pending = list(partition['shards'])
active = {}
finished = []
last_extra = 0
while pending or active:
    grant_bytes = grants.read_bytes()
    grant = json.loads(grant_bytes)
    extra = grant['extra_slots']
    assert type(extra) is int and last_extra <= extra <= 2, 'Grants must be explicit, bounded and nondecreasing'
    if extra != last_extra:
        record('extra_capacity_granted', grant=grant, grant_sha256=hashlib.sha256(grant_bytes).hexdigest())
        last_extra = extra
    for name, (process, log, shard) in list(active.items()):
        result = process.poll()
        if result is None:
            continue
        log.close()
        (work / f'{name}-driver.exit').write_text(str(result) + '\n')
        summary_path = work / name / 'summary.json'
        assert result in (0, 1) and summary_path.is_file(), f'Campaign {name} did not complete normally'
        summary = json.loads(summary_path.read_text())
        assert summary['total'] == shard['tests'], f'Incomplete shard {name}'
        record('shard_complete', campaign=name, runner_exit_status=result,
               summary_sha256=sha(summary_path), summary=summary)
        finished.append(name)
        del active[name]
    while pending and len(active) < 2 + extra:
        shard = pending.pop(0)
        validate_inputs(shard)
        name = shard['campaign']
        assert not (work / name).exists(), f'Preserve existing campaign {name}'
        command = ['python3', str(repo / 'IPs/IP2/scripts/run-regression.py'),
                   str(repo / shard['manifest']), str(work / name),
                   '--simulator', str(simulator), '--chipyard-root', str(repo.parent / 'chipyard'),
                   '--jobs', '1', '--max-cycles', '2000000', '--timeout', '1800', '--seed', '1']
        (work / f'{name}-launch-command.json').write_text(json.dumps(command, indent=2) + '\n')
        log = (work / f'{name}-driver.log').open('w')
        process = subprocess.Popen(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT)
        active[name] = (process, log, shard)
        record('shard_started', campaign=name, pid=process.pid, argv=command,
               active_shards=list(active), capacity=2 + extra,
               manifest_sha256=shard['manifest_sha256'], simulator_sha256=expected)
    if pending or active:
        time.sleep(10)
record('all_shards_complete', campaigns=finished, total_tests=72)
