# Accelerator SoC checks

Shared full `ChipTop` lint and synthesis workflows for generated Chipyard designs.
Set `CONFIG` explicitly (`DualRocketFFTConfig` or `DualRocketNVDLAConfig`) and
`CHIPYARD_ROOT` to the pinned, generated checkout. `GENERATED_DIR` can override
`$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.$CONFIG`.
`IP_DIR` optionally selects the parent for default `build/$CONFIG-*` outputs;
explicit output paths take precedence. Every output directory must be new.

`source_plan.py` reads the generated hierarchy and discovers bundled blackbox
providers whose filenames differ from their module names. This permits the
NVDLA preprocessed RTL to be included explicitly while resolving ordinary
modules through the generated source directory. It rejects unresolved or
ambiguous modules and records the actual hierarchy and source SHA-256 values.
The source plan is inventory evidence; the EDA tools verify actual elaboration.

```bash
export CHIPYARD_ROOT=/path/to/chipyard
export CONFIG=DualRocketFFTConfig
export LINT_OUTPUT_ROOT=/path/to/new-lint-run
export VERILATOR=/path/to/verilator
export SLANG=/path/to/slang
bash scripts/accelerator-soc/lint/run.sh

export PLATFORM_ROOT=/path/to/OpenROAD-flow-scripts/flow/platforms/nangate45
export OSS_CAD_SUITE_ROOT=/path/to/oss-cad-suite
export OPENROAD=/path/to/openroad
export OUTPUT_ROOT=/path/to/new-synthesis-run
bash scripts/accelerator-soc/synthesis/run.sh
```

See [lint](lint/README.md) and [synthesis](synthesis/README.md) for tool versions,
output contents and limitations. These scripts do not install tools, fetch
libraries, generate Chipyard, or claim functional accelerator verification.
Run CPU/accelerator simulation separately and publish its own evidence.

Run `python3 scripts/accelerator-soc/validate-workflow.py` for lightweight metadata
validation tests. For NVDLA memories without a matching 1R1W technology macro,
use the explicitly limited `SYNTHESIS_MODE=preserve-memories` mode documented in
[synthesis](synthesis/README.md#memory-preserving-logic-mapping).
