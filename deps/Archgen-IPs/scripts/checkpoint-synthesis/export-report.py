#!/usr/bin/env python3
"""Export compact normalized evidence from completed independent checkpoint mapping."""
import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--comparison', type=Path)
    args = parser.parse_args()
    source, destination = args.run_root.resolve(strict=True), args.output.resolve()
    if destination.exists():
        parser.error('Output must be a new directory')
    if (source / 'run-status.txt').read_text().strip() != 'exit_status=0':
        parser.error('Cannot export unsuccessful run')
    summary = json.loads((source / 'summary.json').read_text())
    provenance = json.loads((source / 'provenance.json').read_text())
    if summary['status'] != 'PASS' or not summary['openroad_link']['linked']:
        parser.error('Mapped implementation checks did not pass')
    origin = provenance['checkpoint_reuse']['origin']
    replacements = [(str(source), 'SYNTHESIS_OUTPUT_ROOT'), (origin, 'CHECKPOINT_ORIGIN'),
                    (str(Path(__file__).resolve().parents[2]), 'REPOSITORY_ROOT')]
    for record in provenance['inputs']:
        path = Path(record['path'])
        if digest(path) != record['sha256']:
            parser.error(f'Input changed since independent mapping: {path}')
        text = str(path)
        if '/gen-collateral/' in text:
            generated = text.split('/gen-collateral/')[0]
            replacements.extend([(generated + '/gen-collateral', 'rtl'), (generated, 'GENERATED_DIR')])
        if path.name == 'NangateOpenCellLibrary_typical.lib':
            replacements.append((str(path.parent.parent), 'PLATFORM_ROOT'))
        for component, alias in [('/oss-cad-suite/', 'OSS_CAD_SUITE_ROOT'), ('/chipyard_rocketconfig/', 'IP1_ORIGINAL_SOURCE'),
                                 ('/.local/opt/openroad/', 'OPENROAD_PACKAGE_ROOT'), ('/.local/bin/', 'LOCAL_TOOL_LAUNCHERS')]:
            if component in text:
                replacements.append((text.split(component)[0] + component.rstrip('/'), alias))
    # Origin provenance also records the Python launcher, which is not a rerun tool.
    replacements.extend([('/usr/bin/python3.10', 'ORIGINAL_PYTHON'), ('/usr/bin/python3', 'ORIGINAL_PYTHON')])
    replacements = sorted(set(replacements), key=lambda x: len(x[0]), reverse=True)

    def normalize(value):
        if isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
            # Yosys internal temporary ABC directory names are not input paths.
            value = re.sub(r'/tmp/yosys-(?:abc|liberty-scl-cache)[^\s"\']*', 'YOSYS_TEMP', value)
            if re.search(r'/(?:home|tmp|mnt)/', value):
                raise ValueError(f'Unrecognized local path: {value[:250]}')
            return value
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, dict):
            return {normalize(k): normalize(v) for k, v in value.items()}
        return value

    exports = {}
    for name in ['summary.json', 'provenance.json', 'statistics.json', 'openroad-link.json', 'native-tools-after.json',
                 'inherited/provenance.json', 'inherited/source-plan.json', 'inherited/memory-audit.json', 'inherited/macro-map/inventory.json']:
        p = source / name
        if p.exists():
            exports[name] = json.dumps(normalize(json.loads(p.read_text())), indent=2) + '\n'
    for name in ['run-status.txt', 'map.ys', 'finalize.ys', 'direct.abc', 'check.tcl', 'map.log', 'finalize.log',
                 'openroad.console.log', 'inherited/macro-map/test_sram.log']:
        p = source / name
        exports[name] = normalize(p.read_text())
    evidence = {}
    for stage in ['inherited/preflight', 'inherited/elaborate', 'inherited/prepare', 'map', 'finalize']:
        p = source / f'{stage}.log'
        log = p.read_text()
        evidence[stage] = {'evidence': 'inherited' if stage.startswith('inherited/') else 'fresh independent execution',
            'raw_log_sha256': digest(p), 'raw_log_bytes': p.stat().st_size,
            'zero_problem_checks': len(re.findall(r'Found and reported 0 problems', log)),
            'warnings': normalize([line for line in log.splitlines() if line.startswith('Warning:')])}
    exports['check-evidence.json'] = json.dumps(evidence, indent=2) + '\n'
    if args.comparison:
        comparison_root = args.comparison.resolve(strict=True)
        if (comparison_root / 'run-status.txt').read_text().strip() != 'exit_status=0':
            parser.error('Comparison run not successful')
        baseline = json.loads((comparison_root / 'summary.json').read_text())
        baseline_provenance = json.loads((comparison_root / 'provenance.json').read_text())
        if baseline['status'] != 'PASS' or baseline['abc_commands'] != summary['abc_commands']:
            parser.error('Comparison uses different mapping mode or did not pass')
        library_names = ['NangateOpenCellLibrary_typical.lib', 'fakeram45_512x64.lib',
                         'NangateOpenCellLibrary.tech.lef', 'NangateOpenCellLibrary.macro.lef', 'fakeram45_512x64.lef']
        libraries = lambda p: {Path(r['path']).name: r['sha256'] for r in p['inputs'] if Path(r['path']).name in library_names}
        binaries = lambda p: {name: r['sha256'] for name, r in p['native_tools_before']['files'].items()}
        if libraries(provenance) != libraries(baseline_provenance) or binaries(provenance) != binaries(baseline_provenance):
            parser.error('Comparison library or native binary differs')
        measured = lambda s: {'configuration': s['configuration'], 'status': s['status'],
            'standard_cell_instances': s['standard_cell_instances'], 'total_instances': s['mapped_design']['num_cells'],
            'area_um2': s['mapped_design']['area'], 'sram_macros': s['openroad_link']['sram_macros'],
            'checkpoint_sha256': s['checkpoint_reuse']['checkpoint_sha256']}
        current, previous = measured(summary), measured(baseline)
        exports['comparison.json'] = json.dumps({'mapping_mode': summary['mapping_mode'], 'abc_commands': summary['abc_commands'],
            'current': current, 'baseline': previous, 'identical_libraries': libraries(provenance),
            'identical_native_binaries': binaries(provenance),
            'delta': {key: current[key] - previous[key] for key in ['standard_cell_instances', 'total_instances', 'area_um2', 'sram_macros']},
            'scope': 'Both complete SoCs independently mapped from their own verified pre-ABC checkpoints using the same ABC script, native tools and libraries. No timing constraints or physical design.'}, indent=2) + '\n'
    exports['raw-artifacts.json'] = json.dumps([{'path': str(p.relative_to(source)), 'bytes': p.stat().st_size, 'sha256': digest(p)}
        for p in sorted(source.rglob('*')) if p.is_file() and not p.is_symlink()], indent=2) + '\n'
    exports['README.md'] = (
        '# Measured independent checkpoint synthesis\n\n'
        f"`{summary['configuration']}`: **PASS**. The complete mapped ChipTop passed Yosys checks and OpenROAD linking with "
        f"{summary['openroad_link']['sram_macros']} SRAM macros.\n\n"
        'This run reused the origin’s verified pre-ABC checkpoint, RTL elaboration and SRAM comparison evidence. '
        'ABC mapping, residual-cell checks, macro counts and OpenROAD linking were executed independently with '
        '`strash; &get -n; &nf; &put`. The origin’s default ABC run is separate; this report does not assert its completion. '
        'The same direct mapping mode must be used for area comparisons.\n\n'
        'Native binary, source, checkpoint, script and library hashes were checked before and after the independent run. '
        'Historical documentation mismatches, if any, are recorded explicitly in checkpoint_reuse. '
        'Selected files replace machine paths with aliases; raw-artifacts.json identifies original evidence. '
        'No timing constraints, timing closure, placement, routing or full-SoC formal equivalence are claimed.\n')
    destination.mkdir(parents=True)
    for name, contents in exports.items():
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents)
    (destination / 'published-sha256.json').write_text(json.dumps({str(p.relative_to(destination)): digest(p)
        for p in sorted(destination.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(f'Exported {len(exports)} files to {destination}')


if __name__ == '__main__':
    main()
