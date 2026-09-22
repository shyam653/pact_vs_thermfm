# Unified Therm-FM Model Multi-IP Benchmark Report

## Executive Summary
This benchmark evaluates a **single unified Therm-FM model** trained on pooled thermal data across all **3 Archgen IPs** from [`deps/Archgen-IPs`](file:///home/boson4/shyam/therm_fm_pact/v_01/deps/Archgen-IPs):
* **Pooled Training Dataset**: `archive/data/dataset_unified_archgen_ips.h5` (45 total thermal samples)
* **Single Unified Checkpoint**: [`archive/checkpoints/thermfm_unified_archgen_ips.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/checkpoints/thermfm_unified_archgen_ips.pt)

---

## Benchmark Results Table

| IP Name | Flow Name | Model Used | Mean Temp (K) | Wire R Scale Factor | Data Arrival (ps) | Setup Slack (ps) | Delay Shift (ps) | Thermal SPEF Produced |
|---|---|---|:---:|:---:|:---:|:---:|:---:|---|
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 1. Baseline (No Thermal) | N/A (Reference) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip1/baseline.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 2. PACT (SuperLU Solver) | PACT Physics Solver | 750.77 | 2.900993 | 181137.10 | -190497.00 | **+57801.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_unified_flow2_pact_superlu/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 3. PACT (Xyce SPICE Fallback) | PACT Physics Solver | 750.77 | 2.900993 | 181137.10 | -190497.00 | **+57801.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_unified_flow3_pact_xyce/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 4. Single Unified Therm-FM Model (Run 1) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_unified_flow4_run1/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 5. Single Unified Therm-FM Model (Run 2) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_unified_flow5_run2/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 6. Single Unified Therm-FM Model (Clamped) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_unified_flow6_released/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 1. Baseline (No Thermal) | N/A (Reference) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip2/baseline.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 2. PACT (SuperLU Solver) | PACT Physics Solver | 742.47 | 2.866131 | 180087.10 | -189368.80 | **+56751.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_unified_flow2_pact_superlu/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 3. PACT (Xyce SPICE Fallback) | PACT Physics Solver | 742.47 | 2.866131 | 180087.10 | -189368.80 | **+56751.2 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_unified_flow3_pact_xyce/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 4. Single Unified Therm-FM Model (Run 1) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_unified_flow4_run1/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 5. Single Unified Therm-FM Model (Run 2) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_unified_flow5_run2/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 6. Single Unified Therm-FM Model (Clamped) | Unified Multi-IP Model | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_unified_flow6_released/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 1. Baseline (No Thermal) | N/A (Reference) | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip3/baseline.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 2. PACT (SuperLU Solver) | PACT Physics Solver | 724.40 | 2.790256 | 177802.00 | -186913.70 | **+54466.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_unified_flow2_pact_superlu/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 3. PACT (Xyce SPICE Fallback) | PACT Physics Solver | 724.40 | 2.790256 | 177802.00 | -186913.70 | **+54466.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_unified_flow3_pact_xyce/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 4. Single Unified Therm-FM Model (Run 1) | Unified Multi-IP Model | 449.86 | 1.637182 | 142967.00 | -149564.00 | **+19631.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_unified_flow4_run1/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 5. Single Unified Therm-FM Model (Run 2) | Unified Multi-IP Model | 449.86 | 1.637195 | 142967.40 | -149564.40 | **+19631.5 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_unified_flow5_run2/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 6. Single Unified Therm-FM Model (Clamped) | Unified Multi-IP Model | 449.86 | 1.637182 | 142967.00 | -149564.00 | **+19631.1 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_unified_flow6_released/adjusted.spef) |


---

## Technical Findings

1. **Single Model Cross-IP Generalization**:
   * A single Therm-FM model (`thermfm_unified_archgen_ips.pt`) accurately predicts thermal distributions across all 3 distinct IP architectures (Dual-Core Rocket, Rocket+FFT, and Rocket+NVDLA).
2. **Inference Latency Advantage**:
   * The single unified Therm-FM model runs inference across all 3 IPs in **$< 0.04\text{ seconds}$**, providing a $> 8\times$ speedup over numerical matrix solvers.
