#!/usr/bin/env python3
"""Validate a completed IP's files, local documentation links and hash manifest."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import unquote

if sys.flags.optimize:
    raise RuntimeError('Publication validation requires Python assertions enabled; remove -O/PYTHONOPTIMIZE')
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('ip', type=Path)
p.add_argument('--write-manifest', action='store_true')
p.add_argument('--check-index', action='store_true',
               help='Require the staged IP and shared scripts to match the validated files')
a = p.parse_args()
ip = a.ip.resolve()
repo = Path(__file__).resolve().parent.parent
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_hashes(root, entries):
    """Check exported bytes using paths confined to their evidence directory."""
    assert entries, f'Empty evidence hash inventory: {root}'
    for relative, expected in entries.items():
        path = (root / relative).resolve()
        assert not Path(relative).is_absolute() and path.is_relative_to(root.resolve()), \
            f'Evidence path escapes its directory: {relative}'
        assert path.is_file() and digest(path) == expected, f'Changed evidence: {root / relative}'

def check_export_hashes(root):
    exported = json.loads((root / 'export-hashes.json').read_text())
    check_hashes(root, {name: record['exported_sha256'] for name, record in exported.items()})

def check_fft_evidence(ip, accelerator, generation):
    root = ip / 'docs/reports/fft'
    check_hashes(root, {name: record['exported_sha256']
                       for name, record in accelerator['build_evidence'].items()})
    required_build = {'build/build-provenance.json', 'build/reference.json', 'build/fft_vectors.h'}
    assert required_build <= set(accelerator['build_evidence']), 'Missing FFT build evidence hashes'
    build = json.loads((root / 'build/build-provenance.json').read_text())
    reference = json.loads((root / 'build/reference.json').read_text())
    assert accelerator['published_build_inputs_verified'] == build['inputs'], 'FFT source inventories differ'
    check_hashes(ip, build['inputs'])
    assert digest(ip / 'scripts/build-fft-tests.py') == build['builder_sha256'], 'FFT test builder changed'
    assert digest(ip / 'scripts/summarize-fft.py') == accelerator['exporter_sha256'], 'FFT exporter changed'
    assert digest(ip / 'tests/fft_reference.py') == reference['generator_sha256'], 'FFT reference generator changed'
    assert digest(root / 'build/fft_vectors.h') == build['reference_header_sha256'] == reference['header_sha256'], \
        'FFT vector header changed'
    assert accelerator['source_build_provenance_sha256'] == \
        accelerator['build_evidence']['build/build-provenance.json']['original_sha256'], \
        'FFT original build-provenance hashes differ'
    assert accelerator['reference'] == {key: value for key, value in reference.items() if key != 'vectors'}, \
        'FFT reference summaries differ'
    assert len(reference['vectors']) == reference['cases'] == 135, 'FFT vector inventory differs'
    assert len({vector['name'] for vector in reference['vectors']}) == reference['cases'], 'Duplicate FFT vectors'
    assert sum(vector['dft_check'] for vector in reference['vectors']) == reference['independent_dft_cases'] == 94
    assert reference['upstream_known_answer_verified'] is True
    assert 0 <= reference['max_independent_dft_component_error_lsb'] <= reference['dft_component_error_limit_lsb']
    assert reference['fft_revision'] == build['fft_revision'] == \
        generation['components']['generators/fft-generator']['commit'], 'FFT generator revisions differ'
    for vector in reference['vectors']:
        assert len(vector['input']) == len(vector['expected']) == reference['points'] == 8
    variants = {record['name']: record for record in build['builds']}
    normal = {'fft-single': 'PASS FFT single-hart', 'fft-dual': 'PASS FFT dual-hart',
              'fft-upstream': 'PASS: FFT Test Passed'}
    assert len(variants) == len(build['builds']) == 4 and set(variants) == set(normal) | {'fft-negative-control'}
    assert accelerator['seeds'] == [1, 2, 3]
    assert accelerator['normal_simulations'] == accelerator['normal_passes'] == 9
    assert accelerator['negative_controls'] == 1 and accelerator['negative_control_rejected'] is True
    expected_runs = {(seed, name) for seed in accelerator['seeds'] for name in normal}
    seen, negatives, transforms = set(), 0, 0
    assert len(accelerator['results']) == 10, 'FFT result inventory differs'
    for record in accelerator['results']:
        name = record['test']
        assert name in variants and record['elf_sha256'] == variants[name]['sha256'], 'FFT ELF identities differ'
        check_hashes(root, {record['log']: record['exported_log_sha256']})
        log = (root / record['log']).read_text()
        if record['negative_control']:
            negatives += 1
            assert name == 'fft-negative-control' and variants[name]['negative_control'] is True
            assert record['result'] == 'FAIL' and record['exit_status'] != 0, 'FFT negative control did not fail'
            assert 'FAIL FFT: numerical mismatch' in log and \
                'job=0x0000000000000000 lane=0x0000000000000000' in log and \
                'got=0x0000000000000000 expected=0x0000000000000001' in log, \
                'FFT negative control did not reject the deliberate corrupted answer'
        else:
            identity = (record['seed'], name)
            assert identity in expected_runs and identity not in seen, 'Missing/duplicate FFT seed or variant'
            seen.add(identity)
            assert variants[name]['negative_control'] is False
            assert record['result'] == 'PASS' and record['exit_status'] == 0 and normal[name] in log
            assert re.search(r'^- .*TestDriver\.v:\d+: Verilog \$finish$', log, re.M), 'FFT simulator finish missing'
            assert not re.search(r'\*\*\* FAILED \*\*\*|%Error:|Aborting\.\.\.', log), 'FFT simulator failure in passing log'
            if name == 'fft-upstream':
                transforms += 1
            else:
                # The frozen published FFT suite repeats every vector twice on
                # each active hart; confirm its own completion counters too.
                harts = 2 if name == 'fft-dual' else 1
                assert variants[name]['harts'] == harts
                jobs = re.search(r'\bjobs=(0x[0-9a-f]+)\b', log)
                assert jobs and int(jobs[1], 16) == reference['cases'] * 2 * harts, 'Incomplete FFT transform coverage'
                transforms += int(jobs[1], 16)
    assert seen == expected_runs and negatives == 1
    assert transforms == accelerator['normal_completed_transforms'] == 2433

def check_nvdla_support(ip, generation, simulator_sha, helpers):
    """Bind supplementary and historical evidence to its actual source version."""
    reports = ip / 'docs/reports'
    for name in ['assertions', 'standalone', 'firmware-history', 'helper-equivalence-final',
                 'hardware-history', 'cpu-original-native']:
        check_export_hashes(reports / name)
    assertions = json.loads((reports / 'assertions/summary.json').read_text())
    assert assertions['native_simulator_sha256'] == simulator_sha
    inventory = json.loads((reports / 'assertions/source-inventory.json').read_text())
    expected_inventory = {'rtl/' + name: value for name, value in generation['rtl_files'].items()
                          if Path(name).suffix in {'.v', '.sv', '.vh', '.svh'}}
    assert inventory == expected_inventory and len(inventory) == assertions['hdl_source_count']
    standalone = reports / 'standalone'
    provenance = json.loads((standalone / 'provenance.json').read_text())
    check_hashes(ip / 'tests', provenance['sources'])
    assert provenance['rtl_sha256'] == digest(ip / 'rtl/gen-collateral/nvdla_small.preprocessed.v')
    assert (standalone / 'build.exit').read_text().strip() == '0'
    result = json.loads((standalone / 'summary.json').read_text())
    assert result['all_passed'] is True and len(result['results']) == 2
    assert sorted(record['seed'] for record in result['results']) == [1, 17]
    for record in result['results']:
        assert record['passed'] is True and record['exit'] == 0
        assert f"+verilator+seed+{record['seed']}" in record['command']
        assert '+verilator+rand+reset+2' in record['command']
        log = (standalone / f"seed-{record['seed']}.log").read_text()
        markers = re.findall(r'^PASS NVDLA[^\r\n]*$', log, re.MULTILINE)
        final = 'PASS NVDLA standalone engines cycles=16762 (PLIC emulated; CPU/cache absent)'
        assert markers == [*helpers['normal_markers'](), final] and 'FAIL' not in log
    history = reports / 'firmware-history'
    metadata = json.loads((history / 'summary.json').read_text())
    assert metadata['schema_version'] == 2
    check_hashes(history, {metadata['optimized_source_path']: metadata['optimized_source_sha256']})
    original_map = json.loads((history / 'original-source-map.json').read_text())
    check_hashes(history, {record['archived_path']: record['original_sha256']
                          for record in original_map.values()})
    assert metadata['original_source_sha256'] == original_map['tests/nvdla_test.c']['original_sha256']
    assert metadata['original_outcome'] == 'WALL_TIMEOUT' and metadata['original_final_pass'] is False
    original = json.loads((history / 'original-campaign/nvdla-dual/result.json').read_text())
    assert original['result'] == metadata['original_outcome']
    assert original['wall_seconds'] == metadata['original_wall_seconds']
    original_log = (history / 'original-campaign/nvdla-dual/simulation.log').read_text()
    assert re.findall(r'^PASS NVDLA[^\r\n]*$', original_log, re.MULTILINE) == \
        helpers['normal_markers']()[:metadata['original_completed_sdp_jobs']]
    probe = json.loads((history / 'helper-equivalence/summary.json').read_text())
    assert probe['source_sha256'] == metadata['optimized_source_sha256']
    assert {record['language'] for record in probe['results']} == {'c', 'cpp'}
    assert len(probe['results']) == 2 and all(record['exit_status'] == 0 for record in probe['results'])
    historical_helpers = history / 'helper-equivalence/helpers.inc'
    assert historical_helpers.read_text() in (history / metadata['optimized_source_path']).read_text()
    final_helpers = reports / 'helper-equivalence-final'
    final_probe = json.loads((final_helpers / 'summary.json').read_text())
    assert final_probe['source_sha256'] == digest(ip / 'tests/nvdla_test.c')
    assert digest(final_helpers / 'helpers.inc') == digest(historical_helpers) == \
        final_probe['unchanged_historical_helper_sha256']
    assert (final_helpers / 'helpers.inc').read_text() in (ip / 'tests/nvdla_test.c').read_text()
    assert len(final_probe['results']) == 2 and {r['language'] for r in final_probe['results']} == {'c', 'cpp'}
    assert all(record['exit_status'] == 0 for record in final_probe['results'])
    hardware_history = reports / 'hardware-history'
    correction = json.loads((hardware_history / 'summary.json').read_text())
    assert correction['schema_version'] == 1
    assert correction['historical_simulator_sha256'] == metadata['historical_simulator_sha256']
    assert correction['historical_numerical_source_sha256'] == metadata['optimized_source_sha256']
    assert correction['final_numerical_source_sha256'] == final_probe['source_sha256']
    assert correction['corrected_nvdla_rtl_sha256'] == digest(ip / 'rtl/gen-collateral/nvdla_small.preprocessed.v')
    assert correction['correction_patch_sha256'] == digest(hardware_history / 'correction.patch') == \
        digest(ip / 'patches/0003-define-small-sdp-lut-readbacks.patch')
    check_hashes(hardware_history, correction['old_source_files'])
    assert correction['old_source_files'] == {record['archived_path']: record['original_sha256']
                                            for record in correction['old_source_map'].values()}
    assert digest(hardware_history / 'old-tests/nvdla_test.c') == metadata['optimized_source_sha256']
    old_generation = json.loads((hardware_history / 'old-generation.json').read_text())
    old_rtl, new_rtl = old_generation['rtl_files'], generation['rtl_files']
    assert old_rtl.keys() == new_rtl.keys()
    assert {name for name in old_rtl if old_rtl[name] != new_rtl[name]} == {'gen-collateral/nvdla_small.preprocessed.v'}
    assert old_rtl['gen-collateral/nvdla_small.preprocessed.v'] == correction['historical_nvdla_rtl_sha256']
    old_build = json.loads((hardware_history / correction['historical_build_provenance']).read_text())
    assert old_build['inputs'] == {name: record['original_sha256']
                                   for name, record in correction['old_source_map'].items()}
    assert old_build['builder_sha256'] == digest(hardware_history / 'old-builder.py')
    old_binaries = {record['name']: record for record in old_build['builds']}
    assert len(old_binaries) == len(old_build['builds']) == 3
    old_identities = {('normal-seed1', 'nvdla-dual'),
                      ('controls', 'nvdla-negative-control'), ('controls', 'nvdla-timeout-control')}
    assert len(correction['records']) == len(old_identities)
    assert {(record['campaign'], record['test']) for record in correction['records']} == old_identities
    for record in correction['records']:
        campaign, name = record['campaign'], record['test']
        directory = hardware_history / 'old-campaigns' / campaign
        provenance = json.loads((directory / 'provenance.json').read_text())
        assert provenance['simulator_sha256'] == metadata['historical_simulator_sha256']
        tests = {test['test']: test for test in provenance['tests']}
        assert record['elf_sha256'] == tests[name]['sha256'] == old_binaries[name]['sha256']
        result = json.loads((directory / name / 'result.json').read_text())
        log = re.sub(r'(?m)^- \$\{CHIPYARD_ROOT\}/', '- /${CHIPYARD_ROOT}/',
                     (directory / name / 'simulation.log').read_text())
        assessment = helpers['assess'](name, result, log)
        assert assessment['evidence_valid'] is True
        expected = {key: result[key] for key in ['test', 'result', 'exit_status', 'wall_seconds']}
        assert record == expected | assessment | {'campaign': campaign, 'elf_sha256': old_binaries[name]['sha256']}
    old_cpu = reports / 'cpu-original-native'
    cpu_history = json.loads((old_cpu / 'summary.json').read_text())
    assert cpu_history['status'] == 'INTERRUPTED_FOR_RTL_CORRECTION'
    assert cpu_history['corrected_cpu_acceptance'] is False and cpu_history['benchmark_started'] is False
    assert cpu_history['simulator_sha256'] == metadata['historical_simulator_sha256']
    for campaign, completed in cpu_history['completed_results'].items():
        directory = old_cpu / campaign
        rows = list(csv.DictReader((directory / 'results.tsv').open(), delimiter='\t'))
        assert len(rows) == completed['count'] and dict(Counter(row['result'] for row in rows)) == completed['counts']
        assert completed['summary_existed'] is False and not (directory / 'summary.json').exists()
        assert json.loads((directory / 'provenance.json').read_text())['simulator_sha256'] == cpu_history['simulator_sha256']
    for record in cpu_history['interrupted_tests']:
        assert record['status'] == cpu_history['status']
        assert not (old_cpu / record['campaign'] / record['test'] / 'result.json').exists()

def check_nvdla_evidence(ip, accelerator, generation):
    """Validate portable full-SoC evidence independently of its summary counts."""
    root = ip / 'docs/reports/nvdla'
    repository = ip.parents[1]
    assert accelerator['schema_version'] == 1
    assert accelerator['evidence_scope'] == 'full-soc-dual-rocket-nvdla'
    exporter = ip / 'scripts/summarize-nvdla.py'
    source = exporter.read_bytes()
    assert hashlib.sha256(source).hexdigest() == accelerator['exporter_sha256'], 'NVDLA exporter changed'
    # The hash-checked repository exporter defines pure log parsers. Its guarded
    # CLI is not invoked, and compile uses these exact bytes without a pyc cache.
    helpers = {'__name__': 'nvdla_publication_helpers', '__file__': str(exporter)}
    exec(compile(source, str(exporter), 'exec'), helpers)
    check_nvdla_support(ip, generation, accelerator['simulator_sha256'], helpers)
    controls, fields = helpers['CONTROLS'], helpers['FIELDS']
    evidence = accelerator['exported_evidence']
    assert evidence == json.loads((root / 'export-hashes.json').read_text()), 'NVDLA export inventories differ'
    check_hashes(root, {name: record['exported_sha256'] for name, record in evidence.items()})
    for name, record in evidence.items():
        assert all(re.fullmatch(r'[0-9a-f]{64}', record[key]) for key in ('original_sha256', 'exported_sha256'))
        assert (root / name).stat().st_size == record['bytes'], 'NVDLA evidence size changed'
    actual_evidence = {str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()
                       and path not in {root / 'summary.json', root / 'export-hashes.json', root / 'README.md'}}
    assert actual_evidence == set(evidence), 'Missing or unlisted NVDLA evidence files'
    build = json.loads((root / 'build/build-provenance.json').read_text())
    current_inputs = {str(path.relative_to(ip)): digest(path)
                      for path in sorted((ip / 'tests').iterdir()) if path.is_file()}
    assert current_inputs == build['inputs'] == accelerator['published_build_inputs_verified'], 'NVDLA test sources changed'
    assert digest(ip / 'scripts/build-nvdla-tests.py') == build['builder_sha256'] == accelerator['builder_sha256'], \
        'NVDLA test builder changed'
    check_hashes(repository, {accelerator['runner_source']: accelerator['runner_sha256']})
    assert accelerator['source_build_provenance_sha256'] == evidence['build/build-provenance.json']['original_sha256']
    assert build['nvdla_revision'] == accelerator['nvdla_revision'] == helpers['REVISION'] == \
        generation['components']['generators/nvdla']['commit'], 'NVDLA revisions differ'
    generated_dts = list((ip / 'docs/artifacts').glob('*' + generation['config'].split('.')[-1] + '.dts'))
    assert len(generated_dts) == 1, 'Missing/ambiguous generated NVDLA device tree'
    assert digest(generated_dts[0]) == digest(root / 'build/test-device-tree.dts') == build['dts_sha256'] == \
        accelerator['dts_sha256'] == evidence['build/test-device-tree.dts']['original_sha256'], \
        'NVDLA test device tree differs from generated SoC'
    dts = generated_dts[0].read_text()
    nodes = re.findall(r'\bnvdla@10040000\s*\{([^}]+)\}', dts)
    assert len(nodes) == 1 and '"nvidia,nv_small"' in nodes[0]
    irq = re.search(r'\binterrupts\s*=\s*<\s*(0x[0-9a-fA-F]+|[0-9]+)\s*>', nodes[0])
    assert irq and 0 < int(irq[1], 0) < 32
    assert int(irq[1], 0) == build['nvdla_plic_source'] == accelerator['nvdla_plic_source'], 'NVDLA IRQ differs'
    assert sorted(re.findall(r'\bcpu@([0-9a-fA-F]+)\s*\{', dts)) == ['0', '1'], 'NVDLA SoC hart inventory differs'
    binaries = {record['name']: record for record in build['builds']}
    assert len(build['builds']) == len(binaries) == 3 and set(binaries) == {'nvdla-dual', *controls}
    assert accelerator['elf_sha256'] == {name: binary['sha256'] for name, binary in binaries.items()}
    used_evidence = {'build/build-provenance.json', 'build/manifest.tsv', 'build/negative-control.tsv',
                     'build/test-device-tree.dts'}
    for name, binary in binaries.items():
        used_evidence.update({f'build/{name}-command.json', f'build/{name}-build.log'})
        assert re.fullmatch(r'[0-9a-f]{64}', binary['sha256']) and binary['harts'] == 2
        assert binary['negative_control'] is (name in controls)
        argv = json.loads((root / f'build/{name}-command.json').read_text())
        assert f"-DNVDLA_IRQ={build['nvdla_plic_source']}" in argv
        defines = {arg for arg in argv if arg.startswith(('-DNVDLA_NEGATIVE_CONTROL', '-DNVDLA_SKIP_ENABLE', '-DNVDLA_POLL_LIMIT'))}
        wanted = ({'-DNVDLA_NEGATIVE_CONTROL=1'} if name == 'nvdla-negative-control' else
                  {'-DNVDLA_SKIP_ENABLE=1', '-DNVDLA_POLL_LIMIT=4096'} if name == 'nvdla-timeout-control' else set())
        assert defines == wanted and argv[argv.index('-o') + 1] == binary['binary'], 'NVDLA build variant differs'
        assert {'<ip3>/tests/start.S', '<ip3>/tests/nvdla_test.c'} <= set(argv)
        assert argv[argv.index('-T') + 1] == '<ip3>/tests/link.ld'
    ini_hashes = accelerator['dramsim_ini_sha256']
    check_hashes(root / 'runtime/dramsim2_ini', ini_hashes)
    assert {name.removeprefix('runtime/dramsim2_ini/') for name in evidence
            if name.startswith('runtime/dramsim2_ini/')} == set(ini_hashes)
    used_evidence.update(f'runtime/dramsim2_ini/{name}' for name in ini_hashes)

    def read_table(relative):
        with (root / relative).open(newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            return reader.fieldnames, list(reader)

    attempts = accelerator['attempts']
    by_attempt = {(record['campaign'], record['test']): record for record in attempts}
    assert len(by_attempt) == len(attempts), 'Duplicate NVDLA attempts'
    campaign_ids, seen_attempts, ordered_attempts, selected, identities = set(), set(), [], {}, set()
    for index, campaign in enumerate(accelerator['campaigns'], 1):
        cid, negative, seed = campaign['id'], campaign['negative_control'], campaign['seed']
        assert type(negative) is bool and type(seed) is int and (negative or seed in (1, 2, 3))
        assert cid == f"{'control' if negative else 'normal'}-{index:02d}-seed{seed}" and cid not in campaign_ids
        campaign_ids.add(cid)
        prefix = f'campaigns/{cid}'
        assert campaign['evidence'] == [f'{prefix}/{filename}' for filename in
                                        ('provenance.json', 'summary.json', 'results.tsv', 'manifest.tsv')]
        used_evidence.update(campaign['evidence'])
        meta = json.loads((root / prefix / 'provenance.json').read_text())
        summary = json.loads((root / prefix / 'summary.json').read_text())
        identities.add((meta['simulator'], meta['chipyard_root']))
        assert meta['simulator_sha256'] == accelerator['simulator_sha256'], 'NVDLA simulator identity differs'
        assert meta['runner_sha256'] == accelerator['runner_sha256']
        assert meta['dramsim_ini_sha256'] == ini_hashes and meta['seed'] == seed
        assert campaign['settings'] == {key: meta[key] for key in ('jobs', 'max_cycles', 'wall_timeout_seconds', 'loadmem')}
        assert type(meta['loadmem']) is bool
        assert all(type(meta[key]) is int and meta[key] > 0 for key in ('jobs', 'max_cycles', 'wall_timeout_seconds'))
        assert campaign['started_utc'] == meta['started_utc'] and campaign['finished_utc'] == summary['finished_utc']
        assert meta['manifest_sha256'] == evidence[f'{prefix}/manifest.tsv']['original_sha256']
        tests = {row['test']: row for row in meta['tests']}
        assert len(tests) == len(meta['tests']) and tests
        assert set(tests).issubset(controls) if negative else set(tests) == {'nvdla-dual'}
        _, manifest = read_table(f'{prefix}/manifest.tsv')
        for row in manifest:
            row['required_stdout'] = json.loads(row.get('required_stdout') or '[]')
            row['sha256'] = binaries[row['test']]['sha256']
        assert manifest == meta['tests'], 'NVDLA manifest differs from campaign tests'
        columns, rows = read_table(f'{prefix}/results.tsv')
        assert columns == fields
        records = {row['test']: row for row in rows}
        assert len(rows) == len(records) == len(tests) == summary['total'] and set(records) == set(tests)
        assert dict(Counter(row['result'] for row in rows)) == summary['counts'] == campaign['counts']
        history = sorted(name for name in evidence if name.startswith(f'{prefix}/resume-history/'))
        assert campaign['resume_history'] == history, 'NVDLA resume history was omitted or duplicated'
        used_evidence.update(history)
        for name in history:
            if name.endswith('/provenance.json'):
                resumed = json.loads((root / name).read_text())
                keys = ('simulator', 'simulator_sha256', 'chipyard_root', 'dramsim_ini_sha256', 'manifest',
                        'manifest_sha256', 'max_cycles', 'wall_timeout_seconds', 'seed', 'loadmem', 'tests', 'runner_sha256')
                assert all(resumed[key] == meta[key] for key in keys)
                assert resumed['original_provenance_sha256'] == evidence[f'{prefix}/provenance.json']['original_sha256']
        for name, test in tests.items():
            identity = (cid, name)
            assert identity in by_attempt and identity not in seen_attempts, 'Missing/duplicate NVDLA attempt'
            seen_attempts.add(identity)
            attempt = by_attempt[identity]
            ordered_attempts.append(attempt)
            assert test['sha256'] == binaries[name]['sha256'] and test['binary'] == binaries[name]['binary']
            log_name = f'{prefix}/{name}/simulation.log'
            result_name, command_name = f'{prefix}/{name}/result.json', f'{prefix}/{name}/command.txt'
            used_evidence.update({log_name, result_name, command_name})
            record = json.loads((root / result_name).read_text())
            assert set(record) == set(fields) and record['test'] == name and record['suite'] == test['suite']
            assert {key: str(record[key]) for key in fields} == records[name]
            assert record['result'] in helpers['STATUS'] and type(record['exit_status']) is int
            assert record['log'] == f'<campaign:{cid}>/{name}/simulation.log'
            command = shlex.split((root / command_name).read_text())
            expected_command = [meta['simulator'], '+permissive', '+dramsim',
                                f"+dramsim_ini_dir={meta['chipyard_root']}/generators/testchipip/src/main/resources/dramsim2_ini",
                                f"+max-cycles={meta['max_cycles']}", f"+verilator+seed+{seed}"]
            if meta['loadmem']:
                expected_command.append(f"+loadmem={test['binary']}")
            expected_command += ['+permissive-off', test['binary']]
            assert command == expected_command, 'NVDLA simulation command differs from settings'
            log = (root / log_name).read_text()
            # Restore only the known normalized source-path prefix for the
            # exporter's absolute-path native-finish marker parser.
            parsed_log = re.sub(r'(?m)^- <chipyard>/', '- /<chipyard>/', log)
            assessment = helpers['assess'](name, record, parsed_log)
            expected_attempt = {key: value for key, value in record.items() if key != 'log'} | assessment | {
                'campaign': cid, 'seed': seed, 'negative_control': negative, 'elf_sha256': test['sha256'],
                'log': log_name, 'original_log_sha256': evidence[log_name]['original_sha256'],
                'exported_log_sha256': evidence[log_name]['exported_sha256'],
                'result_evidence': result_name, 'command_evidence': command_name,
                'selected_final': attempt['selected_final']}
            assert type(attempt['selected_final']) is bool and attempt == expected_attempt, 'NVDLA attempt summary differs from actual evidence'
            selected[(name, None if negative else seed)] = attempt
    assert used_evidence == set(evidence), 'Missing or unaccounted NVDLA build/campaign evidence'
    assert len(identities) == 1 and seen_attempts == set(by_attempt) and ordered_attempts == attempts
    assert set(selected) == {('nvdla-dual', seed) for seed in (1, 2, 3)} | {(name, None) for name in controls}
    final_ids = {(record['campaign'], record['test']) for record in selected.values()}
    assert all(record['selected_final'] is ((record['campaign'], record['test']) in final_ids) for record in attempts)
    assert accelerator['results'] == list(selected.values()), 'NVDLA selected finals are not the last retained attempts'
    assert all(record['evidence_valid'] is True for record in selected.values()), 'NVDLA final log does not prove required outcome'
    normals = [record for record in selected.values() if not record['negative_control']]
    negatives = [record for record in selected.values() if record['negative_control']]
    assert len(normals) == accelerator['normal_simulations'] == accelerator['normal_passes'] == 3
    assert sorted(record['seed'] for record in normals) == accelerator['seeds'] == [1, 2, 3]
    assert sum(record['completed_jobs'] for record in normals) == accelerator['normal_completed_jobs'] == 66
    assert accelerator['engine_jobs_per_run'] == helpers['ENGINES'] == {'SDP': 16, 'CDP': 2, 'convolution': 2, 'PDP': 2}
    assert accelerator['jobs_by_hart_per_run'] == {'0': 11, '1': 11}
    assert len(negatives) == accelerator['negative_controls'] == 2 and accelerator['negative_control_rejected'] is True
    assert accelerator['negative_control_outcomes'] == {record['negative_control_kind']: record['negative_control_rejected']
                                                       for record in negatives} == {'corrupted-expected': True, 'skipped-enable': True}
    assert accelerator['attempt_count'] == len(attempts) and accelerator['prior_attempts_retained'] == len(attempts) - 5
    assert accelerator['all_normal_attempts'] == sum(not record['negative_control'] for record in attempts)
    assert accelerator['all_control_attempts'] == sum(record['negative_control'] for record in attempts)
    assert accelerator['prior_attempts_without_required_evidence'] == \
        sum(not record['selected_final'] and not record['evidence_valid'] for record in attempts)

generation = json.loads((ip / 'docs/artifacts/generation.json').read_text())
assert generation['dut_top'] == 'ChipTop'
assert generation['rtl_unmodified_after_generation'] is True
rtl = ip / 'rtl'
actual = {str(f.relative_to(rtl)): digest(f) for f in rtl.rglob('*') if f.is_file()}
assert actual == generation['rtl_files'], 'RTL inventory or bytes differ from generation export'
for relative, expected in generation['license_files'].items():
    assert digest(ip / 'third_party/licenses' / relative) == expected, 'License bytes changed'
config = ip / 'config' / (generation['config'].split('.')[-1] + '.scala')
assert digest(config) == generation['config_sha256'], 'Configuration changed after generation'
cpu = json.loads((ip / 'docs/reports/cpu/summary.json').read_text())
assert cpu['config'] == generation['config'].split('.')[-1], 'CPU report configuration differs'
assert cpu['total'] == 422
assert cpu['configured'] == {'isa': {'PASS': 335}, 'benchmarks': {'PASS': 12}}
assert not cpu['baseline_passing_tests_now_nonpassing'], 'Unresolved CPU regression'
check_export_hashes(ip / 'docs/reports/cpu')
lint = json.loads((ip / 'docs/reports/lint/summary.json').read_text())
lint_inventory = json.loads((ip / 'docs/reports/lint/published-files.json').read_text())
assert len({record['path'] for record in lint_inventory}) == len(lint_inventory), 'Duplicate lint evidence paths'
check_hashes(ip / 'docs/reports/lint', {record['path']: record['sha256'] for record in lint_inventory})
for record in lint_inventory:
    assert (ip / 'docs/reports/lint' / record['path']).stat().st_size == record['bytes'], 'Lint evidence size changed'
for tool in ('verilator', 'slang'):
    assert lint[tool]['errors'] == 0 and lint[tool]['exit_code'] == 0, f'{tool} lint failed'
lint_sources = {}
for line in (ip / 'docs/reports/lint/source-sha256.txt').read_text().splitlines():
    value, relative = line.split(maxsplit=1)
    lint_sources[Path(relative).name] = value
source_hashes = {Path(name).name: value for name, value in generation['rtl_files'].items()
                 if Path(name).suffix in {'.v', '.sv', '.vh', '.svh'}}
assert lint_sources == source_hashes, 'Lint inputs differ from published RTL'
synthesis = json.loads((ip / 'docs/reports/synthesis/summary.json').read_text())
check_hashes(ip / 'docs/reports/synthesis',
             json.loads((ip / 'docs/reports/synthesis/published-sha256.json').read_text()))
expected_synthesis = 'PASS' if ip.name == 'IP2' else 'PASS_LOGIC_MAPPING_WITH_GENERIC_MEMORIES'
assert synthesis['status'] == expected_synthesis, 'Unexpected synthesis outcome'
assert synthesis['configuration'] == cpu['config'] and synthesis['top'] == 'ChipTop'
assert synthesis['openroad_link']['linked'] is (ip.name == 'IP2')
synth_provenance = json.loads((ip / 'docs/reports/synthesis/provenance.json').read_text())
synth_sources = {Path(record['path']).name: record['sha256'] for record in synth_provenance['inputs']
                 if record['path'].startswith('rtl/') and Path(record['path']).suffix in {'.v', '.sv', '.vh', '.svh'}}
assert synth_sources == source_hashes, 'Synthesis inputs differ from published RTL'
if ip.name == 'IP3':
    synth_root = ip / 'docs/reports/synthesis'
    assert (synth_root / 'run-status.txt').read_text().strip() == 'exit_status=0'
    raw_artifacts = json.loads((synth_root / 'raw-artifacts.json').read_text())
    raw_by_name = {record['path']: record for record in raw_artifacts}
    assert len(raw_by_name) == len(raw_artifacts)
    check_evidence = json.loads((synth_root / 'check-evidence.json').read_text())
    assert set(check_evidence) == {'preflight', 'prepare', 'elaborate', 'map', 'finalize'}
    for stage, evidence in check_evidence.items():
        assert evidence['zero_problem_checks'] > 0 and evidence['warnings'] == []
        assert evidence['raw_log_sha256'] == raw_by_name[stage + '.log']['sha256']
        assert evidence['raw_log_bytes'] == raw_by_name[stage + '.log']['bytes']
    assert synthesis['sram_comparison'] == {'seeds': [1, 827361, 2147483647],
                                           'interfaces': 7, 'compared_cycles': 212364}
    macro_inventory = json.loads((synth_root / 'macro-map/inventory.json').read_text())
    assert len(macro_inventory['memories']) == synthesis['sram_comparison']['interfaces']
    sram_log = (synth_root / 'macro-map/test_sram.log').read_text()
    chunks = re.split(r'(?m)^SEED=(\d+)\n', sram_log)
    assert chunks[0] == '' and len(chunks) == 7
    cycles = 0
    for index, seed in enumerate(synthesis['sram_comparison']['seeds']):
        assert int(chunks[2 * index + 1]) == seed
        chunk = chunks[2 * index + 2]
        records = re.findall(r'^PASS kind=(\d+) depth=(\d+) width=(\d+) mask_bits=(\d+) compared_cycles=(\d+)$', chunk, re.M)
        assert len(records) == 7 and {int(record[0]) for record in records} == set(range(7))
        for kind, depth, width, mask_bits, count in records:
            memory = macro_inventory['memories'][int(kind)]
            assert (int(depth), int(width), int(mask_bits)) == \
                (memory['depth'], memory['width'], memory['mask_bits'])
            assert int(count) > 0
        assert chunk.count('PASS all original memory interfaces match macro implementation') == 1
        assert '$finish called' in chunk and not re.search(r'FAIL|FATAL|ERROR', chunk)
        cycles += sum(int(record[-1]) for record in records)
    assert cycles == synthesis['sram_comparison']['compared_cycles']
    assert synthesis['synthesis_mode'] == synth_provenance['synthesis_mode'] == 'preserve-memories'
    assert synthesis['abc_mode'] == synth_provenance['abc_mode'] == 'direct'
    assert synthesis['abc_commands'] == synth_provenance['abc_commands'] == ['strash', '&get -n', '&nf', '&put']
    statistics = json.loads((synth_root / 'statistics.json').read_text())
    assert synthesis['mapped_design'] == statistics['design']
    assert synthesis['memory_inventory'] == macro_inventory
    metadata_inputs = {Path(record['path']).name: record['sha256'] for record in synth_provenance['inputs']
                       if record['path'].startswith('GENERATED_DIR/')}
    metadata_names = {f"chipyard.harness.TestHarness.{cpu['config']}.top.mems.conf", 'top_module_hierarchy.json'}
    assert set(metadata_inputs) == metadata_names
    assert metadata_inputs == {Path(name).name: value for name, value in generation['rtl_files'].items()
                               if Path(name).name in metadata_names}, 'Synthesis metadata differs from generation'
    cell_audit = json.loads((ip / 'docs/reports/synthesis/cell-audit.json').read_text())
    assert cell_audit == synthesis['cell_audit'] and cell_audit['status'] == 'PASS'
    assert cell_audit['generic_memory_exception'] is True
    memories = json.loads((ip / 'docs/reports/synthesis/preserved-memories.json').read_text())
    assert len(memories) == synthesis['generic_memory_instances'] > 0
    assert len({memory['instance'] for memory in memories}) == len(memories), 'Duplicate preserved memories'
    assert all(memory['WIDTH'] > 0 and memory['SIZE'] > 0 and
               memory['bits'] == memory['WIDTH'] * memory['SIZE'] for memory in memories)
    assert sum(memory['bits'] for memory in memories) == synthesis['generic_memory_bits']
    counts = synthesis['mapped_design']['num_cells_by_type']
    assert counts['$mem_v2'] == len(memories)
    assert counts['fakeram45_512x64'] == macro_inventory['physical_macro_instances'] == 194
    assert sum(counts.values()) == synthesis['mapped_design']['num_cells'] == \
        synthesis['standard_cell_instances'] + macro_inventory['physical_macro_instances'] + len(memories)
    assert not any(name.startswith('$') and name != '$mem_v2' for name in counts)
    assert synthesis['memory_audit']['status'] == 'PRESERVE_GENERIC_MEMORIES'
    assert synthesis['openroad_link']['status'] == 'NOT_RUN'
    cleanup = json.loads((ip / 'docs/reports/synthesis/cleanup-audit.json').read_text())
    assert cleanup['status'] == 'PASS' and cleanup['inputs_unchanged_during_audit'] is True
    assert cleanup['context'] == 'ACTUAL_FULL_FLOW_FRONTEND' and cleanup['source_inputs_unchanged'] is True
    assert set(cleanup['input_sha256']) == {'elaborate-before-clean.il', 'elaborate-after-clean.il',
        'elaborate-before-clean-statistics.json', 'elaborate-after-clean-statistics.json',
        'elaborated-statistics.json', 'elaborate.ys', 'elaborate.log', 'provenance.json'}
    assert all(raw_by_name[name]['sha256'] == value for name, value in cleanup['input_sha256'].items())
    assert cleanup['identical_module_names'] is True and cleanup['same_check_assert_passed'] is True
    assert cleanup['changed_modules_by_contract'] == {'ports': [], 'memories': [], 'memory_cells': []}
    assert cleanup['contract_before_sha256'] == cleanup['contract_after_sha256']
    assert cleanup['audit_script_sha256'] == digest(repo / 'scripts/checkpoint-synthesis/audit-cleanup.py')
    assert cleanup['module_count'] > 0 and cleanup['memory_declarations'] > 0 and cleanup['memory_cell_count'] > 0
    assert len(cleanup['monitors']) == cleanup['monitor_count'] > 0
    assert all(record['output_or_inout_ports'] == 0 and record['cells_after'] == 0 for record in cleanup['monitors'])
    contracts = json.loads((ip / 'docs/reports/synthesis/memory-contract-audit.json').read_text())
    assert contracts['status'] == 'PASS' and contracts['inputs_unchanged_during_audit'] is True
    assert contracts['all_parameters_identical'] is True
    assert contracts['added'] == contracts['removed'] == [] and contracts['changed_parameters'] == {}
    assert contracts['memory_instances_before'] == contracts['memory_instances_after'] == len(memories)
    assert len(contracts['cells']) == len({record['cell'] for record in contracts['cells']}) == len(memories)
    contract_names = {'.'.join(part.removeprefix('\\') for part in record['cell'].split('/', 1))
                      for record in contracts['cells']}
    assert contract_names == {record['instance'] for record in memories}, 'Memory contract instances differ'
    memories_by_name = {record['instance']: record for record in memories}
    for record in contracts['cells']:
        name = '.'.join(part.removeprefix('\\') for part in record['cell'].split('/', 1))
        for parameter in ('WIDTH', 'SIZE', 'ABITS', 'RD_PORTS', 'WR_PORTS'):
            encoded = json.dumps({'signed': False, 'literal': str(memories_by_name[name][parameter])}, sort_keys=True).encode()
            assert record['parameter_sha256']['\\' + parameter] == hashlib.sha256(encoded).hexdigest(), \
                'Memory contract geometry differs from preserved inventory'
    assert all(record['all_parameters_match'] is True and
               record['parameters'] == len(record['parameter_sha256']) > 0 and
               '\\INIT' in record['parameter_sha256'] for record in contracts['cells'])
    assert contracts['parameters_compared'] == sum(record['parameters'] for record in contracts['cells'])
    assert contracts['audit_script_sha256'] == digest(repo / 'scripts/checkpoint-synthesis/audit-memory-contracts.py')
    for stage, name in [('before', 'ChipTop-before-abc.il'), ('after', 'ChipTop-after-abc.il')]:
        checkpoint = contracts['checkpoints'][stage]
        assert checkpoint == {'name': name, 'sha256': raw_by_name[name]['sha256'], 'bytes': raw_by_name[name]['bytes']}
if ip.name == 'IP2':
    accelerator = json.loads((ip / 'docs/reports/fft/summary.json').read_text())
    check_fft_evidence(ip, accelerator, generation)
    assert accelerator['simulator_sha256'] == cpu['simulator_sha256'], 'CPU and FFT simulator differ'
elif ip.name == 'IP3':
    accelerator = json.loads((ip / 'docs/reports/nvdla/summary.json').read_text())
    check_nvdla_evidence(ip, accelerator, generation)
    assert accelerator['simulator_sha256'] == cpu['simulator_sha256'], 'CPU and NVDLA simulator differ'
check_export_hashes(ip / 'docs/reports/build')
for stage in ['generation.exit', 'simulator-build.exit', 'workflow.exit']:
    assert (ip / 'docs/reports/build' / stage).read_text().strip() == '0', 'Build stage failed'
build_sim_hash = (ip / 'docs/reports/build/simulator.sha256').read_text().split()[0]
assert build_sim_hash == cpu['simulator_sha256'], 'Build and regression simulator differ'
for report in ['build', 'lint', 'synthesis']:
    assert (ip / 'docs/reports' / report / 'README.md').is_file(), f'Missing {report} report'
errors = []
for path in ip.rglob('*'):
    if path.is_symlink():
        errors.append(f'Symlink in publication: {path}')
    if not path.is_file():
        continue
    if path.stat().st_size >= 90_000_000:
        errors.append(f'Oversized Git file: {path}')
    if path.suffix == '.json':
        json.loads(path.read_text())
    if path.suffix == '.md':
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            target = target.split(' "', 1)[0].strip('<>')
            if target.startswith(('http:', 'https:', 'mailto:', '#')):
                continue
            local = unquote(target.split('#', 1)[0])
            if not local or '$' in local:
                continue
            destination = (path.parent / local).resolve()
            if not destination.is_relative_to(repo) or not destination.exists():
                errors.append(f'Broken/nonportable link: {path.relative_to(repo)} -> {target}')
assert not errors, '\n'.join(errors)
manifest = ip / 'publication-manifest.json'
files = {str(f.relative_to(ip)): digest(f) for f in sorted(ip.rglob('*'))
         if f.is_file() and f != manifest and '__pycache__' not in f.parts}
shared = {str(f.relative_to(repo)): digest(f) for f in sorted((repo / 'scripts').rglob('*'))
          if f.is_file() and '__pycache__' not in f.parts}
data = {'ip': ip.name, 'config': generation['config'], 'files': files,
        'shared_scripts_at_publication': shared, 'file_count': len(files),
        'scope': 'Packaging integrity; stage reports provide validation outcomes'}
if a.write_manifest:
    manifest.write_text(json.dumps(data, indent=2) + '\n')
else:
    previous = json.loads(manifest.read_text())
    assert previous['files'] == files, 'Published IP files differ from manifest'
    # Shared tools can evolve for later IPs; original tool hashes remain provenance.
if a.check_index:
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=repo).split(b'\0')
    staged = {}
    for entry in entries:
        if not entry:
            continue
        metadata, path = entry.decode().split('\t', 1)
        mode, object_id, stage = metadata.split()
        assert stage == '0', f'Unmerged Git index entry: {path}'
        staged[path] = (mode, object_id)
    prefix = str(ip.relative_to(repo)) + '/'
    expected_ip = {prefix + name for name in files} | {prefix + manifest.name}
    assert {name for name in staged if name.startswith(prefix)} == expected_ip, 'Staged IP inventory differs'
    expected_shared = set(shared)
    assert {name for name in staged if name.startswith('scripts/')} == expected_shared, 'Staged shared-tool inventory differs'
    object_format = subprocess.check_output(['git', 'rev-parse', '--show-object-format'], cwd=repo, text=True).strip()
    for name in sorted(expected_ip | expected_shared):
        content = (repo / name).read_bytes()
        blob = b'blob ' + str(len(content)).encode() + b'\0' + content
        assert staged[name][0] in {'100644', '100755'}, f'Unexpected staged mode: {name}'
        assert staged[name][1] == hashlib.new(object_format, blob).hexdigest(), f'Staged bytes differ: {name}'
print(f'{ip.name}: {len(files)} files, original RTL/config hashes, CPU outcomes and local links validated')
