#!/usr/bin/env python3
"""Resolve generated ChipTop metadata and bundled blackbox sources without guessing."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def describe(generated, config):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config):
        raise ValueError("CONFIG must be a Scala configuration class name")
    generated = Path(generated).resolve(strict=True)
    rtl = generated / "gen-collateral"
    prefix = f"chipyard.harness.TestHarness.{config}"
    memories = rtl / f"{prefix}.top.mems.v"
    hierarchy_path = generated / "top_module_hierarchy.json"
    for path in (rtl / "ChipTop.sv", memories, hierarchy_path,
                 generated / f"{prefix}.top.mems.conf"):
        if not path.is_file():
            raise ValueError(f"Missing generated input: {path}")
    hierarchy = json.loads(hierarchy_path.read_text())
    if hierarchy["module_name"] != "ChipTop":
        raise ValueError("top_module_hierarchy.json does not describe full ChipTop")
    counts = Counter()

    def walk(node):
        counts[node["module_name"]] += 1
        for child in node["instances"]:
            walk(child)

    walk(hierarchy)
    sources = sorted(p for p in rtl.rglob("*")
                     if p.is_file() and p.suffix in (".sv", ".v", ".vh", ".svh"))
    modules = {}
    for path in sources:
        if path.suffix not in (".v", ".sv"):
            continue
        for name in re.findall(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", path.read_text(), re.M):
            modules.setdefault(name, set()).add(path)
    extra = set()
    for name in counts:
        if (rtl / f"{name}.sv").is_file() or (rtl / f"{name}.v").is_file():
            continue
        providers = modules.get(name, set())
        if memories in providers:
            continue
        if len(providers) != 1:
            raise ValueError(f"Cannot uniquely resolve hierarchy module {name}: {sorted(map(str, providers))}")
        extra.update(providers)
    return {"configuration": config, "top": "ChipTop", "generated_dir": str(generated),
            "rtl_root": str(rtl), "memory_source": str(memories),
            "hierarchy_source": str(hierarchy_path),
            "module_instance_counts": dict(sorted(counts.items())),
            "extra_sources": sorted(map(str, extra)),
            "source_sha256": {str(p.relative_to(rtl)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sources}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-dir", required=True, type=Path)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(describe(args.generated_dir, args.config), indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
