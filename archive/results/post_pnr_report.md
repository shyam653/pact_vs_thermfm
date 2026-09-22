# Archgen-IPs Post-PNR Thermal STA Benchmark Report

## Executive Summary
This report summarizes the **Post-PNR physical layout benchmark** performed on the 3 Archgen IPs using OpenROAD physical layout extraction, original PACT physics solver, and all 3 Therm-FM model variants (Small, Base, Large):
1. **IP1**: Dual-Core RV64 Rocket SoC (`DualRocketConfig`) - DEF Layout: [`archive/pnr/archgen_ip1/post_pnr.def`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip1/post_pnr.def)
2. **IP2**: Dual-Core RV64 Rocket SoC + 8-Point FFT - DEF Layout: [`archive/pnr/archgen_ip2/post_pnr.def`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip2/post_pnr.def)
3. **IP3**: Dual-Core RV64 Rocket SoC + NVDLA INT8 - DEF Layout: [`archive/pnr/archgen_ip3/post_pnr.def`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip3/post_pnr.def)

---

## Post-PNR Benchmark Results Table

| IP Design | Evaluated Flow / Variant | Mean Temp (K) | Wire R Scale Factor | Data Arrival (ps) | Setup Slack (ps) | Thermal Delay Shift (ps) | Latency (s) | Post-PNR Thermal SPEF |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 1. Post-PNR Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.156s | [`post_pnr.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip1/post_pnr.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 2. Post-PNR PACT SuperLU Solver | 7506.93 | 31.276859 | 1003237.90 | -1089530.20 | **+879902.0 ps** | 1.329s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_post_pnr_pact/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 3. Post-PNR Therm-FM Small (scOT-T) | 446.89 | 1.624691 | 142572.20 | -149143.00 | **+19236.3 ps** | 0.0236s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_post_pnr_small/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 3. Post-PNR Therm-FM Base (scOT-B) | 446.89 | 1.624691 | 142572.20 | -149143.00 | **+19236.3 ps** | 0.0214s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_post_pnr_base/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 3. Post-PNR Therm-FM Large (scOT-L) | 445.70 | 1.619708 | 142408.80 | -148969.30 | **+19072.9 ps** | 0.0357s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_post_pnr_large/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 1. Post-PNR Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.155s | [`post_pnr.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip2/post_pnr.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 2. Post-PNR PACT SuperLU Solver | 6988.16 | 29.098045 | 940132.60 | -1020473.10 | **+816796.7 ps** | 1.334s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_post_pnr_pact/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 3. Post-PNR Therm-FM Small (scOT-T) | 446.74 | 1.624068 | 142546.70 | -149116.30 | **+19210.8 ps** | 0.0135s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_post_pnr_small/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 3. Post-PNR Therm-FM Base (scOT-B) | 445.85 | 1.620331 | 142428.50 | -148990.30 | **+19092.6 ps** | 0.0183s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_post_pnr_base/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 3. Post-PNR Therm-FM Large (scOT-L) | 447.03 | 1.625314 | 142591.80 | -149164.00 | **+19255.9 ps** | 0.0362s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_post_pnr_large/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 1. Post-PNR Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.156s | [`post_pnr.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip3/post_pnr.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 2. Post-PNR PACT SuperLU Solver | 5859.08 | 24.355918 | 802812.70 | -870200.40 | **+679476.8 ps** | 1.335s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_post_pnr_pact/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 3. Post-PNR Therm-FM Small (scOT-T) | 447.18 | 1.625936 | 142611.50 | -149185.00 | **+19275.6 ps** | 0.0141s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_post_pnr_small/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 3. Post-PNR Therm-FM Base (scOT-B) | 447.78 | 1.628428 | 142690.30 | -149269.00 | **+19354.4 ps** | 0.0182s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_post_pnr_base/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 3. Post-PNR Therm-FM Large (scOT-L) | 445.11 | 1.617217 | 142330.10 | -148885.30 | **+18994.2 ps** | 0.0301s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_post_pnr_large/adjusted.spef) |


---

## Physical Design Summary
* **Layout Engine**: OpenROAD v2.0+ (Global & Detailed Cell Placement)
* **Placement Sites**: `asap7sc7p5t` (ASAP7 7nm FinFET 7.5T Track Grid)
* **Exported Physical Assets**:
  - `archive/pnr/archgen_ip1/post_pnr.def` (24,639 bytes)
  - `archive/pnr/archgen_ip2/post_pnr.def` (31,799 bytes)
  - `archive/pnr/archgen_ip3/post_pnr.def` (43,735 bytes)
