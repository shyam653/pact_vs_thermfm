#!/usr/bin/env python3
"""Publish completed IP3 CPU runs and explicitly reused IP2 build evidence."""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

repo = next(parent for parent in Path(__file__).resolve().parents
            if (parent / 'IPs/IP2/docs/reports/cpu').is_dir())
out = repo / 'IPs/IP3/docs/reports/cpu'
old = repo / 'IPs/IP2/docs/reports/cpu'
cy = Path(os.environ.get('CHIPYARD_ROOT', str(repo.parent / 'chipyard'))).resolve()
names = ['cpu-isa', 'cpu-pmp', *[f'cpu-bench-shard-{number}' for number in range(1, 5)]]
campaigns = [repo / 'build/IP3' / name for name in names]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def table(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream, delimiter='\t'))

assert not out.exists(), 'Preserve existing evidence; do not overwrite a report'
preflight = read(repo / 'build/IP3/cpu-preflight.json')
corrected = read(repo / 'build/IP3/cpu-corrected-preflight.json')
current = {row['test']: sha(Path(row['binary'])) for row in read(repo / 'build/cpu-rebuilt/inputs.json')}
assert current == preflight['elf_sha256'] == corrected['elf_sha256'] and len(current) == 422
metadata = [read(path / 'provenance.json') for path in campaigns]
simulator_hash = (repo / 'build/IP3/build-sdp-readback-fix/simulator.sha256').read_text().split()[0]
assert simulator_hash == corrected['simulator_sha256'] != corrected['historical_native_sha256']
assert corrected['historical_results_excluded'] is True
assert sha(cy / 'sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig') == simulator_hash
assert all(meta['simulator_sha256'] == simulator_hash for meta in metadata)
partition_dir = repo / 'build/IP3/cpu-bench-shards'
partition = read(partition_dir / 'partition-provenance.json')
assert sha(repo / partition['source_manifest']) == partition['source_manifest_sha256']
assert sha(repo / partition['timing_reference']) == partition['timing_reference_sha256']
assert sha(repo / partition['preparation_script']) == partition['preparation_script_sha256']
assert len(partition['shards']) == 4
derived_rows = []
for shard, meta in zip(partition['shards'], metadata[2:]):
    assert sha(repo / shard['manifest']) == shard['manifest_sha256'] == meta['manifest_sha256']
    part_rows = table(repo / shard['manifest'])
    assert [row['test'] for row in part_rows] == shard['ordered_tests']
    assert len(part_rows) == shard['tests']
    assert all(current[row['test']] == partition['elf_sha256'][row['test']] for row in part_rows)
    assert meta['jobs'] == 1 and meta['seed'] == 1
    assert meta['max_cycles'] == 2000000 and meta['wall_timeout_seconds'] == 1800
    derived_rows.extend(part_rows)
assert len(derived_rows) == len({row['test'] for row in derived_rows}) == 72
assert sorted(derived_rows, key=lambda row: row['test']) == sorted(table(repo / partition['source_manifest']), key=lambda row: row['test'])
assert sorted(derived_rows, key=lambda row: row['test']) == sorted(partition['original_rows'], key=lambda row: row['test'])
events = [json.loads(line) for line in (partition_dir / 'scheduling-events.jsonl').read_text().splitlines()]
assert events[-1]['event'] == 'all_shards_complete' and set(events[-1]['campaigns']) == set(names[2:])
assert events[0]['scheduler_sha256'] == sha(repo / 'build/IP3/queue-cpu-bench-shards.py')
assert events[0]['partition_sha256'] == sha(partition_dir / 'partition-provenance.json')
executed = {}
for path, meta in zip(campaigns, metadata):
    rows = table(path / 'results.tsv')
    assert len(rows) == read(path / 'summary.json')['total'] == len(meta['tests'])
    for test in meta['tests']:
        assert test['test'] not in executed
        executed[test['test']] = test['sha256']
assert executed == current, 'Executed CPU ELF inventory differs from reused build'
command = ['python3', str(repo / 'scripts/cpu-regression/summarize.py')]
for path in campaigns:
    command += ['--campaign', str(path)]
command += ['--chipyard-root', str(cy), '--config', 'DualRocketNVDLAConfig', '--output', str(out)]
(repo / 'build/IP3/cpu-export-command.json').write_text(json.dumps(command, indent=2) + '\n')
with (repo / 'build/IP3/cpu-export.log').open('w') as log:
    subprocess.run(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT, check=True)

