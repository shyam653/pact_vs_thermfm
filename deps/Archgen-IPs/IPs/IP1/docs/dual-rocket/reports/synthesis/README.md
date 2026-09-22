# Fresh Full-SoC Synthesis

**PASS.** The complete `DualRocketConfig` `ChipTop` was freshly synthesized and
linked in OpenROAD after the configuration and SoC documents were completed.
This is not an isolated Rocket core or a synthesis of `TestHarness`.

Successful-run provenance starts at **2026-09-06 13:15:43 UTC**; the verified
summary was finalized at **13:51:31 UTC**. The driver exited **0**. Raw local
artifacts remain in `publication-run/synthesis-retry1`; the earlier failed
tooling attempt remains separately in `publication-run/synthesis`.

## Measured Results

| Metric | Fresh result |
| --- | ---: |
| Total mapped cells / OpenROAD instances | 383,763 |
| Standard-cell instances | 383,569 |
| `fakeram45_512x64` SRAM instances | 194 |
| Flip-flop cells | 55,694 |
| Latch cells (`DLL_X1`) | 1 |
| Unmapped Yosys memories / processes | 0 / 0 |
| Total Liberty area sum | 4,004,732.942 um^2 |
| SRAM Liberty area subtotal | 3,356,478.972 um^2 |
| Standard-cell Liberty area subtotal | 648,253.970 um^2 |
| Logical large-memory capacity | 5,958,656 bits |
| Physical SRAM macro capacity | 6,356,992 bits |
| SRAM interface comparison cycles | 212,364 |

Exact cell-type counts and full-precision area are in
[mapped-statistics.json](mapped-statistics.json). Area subtotals use the
selected SRAM Liberty cell area, 17,301.438 um^2 per macro. These are library
estimates, not a placed die area. OpenROAD's unplaced utilization display is
not a floorplan or utilization result.

## Checks Completed

- All seven generated SRAM interfaces, dimensions, mask lanes, and 16 full-SoC
  memory instances matched the strict inventory in [inventory.json](inventory.json).
- All seven interfaces passed seeds `1`, `827361`, and `2147483647` against the
  original generated memory models: [sram-test.log](sram-test.log).
- Original full-SoC and macro-mapped hierarchy checks passed. Mapping rejected
  residual tristates and required 194 macros before and after cell mapping.
- Mapped-design checks found no unresolved internal cells, processes, or memories.
  OpenROAD independently linked 383,763 instances including 194 SRAMs:
  [openroad-link.log](openroad-link.log).
- All 500 captured source/library/plugin/workflow input hashes were unchanged
  at final validation. Metadata fixtures rejected a 136-bit directory, a 17-bit
  mask lane, and a missing directory instance while accepting the valid control:
  [metadata-guardrail-checks.json](metadata-guardrail-checks.json).

## Reproduce and Attribute

Use the [portable workflow](../../../../scripts/dual-rocket/synthesis/README.md).
It requires generated Chipyard RTL, external Nangate45 libraries, Yosys/slang,
ABC, OpenROAD, and Icarus Verilog; it does not redistribute these dependencies.
Executable overrides must be absolute paths or bare names on `PATH`, and
`OSS_CAD_SUITE_ROOT` must be absolute. Original RTL and existing outputs are not
overwritten. All executable workflow files are the versions used for this run.

Chipyard revision: `e602d917dcc495c58cabe906535e411707096c9c`.
ORFS revision: `68cc9bc974502b4786a68e9f51a092e0fcb56e82`.
The [ORFS Nangate45 platform](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/68cc9bc974502b4786a68e9f51a092e0fcb56e82/flow/platforms/nangate45)
supplies the standard-cell and fakeram Liberty/LEF files. Its README describes
the library as non-manufacturable; its LICENSE and
[fakeram generator attribution](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/68cc9bc974502b4786a68e9f51a092e0fcb56e82/flow/platforms/nangate45/fakeram.cfg)
remain with that upstream distribution. No physical libraries are included here.

[input-provenance.json](input-provenance.json) contains all five exact library
hashes, the explicit slang plugin hash, 476 RTL and two metadata hashes, and
workflow hashes. [tool-versions.txt](tool-versions.txt) records versions;
[native-tool-sha256.json](native-tool-sha256.json) adds native Yosys, ABC, Icarus,
VVP, and OpenROAD hashes, rechecked unchanged after the run. Launcher/plugin
hashes do not capture every shared runtime dependency. After completion, only
the workflow README was clarified about executable paths; both its invoked and
published hashes are explicitly recorded in the input provenance.

## Retry and Limits

The first attempt passed SRAM comparisons but stopped at the first Slang read:
`No such file or directory`, followed by `ERROR: Bad command`. Slang had retained
literal quote characters in `.ys` filename arguments. Relative input symlinks
fixed this, and tiny path-with-spaces / OpenROAD API probes passed before the
clean rerun. Every full validation was rerun, without reusing failed-attempt
results. [retry-history.json](retry-history.json) preserves the explanation and
raw failure-log hashes.

This is exploratory Nangate45/fakeram45 synthesis and netlist linking, not ASIC
signoff. There are no timing constraints, timing-closure, placement, routing,
power, or manufacturability claims. SRAM comparisons start from initialized
memory and are finite simulation, not formal equivalence or X-state proof.
Synthesis success is not a new functional SoC regression result.

Exported logs normalize local path prefixes and trim trailing whitespace; raw
log byte hashes remain preserved. The compact exported bytes are hashed by
[evidence-sha256.json](evidence-sha256.json).
[raw-artifact-sha256.json](raw-artifact-sha256.json) separately identifies local
raw artifacts, including large netlists/RTLIL/ODB files and external input
symlinks that are intentionally not published. No evidence manifest hashes itself.
