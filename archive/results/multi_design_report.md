# Multi-Design Benchmark: Dedicated Therm-FM Models across 130nm & 7nm FinFET

## Executive Summary
This benchmark evaluates **dedicated Therm-FM models** trained specifically on design-specific thermal datasets for **3 open-source VLSI designs**:
1. **Ibex RISC-V Core** (SkyWater 130nm HD PDK) - Checkpoint: [`checkpoints/thermfm_ibex_sky130.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_ibex_sky130.pt)
2. **AES-128 Crypto Engine** (ASAP7 7nm FinFET PDK) - Checkpoint: [`checkpoints/thermfm_aes_asap7.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_aes_asap7.pt)
3. **GCD Math Unit** (ASAP7 7nm FinFET PDK) - Checkpoint: [`checkpoints/thermfm_gcd_asap7.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_gcd_asap7.pt)

## Multi-Design Benchmark Results Table

| Design Name | PDK / Node | Flow Name | Mean Temp (K) | R Scale Factor | Data Arrival (ns) | Setup Slack (ns) | Delay Shift (ps) | Thermal SPEF Produced |
|---|---|---|:---:|:---:|:---:|:---:|:---:|---|
| Ibex RISC-V Core (Sky130 HD 130nm) | Sky130 HD (130nm) | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 4.7761 | 5.0648 | **0.0 ps** | [`ibex_baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/data/ibex_baseline.spef) |
| Ibex RISC-V Core (Sky130 HD 130nm) | Sky130 HD (130nm) | 2. PACT (SuperLU Solver) | 676.06 | 2.458751 | 4.7771 | 5.0635 | **+1.0 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/ibex_sky130_pact_superlu/adjusted.spef) |
| Ibex RISC-V Core (Sky130 HD 130nm) | Sky130 HD (130nm) | 4. Dedicated Therm-FM Model | 313.43 | 1.058984 | 4.7761 | 5.0647 | **+0.0 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/ibex_sky130_thermfm_dedicated/adjusted.spef) |
| AES-128 Crypto Engine (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 123.3359 | -126.9984 | **0.0 ps** | [`aes_asap7_baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/data/aes_asap7_baseline.spef) |
| AES-128 Crypto Engine (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 2. PACT (SuperLU Solver) | 1739.47 | 7.053558 | 302.2672 | -322.4676 | **+178931.3 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/aes_asap7_pact_superlu/adjusted.spef) |
| AES-128 Crypto Engine (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 4. Dedicated Therm-FM Model | 313.78 | 1.065643 | 124.9983 | -128.7214 | **+1662.4 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/aes_asap7_thermfm_dedicated/adjusted.spef) |
| GCD Unit (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 1. Baseline (No Thermal) | 298.15 | 1.000000 | 123.3359 | -126.9984 | **0.0 ps** | [`gcd_asap7_baseline.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/data/gcd_asap7_baseline.spef) |
| GCD Unit (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 2. PACT (SuperLU Solver) | 2047.07 | 8.345467 | 339.5509 | -363.2583 | **+216215.0 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/gcd_asap7_pact_superlu/adjusted.spef) |
| GCD Unit (ASAP7 7nm FinFET) | ASAP7 (7nm FinFET) | 4. Dedicated Therm-FM Model | 313.41 | 1.064084 | 124.9586 | -128.6797 | **+1622.7 ps** | [`adjusted.spef`](file:///home/boson4/shyam/therm_fm_pact/v_01/outputs/gcd_asap7_thermfm_dedicated/adjusted.spef) |


## Dedicated Therm-FM Training & Verification
* **Design-Specific Training Datasets**:
  - `data/dataset_ibex_sky130.h5`
  - `data/dataset_aes_asap7.h5`
  - `data/dataset_gcd_asap7.h5`
* **Dedicated Checkpoints**:
  - `checkpoints/thermfm_ibex_sky130.pt`
  - `checkpoints/thermfm_aes_asap7.pt`
  - `checkpoints/thermfm_gcd_asap7.pt`

---
*Report generated automatically by `src/evaluate_multi_design.py`.*
