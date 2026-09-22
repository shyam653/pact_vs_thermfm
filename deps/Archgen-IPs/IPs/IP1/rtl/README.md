# Dual-Rocket RTL Snapshot

`dual-rocket/gen-collateral/` contains the 476 original Verilog/SystemVerilog
files generated for `chipyard.DualRocketConfig`, copied without RTL edits.
This is the two-core configuration, not the historical single-core
`RocketConfig` snapshot from the source publication repository.

The pinned Chipyard source is `e602d917dcc495c58cabe906535e411707096c9c`,
with Rocket Chip at `55bcad0f59436de98ea510334121de8546b9e9d7` and CIRCT
`firtool` 1.75.0. Configuration, generation conditions, and additional
component revisions are documented in
[CONFIGURATION.md](../docs/dual-rocket/CONFIGURATION.md).

The original generation directory, relative to the Chipyard checkout, was:

```text
sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketConfig/
```

## Scope and Integrity

The hardware DUT is `ChipTop`, which contains both Rocket harts and the
surrounding SoC. The snapshot also retains `TestHarness`, `TestDriver`, and
other simulation resources because they are part of the original 476-file
manifest. They are not additional on-chip hardware. Lint and synthesis must
select the `ChipTop` hierarchy; do not treat all simulation resources as DUTs.

Run this check from the repository root:

```bash
REPO_ROOT="$PWD"
(
  cd "$REPO_ROOT/rtl/dual-rocket/gen-collateral"
  sha256sum --check "$REPO_ROOT/docs/dual-rocket/artifacts/rtl.sha256"
)
```

The original behavioral SRAM modules remain intact. Synthesis-specific SRAM
mapping is performed by the existing synthesis scripts, outside this snapshot.
`top_module_hierarchy.json` and
`chipyard.harness.TestHarness.DualRocketConfig.top.mems.conf` are unmodified
copies required by those scripts. Other compact hardware metadata is under
[docs/dual-rocket/artifacts](../docs/dual-rocket/artifacts/README.md).

Upstream license texts and their origins are listed in
[third_party/README.md](../third_party/README.md). `LICENSE.SiFive` is also
copied beside the RTL for files whose headers reference that name.

## Running Tools

The existing generation and lint wrappers still require a prepared, pinned
external Chipyard checkout via `CHIPYARD_ROOT`. Lint uses the generated RTL
at the original Chipyard layout; this snapshot does not silently replace
that path or change the recorded upstream provenance.

The synthesis wrapper accepts a `GENERATED_DIR` override, so it can consume
this snapshot while retaining the pinned checkout as the source-provenance
reference. From the repository root, after setting `CHIPYARD_ROOT`,
`ORFS_ROOT` (or `PLATFORM_ROOT`), and the documented EDA-tool environment:

```bash
export GENERATED_DIR="$PWD/rtl/dual-rocket"
export OUTPUT_ROOT="$PWD/build/dual-rocket-synthesis-snapshot"
bash scripts/dual-rocket/synthesis/run.sh
```

`OUTPUT_ROOT` must not already exist. See the
[synthesis prerequisites](../scripts/dual-rocket/synthesis/README.md) and
[lint prerequisites](../scripts/dual-rocket/lint/README.md) before running.
EDA executables and Nangate45/fakeram45 libraries are not bundled here.
The snapshot has not been independently rerun through these workflows as
part of publication; the published reports describe the earlier recorded
runs against the identical RTL bytes.

No native simulation executable, C++ simulation-model package, DRAMSim2,
HTIF library, or RISC-V toolchain is included in this directory. Full
simulation reproduction uses the prepared Chipyard build described in the
configuration documentation. Generated absolute-path file lists and large
intermediate FIRRTL/build outputs are intentionally not copied.
