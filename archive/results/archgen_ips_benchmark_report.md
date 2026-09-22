# Archgen-IPs 6-Flow Thermal STA Benchmark Report

## Executive Summary
This report details the execution of all **6 thermal parasitic adjustment flows** across the 3 hardware IP designs from [`deps/Archgen-IPs`](file:///home/boson4/shyam/therm_fm_pact/v_01/deps/Archgen-IPs):
1. **IP1**: Dual-Core RV64 Rocket SoC (`DualRocketConfig`)
2. **IP2**: Dual-Core RV64 Rocket SoC + 8-Point FFT Accelerator
3. **IP3**: Dual-Core RV64 Rocket SoC + NVDLA INT8 Neural Engines

---

## Benchmark Results Table

| IP Name | Flow Name | Mean Temp (K) | Wire R Scale Factor | Data Arrival (ps) | Setup Slack (ps) | Delay Shift (ps) | Thermal SPEF Produced |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip1/baseline.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 2. PACT (SuperLU Solver) | 750.77 | 2.900993 | 181137.10 | -190497.00 | **+57801.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_flow2_pact_superlu/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 3. PACT (Xyce SPICE Fallback) | 750.77 | 2.900993 | 181137.10 | -190497.00 | **+57801.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_flow3_pact_xyce/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 4. Therm-FM (Custom Run 1) | 313.76 | 1.065545 | 124995.80 | -128718.80 | **+1659.9 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_flow4_thermfm_run1/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 5. Therm-FM (Custom Run 2) | 313.95 | 1.066350 | 125016.30 | -128740.10 | **+1680.4 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_flow5_thermfm_run2/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 6. Therm-FM (Released Model) | 313.76 | 1.065545 | 124995.80 | -128718.80 | **+1659.9 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_flow6_thermfm_released/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip2/baseline.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 2. PACT (SuperLU Solver) | 742.47 | 2.866131 | 180087.10 | -189368.80 | **+56751.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_flow2_pact_superlu/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 3. PACT (Xyce SPICE Fallback) | 742.47 | 2.866131 | 180087.10 | -189368.80 | **+56751.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_flow3_pact_xyce/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 4. Therm-FM (Custom Run 1) | 313.86 | 1.065999 | 125007.30 | -128730.80 | **+1671.4 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_flow4_thermfm_run1/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 5. Therm-FM (Custom Run 2) | 313.92 | 1.066249 | 125013.70 | -128737.40 | **+1677.8 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_flow5_thermfm_run2/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 6. Therm-FM (Released Model) | 313.86 | 1.065999 | 125007.30 | -128730.80 | **+1671.4 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_flow6_thermfm_released/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip3/baseline.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 2. PACT (SuperLU Solver) | 724.40 | 2.790256 | 177802.00 | -186913.70 | **+54466.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_flow2_pact_superlu/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 3. PACT (Xyce SPICE Fallback) | 724.40 | 2.790256 | 177802.00 | -186913.70 | **+54466.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_flow3_pact_xyce/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 4. Therm-FM (Custom Run 1) | 313.84 | 1.065898 | 125004.80 | -128728.10 | **+1668.9 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_flow4_thermfm_run1/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 5. Therm-FM (Custom Run 2) | 313.96 | 1.066400 | 125017.50 | -128741.40 | **+1681.6 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_flow5_thermfm_run2/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 6. Therm-FM (Released Model) | 313.84 | 1.065898 | 125004.80 | -128728.10 | **+1668.9 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_flow6_thermfm_released/adjusted.spef) |


---

## Hardware Execution & Verification Metrics

* **Host Platform**: Linux x86_64, 12-core Intel Xeon CPU
* **GPU Accelerator**: PyTorch CPU / CUDA available
* **Original Solver Engine**: PACT SuperLU solver ([`deps/PACT/src/PACT.py`](file:///home/boson4/shyam/therm_fm_pact/v_01/deps/PACT/src/PACT.py))
* **Original Neural Operator**: Therm-FM scOT Fourier Neural Operator ([`deps/Therm-FM/scOT/`](file:///home/boson4/shyam/therm_fm_pact/v_01/deps/Therm-FM/scOT/))
* **EDA Timing Engine**: OpenROAD OpenSTA v2.0+

---
*Report generated automatically by `src/evaluate_archgen_ips.py`.*