hashes = read(out / 'export-hashes.json')
old_hashes = read(old / 'export-hashes.json')
for path in sorted((old / 'rebuild').iterdir()):
    relative = str(path.relative_to(old))
    assert sha(path) == old_hashes[relative]['exported_sha256']
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    hashes[relative] = old_hashes[relative]
helper_path = out / 'rebuild/ip3-reuse-export.py'
helper_path.write_bytes(Path(__file__).read_bytes())
hashes['rebuild/ip3-reuse-export.py'] = {'original_sha256': sha(helper_path), 'exported_sha256': sha(helper_path)}
for filename in ('cpu-preflight.json', 'cpu-corrected-preflight.json', 'pmp-wall-bound-analysis.json'):
    target = out / 'rebuild' / filename
    target.write_bytes((repo / 'build/IP3' / filename).read_bytes())
    hashes[f'rebuild/{filename}'] = {'original_sha256': sha(target), 'exported_sha256': sha(target)}
scheduling_files = {f'scheduling/partition/{path.name}': path for path in partition_dir.iterdir() if path.is_file()}
scheduling_files.update({f'scheduling/idle-queue-replaced/{path.name}': path
                         for path in (repo / 'build/IP3/idle-benchqueue-replaced').iterdir() if path.is_file()})
scheduling_files.update({f'scheduling/idle-shardqueue-replaced/{path.name}': path
                         for path in (repo / 'build/IP3/idle-shardqueue-replaced').iterdir() if path.is_file()})
for filename in ('prepare-bench-shards.py', 'queue-cpu-bench-shards.py', 'cpu-bench-shards-driver.log'):
    scheduling_files[f'scheduling/{filename}'] = repo / 'build/IP3' / filename
for name in names[2:]:
    for suffix in ('launch-command.json', 'driver.log', 'driver.exit'):
        filename = f'{name}-{suffix}'
        scheduling_files[f'scheduling/commands/{filename}'] = repo / 'build/IP3' / filename
for relative, source in scheduling_files.items():
    original = source.read_bytes()
    portable = original.replace(str(repo).encode(), b'${REPO_ROOT}').replace(str(cy).encode(), b'${CHIPYARD_ROOT}')
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(portable)
    hashes[relative] = {'original_sha256': hashlib.sha256(original).hexdigest(),
                        'exported_sha256': sha(target), 'original_bytes': len(original), 'exported_bytes': len(portable)}
