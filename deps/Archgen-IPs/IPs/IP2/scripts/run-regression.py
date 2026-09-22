#!/usr/bin/env python3
"""Run a hashed manifest of ELF tests against an explicitly selected RTL simulator."""

import argparse
import concurrent.futures
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shlex
import signal
import subprocess
import time


RESULT_FIELDS = ["test", "suite", "result", "exit_status", "wall_seconds", "cycles", "log"]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resume_records(output, tests, parser):
    by_name = {row["test"]: row for row in tests}
    completed = {}
    recovered = []
    incomplete = []

    def checked_record(name):
        work = output / name
        record = json.loads((work / "result.json").read_text())
        if (set(record) != set(RESULT_FIELDS)
                or record["test"] != name
                or record["suite"] != by_name[name]["suite"]
                or record["log"] != str(work / "simulation.log")
                or not (work / "simulation.log").is_file()
                or record["result"] not in {
                    "PASS", "FAIL", "WALL_TIMEOUT", "CYCLE_TIMEOUT",
                    "MISSING_FINISH", "MISSING_PASS_MARKER"}):
            raise ValueError(f"invalid result evidence for {name}")
        return record

    results = output / "results.tsv"
    if results.exists() and results.stat().st_size:
        with results.open(newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames != RESULT_FIELDS:
                parser.error("resume results.tsv has an unexpected header")
            for row in reader:
                name = row.get("test")
                if name not in by_name or name in completed:
                    parser.error(f"resume results.tsv has an unknown or duplicate test: {name}")
                try:
                    record = checked_record(name)
                    if {key: str(record[key]) for key in RESULT_FIELDS} != row:
                        raise ValueError(f"results.tsv disagrees with result.json for {name}")
                except (OSError, ValueError, TypeError, KeyError) as error:
                    parser.error(f"cannot preserve completed result: {error}")
                completed[name] = record

    if len(completed) == len(tests):
        parser.error("campaign already has a completed result for every test")
    for row in tests:
        name = row["test"]
        if name in completed:
            continue
        work = output / name
        if work.exists():
            try:
                recovered.append(checked_record(name))
            except (OSError, ValueError, TypeError, KeyError):
                incomplete.append(work)
    return completed, recovered, incomplete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="TSV columns: test, binary, suite")
    parser.add_argument("output", type=Path)
    parser.add_argument("--simulator", type=Path, required=True,
                        help="Verilator executable for the exact SoC being verified")
    parser.add_argument("--chipyard-root", type=Path, required=True,
                        help="Prepared Chipyard checkout supplying DRAMSim2 resources")
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--max-cycles", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--serial-load", action="store_true", default=None)
    parser.add_argument("--resume", action="store_true",
                        help="resume an interrupted campaign; inherit simulation settings")
    args = parser.parse_args()
    args.output = args.output.resolve()
    original = None
    if args.resume:
        if not args.output.is_dir():
            parser.error("resume requires an existing campaign directory")
        if (args.output / "summary.json").exists():
            parser.error("campaign already finished; resume would not run any tests")
        try:
            original = json.loads((args.output / "provenance.json").read_text())
        except (OSError, ValueError) as error:
            parser.error(f"cannot read original campaign provenance: {error}")
    defaults = {"max_cycles": ("max_cycles", 2000000),
                "timeout": ("wall_timeout_seconds", 300), "seed": ("seed", 1)}
    for argument, (key, default) in defaults.items():
        if getattr(args, argument) is None:
            setattr(args, argument, original[key] if original is not None else default)
    if args.serial_load is None:
        args.serial_load = not original["loadmem"] if original is not None else False
    if min(args.jobs, args.max_cycles, args.timeout) < 1:
        parser.error("jobs, max-cycles and timeout must be positive")
    cy = args.chipyard_root.resolve(strict=True)
    sim = args.simulator.resolve(strict=True)
    dramsim_ini = cy / "generators/testchipip/src/main/resources/dramsim2_ini"
    if not sim.is_file() or not os.access(sim, os.X_OK):
        parser.error("simulator must be an executable file")
    if not dramsim_ini.is_dir():
        parser.error("chipyard-root lacks DRAMSim2 configuration resources")
    with args.manifest.open() as stream:
        tests = list(csv.DictReader(stream, delimiter="\t"))
    if not tests or len({row["test"] for row in tests}) != len(tests):
        parser.error("manifest must be nonempty and have unique test names")
    for row in tests:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", row["test"]):
            parser.error(f"unsafe test name: {row['test']}")
        row["binary"] = str(Path(row["binary"]).resolve(strict=True))
        row["sha256"] = hashlib.sha256(Path(row["binary"]).read_bytes()).hexdigest()
        row["required_stdout"] = json.loads(row.get("required_stdout") or "[]")
        if not isinstance(row["required_stdout"], list) or not all(
            isinstance(value, str) and value for value in row["required_stdout"]
        ):
            parser.error("required_stdout must be a JSON array of nonempty strings")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    metadata = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "simulator": str(sim),
        "simulator_sha256": hashlib.sha256(sim.read_bytes()).hexdigest(),
        "chipyard_root": str(cy),
        "dramsim_ini_sha256": {
            str(path.relative_to(dramsim_ini)): file_hash(path)
            for path in sorted(dramsim_ini.rglob("*")) if path.is_file()
        },
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": file_hash(args.manifest),
        "jobs": args.jobs, "max_cycles": args.max_cycles,
        "wall_timeout_seconds": args.timeout, "seed": args.seed,
        "loadmem": not args.serial_load, "tests": tests,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    completed, recovered, incomplete = {}, [], []
    if args.resume:
        identity = ["simulator", "simulator_sha256", "chipyard_root",
                    "dramsim_ini_sha256", "manifest", "max_cycles",
                    "wall_timeout_seconds", "seed", "loadmem", "runner_sha256"]
        if any(original.get(key) != metadata[key] for key in identity):
            parser.error("resume identity/settings mismatch; only --jobs may change")
        if (original.get("manifest_sha256") is not None
                and original["manifest_sha256"] != metadata["manifest_sha256"]):
            parser.error("resume manifest hash differs from the original campaign")
        # Early campaigns predate required_stdout; absence means no extra marker.
        original_tests = [dict(row, required_stdout=row.get("required_stdout", []))
                          for row in original.get("tests", [])]
        if original_tests != tests:
            parser.error("resume manifest rows or ELF hashes differ from the original campaign")
        completed, recovered, incomplete = resume_records(args.output, tests, parser)
    elif args.output.exists():
        parser.error("output already exists; use --resume for an interrupted campaign")
    else:
        args.output.mkdir(parents=True)

    lock = (args.output / ".runner.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("another regression runner holds this campaign lock")
    if args.resume:
        # Recheck after locking in case another invocation completed meanwhile.
        if (args.output / "summary.json").exists():
            parser.error("campaign already finished")
        completed, recovered, incomplete = resume_records(args.output, tests, parser)
        history = args.output / "resume-history" / f"{time.time_ns()}-{os.getpid()}"
        history.mkdir(parents=True)
        metadata.update({
            "original_provenance_sha256": file_hash(args.output / "provenance.json"),
            "prior_results_sha256": file_hash(args.output / "results.tsv")
                if (args.output / "results.tsv").exists() else None,
            "previously_completed": list(completed),
            "recovered_results": [row["test"] for row in recovered],
            "archived_incomplete": [str(history / "incomplete" / path.name)
                                    for path in incomplete],
        })
        for work in incomplete:
            destination = history / "incomplete" / work.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            work.rename(destination)
        (history / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    else:
        (args.output / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")

    def run(row):
        work = args.output / row["test"]
        work.mkdir()
        command = [str(sim), "+permissive", "+dramsim",
                   f"+dramsim_ini_dir={cy}/generators/testchipip/src/main/resources/dramsim2_ini",
                   f"+max-cycles={args.max_cycles}", f"+verilator+seed+{args.seed}"]
        if not args.serial_load:
            command.append(f"+loadmem={row['binary']}")
        command.extend(["+permissive-off", row["binary"]])
        (work / "command.txt").write_text(shlex.join(command) + "\n")
        start = time.monotonic()
        timed_out = False
        with (work / "simulation.log").open("w") as log:
            proc = subprocess.Popen(command, cwd=work, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            try:
                code = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    code = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    code = proc.wait()
        elapsed = time.monotonic() - start
        log = (work / "simulation.log").read_text(errors="replace")
        if timed_out:
            result = "WALL_TIMEOUT"
        elif "*** FAILED ***" in log and "(timeout)" in log:
            result = "CYCLE_TIMEOUT"
        elif code != 0 or re.search(r"\*\*\* FAILED \*\*\*|%Error:|Aborting\.\.\.", log):
            result = "FAIL"
        elif not re.search(r"- /[^\r\n]*TestDriver\.v:\d+: Verilog \$finish$", log, re.MULTILINE):
            result = "MISSING_FINISH"
        elif any(marker not in log for marker in row["required_stdout"]):
            result = "MISSING_PASS_MARKER"
        elif row["test"].startswith("dual-hart-smoke") and (
            "PASS dual-hart: hart0+hart1, peer data visible, 256 atomic increments" not in log
        ):
            result = "MISSING_PASS_MARKER"
        else:
            result = "PASS"
        cycles = re.search(r"after\s+(\d+) simulation cycles", log)
        record = {"test": row["test"], "suite": row["suite"], "result": result,
                  "exit_status": code, "wall_seconds": round(elapsed, 3),
                  "cycles": cycles.group(1) if cycles else "",
                  "log": str(work / "simulation.log")}
        (work / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    counts = {}
    for record in [*completed.values(), *recovered]:
        counts[record["result"]] = counts.get(record["result"], 0) + 1
    finished_names = set(completed) | {record["test"] for record in recovered}
    remaining = [row for row in tests if row["test"] not in finished_names]
    started = time.monotonic()
    results = args.output / "results.tsv"
    needs_header = not results.exists() or not results.stat().st_size
    with results.open("a" if args.resume else "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS, delimiter="\t")
        if needs_header or not args.resume:
            writer.writeheader()
        for record in recovered:
            writer.writerow(record)
        stream.flush()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            pending = {executor.submit(run, row): row for row in remaining}
            done_count = len(finished_names)
            while pending:
                done, _ = concurrent.futures.wait(pending, timeout=30,
                    return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    record = future.result()
                    writer.writerow(record)
                    stream.flush()
                    counts[record["result"]] = counts.get(record["result"], 0) + 1
                    done_count += 1
                    del pending[future]
                    print(f"{done_count}/{len(tests)} {record['test']} "
                          f"{record['result']} {record['wall_seconds']}s", flush=True)
                if not done:
                    print(f"Progress: {done_count}/{len(tests)}, {counts}, "
                          f"elapsed {time.monotonic() - started:.0f}s", flush=True)
    summary = {"total": len(tests), "counts": counts,
               "elapsed_seconds": round(time.monotonic() - started, 3),
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if args.resume:
        summary.update({"resumed": True, "previously_completed": len(completed),
                        "recovered_results": len(recovered),
                        "elapsed_scope": "this resume invocation"})
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    return 0 if counts.get("PASS", 0) == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
