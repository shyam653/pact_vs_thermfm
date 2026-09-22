# Dual Rocket Configuration and Verification

This work selects the existing upstream `DualRocketConfig`, generates a full
two-core SoC, and evaluates it using open-source simulation, lint, and synthesis
tools. Read the configuration and hardware inventory before running the flows.

## Reading Order

1. [Configuration process and source revisions](CONFIGURATION.md).
2. [SoC composition, memory map, and scope](SOC.md).
3. [Portable flow commands](../../scripts/dual-rocket/README.md).
4. [Fresh lint report](reports/lint/README.md).
5. [Fresh synthesis and SRAM adapter report](reports/synthesis/README.md).
6. [Prior completed simulation campaign](reports/simulation/README.md).
7. [Workflow and publication checks](reports/workflow/README.md).

The configuration and SoC documents were written before the new lint and
synthesis invocation. Each report identifies its own run and tools. The
simulation campaign predates this documentation task; it is not presented as a
new simulation run.

## Results on 2026-09-06

| Check | Result |
| --- | --- |
| Verilator lint | 0 errors; 2,484 warnings retained |
| slang lint | 0 errors; 21 warnings and 21 notes |
| Full-SoC synthesis | 383,569 standard cells and 194 SRAM macros; no unmapped cells |
| SRAM adapter comparisons | Seven interfaces, three seeds, 212,364 compared cycles passed |
| OpenROAD link | All 383,763 mapped instances linked successfully |
| Library cell area | 4.004733 square millimeters, including SRAM; not die area |
| Prior simulation | 335 configured ISA and 12 configured benchmarks passed; broader inventory 391 PASS / 25 FAIL / 6 timeouts |

Detailed reports retain warnings, failed attempts, provenance and limits.

## Evidence Policy

[`artifacts/`](artifacts/) contains the small generated DTS, memory map, L2
metadata, memory configuration, and a path-independent SHA-256 manifest of all
476 generated Verilog/SystemVerilog sources. It describes `DualRocketConfig`,
not the historical single-core files under the top-level `rtl/` directory.

Compact machine-readable reports accompany the human-readable reports. Host
paths in exported simulation evidence are made relative to the original run
root; the export manifest records original and published file hashes. Full raw
logs and intermediate products remain in the local experiment directory.

No tool installations, upstream source checkout, third-party technology library,
ELF/simulator binary, full mapped netlist, or OpenROAD database is vendored here.
Reproduction requires the external tools and pinned Chipyard sources described
in the configuration and flow instructions. Large generated outputs belong in
an external output directory or the ignored `build/dual-rocket/` directory.

## Acceptance Boundaries

- Functional simulation uses the full `TestHarness` containing `ChipTop` and
  external memory/host models.
- Lint uses original full-`ChipTop` RTL with behavioral memories and documented
  warnings. Zero errors is not warning-free signoff.
- Synthesis maps full `ChipTop`, including memory interfaces through validated
  adapters to external fakeram45 macros. Simulated DRAM is not on-chip SRAM.
- OpenROAD reading and linking the mapped netlist is not placement, routing,
  static timing analysis, DRC/LVS, power analysis, or signoff.
