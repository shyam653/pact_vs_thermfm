#!/usr/bin/env python3
"""Generate independently checked FFT vectors and build freestanding test ELFs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chipyard-root", type=Path, required=True)
    parser.add_argument("--cc", default="riscv64-unknown-elf-gcc")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tests = root / "tests"
    output = args.output.resolve()
    if output.exists():
        parser.error("output already exists; select a fresh directory to preserve build evidence")
    cc = shutil.which(args.cc)
    if not cc:
        parser.error("RISC-V compiler not found; provide --cc or set PATH")
    source = args.chipyard_root.resolve() / "generators/fft-generator"
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != "e361f229b5574931f555b10e1b48f2769c07832c":
        parser.error("FFT revision differs from the reference model's audited revision")
    output.mkdir(parents=True)
    with (output / "reference-generation.log").open("w") as log:
        subprocess.run(["python3", str(tests / "fft_reference.py"), "--output", str(output)],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    builds = []
    for name, harts, negative in (("fft-single", 1, 0), ("fft-dual", 2, 0),
                                  ("fft-upstream", 1, 0), ("fft-negative-control", 1, 1)):
        binary = output / f"{name}.riscv"
        command = [cc, "-O2", "-Wall", "-Wextra", "-Werror", "-march=rv64imac_zicsr_zifencei",
                   "-mabi=lp64", "-mcmodel=medany", "-nostdlib", "-nostartfiles", "-static",
                   "-fno-builtin", "-fno-common", "-fno-stack-protector", "-Wl,--no-relax",
                   "-T", str(tests / "link.ld"), "-I", str(output), f"-DFFT_HARTS={harts}",
                   f"-DFFT_NEGATIVE_CONTROL={negative}", str(tests / "start.S")]
        if name == "fft-upstream":
            # The upstream test casts its 32-bit int address expression to an
            # RV64 pointer. Preserve its source and silence that known warning.
            command += ["-Wno-int-to-pointer-cast", "-I", str(args.chipyard_root.resolve() / "tests"),
                        str(tests / "upstream_fft.c")]
        else:
            command += [str(tests / "fft_test.c")]
        command += ["-o", str(binary)]
        (output / f"{name}-command.json").write_text(json.dumps(command, indent=2) + "\n")
        with (output / f"{name}-build.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        builds.append({"name": name, "binary": str(binary), "sha256": sha(binary),
                       "harts": harts, "negative_control": bool(negative)})
    with (output / "manifest.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["test", "binary", "suite", "required_stdout"], delimiter="\t")
        writer.writeheader()
        for build in builds[:-1]:
            marker = "PASS FFT dual-hart" if build["harts"] == 2 else "PASS FFT single-hart"
            if build["name"] == "fft-upstream":
                marker = "PASS: FFT Test Passed"
            writer.writerow({"test": build["name"], "binary": build["binary"], "suite": "fft-accelerator",
                             "required_stdout": json.dumps([marker])})
    with (output / "negative-control.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["test", "binary", "suite"])
        writer.writerow([builds[-1]["name"], builds[-1]["binary"], "expected-failure-control"])
    metadata = {"compiler": cc, "compiler_version": subprocess.check_output([cc, "--version"], text=True),
                "fft_revision": revision, "builds": builds,
                "inputs": {str(path.relative_to(root)): sha(path) for path in sorted(tests.iterdir()) if path.is_file()},
                "upstream_test_sha256": sha(args.chipyard_root.resolve() / "tests/fft.c"),
                "builder_sha256": sha(Path(__file__)), "reference_header_sha256": sha(output / "fft_vectors.h")}
    (output / "build-provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"output": str(output), "builds": builds}, indent=2))


if __name__ == "__main__":
    main()
