#!/usr/bin/env python3
"""Check the compact documentation package without invoking EDA tools."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/dual-rocket"
SCRIPTS = ROOT / "scripts/dual-rocket"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(base, name, expected):
    path = (base / name).resolve()
    require(path.is_relative_to(base.resolve()), f"Manifest path escapes evidence directory: {name}")
    require(digest(path) == expected, f"Evidence hash mismatch: {path}")


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main():
    files = [ROOT / "README.md"] + sorted(
        path for base in (DOCS, SCRIPTS) for path in base.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts)
    links = 0
    for path in files:
        require(path.stat().st_size < 8 * 1024 * 1024, f"Unexpected large artifact: {path}")
        content = path.read_text()
        require(not re.search(r"/(?:home|Users|data)/[A-Za-z0-9_.-]+/|github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]{20,}", content),
                f"Private host path or credential-like content: {path}")
        if path.suffix == ".json":
            json.loads(content)
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", content):
                url = urlsplit(target.strip("<>"))
                if url.scheme or not url.path:
                    continue
                require(not url.path.startswith("/"), f"Nonportable Markdown link in {path}: {target}")
                require((path.parent / unquote(url.path)).exists(), f"Broken local link in {path}: {target}")
                links += 1
    manifest = (DOCS / "artifacts/rtl.sha256").read_text().splitlines()
    filenames = []
    for line in manifest:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/]+\.(?:sv|v))", line)
        require(match is not None, "Malformed or nonportable RTL manifest entry")
        filenames.append(match[2])
    require(len(filenames) == len(set(filenames)) == 476, "RTL inventory must contain 476 unique sources")
    require(filenames == sorted(filenames), "RTL manifest ordering is not deterministic")
    for line in (DOCS / "artifacts/artifacts.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        verify(DOCS / "artifacts", name, expected)

    lint = DOCS / "reports/lint/evidence"
    for entry in json.loads((lint / "published-files.json").read_text()):
        verify(lint, entry["path"], entry["sha256"])
    require((lint / "source-sha256.txt").read_text().splitlines() == manifest,
            "Lint and hardware source manifests differ")
    for line in (lint.parent / "wrapper-source-sha256.txt").read_text().splitlines():
        expected, name = line.split("  ", 1)
        verify(ROOT, name, expected)
    synthesis = DOCS / "reports/synthesis"
    for name, expected in json.loads((synthesis / "evidence-sha256.json").read_text()).items():
        verify(synthesis, name, expected)

    workflow = json.loads((DOCS / "reports/workflow/generation-negative-controls.json").read_text())
    require(digest(SCRIPTS / "generate.sh") == workflow["wrapper_sha256"],
            "Generation wrapper changed since its negative controls")
    require(digest(DOCS / "artifacts/rtl.sha256") == workflow["rtl_manifest_sha256"],
            "Generation test manifest differs from publication")
    require(len(workflow["cases"]) == 4 and all(case["status"] == "PASS" for case in workflow["cases"]),
            "Incomplete generation wrapper checks")

    simulation = DOCS / "reports/simulation"
    results = rows(simulation / "all-results.tsv")
    require(len(results) == len({row["test"] for row in results}) == 422, "Simulation inventory mismatch")
    require(Counter(row["result"] for row in results) == {"PASS": 391, "FAIL": 25, "WALL_TIMEOUT": 6},
            "Simulation result counts differ from report")
    export = json.loads((simulation / "export-manifest.json").read_text())
    for entry in export["exports"]:
        verify(simulation, entry["exported_file"], entry["exported_sha256"])
    require(digest(ROOT / export["exporter"]["repository_path"]) == export["exporter"]["sha256"],
            "Simulation exporter changed since packaging")
    print(f"Publication checks passed: {len(files)} text files, {links} local links, 476 RTL hashes, 422 simulation rows")


if __name__ == "__main__":
    main()
