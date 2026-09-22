"""Reject unresolved accelerator blackboxes as well as internal unmapped logic."""
from pathlib import Path
import re


def validate_cells(counts, libraries, preserve_memories):
    allowed = set()
    for path in libraries:
        cells = set(re.findall(r'\bcell\s*\(\s*"?([^\s"()]+)"?\s*\)', Path(path).read_text()))
        if not cells:
            raise ValueError(f"No cell declarations found in Liberty: {path}")
        allowed.update(cells)
    if preserve_memories:
        allowed.add("$mem_v2")
    unknown = set(counts) - allowed
    if unknown:
        raise ValueError(f"Cells lack supported technology or memory implementation: {sorted(unknown)}")
    return {"status": "PASS", "allowed_library_cell_types": len(allowed) - int(preserve_memories),
            "observed_cell_types": len(counts), "generic_memory_exception": preserve_memories,
            "scope": "Actual standard-cell and SRAM Liberty declarations; only $mem_v2 additionally allowed in preserve-memories mode"}
