# CPU and multicore regression

This workflow rebuilds the same 422-test inventory used for IP1: 349 RV64 ISA
tests, 66 scalar/legacy/multicore benchmarks, three Chipyard generic programs,
one explicit dual-hart shared-memory/atomic test, and three corrected benchmark
supplements. It includes all 335 ISA tests and 12 benchmarks selected by the
generated dual-Rocket configuration. It also deliberately retains unsupported
instruction probes and historical benchmark-oracle failures as diagnostics.

"All tests" here means this available applicable inventory plus the separately
documented accelerator tests. RV32, RISC-V vector/hypervisor, unsupported
accelerators, board-specific and external debug workflows are not included.
A passing software test is not exhaustive ISA, coherence or peripheral proof.

## Build and run

Commands run from the catalog root using the pinned, provisioned Chipyard tree.
The builder consumes its `riscv-tests` sources and the RISC-V toolchain, and
downloads pinned `libgloss-htif` commit
`39234a16247ab1fa234821b251f1f1870c3de343` for the three generic programs.
Custom dual-hart startup and corrected benchmark sources are kept in `templates/`.
Their origins are described in IP1's simulation evidence; original upstream
benchmarks remain unchanged. Each corrected test is a separate additional test.

```bash
python3 scripts/cpu-regression/build.py --chipyard-root "$CHIPYARD_ROOT" \
  --config DualRocketFFTConfig --output build/cpu-tests

python3 IPs/IP2/scripts/run-regression.py build/cpu-tests/isa.tsv build/IP2-isa \
  --chipyard-root "$CHIPYARD_ROOT" \
  --simulator "$CHIPYARD_ROOT/sims/verilator/simulator-chipyard.harness-DualRocketFFTConfig" \
  --jobs 2 --max-cycles 2000000 --timeout 300

python3 IPs/IP2/scripts/run-regression.py build/cpu-tests/bench.tsv build/IP2-bench \
  --chipyard-root "$CHIPYARD_ROOT" \
  --simulator "$CHIPYARD_ROOT/sims/verilator/simulator-chipyard.harness-DualRocketFFTConfig" \
  --jobs 2 --max-cycles 2000000 --timeout 600
```

For IP3 select `DualRocketNVDLAConfig` and new campaign directories. Identical
CPU ELFs may be reused across both SoCs; the runner hashes every executable.
Build provenance records the compiler commands and ELF hashes. The initial
rebuild's 422 loadable code/data section sets were verified identical to the
previous IP1 test programs, excluding GNU build-ID notes; full ELF hashes differ
when non-executed metadata changes.

The default fast loading uses `+loadmem` to initialize simulated DRAM; the CPUs
still execute the boot ROM and test against the full RTL and DRAMSim2 model.
Use `--serial-load` for an additional serial-host loading check. It can be much
slower, and is not the default loading path for the entire inventory.

The runner returns nonzero when any test fails or times out, including diagnostic
cases. A pass requires exit zero, normal Verilog `$finish`, no failure marker,
and all declared software pass messages. Timeout takes precedence over a normal
finish that occurs during process termination. Every test retains its command,
log, elapsed time and outcome. `--resume` requires unchanged inputs and settings.

PMP needs a longer separate retry (20 million cycles, 1800-second wall limit).
Other retries must have a recorded reason and preserve the original attempt.
Create a manifest containing only the tests to retry; do not edit old logs or
turn expected diagnostic failures into passes.

## Summarize

```bash
python3 scripts/cpu-regression/summarize.py \
  --chipyard-root "$CHIPYARD_ROOT" --config DualRocketFFTConfig \
  --campaign build/IP2-isa --campaign build/IP2-bench \
  --campaign build/IP2-pmp-retry --output IPs/IP2/docs/reports/cpu
```

Campaigns are supplied in chronological order. The last explicit retry determines
the final outcome, while all attempts are exported. The summary validates the
complete inventory and simulator/ELF identity, checks the actual generated
configured-test lists, compares each outcome against IP1, and fails if a
configured test fails or a previously passing test becomes nonpassing. Raw and
path-normalized export hashes remain separate.
