# Archgen IPs

This repository is organized as a catalog of self-contained hardware IPs.

| IP | Description | Location |
| --- | --- | --- |
| IP1 | Dual-core RV64 Rocket SoC generated from Chipyard `DualRocketConfig` | [`IPs/IP1`](IPs/IP1/) |
| IP2 | Dual-core RV64 Rocket SoC with a shared 8-point fixed-point FFT | [`IPs/IP2`](IPs/IP2/) |
| IP3 | Dual-core RV64 Rocket SoC with NVDLA small INT8 engines and coherent DMA | [`IPs/IP3`](IPs/IP3/) |

Each IP directory contains its RTL, configuration notes, verification evidence, and reproduction scripts. Accelerator configurations share the pinned build, CPU regression, lint and synthesis workflows in [`scripts`](scripts/).
