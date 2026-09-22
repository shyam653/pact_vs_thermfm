# DualRocketConfig open-source lint

Prerequisites: generated DualRocketConfig RTL, Bash, Git, ripgrep, jq, GNU
coreutils, Verilator with SARIF diagnostics support, and the slang CLI.
The recorded baseline used Verilator 5.051 and slang 11.0.448.

```sh
export CHIPYARD_ROOT=/path/to/chipyard
export PATH=/path/to/eda/bin:$PATH
export LINT_OUTPUT_ROOT="$PWD/build/dual-rocket-lint"
bash scripts/dual-rocket/lint/run.sh
```

`VERILATOR` and `SLANG` may override the executable names or paths. Both default
to tools on `PATH`. `LINT_OUTPUT_ROOT` defaults to `build/dual-rocket-lint` under
the invoking directory and must be new, preserving existing run evidence.
`LINT_BASELINE_ROOT` optionally selects an earlier output directory containing
Verilator SARIF and slang summary JSON; when supplied, `comparison.json`
reports warning changes by rule. Without it, comparison is skipped.

Both tools elaborate the full `ChipTop` with `SYNTHESIS` defined and the
original `chipyard.harness.TestHarness.DualRocketConfig.top.mems.v` behavioral
memories. This includes both Rocket tiles, FPUs, caches, interconnect,
peripherals, and clock/reset logic. TestHarness, external simulation models,
and synthesis-specific SRAM replacements are excluded.

Verilator uses `--lint-only -Wall -Wno-fatal`. slang uses `-Wextra` and full
elaboration. Both use the default timescale `1ns/1ps`; explicit source
timescales remain effective. This setting is not a clock-period constraint.
No blanket source-warning waiver is added. Existing embedded directives remain
active and are inventoried in `source-lint-directives.txt`, including the
`UNOPTFLAT` directive in the clock-gating wrapper.

Each tool directory records the raw log, diagnostics, version and exact command
in `provenance.json`, tool exit code, summary JSON, relative source SHA-256
inventory, and post-run source-integrity result. slang additionally records
its resolved dependency paths, their hashes, and time statistics. The top-level
summary combines both tools; `workflow-exits.json` also captures wrapper or
source-integrity failures. A successful run can still contain warnings because
Verilator's `-Wno-fatal` preserves the complete warning baseline.

The two jobs run concurrently and the coordinator waits for both. Tool errors
or source-integrity failures make the workflow fail. Lint is not simulation,
formal equivalence, timing closure, or dedicated clock/reset crossing sign-off.

For a compact publication export, Python 3 is additionally required:

```sh
python3 scripts/dual-rocket/lint/export-report.py "$LINT_OUTPUT_ROOT" \
  "$PWD/build/dual-rocket-lint-report" \
  --baseline-label 'previous DualRocketConfig run'
```

The destination must be new. The baseline label is required only when the run
contains `comparison.json`. The export retains every diagnostic result and
location, but drops repeated rendered source snippets and replaces local paths
with declared aliases. It records hashes of the original raw files and the
published files. Raw logs and full Verilator SARIF stay in `LINT_OUTPUT_ROOT`;
the compact JSON is derived evidence, not a byte-identical SARIF copy.
