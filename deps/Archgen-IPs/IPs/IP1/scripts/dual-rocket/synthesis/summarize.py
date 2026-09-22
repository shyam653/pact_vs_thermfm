#!/usr/bin/env python3
"""Emit compact measured synthesis results only after all stages succeed."""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from prepare import digest, require


def main():
    output = Path(os.environ["OUTPUT_ROOT"]).resolve(strict=True)
    statistics = json.loads((output / "statistics.json").read_text())
    design = statistics["design"]
    counts = design["num_cells_by_type"]
    link = json.loads((output / "openroad-link.json").read_text())
    require(link["linked"] and link["top"] == "ChipTop" and link["sram_macros"] == 194,
            "OpenROAD SRAM/link check did not pass")
    require(counts["fakeram45_512x64"] == 194, "Mapped SRAM count changed")
    require(design["num_memories"] == 0 and design["num_processes"] == 0,
            "Unmapped memories or processes remain")
    require(not any(name.startswith("$") for name in counts), "Unmapped internal cells remain")
    require(link["instances"] == design["num_cells"], "OpenROAD/Yosys cell counts disagree")
    log = (output / "macro-map/test_sram.log").read_text()
    require("FAIL" not in log, "SRAM comparison failure marker")
    require(re.findall(r"^SEED=(\d+)$", log, re.MULTILINE) == ["1", "827361", "2147483647"],
            "Incomplete SRAM test seeds")
    matches = re.findall(r"^PASS kind=(\d+) .* compared_cycles=(\d+)$", log, re.MULTILINE)
    require(Counter(kind for kind, _ in matches) == Counter({str(kind): 3 for kind in range(7)}),
            "Incomplete SRAM interface comparisons")
    cycles = sum(int(count) for _, count in matches)
    require(cycles == 212364 and log.count("PASS all seven original dual-core memory interfaces") == 3,
            "Unexpected SRAM comparison coverage")
    provenance = json.loads((output / "provenance.json").read_text())
    for record in provenance["inputs"]:
        require(digest(Path(record["path"])) == record["sha256"],
                f"Input changed during synthesis: {record['path']}")
    summary = {"completed_utc": datetime.now(timezone.utc).isoformat(),
               "configuration": "DualRocketConfig", "top": "ChipTop", "status": "PASS",
               "yosys_creator": statistics["creator"], "mapped_design": design,
               "standard_cell_instances": design["num_cells"] - 194,
               "openroad_link": link,
               "sram_comparison": {"seeds": [1, 827361, 2147483647],
                                   "interfaces": 7, "compared_cycles": cycles},
               "limitations": ["Nangate45/fakeram45 exploratory non-manufacturable mapping",
                               "No timing constraints, timing closure, placement, or routing",
                               "SRAM comparisons are finite simulation, not formal equivalence",
                               "Synthesis/link success is not functional SoC signoff"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    artifacts = [path for path in output.rglob("*") if path.is_file()
                 and path.name not in {"artifact-sha256.json", "run-status.txt"}]
    (output / "artifact-sha256.json").write_text(json.dumps(
        {str(path.relative_to(output)): digest(path) for path in sorted(artifacts)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
