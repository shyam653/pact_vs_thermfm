#!/usr/bin/env python3
"""Build/run the supplemental NVDLA engine harness from exported patched RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=Path, required=True, help="patched nvdla_small.preprocessed.v")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verilator", default="verilator")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error("output exists; use a fresh evidence directory")
    verilator = shutil.which(args.verilator)
    if not verilator:
        parser.error("Verilator not found")
    tests = Path(__file__).resolve().parents[1] / "tests"
    rtl = args.rtl.resolve(strict=True)
    out.mkdir(parents=True)
    command = [verilator, "--cc", "--exe", "--build", "-j", "1", "--top-module", "nvdla_small",
               "-Wno-fatal", "--Mdir", str(out / "obj"), "-CFLAGS", "-O1 -fno-pie",
               "-LDFLAGS", "-no-pie", str(rtl), str(tests / "nvdla_standalone.cpp")]
    metadata = {"rtl": str(rtl), "rtl_sha256": sha(rtl), "command": command,
                "verilator_version": subprocess.check_output([verilator, "--version"], text=True),
                "scope": "NVDLA engines, APB/AXI harness; no CPUs/caches; PLIC emulated",
                "sources": {p.name: sha(p) for p in (tests / "nvdla_standalone.cpp", tests / "nvdla_test.c", tests / "nvdla.h")}}
    (out / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    with (out / "build.log").open("w") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    (out / "build.exit").write_text(str(result.returncode) + "\n")
    result.check_returncode()
    binary = out / "obj/Vnvdla_small"
    outcomes = []
    for seed in (1, 17):
        command = [str(binary), f"+verilator+seed+{seed}", "+verilator+rand+reset+2"]
        start = time.monotonic()
        with (out / f"seed-{seed}.log").open("w") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        log = (out / f"seed-{seed}.log").read_text()
        ok = result.returncode == 0 and "PASS NVDLA standalone engines" in log
        outcomes.append({"seed": seed, "passed": ok, "exit": result.returncode,
                         "elapsed_seconds": time.monotonic()-start, "command": command})
    summary = {"binary_sha256": sha(binary), "results": outcomes,
               "all_passed": all(row["passed"] for row in outcomes)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
