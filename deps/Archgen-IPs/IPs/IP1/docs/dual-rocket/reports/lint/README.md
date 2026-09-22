# Fresh DualRocketConfig Lint

This fresh run followed completion and review of the configuration and SoC
documents. slang and Verilator both started at **2026-09-06T13:19:52Z** using
the finalized, schema-hardened wrappers. Both completed with tool exit code 0, wrapper exit code
0, zero diagnostic errors, and successful post-run source hash checks.

## Scope and Reproduction

The input is the full `ChipTop` generated from Chipyard commit
`e602d917dcc495c58cabe906535e411707096c9c`, configuration
`chipyard.DualRocketConfig`. Chipyard tracked sources were clean at invocation.
Both tools use `SYNTHESIS`, the original
`chipyard.harness.TestHarness.DualRocketConfig.top.mems.v` behavioral memories,
and default timescale `1ns/1ps`. The timescale is not a clock-period constraint.
The flow covers both Rocket tiles, their FPUs and caches, shared interconnect,
peripherals, and clock/reset circuitry. It excludes `TestHarness`, external
simulation models, and synthesis SRAM replacements.

The identical 476-source snapshots recorded by both tools match the published
[hardware RTL manifest](../../artifacts/rtl.sha256) byte-for-byte. This inventory
covers all generated Verilog/SystemVerilog files, including files not reachable
from this top. slang's elaborated dependency list contains **419 source files**;
476 is not a claim that every generated module is instantiated by `ChipTop`.

Run the [portable workflow](../../../../scripts/dual-rocket/lint/README.md)
against that generated checkout. The publication invocation set
`LINT_OUTPUT_ROOT` to a new `publication-run/lint-final` directory and
`LINT_BASELINE_ROOT` to the prior **DualRocketConfig full-ChipTop** lint output.
Tools were selected through `VERILATOR` and `SLANG` executable overrides. The
exact argument arrays, versions, and executable SHA-256 values are retained in
the [Verilator](evidence/verilator/provenance.json) and
[slang](evidence/slang/provenance.json) provenance, with declared path aliases.
The [wrapper source manifest](wrapper-source-sha256.txt) records the exact
repository-relative scripts and workflow documentation hashed before execution.
Those hashes were rechecked successfully after completion; no wrapper changed
during this final run. Verify them from the repository root with
`sha256sum --check docs/dual-rocket/reports/lint/wrapper-source-sha256.txt`.

## Results

| Tool | Version | Errors | Warnings | Notes | Exit |
| --- | --- | ---: | ---: | ---: | ---: |
| Verilator | 5.051 devel, v5.050-312-gb1c06fdb0 (mod) | 0 | 2,484 | 0 | 0 |
| slang | 11.0.448+e222e7dc0 | 0 | 21 | 21 | 0 |

| Verilator Rule | Count |
| --- | ---: |
| UNUSEDSIGNAL | 2,047 |
| PINCONNECTEMPTY | 424 |
| EOFNEWLINE | 4 |
| SYNCASYNCNET | 4 |
| VARHIDDEN | 2 |
| DECLFILENAME | 1 |
| LATCH | 1 |
| UNUSEDPARAM | 1 |

All 21 slang warnings are `arith-in-shift`, each accompanied by a note. Warning
totals and every category are unchanged from the prior DualRocketConfig run
(Verilator start `2026-09-06T09:40:22Z`): **all deltas are zero**. This is not a
comparison against the historical single-core Rocket baseline. See
[summary.json](evidence/summary.json) and
[comparison.json](evidence/comparison.json).

## Findings and Waivers

- `LATCH`: `EICG_wrapper.v:12` retains the clock-gate enable while the input
  clock is high. This is consistent with an intentional low-phase latch in the
  wrapper; the warning remains visible and is not formal verification of clock
  gating or a physical implementation approval.
- `SYNCASYNCNET`: four reset-related nets occur at `ChipTop.sv:176`, `:183`,
  `:191`, and `SerialTL0ClockSinkDomain.sv:34`. The tools observe synchronous
  and asynchronous uses. These require dedicated reset/clock-domain review;
  lint success is not CDC/RDC signoff.
- `arith-in-shift`: generated expressions in `IBuf.sv`, `RocketALU.sv`,
  `MulDiv.sv`, and `FPToInt.sv` combine shifts with arithmetic. Language
  precedence determines their current behavior; explicit parenthesization
  would improve clarity but has not been added to generated RTL here.
- Unused signals/parameters and empty named output connections dominate the
  Verilator baseline. Filename/module-name, trailing-newline, and name-hiding
  diagnostics also remain. The complete locations and messages are retained;
  no blanket claim that these warnings are harmless is made.

Verilator uses `-Wall -Wno-fatal`; slang uses `-Wextra`. `-Wno-fatal` allows the
full warning baseline to complete; it does not suppress warning output. No
source edits or added warning suppressions were made. The existing
[`lint_off` inventory](evidence/source-lint-directives.txt) contains
`UNOPTFLAT` at `EICG_wrapper.v:1` and `WIDTH` at `SimDRAM.v:227`. The latter is
in an external simulation model outside this `ChipTop` lint hierarchy.

## Evidence and Workflow Checks

The [portable export](../../../../scripts/dual-rocket/lint/export-report.py)
retains all 2,484 Verilator result records and all 42 slang warning/note records.
[Verilator diagnostics](evidence/verilator/diagnostics.json) preserve primary
and related locations, severities, rule IDs, and messages, but omit repeated
rendered source snippets and the SARIF rule-table index. The smaller
[slang diagnostics](evidence/slang/diagnostics.json) retain all diagnostics and
notes. Source, executable, and output paths are replaced with declared aliases.
`rtl/` means the generated DualRocketConfig `gen-collateral` directory, not the
repository's historical top-level `rtl/` directory.

**Full raw logs and the original 19.5 MB Verilator SARIF are not committed.**
They remain in the original local run directory. The compact export is derived
evidence, not a byte-identical replacement for those files.
[export.json](evidence/export.json) identifies every raw artifact by relative
path, byte size, and SHA-256. [published-files.json](evidence/published-files.json)
hashes the exported evidence files. Source inventories, actual tool and wrapper
exit codes, integrity-check exits, slang dependency hashes, and time statistics
are included. Exporting refuses an existing destination, mismatched source
snapshots, failed workflows, tool errors, or mismatched diagnostic totals.

Bash syntax checks passed. Isolated mock-tool checks confirmed that missing or
malformed diagnostics, diagnostic errors despite a zero tool exit, and nonzero tool exits
fail the wrapper; valid structured results succeed. A repeated run against an
existing output directory was rejected without changing any prior output
bytes. An earlier fresh run at 13:06 UTC prompted tighter diagnostic-container
and severity validation in the wrappers, not an RTL fix. This report uses the
subsequent complete run with those checks already in place. Earlier raw output
and the earlier report/export remain preserved locally. Mock checks were
workflow negative controls, not RTL simulations.

This report establishes reproducible lint completion with documented warnings.
It does not establish functional correctness, formal equivalence, memory-macro
equivalence, timing closure, physical implementation, or signoff readiness.
