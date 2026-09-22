#!/usr/bin/env python3
"""Export compact, path-portable evidence from a completed lint run."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline-label")
    args = parser.parse_args()
    source = args.run_root.resolve()
    destination = args.output.resolve()
    if destination.exists():
        parser.error("output must be a new directory")
    summary = read_json(source / "summary.json")
    provenance = {name: read_json(source / name / "provenance.json")
                  for name in ("verilator", "slang")}
    if any(value != 0 for value in read_json(source / "workflow-exits.json").values()):
        parser.error("cannot publish a successful-run report for a failed workflow")
    if (source / "comparison.json").exists() and not args.baseline_label:
        parser.error("--baseline-label is required when exporting a comparison")
    replacements = []
    for name, record in provenance.items():
        rtl = record["rtl_root"]
        replacements.extend([
            ("file://" + rtl + "/", "rtl/"),
            (rtl, "rtl"),
            (str(Path(rtl).relative_to(record["chipyard_root"])), "rtl"),
            (record["chipyard_root"], "CHIPYARD_ROOT"),
            (record["executable"], name),
        ])
        if int((source / name / "source-integrity-exit-code.txt").read_text()) != 0:
            parser.error("source-integrity check failed")
        if summary[name]["errors"] or summary[name]["exit_code"]:
            parser.error("tool errors or nonzero exit status")
    replacements.append((str(source), "LINT_OUTPUT_ROOT"))
    replacements = sorted(set(replacements), key=lambda pair: len(pair[0]), reverse=True)

    def normalize(value):
        if isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
            return value
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()
                    if key not in ("markdown", "snippit", "snippet")}
        return value

    verilator = read_json(source / "verilator/diagnostics.sarif")["runs"][0]["results"]
    slang = read_json(source / "slang/diagnostics.json")
    for name, diagnostics, severity_key in (
        ("verilator", verilator, "level"), ("slang", slang, "severity")
    ):
        count = sum(item[severity_key] == "warning" for item in diagnostics)
        if count != summary[name]["warnings"]:
            parser.error(f"{name} diagnostic count does not match summary")
    source_manifest = (source / "verilator/source-sha256.txt").read_bytes()
    if source_manifest != (source / "slang/source-sha256.txt").read_bytes():
        parser.error("tools did not consume matching source snapshots")

    destination.mkdir(parents=True)

    def write_json(name, value):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(normalize(value), indent=2) + "\n")

    write_json("summary.json", summary)
    write_json("workflow-exits.json", read_json(source / "workflow-exits.json"))
    if (source / "comparison.json").exists():
        write_json("comparison.json", {
            "baseline_label": args.baseline_label,
            "tools": read_json(source / "comparison.json"),
        })
    for name, diagnostics in (("verilator", verilator), ("slang", slang)):
        write_json(f"{name}/diagnostics.json", diagnostics)
        write_json(f"{name}/provenance.json", provenance[name])
        for filename in ("exit-code.txt", "source-integrity-exit-code.txt"):
            (destination / name / filename).write_bytes((source / name / filename).read_bytes())
    for filename in ("source-sha256.txt", "source-lint-directives.txt"):
        (destination / filename).write_bytes((source / "verilator" / filename).read_bytes())
    for filename in ("module-dependencies.txt", "dependency-sha256.txt"):
        (destination / "slang" / filename).write_text(normalize((source / "slang" / filename).read_text()))
    write_json("slang/time-stats.json", read_json(source / "slang/time-stats.json"))
    raw_artifacts = [{"path": str(path.relative_to(source)),
                      "bytes": path.stat().st_size, "sha256": digest(path)}
                     for path in sorted(source.rglob("*")) if path.is_file()]
    write_json("export.json", {
        "format_version": 1,
        "source_label": "LINT_OUTPUT_ROOT",
        "path_aliases": {
            "rtl": "the generated DualRocketConfig gen-collateral directory in the external Chipyard checkout",
            "CHIPYARD_ROOT": "external pinned Chipyard checkout",
            "LINT_OUTPUT_ROOT": "original complete local lint output directory",
            "verilator": "resolved Verilator executable; original bytes identified by SHA-256",
            "slang": "resolved slang executable; original bytes identified by SHA-256",
        },
        "transformations": [
            "Replace machine-local source, executable, and output paths with aliases.",
            "Extract all Verilator SARIF result objects; omit ruleIndex, rendered markdown and source snippets.",
            "Retain all diagnostic severities, rule IDs, messages, primary and related locations.",
            "Retain slang diagnostics and notes; deduplicate the identical source inventories.",
        ],
        "raw_artifacts_not_vendored": raw_artifacts,
    })
    # A rule index is meaningful only alongside the original SARIF rule table.
    diagnostics_path = destination / "verilator/diagnostics.json"
    compact = read_json(diagnostics_path)
    for result in compact:
        result.pop("ruleIndex", None)
    write_json("verilator/diagnostics.json", compact)
    published = [{"path": str(path.relative_to(destination)),
                  "bytes": path.stat().st_size, "sha256": digest(path)}
                 for path in sorted(destination.rglob("*")) if path.is_file()]
    write_json("published-files.json", published)
    print(f"Exported {len(verilator)} Verilator and {len(slang)} slang diagnostic records to {destination}")


if __name__ == "__main__":
    main()
