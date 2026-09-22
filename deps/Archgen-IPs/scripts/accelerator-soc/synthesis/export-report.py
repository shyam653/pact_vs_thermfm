#!/usr/bin/env python3
"""Publish compact, path-normalized evidence from a successful synthesis run."""

import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source, destination = args.run_root.resolve(strict=True), args.output.resolve()
    if destination.exists():
        parser.error("output must be a new directory")
    if (source / "run-status.txt").read_text().strip() != "exit_status=0":
        parser.error("cannot export a successful synthesis report for a failed run")
    summary = json.loads((source / "summary.json").read_text())
    if summary["status"] not in {"PASS", "PASS_LOGIC_MAPPING_WITH_GENERIC_MEMORIES"}:
        parser.error("synthesis did not report a supported successful status")
    provenance = json.loads((source / "provenance.json").read_text())
    plan = json.loads((source / "source-plan.json").read_text())
    replacements = [(str(source), "SYNTHESIS_OUTPUT_ROOT"),
                    (plan["rtl_root"], "rtl"),
                    (plan["generated_dir"], "GENERATED_DIR"),
                    (str(Path(__file__).resolve().parent.parent), "scripts/accelerator-soc")]
    for record in provenance["inputs"]:
        path = Path(record["path"])
        if digest(path) != record["sha256"]:
            parser.error(f"source input changed since synthesis: {path}")
        if path.name == "NangateOpenCellLibrary_typical.lib":
            replacements.append((str(path.parent.parent), "PLATFORM_ROOT"))
    for name, record in provenance["tools"].items():
        replacements.append((record["path"], name))
        if "/oss-cad-suite/" in record["path"]:
            replacements.append((record["path"].split("/oss-cad-suite/")[0] + "/oss-cad-suite",
                                 "OSS_CAD_SUITE_ROOT"))
    replacements = sorted(set(replacements), key=lambda pair: len(pair[0]), reverse=True)

    def normalize(value):
        if isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
            if re.search(r"/(?:home|tmp|mnt)/", value):
                raise ValueError(f"Unrecognized local path in export: {value[:240]}")
            return value
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {normalize(key): normalize(item) for key, item in value.items()}
        return value

    # Validate and prepare every output before creating the destination.
    exports = {}
    for name in ("summary.json", "statistics.json", "memory-audit.json", "cell-audit.json", "source-plan.json",
                 "provenance.json", "macro-map/inventory.json", "preserved-memories.json",
                 "openroad-link.json"):
        path = source / name
        if path.exists():
            exports[name] = json.dumps(normalize(json.loads(path.read_text())), indent=2) + "\n"
    for name in ("run-status.txt", "tool-versions.txt", "macro-map/test_sram.log",
                 "openroad.console.log", "preflight.ys", "elaborate.ys", "prepare.ys", "map.ys", "finalize.ys"):
        path = source / name
        if path.exists():
            exports[name] = normalize(path.read_text())
    evidence = {}
    for stage in ("preflight", "elaborate", "prepare", "map", "finalize"):
        path = source / f"{stage}.log"
        log = path.read_text()
        evidence[stage] = {"raw_log_sha256": digest(path), "raw_log_bytes": path.stat().st_size,
                           "zero_problem_checks": len(re.findall(r"Found and reported 0 problems", log)),
                           "warnings": normalize([line for line in log.splitlines()
                                                  if line.startswith("Warning:")])}
    exports["check-evidence.json"] = json.dumps(evidence, indent=2) + "\n"
    artifacts = [{"path": str(path.relative_to(source)), "bytes": path.stat().st_size,
                  "sha256": digest(path)} for path in sorted(source.rglob("*"))
                 if path.is_file() and not path.is_symlink()]
    exports["raw-artifacts.json"] = json.dumps(artifacts, indent=2) + "\n"
    exports["README.md"] = (
        "# Measured synthesis evidence\n\n"
        f"Configuration: `{summary['configuration']}`. Status: `{summary['status']}`.\n\n"
        "Generated from a completed run with exit status zero and unchanged hashed inputs. "
        "JSON and selected logs have machine-local paths replaced by named aliases. "
        "Raw artifact hashes identify omitted logs, netlists and intermediates. "
        "See summary.json for actual mapping scope, memory counts and limitations.\n")
    destination.mkdir(parents=True)
    for name, contents in exports.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    published = {str(path.relative_to(destination)): digest(path)
                 for path in sorted(destination.rglob("*")) if path.is_file()}
    (destination / "published-sha256.json").write_text(json.dumps(published, indent=2) + "\n")
    print(f"Exported {len(exports)} compact synthesis evidence files to {destination}")


if __name__ == "__main__":
    main()
