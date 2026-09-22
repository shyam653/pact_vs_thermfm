# FFT verification

`fft_reference.py` derives 135 input/output vectors without reading RTL simulation results. It uses a recursive radix-2 decomposition, distinct from the generator's explicit lane network. Ninety-four bounded vectors also pass an independent direct O(N²) complex DFT comparison; these include every impulse position, positive-frequency complex tones in every bin, signed DC, zero, one-LSB cases, and 64 deterministic random inputs. The remaining 41 cases cover signed extrema and 32 deterministic full-scale random inputs using the implementation's finite-width arithmetic. The upstream Chipyard known-answer vector is checked exactly.

`fft_test.c` runs every vector twice on each active hart: 270 transforms in the single-hart test and 540 in the dual-hart test. Both harts take turns owning the complete input/write/read transaction sequence. It checks reset outputs, unchanged result registers after seven inputs, immediate result reads after the eighth input, ascending/reverse read order, non-destructive repeated reads, 32/64-bit MMIO transactions, and zero reserved upper bits. There is no polling for an expected output value that could hide stale results. A separate negative-control ELF deliberately corrupts one expected bit and must fail.

`upstream_fft.c` includes Chipyard's unmodified `tests/fft.c` and executes its original `main`, using a minimal HTIF implementation of the `%x` formatting that source uses. The compiler suppresses only the upstream source's integer-to-pointer-size warning. All local C is compiled with `-Wall -Wextra -Werror`. Startup admits two harts, initializes BSS coherently, installs a failure trap handler, and gives each hart a separate 16 KiB stack. A single designated owner writes HTIF output. The ELF contains separate executable and writable load segments.

## Exact arithmetic and interface contract

The audited FFT generator revision is `e361f229b5574931f555b10e1b48f2769c07832c`. Configuration is eight points/eight lanes, signed 16-bit real and imaginary components with eight fractional bits, no pipeline stages. Input words put real in bits 31:16 and imaginary in bits 15:0. Write each sample to `0x2400`; read output bin `i` at `0x2408 + 8*i`. There are no busy/done registers, DMA, interrupt, saturation, or overflow flags. Outputs are registered and stay readable until a new complete frame replaces them. The immediate-read test verifies the peripheral bus provides enough transaction latency for this configuration; a different clock ratio, pipeline depth, or wrapper needs a new completion contract.

Twiddles use 19 signed bits and 17 fractional bits. The native DSP complex multiplier uses three products and wraps its 16-bit input pre-add/subtract operations before multiplication. Each FFT butterfly output then arithmetic-shifts to eight fractional bits and wraps to 16 bits. Full-scale complex signals can consequently differ from an ideal DFT beyond ordinary output overflow. This test checks that behavior explicitly; passing full-scale tests does not establish saturation or ideal full-scale DFT accuracy. Applications must scale inputs to avoid intermediate overflow. Bounded vectors are checked independently against the ideal DFT with an explicit component error bound in the generated `reference.json`.

## Reproduce

Use a prepared, pinned Chipyard checkout and the RISC-V GCC toolchain. Build output must be a fresh directory.

```sh
python3 IPs/IP2/scripts/build-fft-tests.py \
  --chipyard-root "$CHIPYARD_ROOT" \
  --cc "$RISCV/bin/riscv64-unknown-elf-gcc" \
  --output "$PWD/build/fft-tests"

python3 IPs/IP2/scripts/run-regression.py \
  build/fft-tests/manifest.tsv build/fft-seed1 \
  --chipyard-root "$CHIPYARD_ROOT" \
  --simulator "$CHIPYARD_ROOT/sims/verilator/simulator-chipyard.harness-DualRocketFFTConfig" \
  --jobs 1 --max-cycles 10000000 --timeout 600 --seed 1
```

Repeat the normal campaign with seeds 2 and 3 and fresh output directories. Run `negative-control.tsv` separately with the same simulator. The negative-control runner must return failure, and its test log must identify the deliberate first-output numerical mismatch; a timeout or infrastructure failure is not a successful negative control.

Build provenance records source, vector-header, upstream-test, and ELF hashes. Simulation provenance records simulator and ELF hashes, seed, cycle and wall limits, DRAMSim configuration hashes, and exact commands. A normal result only passes if the simulator exits zero, emits its Verilog finish marker, has no simulator failure marker, and prints the expected software pass marker. Resume requires unchanged executable, manifest, runner, and simulation settings. CPU ISA/benchmark tests use the same runner and independent manifests.
