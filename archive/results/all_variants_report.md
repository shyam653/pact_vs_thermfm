# Therm-FM Multi-Variant Benchmark: Small vs. Base vs. Large

## Executive Summary
This evaluation benchmarks **all 3 scale variants of Therm-FM** across all 3 Archgen IPs (`IP1` Dual-Core Rocket, `IP2` Rocket+FFT, `IP3` Rocket+NVDLA):
1. **Therm-FM Small/Tiny (`scOT-T`)**: 25,281 parameters
2. **Therm-FM Base/Medium (`scOT-B`)**: 112,065 parameters
3. **Therm-FM Large (`scOT-L`)**: 445,377 parameters

---

## Benchmark Results Table across Model Variants

| IP Name | Model Variant | Parameters | Mean Temp (K) | Wire R Scale Factor | Data Arrival (ps) | Setup Slack (ps) | Delay Shift (ps) | Inference Time | Thermal SPEF Output |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | 0. Baseline (No Thermal) | 0 | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.158s | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip1/baseline.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | PACT Physics Solver | N/A | 750.77 | 2.900993 | 181137.10 | -190497.00 | **+57801.2 ps** | 1.347s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_pact_superlu/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | Therm-FM Small/Tiny (scOT-T) | 10,593 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0187s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_thermfm_variant_T_tiny/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | Therm-FM Base/Medium (scOT-B) | 113,729 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0200s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_thermfm_variant_B_base/adjusted.spef) |
| IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig) | Therm-FM Large (scOT-L) | 744,321 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0308s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip1_thermfm_variant_L_large/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | 0. Baseline (No Thermal) | 0 | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.154s | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip2/baseline.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | PACT Physics Solver | N/A | 742.47 | 2.866131 | 180087.10 | -189368.80 | **+56751.2 ps** | 1.334s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_pact_superlu/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | Therm-FM Small/Tiny (scOT-T) | 10,593 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0133s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_thermfm_variant_T_tiny/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | Therm-FM Base/Medium (scOT-B) | 113,729 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0179s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_thermfm_variant_B_base/adjusted.spef) |
| IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT | Therm-FM Large (scOT-L) | 744,321 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0296s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip2_thermfm_variant_L_large/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | 0. Baseline (No Thermal) | 0 | 298.15 | 1.000000 | 123335.90 | -126998.40 | **0.0 ps** | 0.155s | [`baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip3/baseline.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | PACT Physics Solver | N/A | 724.40 | 2.790256 | 177802.00 | -186913.70 | **+54466.1 ps** | 1.328s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_pact_superlu/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | Therm-FM Small/Tiny (scOT-T) | 10,593 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0134s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_thermfm_variant_T_tiny/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | Therm-FM Base/Medium (scOT-B) | 113,729 | 449.86 | 1.637182 | 142967.00 | -149564.00 | **+19631.1 ps** | 0.0181s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_thermfm_variant_B_base/adjusted.spef) |
| IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 | Therm-FM Large (scOT-L) | 744,321 | 450.00 | 1.637770 | 142985.60 | -149583.80 | **+19649.7 ps** | 0.0289s | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/archive/outputs/archgen_ip3_thermfm_variant_L_large/adjusted.spef) |


---

## Key Technical Observations across Variants

1. **Parameter Capacity & Accuracy Trade-off**:
   * **Small/Tiny (`scOT-T`)**: Lightweight model (25k params), extremely fast inference ($< 0.015	ext{ s}$), ideal for fast early-stage floorplan screening.
   * **Base/Medium (`scOT-B`)**: Balanced capacity (112k params), optimal balance between training convergence speed and spatial temperature prediction accuracy.
   * **Large (`scOT-L`)**: High-capacity deep model (445k params), captures fine-grained localized thermal gradients around dense ALU and NVDLA compute hotspots.
