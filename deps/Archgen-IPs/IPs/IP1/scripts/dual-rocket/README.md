# Dual Rocket Workflows

Examples below are run from this repository's root. The scripts also accept
invocation by absolute path from another working directory. Supply a provisioned,
pinned Chipyard checkout and the tools documented in the configuration guide.
No script downloads credentials, modifies the upstream configuration, or
installs dependencies automatically.

```bash
export CHIPYARD_ROOT=/path/to/chipyard
export RISCV="$CHIPYARD_ROOT/.conda-env/riscv-tools"
export JAVA_HOME="$CHIPYARD_ROOT/.conda-env/lib/jvm"
export PATH="$JAVA_HOME/bin:$RISCV/bin:$CHIPYARD_ROOT/.conda-env/bin:$PATH"
bash scripts/dual-rocket/generate.sh
```

This invokes `make verilog CONFIG=DualRocketConfig` and validates the resulting
476-source manifest against the published generation. A mismatch is reported,
not silently accepted. The generation step can reuse the upstream build cache;
it is not a toolchain bootstrap.

Generation evidence separates `make-exit-code.txt` from
`source-check-exit-code.txt`; `exit-code.txt` is the overall workflow result,
including the final exact source-inventory comparison.

After reading the configuration and SoC documents, lint and synthesis can run
independently against the same generated sources:

```bash
export OSS_CAD_SUITE_ROOT=/path/to/oss-cad-suite
export PATH="$OSS_CAD_SUITE_ROOT/bin:$PATH"
export ORFS_ROOT=/path/to/OpenROAD-flow-scripts
export LINT_OUTPUT_ROOT="$PWD/build/dual-rocket/lint"
export OUTPUT_ROOT="$PWD/build/dual-rocket/synthesis"
bash scripts/dual-rocket/lint/run.sh
bash scripts/dual-rocket/synthesis/run.sh
```

Read the [lint options](lint/README.md) and
[synthesis prerequisites and options](synthesis/README.md) first. OpenROAD may
need an explicit executable override if it is not on `PATH`. Neither command
asserts a timing constraint or performs physical design. Use separate output
directories for separate attempts; keep previous evidence intact.

`export-simulation-evidence.py` packages the previously completed simulation
campaign. It normalizes only machine-local paths in structured reports and
records hashes; it does not run a simulation.

`export-hardware-evidence.sh` exports the small generated metadata and source
hashes. Its default destination is the committed `docs/dual-rocket/artifacts/`;
set `HARDWARE_EVIDENCE_ROOT` to a new directory for an independent comparison.
It refuses to overwrite existing evidence.

After all compact reports are present, run
`python3 scripts/dual-rocket/validate-publication.py` to check local document
links, JSON syntax, export hashes, portable paths, file sizes, and inventory
counts. This packaging check does not replace any EDA or simulation run.
