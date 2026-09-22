#!/usr/bin/env python3
"""Build NVDLA numerical/DMA/PLIC tests for the generated dual-Rocket SoC."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chipyard-root", type=Path, required=True)
    parser.add_argument("--dts", type=Path, required=True)
    parser.add_argument("--cc", default="riscv64-unknown-elf-gcc")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tests = root / "tests"
    output = args.output.resolve()
    if output.exists():
        parser.error("output already exists; use a fresh path to preserve build evidence")
    cc = shutil.which(args.cc)
    if not cc:
        parser.error("RISC-V compiler not found; provide --cc or set PATH")
    source = args.chipyard_root.resolve() / "generators/nvdla"
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != "d99ffdc79bbf9b86c6cad0c278a785d5802c8209":
        parser.error("NVDLA wrapper revision differs from the audited revision")
    dts = args.dts.read_text()
    matches = re.findall(r"\bnvdla@10040000\s*\{([^}]+)\}", dts)
    if len(matches) != 1 or '"nvidia,nv_small"' not in matches[0]:
        parser.error("device tree must contain one small NVDLA at 0x10040000")
    irq_match = re.search(r"\binterrupts\s*=\s*<\s*(0x[0-9a-fA-F]+|[0-9]+)\s*>", matches[0])
    if not irq_match:
        parser.error("NVDLA node lacks one interrupt source")
    irq = int(irq_match[1], 0)
    if not 0 < irq < 32:
        parser.error("test currently requires a PLIC source in the first pending/enable word")
    if sorted(re.findall(r"\bcpu@([0-9a-fA-F]+)\s*\{", dts)) != ["0", "1"]:
        parser.error("device tree must contain exactly CPU harts 0 and 1")
    output.mkdir(parents=True)
    variants = [
        ("nvdla-dual", [], False),
        ("nvdla-negative-control", ["-DNVDLA_NEGATIVE_CONTROL=1"], True),
        ("nvdla-timeout-control", ["-DNVDLA_SKIP_ENABLE=1", "-DNVDLA_POLL_LIMIT=4096"], True),
    ]
    builds = []
    for name, flags, negative in variants:
        binary = output / f"{name}.riscv"
        command = [cc, "-O2", "-Wall", "-Wextra", "-Werror", "-march=rv64imac_zicsr_zifencei",
                   "-mabi=lp64", "-mcmodel=medany", "-nostdlib", "-nostartfiles", "-static",
                   "-fno-builtin", "-fno-common", "-fno-stack-protector", "-Wl,--no-relax",
                   "-T", str(tests / "link.ld"), f"-DNVDLA_IRQ={irq}", *flags,
                   str(tests / "start.S"), str(tests / "nvdla_test.c"), "-o", str(binary)]
        (output / f"{name}-command.json").write_text(json.dumps(command, indent=2) + "\n")
        with (output / f"{name}-build.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        builds.append({"name": name, "binary": str(binary), "sha256": sha(binary),
                       "harts": 2, "negative_control": negative})
    for filename, selected in (("manifest.tsv", builds[:1]), ("negative-control.tsv", builds[1:])):
        with (output / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["test", "binary", "suite", "required_stdout"], delimiter="\t")
            writer.writeheader()
            for build in selected:
                negative = build["negative_control"]
                writer.writerow({"test": build["name"], "binary": build["binary"],
                                 "suite": "expected-failure-control" if negative else "nvdla-accelerator",
                                 "required_stdout": "[]" if negative else json.dumps(["PASS NVDLA dual-hart"])})
    metadata = {"compiler": cc, "compiler_version": subprocess.check_output([cc, "--version"], text=True),
                "nvdla_revision": revision, "builds": builds, "nvdla_plic_source": irq,
                "dts": str(args.dts.resolve()), "dts_sha256": sha(args.dts),
                "inputs": {str(path.relative_to(root)): sha(path) for path in sorted(tests.iterdir()) if path.is_file()},
                "builder_sha256": sha(Path(__file__))}
    (output / "build-provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"output": str(output), "builds": builds, "nvdla_irq": irq}, indent=2))


if __name__ == "__main__":
    main()
