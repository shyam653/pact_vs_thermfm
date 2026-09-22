# 2coreriscv_chipyard1

Dual-Rocket full-SoC RTL, configuration documentation, verification reports,
and an editable presentation, generated from the pinned Chipyard
`DualRocketConfig`.

## Start Here

- [SoC inventory](docs/dual-rocket/SOC.md): two RV64 Rocket cores, private
  instruction/data caches, shared 512 KiB L2, scratchpad, UART, interrupts,
  debug, serial TileLink, and external AXI memory interface. No FFT accelerator.
- [Configuration and build process](docs/dual-rocket/CONFIGURATION.md).
- [Actual dual-core RTL](rtl/README.md), including the complete generated
  source inventory and required synthesis metadata.
- [Simulation report](docs/dual-rocket/reports/simulation/README.md).
- [Lint report](docs/dual-rocket/reports/lint/README.md).
- [Full-SoC synthesis report](docs/dual-rocket/reports/synthesis/README.md).
- [PowerPoint](presentations/dual-rocket-soc/Dual_Rocket_SoC_Overview.pptx)
  and [PDF](presentations/dual-rocket-soc/Dual_Rocket_SoC_Overview.pdf).
- [Reproduction scripts](scripts/dual-rocket/README.md).

## Recorded Results

The reports retain their original September 6, 2026 evidence. Publication and
presentation preparation did not rerun EDA or simulation.

| Check | Recorded result |
| --- | --- |
| Configured simulation tests | 335 ISA tests and 12 benchmarks passed |
| Broader 422-test campaign | 391 passed, 25 failed, 6 host wall-clock timeouts |
| Fresh full-SoC lint | Verilator: 0 errors, 2484 warnings; slang: 0 errors, 21 warnings |
| Full `ChipTop` synthesis | 383,569 standard cells and 194 SRAM macro instances |
| SRAM adapter comparison | 212,364 compared cycles passed across three seeds |
| OpenROAD | Mapped design linked successfully; no place-and-route or timing signoff |

Read the reports for unsupported probes, test-oracle defects, residual warnings,
and untested behavior. Simulation success is not exhaustive ISA or coherence
verification. Nangate45/fakeram45 is an exploratory, non-manufacturable platform;
reported library area is not die area or proof of an achieved clock frequency.

## Snapshot Scope

This repository publishes the **dual-core** snapshot. It does not include the
historical single-core RTL or generated native simulator from the original
`chipyard_rocketconfig` repository. The 476 RTL files include harness resources;
the lint and synthesis design under test is `ChipTop`.

Tools, PDK/library files, native simulator binaries, large mapped netlists and
physical databases are not bundled. The existing reproduction scripts require
a provisioned, pinned Chipyard checkout and external tools. See
[publication provenance](PUBLICATION.md) and [third-party notices](third_party/README.md).

Validate the compact reports from this repository root:

```bash
python3 scripts/dual-rocket/validate-publication.py
```
