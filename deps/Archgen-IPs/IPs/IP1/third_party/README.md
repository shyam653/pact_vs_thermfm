# Upstream Notices and Provenance

The dual-Rocket RTL was generated from existing Chipyard and dependency
sources. Original license texts are preserved under `licenses/`, grouped
by their source repository. This directory does not assign a new blanket
license to the RTL, scripts, documentation, or presentation.

The paths in the following table are relative to the pinned Chipyard
checkout. Each archived license is a byte-for-byte copy of its source file.

| Component | Source path | Archived directory | Pinned commit |
| --- | --- | --- | --- |
| Chipyard | `LICENSE`, `LICENSE.SiFive` | [chipyard](licenses/chipyard/) | `e602d917dcc495c58cabe906535e411707096c9c` |
| Rocket Chip | `generators/rocket-chip/LICENSE.Berkeley`, `LICENSE.SiFive`, `LICENSE.jtag` | [rocket-chip](licenses/rocket-chip/) | `55bcad0f59436de98ea510334121de8546b9e9d7` |
| Inclusive cache | `generators/rocket-chip-inclusive-cache/LICENSE` | [rocket-chip-inclusive-cache](licenses/rocket-chip-inclusive-cache/) | `85420cf26f9abcebf685f0d68d14189598943c19` |
| TestChipIP | `generators/testchipip/LICENSE` | [testchipip](licenses/testchipip/) | `c807cad815069bd8779dd700239242a5891498b4` |
| Rocket Chip blocks | `generators/rocket-chip-blocks/LICENSE` | [rocket-chip-blocks](licenses/rocket-chip-blocks/) | `f8c7fddbd7639b15fefc968af59fcc4a8f7df73b` |
| Diplomacy | `generators/diplomacy/LICENSE.SiFive` | [diplomacy](licenses/diplomacy/) | `fe5e131d4fc8adec14a3ce4a4935bb5c0a269871` |
| HardFloat | `generators/hardfloat/LICENSE` | [hardfloat](licenses/hardfloat/) | `0ecaef097ce2accbd16a61613699450ed5533f29` |
| CDE | `tools/cde/LICENSE` | [cde](licenses/cde/) | `2bcaeae2b9914bd25497ce3c6fa62dc5ca80e09f` |

The generated `plusarg_reader` resources, `SimJTAG.v`, and `TestDriver.v`
explicitly refer to `LICENSE.SiFive`. A copy of the pinned Rocket Chip
`LICENSE.SiFive` is therefore also retained in
`rtl/dual-rocket/gen-collateral/`. That copy is a license notice, not an
additional Verilog source, and is outside the 476-entry RTL hash manifest.

Generated modules retain their original comments and source-location
references. Their generation by CIRCT does not replace the applicable
upstream notices. Relevant source repository links and the configuration
composition are in
[CONFIGURATION.md](../docs/dual-rocket/CONFIGURATION.md).

No EDA tool installation, foundry PDK, Nangate45 standard-cell library,
fakeram45 library, or simulation-toolchain dependency is redistributed in
this directory. Such external dependencies have their own licenses and
installation requirements.
