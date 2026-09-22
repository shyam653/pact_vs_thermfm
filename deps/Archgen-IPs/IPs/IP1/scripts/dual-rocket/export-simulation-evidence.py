#!/usr/bin/env python3
"""Export the completed prior simulation campaign without running simulations."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[2]
CAMPAIGNS = ("isa-run", "bench-run", "smoke-run", "cpp-retry", "corrected-run", "pmp-retry")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def tsv_rows(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter="\t")
    fields = reader.fieldnames
    require(fields and len(fields) == len(set(fields)), "Missing or duplicate TSV columns")
    rows = list(reader)
    require(all(None not in row and None not in row.values() for row in rows), "Malformed TSV")
    return fields, rows


def tsv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def by_name(rows):
    result = {row["test"]: row for row in rows}
    require(len(result) == len(rows) and "" not in result, "Duplicate or empty test names")
    return result


def require_disjoint(output, protected_roots):
    for root in protected_roots:
        require(not output.is_relative_to(root) and not root.is_relative_to(output),
                "Output must not overlap the original experiment or upstream checkout")


def export(run_root, output):
    # Protect the complete experiment, including sibling smoke and diagnostic evidence.
    require_disjoint(output, (run_root.parent,))
    narrative_path = output / "README.md"
    require(narrative_path.is_file() and not narrative_path.is_symlink(),
            "Output requires an existing maintained README.md; the exporter does not invent narrative")
    sources = {}

    def read(relative):
        if relative not in sources:
            sources[relative] = (run_root / relative).read_bytes()
        return sources[relative]

    summary = json.loads(read("summary.json"))
    _, results = tsv_rows(read("all-results.tsv"))
    final = by_name(results)
    require(len(final) == summary["unique_tests"] == 422, "Expected completed 422-test campaign")
    counts = dict(Counter(row["result"] for row in results))
    require(counts == summary["unique_results"] == {"PASS": 391, "FAIL": 25, "WALL_TIMEOUT": 6},
            "Prior campaign totals differ from the documented 391/25/6 results")
    _, comparison_rows = tsv_rows(read("reference-comparison/comparison.tsv"))
    comparison = by_name(comparison_rows)
    reference_summary = json.loads(read("reference-comparison/summary.json"))
    require(set(comparison) == set(final), "Incomplete reference name coverage")
    require(reference_summary["unique_tests"] == 422 and
            reference_summary["comparison_counts"] == {"PASS_AGREE": 391, "NONPASS_AGREE": 31}
            and not reference_summary["pass_nonpass_disagreements"], "Reference summary mismatch")
    require(dict(Counter(row["comparison"] for row in comparison_rows)) ==
            reference_summary["comparison_counts"], "Reference row counts differ from summary")
    for name, row in comparison.items():
        require(row["rtl_result"] == final[name]["result"], f"RTL/reference row mismatch: {name}")
        require((row["rtl_result"] == "PASS") == (row["spike_status"] == "PASS"),
                f"Unexpected pass/non-pass disagreement: {name}")

    configured = {}
    for relative, count in (("config-isa-targets.txt", 335), ("config-benchmark-targets.txt", 12)):
        names = read(relative).decode("utf-8").split()
        if relative == "config-benchmark-targets.txt":
            require(all(Path(name).suffix == ".riscv" for name in names), "Unexpected benchmark filename suffix")
            names = [Path(name).stem for name in names]
        require(len(names) == len(set(names)) == count, f"Configured inventory mismatch: {relative}")
        require(all(name in final and final[name]["result"] == "PASS" for name in names),
                f"Configured test did not pass: {relative}")
        configured[relative] = names

    provenance = {name: json.loads(read(f"{name}/provenance.json")) for name in CAMPAIGNS}
    upstream = Path(provenance["isa-run"]["simulator"]).resolve().parents[2]
    require_disjoint(output, (upstream,))
    roots = ((run_root, ""), (run_root.parent / "simulation", "../simulation"),
             (upstream, "upstream-chipyard"))

    def portable(value):
        if isinstance(value, str) and value.startswith("/"):
            path = Path(value).resolve()
            for root, prefix in roots:
                if path.is_relative_to(root):
                    relative = path.relative_to(root).as_posix()
                    return f"{prefix}/{relative}" if prefix else relative
            raise ValueError("Unexpected absolute path outside known evidence roots")
        if isinstance(value, dict):
            result = {portable(key): portable(item) for key, item in value.items()}
            require(len(result) == len(value), "Path normalization collided with a JSON key")
            return result
        if isinstance(value, list):
            return [portable(item) for item in value]
        return value

    artifacts, entries = {}, []

    def add(name, data, inputs, transformation):
        require(b"/home/" not in data and b"/Users/" not in data and b"/root/" not in data,
                f"Unnormalized private host path in {name}")
        artifacts[name] = data
        entries.append({"exported_file": name, "exported_sha256": sha256(data),
                        "source_files": inputs, "transformation": transformation})

    for relative in ("all-results.tsv", "reference-comparison/comparison.tsv", "bench-build/oracle-kernels.tsv"):
        fields, rows = tsv_rows(read(relative))
        target = "oracle-kernels.tsv" if relative.startswith("bench-build/") else relative
        add(target, tsv_bytes(fields, portable(rows)), [relative],
            "Parsed TSV; absolute evidence paths normalized; UTF-8 with LF line endings")
    for relative in ("summary.json", "reference-comparison/summary.json"):
        add(relative, json_bytes(portable(json.loads(read(relative)))), [relative],
            "Parsed JSON; absolute path values and keys normalized; formatted with LF line endings")
    for relative, names in configured.items():
        transformation = "Validated test names; LF line endings"
        if relative == "config-benchmark-targets.txt":
            transformation += "; removed the .riscv executable suffix to match final test identifiers"
        add(relative, ("\n".join(names) + "\n").encode(), [relative], transformation)

    settings = {}
    for name, original in provenance.items():
        current = {key: value for key, value in original.items() if key != "tests"}
        current["recorded_test_count"] = len(original["tests"])
        current["completed_summary"] = summary["campaigns"][name]
        settings[name] = current
    add("campaign-settings.json", json_bytes(portable(settings)),
        [f"{name}/provenance.json" for name in CAMPAIGNS] + ["summary.json"],
        "Parsed campaign provenance without repeated per-test ELF arrays; added recorded test counts and completed summaries; normalized paths")

    reruns, rerun_sources = [], []
    for campaign, test in (("bench-run", "pmp"), ("pmp-retry", "pmp"),
                           ("smoke-run", "chipyard-cpp-hello"), ("cpp-retry", "chipyard-cpp-hello")):
        relative = f"{campaign}/results.tsv"
        fields, rows = tsv_rows(read(relative))
        require(test in by_name(rows), f"Missing rerun evidence: {campaign}/{test}")
        row = by_name(rows)[test].copy()
        row["campaign"] = campaign
        row["selected_final"] = str(final[test]["campaign"] == campaign).lower()
        reruns.append(row)
        rerun_sources.append(relative)
    add("rerun-history.tsv", tsv_bytes(fields + ["campaign", "selected_final"], portable(reruns)),
        rerun_sources + ["all-results.tsv"], "Selected unchanged-ELF PMP and C++ original/retry rows; preserved raw outcomes; normalized paths")

    # The narrative is maintained manually; record its input evidence and exported digest too.
    narrative_sources = ["RESULTS.md", "README.md", "bench-build/ORACLE_AUDIT.md"]
    for relative in narrative_sources:
        read(relative)
    narrative = narrative_path.read_bytes()
    add("README.md", narrative, narrative_sources,
        "Manually authored self-contained summary of the prior campaign; not a verbatim report copy")
    manifest = {
        "schema_version": 1,
        "campaign": "Prior completed DualRocketConfig simulation campaign, 2026-09-06",
        "unique_tests": 422,
        "normalization": {
            "relative_paths": "Log and ELF fields are relative to the external regression run root, not this Git export folder",
            "../simulation": "Sibling earlier smoke directory outside the regression run root",
            "upstream-chipyard": "Portable alias for the external prepared upstream Chipyard checkout",
            "raw_logs_in_git": False,
        },
        "source_files": {name: {"original_sha256": sha256(data), "original_bytes": len(data)}
                         for name, data in sorted(sources.items())},
        "exports": entries,
        "exporter": {"repository_path": "scripts/dual-rocket/export-simulation-evidence.py",
                     "sha256": sha256(Path(__file__).read_bytes())},
        "manifest_hash_note": "The manifest does not hash itself; every listed export has a digest",
    }
    destinations = [output / name for name in artifacts] + [output / "export-manifest.json"]
    require(all(path.resolve().is_relative_to(output) and not path.is_symlink()
                for path in destinations), "Export destination symlink escapes or aliases maintained files")
    for name, data in artifacts.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name != "README.md":
            path.write_bytes(data)
    (output / "export-manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"unique_tests": 422, "exports": len(entries),
                      "original_sources_hashed": len(sources), "simulations_run": 0}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True,
                        help="Existing completed regression directory; read only")
    parser.add_argument("--output", type=Path,
                        default=REPO / "docs/dual-rocket/reports/simulation",
                        help="Separate export directory with an existing maintained README.md")
    args = parser.parse_args()
    export(args.run_root.resolve(strict=True), args.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Simulation evidence export refused: {error}", file=sys.stderr)
        sys.exit(2)
