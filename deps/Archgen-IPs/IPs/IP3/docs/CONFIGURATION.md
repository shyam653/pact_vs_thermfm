# Configuration and reproduction

The authoritative configuration is
[`DualRocketNVDLAConfig.scala`](../config/DualRocketNVDLAConfig.scala):
`WithNVDLA("small", synthRAMs=false) ++ WithNHugeCores(2) ++ AbstractConfig`.
The [integration notes](INTEGRATION.md) describe the two recorded AXI wrapper
fixes, the small SDP readback tieoffs and the behavioral RAM selection.

| Input | Pinned revision |
| --- | --- |
| Chipyard | `e602d917dcc495c58cabe906535e411707096c9c` |
| NVDLA wrapper | `d99ffdc79bbf9b86c6cad0c278a785d5802c8209` |
| NVIDIA hardware reference | `8e06b1b9d85aab65b40d43d08eec5ea4681ff715` |
| Rocket Chip | `55bcad0f59436de98ea510334121de8546b9e9d7` |

Commands run from the catalog root. A matching provisioned Chipyard checkout,
Chisel 6.7.0/Scala 2.13.16, CIRCT firtool 1.75.0, Java, Verilator and the RISC-V
toolchain are external dependencies. This workspace uses Chipyard's
`.conda-env`; build scripts permit tool environment overrides.

```bash
export CHIPYARD_ROOT=/path/to/chipyard
bash scripts/build-soc.sh IPs/IP3 build/IP3-rebuild
python3 scripts/cpu-regression/build.py --chipyard-root "$CHIPYARD_ROOT" \
  --config DualRocketNVDLAConfig --output build/IP3-cpu-tests
```

The build wrapper verifies the pinned accelerator and applies exactly the
published patch set, or accepts an already matching worktree. It records the
actual configuration, changes, commands, exit codes and simulator hash.
Use a new output directory. Matching make artifacts may be reused; this is
not a clean-room toolchain bootstrap.

Follow the [NVDLA test instructions](../tests/README.md) to build programs
against the actual generated DTS and run the numerical jobs and both negative
controls. The [CPU workflow](../../../scripts/cpu-regression/README.md) covers
the applicable RV64 inventory, configured acceptance set and diagnostic cases.
All full-SoC campaigns must use the same published simulator identity.

The final normal campaigns use
`--max-cycles 3000000 --timeout 2400 --jobs 1`. Earlier attempts established
that the initial 900-second example was too short for this shared workspace;
those source versions and outcomes are retained as history. Use the exact
seed and control commands in the [numerical report](reports/nvdla/README.md)
to reproduce the accepted campaign. Host time varies with processor speed
and concurrent work.

For [lint and synthesis](../../../scripts/accelerator-soc/README.md), select
`CONFIG=DualRocketNVDLAConfig` and use `VERILATOR_MAX_NUM_WIDTH=1048576`
for lint, matching the native build's accepted numeric-constant width.
Synthesis additionally requires
`SYNTHESIS_MODE=preserve-memories ABC_MODE=direct`. This preserves RAM behavior and explicitly
reports memories without technology macros. Its mapped-portion area is not directly
comparable with the fully memory-mapped IP1/IP2 exploratory estimates.

The [generation manifest](artifacts/generation.json) records component pins,
original RTL bytes, configuration and license hashes. From
`IPs/IP3/rtl/gen-collateral`, check source bytes with:

```bash
sha256sum -c ../../docs/artifacts/rtl.sha256
```
