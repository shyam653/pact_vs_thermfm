# Configuration and reproduction

The authoritative configuration is
[`DualRocketFFTConfig.scala`](../config/DualRocketFFTConfig.scala). It selects
an 8-point FFT at `0x2400`, 16 bits per component and eight fractional bits,
two Huge Rocket cores, and Chipyard's `AbstractConfig`.

| Input | Pinned revision |
| --- | --- |
| Chipyard | `e602d917dcc495c58cabe906535e411707096c9c` |
| FFTGenerator | `e361f229b5574931f555b10e1b48f2769c07832c` |
| Rocket Chip | `55bcad0f59436de98ea510334121de8546b9e9d7` |

The complete component pins and source hashes are in
[`generation.json`](artifacts/generation.json). The FFT generator itself is
unmodified. The custom Scala configuration is the intentional Chipyard addition.
The NVDLA wrapper was initialized while preparing IP3 and is present in the
generator assembly, but no NVDLA device is instantiated by this configuration.

Commands below run from the catalog repository root. A provisioned matching
Chipyard checkout, Chisel 6.7.0/Scala 2.13.16, CIRCT firtool 1.75.0, Java,
Verilator, and the RISC-V toolchain are external dependencies. This workspace
uses Chipyard's `.conda-env`; the scripts permit tool environment overrides.

```bash
export CHIPYARD_ROOT=/path/to/chipyard
bash scripts/build-soc.sh IPs/IP2 build/IP2-rebuild
python3 scripts/cpu-regression/build.py --chipyard-root "$CHIPYARD_ROOT" \
  --config DualRocketFFTConfig --output build/cpu-tests
```

The build wrapper checks the pinned source, initializes the accelerator,
installs the exact configuration without overwriting a different file,
checks the accelerator against its published patch set, and runs RTL generation
and the native simulator build. Output directories must be new. Make may reuse
matching generator or native build artifacts; this is not a clean-room toolchain
bootstrap. Provenance records the actual worktree state and build commands.

Run the CPU suites against the resulting simulator using
`IPs/IP2/scripts/run-regression.py`; use the FFT commands in
[`tests/README.md`](../tests/README.md) for accelerator tests and negative control.
The shared [CPU workflow](../../../scripts/cpu-regression/README.md) explains the
complete inventory, limits, retries and baseline comparison.

Full-SoC lint and synthesis use
[`scripts/accelerator-soc`](../../../scripts/accelerator-soc/README.md), with
`CONFIG=DualRocketFFTConfig`. Synthesized SRAM adapters are generated outside
the original RTL snapshot and compared against every original memory interface.
Nangate45/fakeram45 is an exploratory library, not a manufacturable target.

The published implementation result uses the separately recorded
[checkpoint mapping workflow](../../../scripts/checkpoint-synthesis/README.md).
It reuses the verified pre-ABC ChipTop produced by the original synthesis flow,
then runs `strash; &get -n; &nf; &put`, mapped-design checks and OpenROAD linking.
The original default optimizer was stopped after the independent runs passed.
The [comparison](reports/synthesis/comparison.json) uses a fresh IP1 mapping
with the same explicit ABC commands and libraries. Its numbers must not be
mixed with IP1's earlier default-optimizer area estimate.

The exported [`rtl`](../rtl/) contains unchanged generated source bytes plus
hierarchy and memory-interface metadata. Validate its source hashes from
`IPs/IP2/rtl/gen-collateral` with:

```bash
sha256sum -c ../../docs/artifacts/rtl.sha256
```
