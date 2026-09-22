# Full Dual-Rocket Synthesis

This flow synthesizes the complete generated `ChipTop`, not an isolated Rocket
core or the simulation harness. It retains both Rocket tiles, their caches,
the shared L2, scratchpad, and the generated SoC interconnect and peripherals.
It accepts the documented `DualRocketConfig` SRAM inventory only.

## Prerequisites

- An existing Chipyard checkout with `DualRocketConfig` generation completed.
- Yosys with the `slang` plugin and ABC, plus OpenROAD.
- Icarus Verilog (`iverilog` and `vvp`), Python 3, Bash, and Git.
- An external OpenROAD-flow-scripts Nangate45 platform containing the standard
  cell Liberty/LEF files and `fakeram45_512x64.lib` / `.lef`.

The flow uses an installed toolchain. It does not download tools, install a
PDK, regenerate Chipyard, or redistribute Liberty, LEF, GDS, or tool binaries.
Use the tool versions and input hashes in a completed report when reproducing
its exact result; newer tool/library versions can change mapped counts and area.

## Run

Finish configuration generation and inspection before starting this command.
Choose a new output directory; an existing directory is never overwritten.

```bash
export CHIPYARD_ROOT=/path/to/chipyard
export ORFS_ROOT=/path/to/OpenROAD-flow-scripts
export OSS_CAD_SUITE_ROOT=/path/to/oss-cad-suite
export OPENROAD=/path/to/openroad
export OUTPUT_ROOT=/path/to/new-dual-rocket-synthesis
bash scripts/dual-rocket/synthesis/run.sh
```

The command can be launched from any working directory by using an absolute
path to `run.sh`. The defaults and overrides are:

| Variable | Default or meaning |
| --- | --- |
| `CHIPYARD_ROOT` | Required generated Chipyard checkout |
| `GENERATED_DIR` | `$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketConfig` |
| `PLATFORM_ROOT` | `$ORFS_ROOT/flow/platforms/nangate45`; may be set directly without `ORFS_ROOT` |
| `OUTPUT_ROOT` | `$PWD/dual-rocket-synthesis`, must not exist |
| `OSS_CAD_SUITE_ROOT` | Optional prefix for Yosys, Icarus Verilog, and VVP |
| `YOSYS`, `IVERILOG`, `VVP` | Explicit executable overrides, otherwise suite `bin/` or `PATH` |
| `OPENROAD` | `openroad` on `PATH`, or an explicit executable |
| `PYTHON` | `python3` |
| `SLANG_PLUGIN` | `slang`; may be the installed plugin's absolute filename |

All executable variables identify one executable, not a shell command with
arguments. Executable overrides must be absolute paths or bare command names
on `PATH`; use an absolute `OSS_CAD_SUITE_ROOT` as well. Relative executable
paths containing `/` are not supported because Yosys runs from the output
directory. Set `PATH` as needed for the selected installation's helper tools.
Paths containing spaces are handled by shell/Tcl quoting and whitespace-free
relative input symlinks for Yosys. This avoids frontend-specific `.ys` quoting
behavior; the original inputs remain external and read-only.

## Stages and Evidence

1. `prepare.py` checks the metadata and generated public memory interfaces,
   counts instances in `top_module_hierarchy.json`, and generates wrappers.
   Golden memories differ from the original models only by seven module names.
2. A lightweight `preflight.ys` checks plugin loading and the directory-wrapper
   macro interface before the longer tests. `macro-map/test.sh` then compares
   all seven interfaces against those original
   models using seeds `1`, `827361`, and `2147483647`. It covers full-memory
   initialization, mask lanes, bank boundaries, held-read-address writes, idle
   cycles, and random operations: 212,364 compared cycles across the three runs.
3. `elaborate.ys` checks the original full-SoC hierarchy with original memories.
4. `prepare.ys` elaborates the same top with the generated SRAM wrappers.
5. `map.ys` requires 194 SRAM cells, lowers only provably always-enabled output
   buffers, rejects remaining tristates, and runs standard-cell mapping / ABC.
6. `finalize.ys` checks the fully mapped design, requires 194 SRAM cells again,
   and writes statistics and mapped netlists.
7. `check.tcl` links the mapped top against the external Liberty/LEF libraries,
   verifies the flattened physical SRAM count, reports area, and writes an ODB.
8. `summarize.py` validates the SRAM test coverage, mapped/link counts, and
   unchanged source inputs before emitting `summary.json` and artifact hashes.

The output directory holds stage logs, generated `.ys` scripts, RTLIL
intermediates, netlists, statistics, the linked ODB, SRAM test evidence,
`provenance.json`, `tool-versions.txt`, and `artifact-sha256.json`. Large
intermediates and library files are not intended for Git. Runtime provenance
contains the executing machine's paths; publish only reviewed, path-normalized
report evidence. Tool executable hashes do not capture every linked runtime
library, ABC executable, or named-plugin dependency. An explicit `SLANG_PLUGIN`
file is also hashed when supplied.

A failure stops the flow with a nonzero status and leaves evidence in that
new output directory. There is no stage-resume mode; keep the failed directory
and use a different output directory for a rerun. `run-status.txt` records the
exit status after preparation has succeeded.

## SRAM Inventory

The specification rows are depth, width, port kind, mask-lane width, and full-SoC
instance count. The generator intentionally rejects other configurations.

| Memory | Shape | Instances | 512x64 macros each |
| --- | --- | ---: | ---: |
| L2 directory `cc_dir_ext` | 1024x144, 18-bit masks | 1 | 6 |
| L2 data `cc_banks_0_ext` | 16384x64, unmasked | 4 | 32 |
| D-cache data | 512x512, 8-bit masks | 2 | 8 |
| D-cache tags | 64x176, 22-bit masks | 2 | 3 |
| I-cache tags | 64x168, 21-bit masks | 2 | 3 |
| I-cache data | 512x256, 32-bit masks | 4 | 4 |
| Scratchpad `mem_ext` | 8192x64, 8-bit masks | 1 | 16 |

Total: 16 generated large-memory instances, 5,958,656 logical bits, and 194
physical macro instances with 6,356,992 capacity bits. Small memories may map
to standard-cell logic; the large full-SoC arrays must not expand into flip-flops.

## Scope Limits

Nangate45 and fakeram45 provide exploratory area estimates, not manufacturable
silicon. The ORFS platform describes Nangate45 as purposely non-manufacturable;
obtain libraries from their upstream distribution and retain its license terms.
The included SRAM model is simulation-only read-before-write behavior, not
vendor timing or physical characterization.

There are no timing constraints, placement, routing, extracted parasitics,
power analysis, or timing-closure claims in this flow. OpenROAD linking is not
physical implementation. Finite SRAM comparisons are not formal equivalence,
and synthesis success is not functional verification or SoC signoff. The
mapped design may contain a latch; report actual mapped cell types rather than
assuming a zero-latch result.
