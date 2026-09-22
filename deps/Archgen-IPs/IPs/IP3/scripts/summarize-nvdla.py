#!/usr/bin/env python3
"""Export checked full-SoC NVDLA evidence; pass retry campaigns oldest first.

Repeat --campaign for normal campaigns and --negative-control for controls.
The last attempt for each normal seed/control is selected; all supplied attempts
and any runner resume history are retained. No simulation is run by this tool.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shlex


REVISION = "d99ffdc79bbf9b86c6cad0c278a785d5802c8209"
FIELDS = ["test", "suite", "result", "exit_status", "wall_seconds", "cycles", "log"]
STATUS = {"PASS", "FAIL", "WALL_TIMEOUT", "CYCLE_TIMEOUT", "MISSING_FINISH", "MISSING_PASS_MARKER"}
ENGINES = {"SDP": 16, "CDP": 2, "convolution": 2, "PDP": 2}
FINAL_MARKER = "PASS NVDLA dual-hart: 16 SDP + 2 CDP + 2 convolution + 2 pooling jobs, coherent DMA, guards, PLIC"
CONTROLS = {
    "nvdla-negative-control": ("corrupted-expected", "numerical/guard mismatch", 64, 128, 129),
    "nvdla-timeout-control": ("skipped-enable", "completion timeout", 0x100c, 0, 1),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return sha(path.read_bytes())


def read(path):
    return json.loads(path.read_text())


def table(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        return reader.fieldnames, list(reader)


def normal_markers():
    markers = []
    elements = [8, 48, 256, 1224, 384, 144, 272, 256]
    for job in range(16):
        markers.append(f"PASS NVDLA job={job:#018x} hart={job % 2:#018x} elements={elements[job // 2]:#018x}")
    for hart in range(2):
        markers.append(f"PASS NVDLA CDP LUT job={16 + hart:#018x} gain={hart + 1:#018x} elements=256")
    for hart in range(2):
        markers.append(f"PASS NVDLA convolution 1x1 C8 K8 hart={hart:#018x} outputs=8")
    markers += [f"PASS NVDLA PDP 2x2 {mode} outputs=8" for mode in ("max", "min")]
    return markers


def assess(name, record, log):
    """Keep unsuccessful attempts, but only select a final with exact evidence."""
    pass_lines = re.findall(r"^PASS NVDLA[^\r\n]*$", log, re.MULTILINE)
    fail_lines = re.findall(r"^FAIL NVDLA[^\r\n]*$", log, re.MULTILINE)
    finish = bool(re.search(r"^- /[^\r\n]*TestDriver\.v:\d+: Verilog \$finish$", log, re.MULTILINE))
    simulator_failure = bool(re.search(r"\*\*\* FAILED \*\*\*|%Error:|Aborting\.\.\.", log))
    common = {"normal_finish": finish, "pass_markers": pass_lines, "failure_markers": fail_lines}
    if name == "nvdla-dual":
        valid = (record["result"] == "PASS" and record["exit_status"] == 0
                 and finish and not simulator_failure and not fail_lines
                 and pass_lines == [*normal_markers(), FINAL_MARKER])
        return common | {"evidence_valid": valid, "completed_jobs": 22 if valid else None,
                         "engine_jobs": ENGINES if valid else None,
                         "jobs_by_hart": {"0": 11, "1": 11} if valid else None}
    kind, reason, index, got, expected = CONTROLS[name]
    diagnostic = (f"FAIL NVDLA: {reason} hart={0:#018x} job={0:#018x} index={index:#018x} "
                  f"got={got:#018x} expected={expected:#018x}")
    valid = (record["result"] == "FAIL" and record["exit_status"] != 0 and not finish
             and not pass_lines and fail_lines == [diagnostic]
             and not ("*** FAILED ***" in log and "(timeout)" in log))
    return common | {"evidence_valid": valid, "negative_control_kind": kind,
                     "intended_failure_marker": diagnostic, "negative_control_rejected": valid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, action="append", required=True)
    parser.add_argument("--negative-control", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner", type=Path, help="Executed run-regression.py; defaults to the shared IP2 runner")
    args = parser.parse_args()
    ip = Path(__file__).resolve().parents[1]
    repo = ip.parents[1]
    runner = (args.runner or repo / "IPs/IP2/scripts/run-regression.py").resolve(strict=True)
    build_dir = args.build.resolve(strict=True)
    require(not args.output.exists(), "output exists; preserve prior evidence")
    build = read(build_dir / "build-provenance.json")
    source_inventory = {str(path.relative_to(ip)): file_hash(path)
                        for path in sorted((ip / "tests").iterdir()) if path.is_file()}
    require(source_inventory == build["inputs"], "current test source inventory differs from compiled inputs")
    builder_hash = file_hash(ip / "scripts/build-nvdla-tests.py")
    require(builder_hash == build["builder_sha256"], "test builder changed since compilation")
    require(build["nvdla_revision"] == REVISION, "unexpected NVDLA wrapper revision")
    dts_path = Path(build["dts"]).resolve(strict=True)
    require(file_hash(dts_path) == build["dts_sha256"], "compiled device tree changed")
    dts = dts_path.read_text()
    nodes = re.findall(r"\bnvdla@10040000\s*\{([^}]+)\}", dts)
    require(len(nodes) == 1 and '"nvidia,nv_small"' in nodes[0], "missing unique small NVDLA device")
    irq = re.search(r"\binterrupts\s*=\s*<\s*(0x[0-9a-fA-F]+|[0-9]+)\s*>", nodes[0])
    require(irq and 0 < int(irq[1], 0) < 32 and int(irq[1], 0) == build["nvdla_plic_source"],
            "device tree interrupt differs from compiled test")
    require(sorted(re.findall(r"\bcpu@([0-9a-fA-F]+)\s*\{", dts)) == ["0", "1"],
            "device tree must contain exactly harts 0 and 1")
    binaries = {row["name"]: row for row in build["builds"]}
    require(len(build["builds"]) == len(binaries) == 3 and set(binaries) == {"nvdla-dual", *CONTROLS},
            "unexpected build variants")
    for name, binary in binaries.items():
        require(binary["harts"] == 2 and binary["negative_control"] == (name in CONTROLS),
                f"wrong build variant metadata: {name}")
        require(file_hash(Path(binary["binary"])) == binary["sha256"], f"ELF bytes changed: {name}")
        argv = read(build_dir / f"{name}-command.json")
        require(f"-DNVDLA_IRQ={build['nvdla_plic_source']}" in argv, "compiler IRQ definition mismatch")
        defines = {arg for arg in argv if arg.startswith(("-DNVDLA_NEGATIVE_CONTROL", "-DNVDLA_SKIP_ENABLE", "-DNVDLA_POLL_LIMIT"))}
        wanted = ({"-DNVDLA_NEGATIVE_CONTROL=1"} if name == "nvdla-negative-control" else
                  {"-DNVDLA_SKIP_ENABLE=1", "-DNVDLA_POLL_LIMIT=4096"} if name == "nvdla-timeout-control" else set())
        require(defines == wanted, f"unexpected control compiler flags: {name}")
        require(argv[argv.index("-o") + 1] == binary["binary"], "compiler output differs from built ELF")

    campaign_inputs = [(path.resolve(strict=True), False) for path in args.campaign]
    campaign_inputs += [(path.resolve(strict=True), True) for path in args.negative_control]
    require(len({path for path, _ in campaign_inputs}) == len(campaign_inputs), "duplicate campaign directory")
    metadata = [read(path / "provenance.json") for path, _ in campaign_inputs]
    identities = {(row["simulator"], row["simulator_sha256"], row["chipyard_root"]) for row in metadata}
    require(len(identities) == 1, "campaign simulator or Chipyard identity differs")
    simulator_path, simulator_hash, chipyard_path = next(iter(identities))
    require(file_hash(Path(simulator_path)) == simulator_hash, "simulator bytes changed since execution")
    chipyard = Path(chipyard_path).resolve(strict=True)
    runner_hash = file_hash(runner)
    ini_root = chipyard / "generators/testchipip/src/main/resources/dramsim2_ini"
    ini_hashes = {str(path.relative_to(ini_root)): file_hash(path)
                  for path in sorted(ini_root.rglob("*")) if path.is_file()}
    require(bool(ini_hashes), "missing DRAMSim configuration")
    aliases = [(str(build_dir), "<test-build>"), (str(ip), "<ip3>"), (str(repo), "<repo>"),
               (str(chipyard), "<chipyard>"), (str(dts_path), "<test-dts>")]
    campaign_ids = [f"{'control' if negative else 'normal'}-{index:02d}-seed{meta['seed']}"
                    for index, ((_, negative), meta) in enumerate(zip(campaign_inputs, metadata), 1)]
    aliases += [(str(path), f"<campaign:{cid}>") for (path, _), cid in zip(campaign_inputs, campaign_ids)]
    aliases.sort(key=lambda pair: len(pair[0]), reverse=True)
    exports, exported_hashes = {}, {}

    def export(path, destination):
        require(destination not in exports, f"duplicate export: {destination}")
        original = path.read_bytes()
        portable = original.decode()
        for before, after in aliases:
            portable = portable.replace(before, after)
        data = portable.encode()
        exports[destination] = data
        exported_hashes[destination] = {"original_sha256": sha(original), "exported_sha256": sha(data), "bytes": len(data)}
        return destination

    build_files = ["build-provenance.json", "manifest.tsv", "negative-control.tsv"]
    for name in binaries:
        build_files += [f"{name}-command.json", f"{name}-build.log"]
    for filename in build_files:
        export(build_dir / filename, f"build/{filename}")
    export(dts_path, "build/test-device-tree.dts")
    for relative in ini_hashes:
        export(ini_root / relative, f"runtime/dramsim2_ini/{relative}")
    campaigns, attempts, selected = [], [], {}
    for (campaign, negative), meta, cid in zip(campaign_inputs, metadata, campaign_ids):
        require(meta["runner_sha256"] == runner_hash, "executed runner differs from current runner")
        require(meta["dramsim_ini_sha256"] == ini_hashes, "DRAMSim configuration changed")
        require(type(meta["seed"]) is int and (negative or meta["seed"] in (1, 2, 3)), "unexpected normal seed")
        require(all(type(meta[key]) is int and meta[key] > 0 for key in ("jobs", "max_cycles", "wall_timeout_seconds")),
                "invalid campaign execution limits")
        manifest = Path(meta["manifest"])
        require(file_hash(manifest) == meta["manifest_sha256"], "executed manifest changed")
        _, manifest_rows = table(manifest)
        for row in manifest_rows:
            row["binary"] = str(Path(row["binary"]).resolve(strict=True))
            row["required_stdout"] = json.loads(row.get("required_stdout") or "[]")
            row["sha256"] = file_hash(Path(row["binary"]))
        require(manifest_rows == meta["tests"], "manifest content differs from executed tests")
        tests = {row["test"]: row for row in meta["tests"]}
        require(len(tests) == len(meta["tests"]) and bool(tests), "duplicate or empty campaign tests")
        require(set(tests).issubset(CONTROLS) if negative else set(tests) == {"nvdla-dual"},
                "unexpected campaign test coverage")
        columns, rows = table(campaign / "results.tsv")
        require(columns == FIELDS, "unexpected results TSV columns")
        records = {row["test"]: row for row in rows}
        summary = read(campaign / "summary.json")
        require(len(rows) == len(records) == len(tests) == summary["total"] and set(records) == set(tests),
                "incomplete or duplicate results")
        require(dict(Counter(row["result"] for row in rows)) == summary["counts"], "campaign counts mismatch")
        prefix = f"campaigns/{cid}"
        evidence = [export(campaign / filename, f"{prefix}/{filename}")
                    for filename in ("provenance.json", "summary.json", "results.tsv")]
        evidence.append(export(manifest, f"{prefix}/manifest.tsv"))
        resume_files = []
        history = campaign / "resume-history"
        if history.exists():
            for resume_path in sorted(history.glob("*/provenance.json")):
                resumed = read(resume_path)
                resume_identity = ("simulator", "simulator_sha256", "chipyard_root", "dramsim_ini_sha256",
                                   "manifest", "manifest_sha256", "max_cycles", "wall_timeout_seconds",
                                   "seed", "loadmem", "tests", "runner_sha256")
                require(all(resumed[key] == meta[key] for key in resume_identity),
                        "resume campaign identity/settings differ")
                require(resumed["original_provenance_sha256"] == file_hash(campaign / "provenance.json"),
                        "resume history is not bound to original campaign")
            for path in sorted(history.rglob("*")):
                if path.is_file() and path.name in {"provenance.json", "result.json", "simulation.log", "command.txt"}:
                    resume_files.append(export(path, f"{prefix}/{path.relative_to(campaign)}"))
        campaigns.append({"id": cid, "negative_control": negative, "seed": meta["seed"],
                          "settings": {key: meta[key] for key in ("jobs", "max_cycles", "wall_timeout_seconds", "loadmem")},
                          "started_utc": meta["started_utc"], "finished_utc": summary["finished_utc"],
                          "counts": summary["counts"], "evidence": evidence, "resume_history": resume_files})
        for name, test in tests.items():
            require(test["sha256"] == binaries[name]["sha256"] and test["binary"] == binaries[name]["binary"],
                    f"executed ELF differs from build: {name}")
            record = read(campaign / name / "result.json")
            require(set(record) == set(FIELDS) and record["test"] == name and record["suite"] == test["suite"],
                    f"result identity mismatch: {cid}/{name}")
            require({key: str(record[key]) for key in FIELDS} == records[name], "result TSV/JSON mismatch")
            require(record["result"] in STATUS and type(record["exit_status"]) is int,
                    "invalid result status")
            require(record["log"] == str(campaign / name / "simulation.log"), "unexpected simulation log path")
            command = shlex.split((campaign / name / "command.txt").read_text())
            expected_command = [meta["simulator"], "+permissive", "+dramsim", f"+dramsim_ini_dir={ini_root}",
                                f"+max-cycles={meta['max_cycles']}", f"+verilator+seed+{meta['seed']}"]
            if meta["loadmem"]:
                expected_command.append(f"+loadmem={test['binary']}")
            expected_command += ["+permissive-off", test["binary"]]
            require(command == expected_command, "simulator command differs from recorded settings")
            log = (campaign / name / "simulation.log").read_text()
            assessment = assess(name, record, log)
            log_destination = export(campaign / name / "simulation.log", f"{prefix}/{name}/simulation.log")
            record_destination = export(campaign / name / "result.json", f"{prefix}/{name}/result.json")
            command_destination = export(campaign / name / "command.txt", f"{prefix}/{name}/command.txt")
            attempt = {key: value for key, value in record.items() if key != "log"} | assessment | {
                "campaign": cid, "seed": meta["seed"], "negative_control": negative,
                "elf_sha256": test["sha256"], "log": log_destination,
                "original_log_sha256": exported_hashes[log_destination]["original_sha256"],
                "exported_log_sha256": exported_hashes[log_destination]["exported_sha256"],
                "result_evidence": record_destination, "command_evidence": command_destination,
                "selected_final": False}
            attempts.append(attempt)
            selected[(name, None if negative else meta["seed"])] = attempt
    require(set(selected) == {("nvdla-dual", seed) for seed in (1, 2, 3)} | {(name, None) for name in CONTROLS},
            "need normal seeds 1, 2, 3 and both separate failure controls")
    for key, attempt in selected.items():
        require(attempt["evidence_valid"], f"final attempt does not prove required outcome: {key}")
        attempt["selected_final"] = True
    results = list(selected.values())
    report = {
        "schema_version": 1, "evidence_scope": "full-soc-dual-rocket-nvdla",
        "normal_simulations": 3, "normal_passes": 3, "seeds": [1, 2, 3],
        "normal_completed_jobs": 66, "engine_jobs_per_run": ENGINES, "jobs_by_hart_per_run": {"0": 11, "1": 11},
        "negative_controls": 2, "negative_control_rejected": True,
        "negative_control_outcomes": {value[0]: True for value in CONTROLS.values()},
        "attempt_count": len(attempts), "prior_attempts_retained": len(attempts) - len(results),
        "all_normal_attempts": sum(not attempt["negative_control"] for attempt in attempts),
        "all_control_attempts": sum(attempt["negative_control"] for attempt in attempts),
        "prior_attempts_without_required_evidence": sum(not attempt["selected_final"] and not attempt["evidence_valid"]
                                                      for attempt in attempts),
        "retry_selection": "Last supplied campaign for each normal seed/control; all supplied attempts retained",
        "simulator_sha256": simulator_hash, "runner_sha256": runner_hash,
        "runner_source": str(runner.relative_to(repo)) if runner.is_relative_to(repo) else runner.name,
        "builder_sha256": builder_hash, "nvdla_revision": build["nvdla_revision"],
        "dts_sha256": build["dts_sha256"], "nvdla_plic_source": build["nvdla_plic_source"],
        "source_build_provenance_sha256": file_hash(build_dir / "build-provenance.json"),
        "published_build_inputs_verified": source_inventory, "dramsim_ini_sha256": ini_hashes,
        "elf_sha256": {name: binary["sha256"] for name, binary in binaries.items()},
        "campaigns": campaigns, "attempts": attempts, "results": results,
        "exported_evidence": exported_hashes, "exporter_sha256": file_hash(Path(__file__)),
        "path_normalization": "Only known repository, checkout, build, device-tree and campaign paths replaced; original and exported hashes retained",
        "coverage_limits": "PLIC pending/claim/device clear/completion are polled with mie=0; CPU interrupt trap delivery is not tested. Convolution is one 1x1 C8 K8 spatial point; CDP tests linear LUT with square-sum and input multiplication bypassed; PDP tests 2x2 max/min pooling. See docs/INTEGRATION.md.",
    }
    for relative, data in exports.items():
        path = args.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (args.output / "export-hashes.json").write_text(json.dumps(exported_hashes, indent=2) + "\n")
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("normal_simulations", "normal_passes", "normal_completed_jobs",
                                                "negative_control_rejected", "attempt_count", "prior_attempts_retained")}, indent=2))


if __name__ == "__main__":
    main()
