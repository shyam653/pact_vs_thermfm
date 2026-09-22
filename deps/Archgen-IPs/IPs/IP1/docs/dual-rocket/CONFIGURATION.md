# How DualRocketConfig Was Generated

This document records the existing upstream configuration used for the
dual-core experiment. The [SoC inventory](SOC.md) describes the resulting
hardware. Configuration documentation was prepared before the new lint and
synthesis rerun; this page does not assert results for that rerun.

## Exact Configuration

The selected class is `chipyard.DualRocketConfig`, already present in
Chipyard. No Scala configuration or generated RTL was edited to add the
second CPU:

```scala
class DualRocketConfig extends Config(
  new freechips.rocketchip.rocket.WithNHugeCores(2) ++
  new chipyard.config.AbstractConfig)
```

The single-core `RocketConfig` at this revision uses the same composition
with `WithNHugeCores(1)`. Selecting the existing two-core class preserves the
base SoC while adding a second Rocket tile. The name `Huge` is an upstream
parameter preset, not a measured performance designation.

Sources: [RocketConfigs.scala, lines 11-17](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/config/RocketConfigs.scala#L11-L17)
and [WithNHugeCores](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60).

CDE configuration composition searches the left side first. A fragment can
read the lower-priority composition through `up`, so this is not ordinary
Scala class inheritance or a textual concatenation of modules.
`WithNHugeCores` adds two tile parameters and increments `NumTiles`;
`AbstractConfig` provides the surrounding system and ultimately delegates
defaults to Rocket Chip's `BaseConfig`. `AbstractConfig` alone has no tiles
and is not the complete runnable design. See the pinned
[CDE precedence implementation](https://github.com/chipsalliance/cde/blob/2bcaeae2b9914bd25497ce3c6fa62dc5ca80e09f/cde/src/chipsalliance/rocketchip/config.scala#L118-L127)
and [AbstractConfig](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/config/AbstractConfig.scala#L13).

## Pinned Inputs

The upstream checkout was clean when generation was recorded. These are
the relevant checked-out commits, not moving branch names:

| Component | Commit |
| --- | --- |
| Chipyard | `e602d917dcc495c58cabe906535e411707096c9c` |
| Rocket Chip | `55bcad0f59436de98ea510334121de8546b9e9d7` |
| Inclusive cache | `85420cf26f9abcebf685f0d68d14189598943c19` |
| TestChipIP | `c807cad815069bd8779dd700239242a5891498b4` |
| Rocket Chip blocks | `f8c7fddbd7639b15fefc968af59fcc4a8f7df73b` |
| Diplomacy | `fe5e131d4fc8adec14a3ce4a4935bb5c0a269871` |
| HardFloat | `0ecaef097ce2accbd16a61613699450ed5533f29` |
| CDE | `2bcaeae2b9914bd25497ce3c6fa62dc5ca80e09f` |

Chipyard's pinned [.gitmodules](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/.gitmodules)
identifies the upstream repositories. Its gitlinks pin the submodule
revisions. The generation provenance records the larger submodule inventory;
unrelated accelerator and software submodules were not all initialized.

The recorded generation used Chisel **6.7.0**, Scala **2.13.16**, CIRCT
`firtool` **1.75.0**, and OpenJDK **20.0.2-internal**. `USE_CHISEL7` was
unset. These are observed versions, not a claim that arbitrary newer
versions produce identical RTL. Chipyard's pinned
[build.sbt](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/build.sbt#L3-L6)
selects the Chisel/Scala versions. Generation reused existing cached
generator JARs; it was not a clean-room dependency/toolchain bootstrap.

## Generation Flow

1. GNU make selects `SBT_PROJECT=chipyard`, `CONFIG_PACKAGE=chipyard`,
   `CONFIG=DualRocketConfig`, `MODEL=TestHarness`, and `TOP=ChipTop`.
2. `chipyard.Generator` runs Chipyard's Chisel stage, constructs the
   parameter composition, and elaborates `chipyard.harness.TestHarness`.
   That harness instantiates a `ChipTop`, whose default system is
   `DigitalTop`. Diplomacy negotiates devices, buses and clocks.
3. Elaboration emits FIRRTL, annotations, the device tree, register maps,
   memory map, L2 metadata, and selected simulation test suites.
4. `firtool --format=fir` lowers FIRRTL with the generated annotations.
   The recorded flow uses `--repl-seq-mem`, `--split-verilog`, and
   `--export-module-hierarchy`, producing separate RTL modules and memory
   interface descriptions. These are logical memory interfaces, not
   automatically selected foundry SRAM macros.
5. The make flow collects black-box resources and builds source file lists
   for the DUT and simulation model. The `verilog` target stops at RTL
   generation. Building the native Verilator simulator is a separate step.

The executable generator call selected:

```text
chipyard.Generator
  --name chipyard.harness.TestHarness.DualRocketConfig
  --top-module chipyard.harness.TestHarness
  --legacy-configs chipyard:DualRocketConfig
```

Implementation references: [Generator.scala](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/Generator.scala),
[make defaults](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/variables.mk#L88-L101),
and [generation recipes](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/common.mk#L145-L240).

## Reproduce From a Prepared Checkout

Use the pinned Chipyard checkout and its required submodules, with the
matching toolchain/dependencies installed. First-time setup can require
network downloads, Java/SBT dependency resolution, native build tools,
`dtc`, `jq`, and the RISC-V compiler used by the boot software. This recipe
does not pretend that cloning this RTL/results repository installs those
dependencies.

Run from the prepared Chipyard checkout. The following reproduces the
environment layout used for this generation without host-specific paths:

```bash
export CY_DIR="$PWD"
git rev-parse HEAD
git status --short
git submodule status
source "$CY_DIR/env.sh"

export JAVA_HOME="$CY_DIR/.conda-env/lib/jvm"
export RISCV="$CY_DIR/.conda-env/riscv-tools"
export PATH="$JAVA_HOME/bin:$RISCV/bin:$CY_DIR/.conda-env/bin:$PATH"
export LD_LIBRARY_PATH="$RISCV/lib:$CY_DIR/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
unset USE_CHISEL7
mkdir -p "$CY_DIR/.java_tmp"
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M -Djava.io.tmpdir=$CY_DIR/.java_tmp"

java -version
firtool --version
make -C "$CY_DIR/sims/verilator" verilog CONFIG=DualRocketConfig -j2
```

In the recorded environment, `env.sh` only set the checkout location; it
did not activate Java, CIRCT, or RISC-V tools. On another installation,
activate the corresponding prepared environment instead of assuming the
same `.conda-env` layout. Confirm tool versions before generation. Cached
JARs must match the selected source/dependencies; do not reuse an unrelated
cache after changing the checkout.

The separate simulator build command is:

```bash
make -C "$CY_DIR/sims/verilator" CONFIG=DualRocketConfig -j2
```

It additionally needs a working native compiler and Verilator; the
recorded simulator used Verilator 5.022. RTL generation by itself is not
simulation, lint, synthesis, timing closure, or a passing software test.

## Generated Evidence

Relative to the upstream checkout, the output directory is:

```text
sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketConfig/
```

For brevity, `NAME` below means
`chipyard.harness.TestHarness.DualRocketConfig`.

Small generated metadata is archived in this repository's
[artifacts directory](artifacts/):
[DTS](artifacts/chipyard.harness.TestHarness.DualRocketConfig.dts),
[hardware JSON](artifacts/chipyard.harness.TestHarness.DualRocketConfig.json),
[memory map](artifacts/chipyard.harness.TestHarness.DualRocketConfig.memmap.json),
and [L2 metadata](artifacts/chipyard.harness.TestHarness.DualRocketConfig.l2.json).
The full upstream output directory remains the reference for the other
artifact types listed below.

| Artifact | Purpose |
| --- | --- |
| `NAME.dts`, `NAME.json` | Generated software-visible hardware description |
| `NAME.memmap.json` | Elaborated address ranges and access attributes |
| `NAME.l2.json` | L2 bank geometry and two coherent directory clients |
| `NAME.top.mems.conf` | Seven distinct DUT SRAM interface shapes |
| `top_module_hierarchy.json` | DUT hierarchy, separate from the model hierarchy |
| `NAME.d` | Configured ISA and benchmark selections |
| `gen-collateral/ChipTop.sv` | DUT ports and top-level implementation |
| `gen-collateral/TestHarness.sv`, `TestDriver.v` | Simulation-side integration |

The recorded directory contained 476 `.sv`/`.v` source files, including
simulation resources. That count is not the number of hardware instances
or the number of synthesizable DUT source files. Downstream lint and
synthesis must select the **ChipTop hierarchy**, not synthesize every
simulation resource as part of the SoC. Preserve source hashes and the
original behavioral memories before applying synthesis-specific adapters.

## Retained Generation Warnings

The configuration retains the decoupled serial TileLink PHY warning:
heavy link loading can deadlock, and the generator points to
`CreditedSourceSyncSerialPhyParams` when deadlock freedom is required.
No PHY replacement was made. See [interfaces and limits](SOC.md#interfaces-and-limits).

The recorded generation also reported fixed-clock device-tree warnings,
two debug-hart-index width warnings during Chisel elaboration, and CIRCT
warnings about deprecated printf-encoded verification operations. Generation
completed, but completion does not make these warnings disappear or
substitute for a fresh lint report.
