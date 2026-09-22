#!/usr/bin/env python3
"""Emit compact measured synthesis results only after all stages succeed."""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from prepare import digest, require
from cell_audit import validate_cells


def preserved_memories(path):
    modules = json.loads(path.read_text())["modules"]
    memories = []

    def walk(name, instance, ancestors):
        require(name not in ancestors, f"Recursive netlist hierarchy: {name}")
        for cell_name, cell in modules[name]["cells"].items():
            cell_path = instance + "." + cell_name
            if cell["type"] == "$mem_v2":
                params = cell["parameters"]
                decoded = {key: int(params[key], 2) for key in
                           ("WIDTH", "SIZE", "ABITS", "RD_PORTS", "WR_PORTS")}
                memories.append({"instance": cell_path, **decoded,
                                 "bits": decoded["WIDTH"] * decoded["SIZE"]})
            elif cell["type"] in modules and modules[cell["type"]].get("cells"):
                walk(cell["type"], cell_path, ancestors | {name})

    walk("ChipTop", "ChipTop", set())
    return memories


def main():
    output = Path(os.environ["OUTPUT_ROOT"]).resolve(strict=True)
    inventory = json.loads((output / "macro-map/inventory.json").read_text())
    expected_macros = inventory["physical_macro_instances"]
    interfaces = len(inventory["memories"])
    statistics = json.loads((output / "statistics.json").read_text())
    design = statistics["design"]
    counts = design["num_cells_by_type"]
    provenance = json.loads((output / "provenance.json").read_text())
    mode = provenance["synthesis_mode"]
    frontend_cleanup = {"command": provenance["frontend_cleanup"], "stages": {}}
    for stage in ("elaborate", "prepare"):
        frontend_cleanup["stages"][stage] = {
            moment: {key: value for key, value in json.loads(
                (output / f"{stage}-{moment}-clean-statistics.json").read_text())["design"].items()
                if not isinstance(value, dict)}
            for moment in ("before", "after")}
    cell_audit = validate_cells(counts, [output / "inputs/cell.lib", output / "inputs/sram.lib"],
                                mode == "preserve-memories")
    (output / "cell-audit.json").write_text(json.dumps(cell_audit, indent=2) + "\n")
    generic = []
    if mode == "mapped":
        link = json.loads((output / "openroad-link.json").read_text())
        require(link["linked"] and link["top"] == "ChipTop" and link["sram_macros"] == expected_macros,
                "OpenROAD SRAM/link check did not pass")
        require(not any(name.startswith("$") for name in counts), "Unmapped internal cells remain")
        require(link["instances"] == design["num_cells"], "OpenROAD/Yosys cell counts disagree")
    else:
        require(mode == "preserve-memories", f"Unsupported synthesis mode {mode}")
        link = {"linked": False, "status": "NOT_RUN", "reason": "Generic memories lack physical SRAM macros"}
        require(not any(name.startswith("$") and name != "$mem_v2" for name in counts),
                "Unmapped internal logic remains")
        generic = preserved_memories(output / "ChipTop-logic-mapped.json")
        require(len(generic) == counts.get("$mem_v2", 0) and generic,
                "Preserved-memory inventory does not match synthesized design")
        (output / "preserved-memories.json").write_text(json.dumps(generic, indent=2) + "\n")
    require(counts["fakeram45_512x64"] == expected_macros, "Mapped SRAM count changed")
    require(design["num_memories"] == 0 and design["num_processes"] == 0,
            "Unmapped memories or processes remain")
    log = (output / "macro-map/test_sram.log").read_text()
    require("FAIL" not in log, "SRAM comparison failure marker")
    require(re.findall(r"^SEED=(\d+)$", log, re.MULTILINE) == ["1", "827361", "2147483647"],
            "Incomplete SRAM test seeds")
    matches = re.findall(r"^PASS kind=(\d+) .* compared_cycles=(\d+)$", log, re.MULTILINE)
    require(Counter(kind for kind, _ in matches) == Counter({str(kind): 3 for kind in range(interfaces)}),
            "Incomplete SRAM interface comparisons")
    cycles = sum(int(count) for _, count in matches)
    expected_cycles = 3 * sum(10002 + 6 * ((m["depth"] + 510) // 511) + 4 * m["mask_bits"]
                              for m in inventory["memories"])
    require(cycles == expected_cycles and log.count("PASS all original memory interfaces") == 3,
            "Unexpected SRAM comparison coverage")
    audit = json.loads((output / "memory-audit.json").read_text())
    require(audit["status"] == ("PASS" if mode == "mapped" else "PRESERVE_GENERIC_MEMORIES"),
            "Memory audit failed")
    for record in provenance["inputs"]:
        require(digest(Path(record["path"])) == record["sha256"],
                f"Input changed during synthesis: {record['path']}")
    summary = {"completed_utc": datetime.now(timezone.utc).isoformat(),
               "configuration": inventory["configuration"], "top": "ChipTop",
               "status": "PASS" if mode == "mapped" else "PASS_LOGIC_MAPPING_WITH_GENERIC_MEMORIES",
               "synthesis_mode": mode,
               "frontend_cleanup": frontend_cleanup,
               "stage_order": provenance["stage_order"],
               "abc_mode": provenance["abc_mode"], "abc_commands": provenance["abc_commands"],
               "cell_audit": cell_audit,
               "yosys_creator": statistics["creator"], "mapped_design": design,
               "standard_cell_instances": design["num_cells"] - expected_macros - len(generic),
               "generic_memory_instances": len(generic),
               "generic_memory_bits": sum(m["bits"] for m in generic),
               "openroad_link": link,
               "sram_comparison": {"seeds": [1, 827361, 2147483647],
                                   "interfaces": interfaces, "compared_cycles": cycles},
               "memory_inventory": inventory,
               "memory_audit": {"status": audit["status"],
                                "remaining_behavioral_arrays": len(audit["remaining_behavioral_memories"])},
               "limitations": ["Nangate45/fakeram45 exploratory non-manufacturable mapping",
                               "No timing constraints, timing closure, placement, or routing",
                               "SRAM comparisons are finite simulation, not formal equivalence",
                               "Synthesis/link success is not functional SoC signoff"]}
    if generic:
        summary["limitations"].append("Generic memory cells retain port semantics but have no SRAM "
                                      "technology mapping, physical area or physical netlist link; "
                                      "reported logic area excludes their storage area")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    artifacts = [path for path in output.rglob("*") if path.is_file()
                 and path.name not in {"artifact-sha256.json", "run-status.txt"}]
    (output / "artifact-sha256.json").write_text(json.dumps(
        {str(path.relative_to(output)): digest(path) for path in sorted(artifacts)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
