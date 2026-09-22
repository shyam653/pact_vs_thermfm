# Full-SoC lint

Run `bash scripts/accelerator-soc/lint/run.sh` with `CONFIG`, `CHIPYARD_ROOT`,
`LINT_OUTPUT_ROOT`, and optional `GENERATED_DIR`, `IP_DIR`, `VERILATOR`, `SLANG`.
Bash, Python 3, jq, rg, Git, GNU coreutils, Verilator with SARIF support, and
the slang CLI are required. Select the installed tools explicitly when PATH
contains older versions. The output directory must not exist.

`VERILATOR_MAX_NUM_WIDTH` optionally sets Verilator's supported
`--max-num-width` parser limit and is recorded in the command provenance.
For NVDLA, use `1048576`, matching Chipyard's native simulation Makefile:
generated TileLink monitors contain constants wider than Verilator's default
64K limit. This changes the tool's accepted width, without changing RTL or
waiving diagnostics.

Both tools elaborate `ChipTop` with `SYNTHESIS`, original behavioral memories,
and any bundled generated blackbox sources required by its hierarchy. Verilator
runs `--lint-only -Wall -Wno-fatal`; slang runs `-Wextra`. The default timescale
is `1ns/1ps`, not a clock-period constraint. No blanket warning waiver is added.
Jobs run sequentially to bound memory usage on accelerator designs.

Outputs retain raw logs, every structured diagnostic, actual tool versions and
commands, source hashes, integrity-check results, exit codes, and warning/error
counts. `LINT_BASELINE_ROOT` optionally compares warnings with a prior compatible
raw run; comparison does not reuse its results or assert warning equivalence.
Nonzero tool/wrapper status, errors, and source-integrity failures fail the run.
Warnings remain visible even when the run succeeds.

```bash
python3 scripts/accelerator-soc/lint/export-report.py "$LINT_OUTPUT_ROOT" \
  /path/to/new-publication-report
```

The exporter requires a completed successful run and produces path-normalized
JSON preserving diagnostic text and locations. With a comparison, also set
`--baseline-label`. Raw evidence remains in the original output directory.
Lint does not establish functionality, timing closure or clock/reset crossings.
