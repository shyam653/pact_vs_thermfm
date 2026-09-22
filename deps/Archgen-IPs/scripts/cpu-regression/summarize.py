#!/usr/bin/env python3
"""Export complete CPU campaign evidence, retaining failed attempts and retries."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

if sys.flags.optimize:
    raise RuntimeError('Evidence validation requires assertions enabled; remove -O/PYTHONOPTIMIZE')

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--campaign', type=Path, action='append', required=True,
               help='Chronological order; a later explicit retry supersedes final outcome only')
p.add_argument('--chipyard-root', type=Path, required=True)
p.add_argument('--config', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert len({x.name for x in a.campaign}) == len(a.campaign), 'Campaign basenames must be unique'
repo = Path(__file__).resolve().parents[2]
out, cy = a.output.resolve(), a.chipyard_root.resolve()
if out.exists():
    p.error('output already exists')
baseline_path = repo / 'IPs/IP1/docs/dual-rocket/reports/simulation/all-results.tsv'
baseline = {r['test']: r for r in csv.DictReader(baseline_path.open(), delimiter='\t')}
final, history, provenance, raw_hashes = {}, [], {}, {}
sim_hashes = set()
elf_hashes = {}
def sha(data):
    return hashlib.sha256(data).hexdigest()
replacements = [(str(repo), '${REPO_ROOT}'), (str(cy), '${CHIPYARD_ROOT}')]
for campaign in a.campaign:
    replacements.append((str(campaign.resolve()), '${CAMPAIGN_ROOT}/' + campaign.name))
replacements.sort(key=lambda x: len(x[0]), reverse=True)
def portable(text):
    for before, after in replacements:
        text = text.replace(before, after)
    return text
def export(source, relative):
    data = source.read_bytes()
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # Legacy programs may emit arbitrary bytes. Preserve those bytes while
    # normalizing only the documented workspace path identifiers.
    exported = data
    for before, after in replacements:
        exported = exported.replace(before.encode(), after.encode())
    target.write_bytes(exported)
    raw_hashes[str(relative)] = {'original_sha256': sha(data), 'exported_sha256': sha(target.read_bytes())}

for campaign in a.campaign:
    campaign = campaign.resolve()
    meta = json.loads((campaign / 'provenance.json').read_text())
    summary = json.loads((campaign / 'summary.json').read_text())
    records = list(csv.DictReader((campaign / 'results.tsv').open(), delimiter='\t'))
    assert len(records) == summary['total'] == len(meta['tests']), 'Incomplete campaign'
    assert len({r['test'] for r in records}) == len(records), 'Duplicate test outcome'
    assert {r['test'] for r in records} == {r['test'] for r in meta['tests']}, 'Campaign test identity mismatch'
    assert Counter(r['result'] for r in records) == summary['counts'], 'Campaign summary mismatch'
    sim_hashes.add(meta['simulator_sha256'])
    for test in meta['tests']:
        assert test['test'] not in elf_hashes or elf_hashes[test['test']] == test['sha256'], 'Retry ELF changed'
        elf_hashes[test['test']] = test['sha256']
    provenance[campaign.name] = summary
    for filename in ['provenance.json', 'summary.json', 'results.tsv']:
        export(campaign / filename, Path('campaigns') / campaign.name / filename)
    for record in records:
        work = campaign / record['test']
        native = json.loads((work / 'result.json').read_text())
        assert all(str(native[k]) == record[k] for k in record), 'Per-test outcome mismatch'
        log = (work / 'simulation.log').read_text(errors='replace')
        if record['result'] == 'PASS':
            assert record['exit_status'] == '0' and 'Verilog $finish' in log
            assert not re.search(r'\*\*\* FAILED \*\*\*|%Error:|Aborting\.\.\.', log)
            spec = next(t for t in meta['tests'] if t['test'] == record['test'])
            assert all(marker in log for marker in spec['required_stdout'])
        record['campaign'] = campaign.name
        record['log'] = str(Path('campaigns') / campaign.name / record['test'] / 'simulation.log')
        history.append(record)
        final[record['test']] = record
        for filename in ['simulation.log', 'command.txt', 'result.json']:
            export(work / filename, Path('campaigns') / campaign.name / record['test'] / filename)
assert len(sim_hashes) == 1, 'Campaign simulator identity changed'
assert set(final) == set(baseline) and len(final) == 422, 'Frozen test inventory mismatch'
name = 'chipyard.harness.TestHarness.' + a.config
definition = (cy / 'sims/verilator/generated-src' / name / (name + '.d')).read_text()
configured = {'isa': set(), 'benchmarks': set()}
for kind, body in re.findall(r'^\S+-(asm|bmark)-tests\s*=\s*(.*?)(?=\n\n)', definition, re.M | re.S):
    configured['isa' if kind == 'asm' else 'benchmarks'].update(body.replace('\\\n', ' ').split())
configured['benchmarks'] = {x.removesuffix('.riscv') for x in configured['benchmarks']}
assert len(configured['isa']) == 335 and len(configured['benchmarks']) == 12
assert all(configured[k] <= set(final) for k in configured)
comparison = [{'test': n, 'baseline': baseline[n]['result'], 'current': final[n]['result'],
               'suite': final[n]['suite']} for n in sorted(final)]
regressions = [r for r in comparison if r['baseline'] == 'PASS' and r['current'] != 'PASS']
summary = {'config': a.config, 'total': len(final), 'counts': dict(Counter(r['result'] for r in final.values())),
           'configured': {k: dict(Counter(final[n]['result'] for n in names)) for k, names in configured.items()},
           'baseline_passing_tests_now_nonpassing': regressions, 'campaigns': provenance,
           'simulator_sha256': next(iter(sim_hashes)), 'baseline_table_sha256': sha(baseline_path.read_bytes()),
           'exporter_sha256': sha(Path(__file__).read_bytes()),
           'failed_attempts_retained': True, 'all_tests_means': 'Frozen 422-test applicable RV64 CPU inventory; not exhaustive verification'}
for filename, rows in [('all-results.tsv', [final[n] for n in sorted(final)]), ('attempts.tsv', history), ('baseline-comparison.tsv', comparison)]:
    with (out / filename).open('w') as f:
        w = csv.DictWriter(f, list(rows[0]), delimiter='\t')
        w.writeheader()
        w.writerows(rows)
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(out / 'export-hashes.json').write_text(json.dumps(raw_hashes, indent=2) + '\n')
print(json.dumps(summary, indent=2))
raise SystemExit(bool(regressions or any(final[n]['result'] != 'PASS' for names in configured.values() for n in names)))