reuse = {
    'captured_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'IP3 reuses the exact CPU ELFs compiled for IP2; no CPU program was recompiled for IP3',
    'origin_ip2_commit': preflight['origin_ip2_commit'],
    'origin_ip2_cpu_summary_sha256': preflight['ip2_cpu_summary_sha256'],
    'historical_build_capture_sha256': sha(out / 'rebuild/capture.json'),
    'current_build_inputs_sha256': sha(repo / 'build/cpu-rebuilt/inputs.json'),
    'corrected_native_preflight_sha256': sha(repo / 'build/IP3/cpu-corrected-preflight.json'),
    'current_elf_hashes_match_ip2_preflight_and_ip3_campaigns': len(current),
    'elf_sha256': current,
    'simulator_sha256': simulator_hash,
    'campaign_provenance_sha256': {name: sha(path / 'provenance.json') for name, path in zip(names, campaigns)},
    'current_runner_sha256': sha(repo / 'IPs/IP2/scripts/run-regression.py'),
    'current_cpu_exporter_sha256': sha(repo / 'scripts/cpu-regression/summarize.py'),
    'reuse_export_helper_sha256': sha(Path(__file__)),
    'benchmark_partition_sha256': sha(partition_dir / 'partition-provenance.json'),
    'benchmark_scheduler_sha256': sha(repo / 'build/IP3/queue-cpu-bench-shards.py'),
    'benchmark_scheduling_events_sha256': sha(partition_dir / 'scheduling-events.jsonl'),
    'benchmark_partition_exact_original_rows_and_elfs_verified': len(derived_rows),
}
reuse_path = out / 'rebuild/ip3-reuse-capture.json'
reuse_path.write_text(json.dumps(reuse, indent=2) + '\n')
hashes['rebuild/ip3-reuse-capture.json'] = {'original_sha256': sha(reuse_path), 'exported_sha256': sha(reuse_path)}
(out / 'export-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
summary = read(out / 'summary.json')
rows = table(out / 'all-results.tsv')
comparison = table(out / 'baseline-comparison.tsv')
assert sum(row['baseline'] == 'PASS' and row['current'] == 'PASS' for row in comparison) == 391
groups = [('isa', 'RV64 ISA inventory'), ('benchmark-configured', 'Configured benchmarks'),
          ('benchmark-extra', 'Additional scalar benchmarks'), ('benchmark-dual', 'Additional two-hart benchmarks'),
          ('legacy-mt', 'Original legacy kernels'), ('chipyard-generic', 'Chipyard C/C++ and two-hart hello'),
          ('dual-hart-smoke', 'Explicit two-hart atomic smoke'), ('corrected-mt-supplement', 'Corrected multicore supplements')]
count_rows = []
for suite, label in [*groups, (None, '**Unique total**')]:
    counts = Counter(row['result'] for row in rows if suite is None or row['suite'] == suite)
    count_rows.append(f"| {label} | {sum(counts.values())} | {counts['PASS']} | {counts['FAIL']} | {counts['CYCLE_TIMEOUT']} | {counts['WALL_TIMEOUT']} |")
campaign_rows = []
for name, meta in zip(names, metadata):
    campaign_rows.append(f"| {name} | {len(meta['tests'])} | {meta['jobs']} | {meta['max_cycles']:,} | {meta['wall_timeout_seconds']:,} seconds |")
differences = [row for row in comparison if row['baseline'] != row['current']]
diff_text = ('| Test | IP1 | IP3 |\n| --- | --- | --- |\n' + '\n'.join(
    f"| `{row['test']}` | {row['baseline']} | {row['current']} |" for row in differences)) if differences else 'Every raw result classification matches IP1.'
pmp = next(row for row in rows if row['test'] == 'pmp')
non_utf8 = 0
for path in (out / 'campaigns').glob('*/*/simulation.log'):
    try:
        path.read_bytes().decode()
    except UnicodeDecodeError:
        non_utf8 += 1
finished = max(read(path / 'summary.json')['finished_utc'] for path in campaigns)
bounds = read(repo / 'build/IP3/pmp-wall-bound-analysis.json')
readme = f'''# IP3 full-SoC CPU simulation

Fresh simulation of `DualRocketNVDLAConfig` completed at {finished}. All **335 configured ISA tests** and **12 configured benchmarks** passed. The broader frozen inventory contains 422 unique programs; raw diagnostics remain nonpassing.

| Group | Total | PASS | FAIL | Cycle timeout | Wall timeout |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(count_rows)}

The exact 422 ELF binaries compiled for IP2 were reused. Every complete ELF hash matches IP2's published campaign evidence and the fresh IP3 campaigns; no CPU test was recompiled for IP3. The preserved [build capture](rebuild/capture.json) is historical IP2 evidence. The new [IP3 reuse capture](rebuild/ip3-reuse-capture.json) records current verification of that reuse and the actual IP3 simulator identity. [Compiler commands](rebuild/commands.json), [build inputs](rebuild/inputs.json), and [loadable-section comparison with IP1](rebuild/baseline-loadable-comparison.json) remain available. IP2's source-pin and Python optimization guards were added after the original compilation; the historical capture does not claim a contemporaneous compiler-run hash for the final builder.

[Final outcomes](all-results.tsv), [all attempts](attempts.tsv), [IP1 comparison](baseline-comparison.tsv), and [aggregate evidence](summary.json) retain the actual classifications. All **391 IP1 PASS programs passed again**, with no previous PASS becoming nonpassing. Raw classification differences are:

{diff_text}

A cycle timeout is the actual TestDriver stop at the recorded cycle limit; a wall timeout is host termination at the recorded time limit. IP1 initially used a 10-million-cycle benchmark ceiling, whereas IP3 uses 2 million for the shorter benchmark partition. Neither timeout classification is converted to a pass.

## Method and limits

The simulator contains the complete dual-Rocket ChipTop with small NVDLA, behavioral memories and DRAMSim2. CPU programs boot against the RTL. `+loadmem` loads ELF contents into simulated memory, so serial-host program transfer is not covered. Accelerator arithmetic, DMA, PLIC polling and deliberate failure controls are documented separately in the [NVDLA report](../nvdla/README.md).

All CPU campaigns use seed 1 and simulator SHA256:

```text
{simulator_hash}
```

| Campaign | Tests | Workers | Cycle ceiling | Wall limit per test |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(campaign_rows)}

The 72 shorter benchmarks were divided into four disjoint groups using descending IP2 host runtimes and assignment to the least-loaded group. Historical group totals were 1360.873, 1351.825, 1358.476 and 1364.085 seconds. All original manifest fields and ELF identities remained identical. The [partition evidence](scheduling/partition/partition-provenance.json) records every weight, assignment and hash. ISA completion contributes two worker slots; each explicitly coordinated NVDLA release can contribute one additional slot immediately, even before ISA finishes. Benchmark scheduling uses at most four heavy workers. The earlier ISA/PMP phase briefly overlapped a fifth EDA/accelerator worker. [Scheduling events](scheduling/partition/scheduling-events.jsonl), [the scheduler](scheduling/queue-cpu-bench-shards.py) and exact commands preserve the actual benchmark schedule. The [original idle queue](scheduling/idle-queue-replaced/change.json) and [first idle shard scheduler](scheduling/idle-shardqueue-replaced/change.json) were replaced before any benchmark launched; both code and event histories are retained, and neither replacement interrupted a simulation.

PMP ran separately and passed in {pmp['wall_seconds']} seconds. Host times include contention with other verification work and are not CPU performance measurements. A blank cycle field means the non-tracing log did not print a cycle count. These campaigns contain exactly one attempt per test and no retry-dependent final outcomes.

The initial PMP and benchmark wall limits were selected conservatively from [historical pre-correction host runtimes](rebuild/pmp-wall-bound-analysis.json): {bounds['matched_virtual_pass_tests']} completed virtual tests on the original native showed a median ratio to IP2 of {bounds['median_ratio']:.3f} and a maximum of {bounds['maximum_ratio']:.3f}. Applying the maximum to IP2's PMP time projected about {bounds['pmp_projection_at_maximum_observed_ratio']:.0f} seconds; the initial 7200-second limit provided additional margin. These observations guided host timeouts and do not measure processor performance or count toward corrected-native acceptance. The [interrupted original-native campaign](../cpu-original-native/README.md) is preserved separately; every final result above comes from the corrected simulator.

PASS requires exit zero, native Verilog `$finish`, absence of simulator failure markers and every declared required output string. A host timeout remains a timeout even if termination prints a finish message or returns zero. The upstream NVDLA native build omits `--assert`; generated Chipyard procedural monitors and TestDriver failure checks remain active, while vendor macro-gated assertions and coverage constructs are excluded. The [assertion-scope audit](../assertions/README.md) records the actual generated C++ evidence and remaining empty assertion-helper instances.

## Diagnostic and software-oracle qualification

The configured 335-test ISA subset excludes the extra Zicboz/Zbc and misaligned-data probes that failed or timed out in IP1. Those features and access expectations remain outside this configuration. A `v` suffix denotes the virtual-memory environment, not vector instructions. A passing `rv64ssvnapot-p-napot` accepts the unsupported page fault and does not establish Svnapot support.

The 49 original legacy matrix/vector kernels retain the [IP1 oracle audit](../../../../IP1/docs/dual-rocket/reports/simulation/README.md): 22 matrix variants have incompatible dataset geometry; some reported passes have out-of-bounds accesses or incomplete two-hart success aggregation. The `ce_matmul` output bounds, `vvadd1` tail accesses, original matrix wrapper, and hart-0-only `bc_matmul`/`dc_matmul` cases remain qualified. Raw outcomes and the three separately named corrected supplements are preserved.

The explicit dual-hart smoke requires both harts, peer-data visibility and 256 atomic increments. Two-hart hello requires both hart-identifying outputs. Physical ISA tests park the secondary hart; virtual-memory tests run background traffic on it. Original names beginning `mt-` alone do not prove both harts participated; additional `-dual` variants use the two-hart startup.

IP1's Spike comparison and diagnostic traces are inherited reference evidence, not fresh IP3 Spike runs. Matching software-test outcomes do not establish exhaustive ISA, coherence or peripheral verification. These campaigns do not cover Linux, external JTAG/debug, gate-level timing, physical signoff, formal proof or coverage percentages.

## Evidence and replay

Full non-tracing logs, commands, per-test results and campaign metadata are retained under `campaigns/`. {non_utf8} logs contain non-UTF8 bytes; the exporter preserves them and normalizes only workspace path bytes. Binary ELFs, simulator build trees and DRAMSim working files remain external artifacts. Portable paths use `${{REPO_ROOT}}`, `${{CHIPYARD_ROOT}}` and `${{CAMPAIGN_ROOT}}/<campaign>`. [Export hashes](export-hashes.json) distinguish original from exported bytes; historical rebuild hashes are carried forward unchanged with their matching files.

Use the [shared CPU workflow](../../../../../scripts/cpu-regression/README.md) to rebuild the pinned inventory. The archived manifests and commands provide the exact test split and limits. The [CPU exporter](../../../../../scripts/cpu-regression/summarize.py) checks all 422 identities, generated configured-test sets, simulator/ELF identity, PASS log requirements and IP1 regressions before accepting the report.
'''
(out / 'README.md').write_text(readme)
print(json.dumps({'summary': summary, 'reuse_verified': len(current), 'non_utf8_logs_preserved': non_utf8}, indent=2))
