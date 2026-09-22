#!/usr/bin/env python3
"""Publish checked FFT simulation evidence, retaining original and exported log hashes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, action="append", required=True)
    parser.add_argument("--negative-control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "output exists; preserve prior evidence")
    require(len(args.campaign) == 3, "expected three normal seed campaigns")
    build = read(args.build / "build-provenance.json")
    reference = read(args.build / "reference.json")
    ip = Path(__file__).resolve().parents[1]
    for relative, digest in build["inputs"].items():
        path = (ip / relative).resolve(strict=True)
        require(path.is_relative_to(ip) and sha(path.read_bytes()) == digest,
                f"published source differs from the compiled input: {relative}")
    require(sha((ip / "scripts/build-fft-tests.py").read_bytes()) == build["builder_sha256"],
            "published test builder differs from the recorded builder")
    require(sha((args.build / "fft_vectors.h").read_bytes()) == build["reference_header_sha256"] == reference["header_sha256"],
            "reference vector header changed")
    elf_hashes = {b["name"]: b["sha256"] for b in build["builds"]}
    for binary in build["builds"]:
        require(sha(Path(binary["binary"]).read_bytes()) == binary["sha256"], "built ELF bytes changed")
    expected = {"fft-single", "fft-dual", "fft-upstream"}
    logs, results, hashes, seeds, checkout_roots = {}, [], set(), set(), set()
    normal_transforms = 0
    for campaign in [*args.campaign, args.negative_control]:
        negative = campaign == args.negative_control
        provenance = read(campaign / "provenance.json")
        require(provenance["runner_sha256"] == sha((ip / "scripts/run-regression.py").read_bytes()),
                "published runner differs from the executed runner")
        checkout_roots.add(provenance["chipyard_root"])
        summary = read(campaign / "summary.json")
        with (campaign / "results.tsv").open() as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        tsv = {row["test"]: row for row in rows}
        hashes.add(provenance["simulator_sha256"])
        names = {test["test"] for test in provenance["tests"]}
        require(names == ({"fft-negative-control"} if negative else expected), "unexpected campaign coverage")
        require(len(provenance["tests"]) == len(names) == len(rows) == len(tsv) == summary["total"] and
                set(tsv) == names, "incomplete or duplicate test result rows")
        require(summary["counts"] == ({"FAIL": 1} if negative else {"PASS": 3}), "unexpected campaign outcomes")
        if not negative:
            require(provenance["seed"] not in seeds, "duplicate normal seed")
            seeds.add(provenance["seed"])
            normal_transforms += reference["cases"] * 6 + 1
        campaign_name = "negative-control" if negative else f"seed{provenance['seed']}"
        for test in provenance["tests"]:
            name = test["test"]
            require(test["sha256"] == elf_hashes[name], "simulation ELF does not match test build")
            record = read(campaign / name / "result.json")
            require(all(str(record[k]) == value for k, value in tsv[name].items()), "result TSV/JSON mismatch")
            original = (campaign / name / "simulation.log").read_bytes()
            decoded = original.decode(errors="replace")
            if negative:
                require(record["result"] == "FAIL" and record["exit_status"] != 0,
                        "negative control did not fail normally")
                require("FAIL FFT: numerical mismatch" in decoded and
                        "job=0x0000000000000000 lane=0x0000000000000000" in decoded and
                        "got=0x0000000000000000 expected=0x0000000000000001" in decoded,
                        "negative control failure is not the deliberate output-bit corruption")
            else:
                require(record["result"] == "PASS" and record["exit_status"] == 0, "normal test failed")
                require(all(marker in decoded for marker in test["required_stdout"]), "missing pass marker")
                require(re.search(r"- /[^\r\n]*TestDriver\.v:\d+: Verilog \$finish$", decoded, re.MULTILINE),
                        "missing simulator finish marker")
                require(not re.search(r"\*\*\* FAILED \*\*\*|%Error:|Aborting\.\.\.", decoded),
                        "simulator failure marker in normal run")
            exported = decoded.replace(provenance["chipyard_root"], "<chipyard>")
            exported = exported.replace(str(campaign.resolve()), f"<campaign:{campaign_name}>").encode()
            destination = f"logs/{campaign_name}/{name}.log"
            logs[destination] = exported
            results.append({k: v for k, v in record.items() if k != "log"} | {
                "seed": provenance["seed"], "negative_control": negative,
                "max_cycles": provenance["max_cycles"], "wall_timeout_seconds": provenance["wall_timeout_seconds"],
                "elf_sha256": test["sha256"], "log": destination,
                "original_log_sha256": sha(original), "exported_log_sha256": sha(exported)})
    require(len(hashes) == 1, "campaigns used different simulator executables")
    require(len(checkout_roots) == 1, "campaigns used different Chipyard checkouts")
    require(seeds == {1, 2, 3}, "expected seeds 1, 2, and 3")
    chipyard = Path(next(iter(checkout_roots)))
    require(sha((chipyard / "tests/fft.c").read_bytes()) == build["upstream_test_sha256"],
            "upstream known-answer test changed")
    build_exports = {}
    files = ["build-provenance.json", "reference.json", "fft_vectors.h", "reference-generation.log"]
    for binary in build["builds"]:
        files += [f"{binary['name']}-command.json", f"{binary['name']}-build.log"]
    replacements = sorted([(str(args.build.resolve()), "<test-build>"), (str(ip), "<ip2>"),
                           (str(chipyard), "<chipyard>")], key=lambda pair: len(pair[0]), reverse=True)
    for filename in files:
        original = (args.build / filename).read_bytes()
        normalized = original.decode()
        for before, after in replacements:
            normalized = normalized.replace(before, after)
        exported = normalized.encode()
        destination = f"build/{filename}"
        logs[destination] = exported
        build_exports[destination] = {"original_sha256": sha(original), "exported_sha256": sha(exported)}
    report = {"normal_simulations": 9, "normal_passes": 9, "negative_controls": 1,
              "negative_control_rejected": True, "normal_completed_transforms": normal_transforms,
              "seeds": sorted(seeds), "simulator_sha256": next(iter(hashes)),
              "reference": {k: v for k, v in reference.items() if k != "vectors"},
              "results": results, "log_normalization": "Only known checkout/campaign paths replaced; original hashes retained",
              "source_build_provenance_sha256": sha((args.build / "build-provenance.json").read_bytes()),
              "published_build_inputs_verified": build["inputs"], "build_evidence": build_exports,
              "build_path_normalization": {"<ip2>": "IPs/IP2", "<chipyard>": "Prepared pinned Chipyard checkout",
                                           "<test-build>": "Original external test build directory"},
              "exporter_sha256": sha(Path(__file__).read_bytes())}
    for path, data in logs.items():
        destination = args.output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("normal_simulations", "normal_passes", "negative_control_rejected", "normal_completed_transforms")}, indent=2))


if __name__ == "__main__":
    main()
