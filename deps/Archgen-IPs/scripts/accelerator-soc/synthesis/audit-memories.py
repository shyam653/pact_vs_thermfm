#!/usr/bin/env python3
"""Reject unadapted large memories before standard-cell expansion."""

import json
import os
from pathlib import Path
import re


def inspect(path):
    memories = []
    module = None
    for line in path.open():
        if line.startswith("module "):
            module = line.split(maxsplit=1)[1].strip()
        if line.startswith("  cell $mem") and not line.startswith(("  cell $memrd", "  cell $memwr", "  cell $meminit")):
            raise ValueError("Unsupported collected memory in pre-mapping RTLIL; inspect before synthesis")
        if not line.startswith("  memory "):
            continue
        match = re.fullmatch(r"  memory (?:width (\d+) )?size (\d+) (.+)\n?", line)
        if not match:
            raise ValueError(f"Unsupported RTLIL memory declaration: {line.strip()}")
        width, depth, name = int(match[1] or 1), int(match[2]), match[3]
        memories.append({"module": module, "memory": name, "width": width,
                         "depth": depth, "bits": width * depth})
    return memories


def main():
    output = Path(os.environ["OUTPUT_ROOT"])
    memories = inspect(output / "ChipTop-macro-elaborated.il")
    unsupported = [m for m in memories if m["bits"] > 8192]
    preserved = os.environ.get("SYNTHESIS_MODE", "mapped") == "preserve-memories"
    report = {"per_memory_standard_cell_bit_limit": 8192,
              "remaining_behavioral_memories": memories,
              "unsupported_large_memories": unsupported,
              "synthesis_mode": os.environ.get("SYNTHESIS_MODE", "mapped"),
              "status": "PRESERVE_GENERIC_MEMORIES" if preserved else "FAIL" if unsupported else "PASS",
              "scope": "Static memories in elaborated RTLIL after generated SRAM replacement; "
                       "these remaining small arrays may map to standard cells."}
    (output / "memory-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    if unsupported and not preserved:
        raise ValueError(f"{len(unsupported)} unadapted large memories; see memory-audit.json. "
                         "Implement and verify appropriate SRAM adapters before synthesis.")
    print(f"Memory audit: {len(memories)} remaining arrays, {len(unsupported)} large; "
          f"{'all retained as generic memories' if preserved else 'small arrays map to cells'}")


if __name__ == "__main__":
    main()
