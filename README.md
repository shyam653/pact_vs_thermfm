# PACT vs. Therm-FM: Thermal-Aware Downstream STA Benchmark

A comprehensive VLSI thermal modeling and static timing analysis (STA) benchmarking suite comparing **PACT** (Physics-based Thermal Simulator) and **Therm-FM** (Neural Operator / Foundation Model for Thermal Simulation).

## Overview

Thermal effects significantly impact interconnect resistance and downstream Static Timing Analysis (STA) in modern VLSI design nodes (e.g., SkyWater 130nm). This repository provides an end-to-end pipeline to:
1. Extract power, floorplan, and parasitic SPEF data from PNR.
2. Run steady-state and transient thermal simulations using physics-based **PACT** (SuperLU/Xyce backend) and neural operator **Therm-FM**.
3. Adjust parasitic resistance based on spatially resolved temperature profiles:
   $$R(T) = R_{ref} \cdot [1 + \alpha \cdot (T - T_{ref})]$$
4. Perform thermal-aware downstream STA sign-off using OpenSTA across multiple design targets (Ibex RISC-V, GCD, AES, Archgen IPs).

## Repository Structure

- `src/`: Core Python modules for dataset generation, model training, thermal inference, SPEF adjustment, OpenSTA timing evaluation, and benchmarks.
- `docs/`: VLSI thermal STA specification and pipeline diagrams (`VLSI_THERMAL_STA_SPEC.md`).
- `deps/`: Embedded EDA tool wrappers and sub-modules (PACT, Therm-FM, Archgen-IPs, ORFS, Ibex).
- `archive/`: Benchmark results, reports, datasets, checkpoints, and generated thermal outputs.

## Getting Started

### Prerequisites

- Python 3.10+
- PyTorch, NumPy, SciPy, Pandas, h5py, Matplotlib
- Yosys & OpenROAD (OpenRCX / OpenSTA) for PNR and timing analysis

### Setup

```bash
git clone git@github.com:shyam653/pact_vs_thermfm.git
cd pact_vs_thermfm
```

### Running Benchmarks

```bash
# Run model training and evaluation across all design variants
python3 src/train_and_eval_all_variants.py

# Generate comprehensive analysis report
python3 src/generate_comprehensive_analysis.py
```
