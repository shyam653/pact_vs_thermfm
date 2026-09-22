#!/usr/bin/env python3
"""Deterministically partition the unchanged IP3 benchmark inputs using IP2 times."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
out = repo / 'build/IP3/cpu-bench-shards'
source = repo / 'build/cpu-rebuilt/bench-short.tsv'
timings = repo / 'IPs/IP2/docs/reports/cpu/campaigns/cpu-bench/results.tsv'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream, delimiter='\t'))

assert not out.exists(), 'Preserve an existing derived partition'
original = rows(source)
weights = {row['test']: Decimal(row['wall_seconds']) for row in rows(timings)}
inputs = json.loads((repo / 'build/cpu-rebuilt/inputs.json').read_text())
elfs = {row['test']: row['sha256'] for row in inputs}
assert len(original) == len({row['test'] for row in original}) == 72
assert set(weights) == {row['test'] for row in original}
assert all(weights[row['test']] > 0 for row in original)
assert all(sha(Path(row['binary'])) == elfs[row['test']] for row in original)
shards = [[] for _ in range(4)]
totals = [Decimal(0) for _ in range(4)]
for row in sorted(original, key=lambda row: (-weights[row['test']], row['test'])):
    selected = min(range(4), key=lambda index: (totals[index], index))
    shards[selected].append(row)
    totals[selected] += weights[row['test']]
assert len([row for shard in shards for row in shard]) == 72
assert {row['test']: row for shard in shards for row in shard} == {row['test']: row for row in original}
out.mkdir()
metadata = []
for number, (shard, total) in enumerate(zip(shards, totals), 1):
    path = out / f'bench-shard-{number}.tsv'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(original[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(shard)
    assert rows(path) == shard
    metadata.append({'number': number, 'campaign': f'cpu-bench-shard-{number}',
                     'manifest': str(path.relative_to(repo)), 'manifest_sha256': sha(path),
                     'tests': len(shard), 'ip2_wall_seconds_sum': str(total),
                     'ordered_tests': [row['test'] for row in shard]})
evidence = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'method': 'Longest processing time first: descending IP2 per-test wall_seconds, test-name tie break; assign to lowest total, shard-index tie break',
    'timing_scope': 'Historical IP2 host durations guide scheduling only; they do not predict hardware performance or establish IP3 outcomes',
    'source_manifest': str(source.relative_to(repo)), 'source_manifest_sha256': sha(source),
    'timing_reference': str(timings.relative_to(repo)), 'timing_reference_sha256': sha(timings),
    'preparation_script': str(Path(__file__).resolve().relative_to(repo)), 'preparation_script_sha256': sha(Path(__file__)),
    'original_rows': original, 'elf_sha256': {row['test']: elfs[row['test']] for row in original},
    'historical_ip2_wall_seconds': {row['test']: str(weights[row['test']]) for row in original},
    'shards': metadata, 'disjoint_union_exactly_original_72': True,
    'all_original_row_fields_identical': True, 'current_elf_hashes_match_reused_inputs': True,
    'fixed_settings': {'jobs': 1, 'seed': 1, 'max_cycles': 2000000, 'wall_timeout_seconds': 1800},
}
(out / 'partition-provenance.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
