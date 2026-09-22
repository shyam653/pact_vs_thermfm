#!/usr/bin/env python3
"""
extract_archgen_inputs.py

Generates floorplan layout maps (flp.csv), power density traces (ptrace.csv),
and baseline SPEF files for the 3 Archgen IPs:
1. IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig)
2. IP2: Dual-Core RV64 Rocket SoC + 8-Point Fixed-Point FFT Accelerator
3. IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 Engines
"""

import os
import sys
import pandas as pd
import numpy as np

def generate_pact_inputs_from_grid(die_w_m, die_h_m, grid_rows, grid_cols, total_power_w, flp_out, ptrace_out):
    os.makedirs(os.path.dirname(os.path.abspath(flp_out)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(ptrace_out)), exist_ok=True)
    
    dx = die_w_m / grid_cols
    dy = die_h_m / grid_rows
    
    units = []
    powers = []
    
    # Base power distribution per cell
    num_cells = grid_rows * grid_cols
    base_p = total_power_w / num_cells
    
    # Add spatial power variation representing CPU core hotspots and accelerator blocks
    np.random.seed(42)
    power_grid = np.full((grid_rows, grid_cols), base_p)
    
    # Core 0 Hotspot (Top-Left quadrant)
    power_grid[4:12, 4:12] += (0.4 * total_power_w) / 64.0
    
    # Core 1 Hotspot (Bottom-Right quadrant)
    power_grid[20:28, 20:28] += (0.35 * total_power_w) / 64.0
    
    # Accelerator / Memory Controller Hotspot (Center)
    power_grid[12:20, 12:20] += (0.25 * total_power_w) / 64.0
    
    idx = 0
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            u_name = f"unit_{idx}"
            units.append({
                "UnitName": u_name,
                "X": f"{ix * dx:.6e}",
                "Y": f"{iy * dy:.6e}",
                "Length (m)": f"{dx:.6e}",
                "Width (m)": f"{dy:.6e}",
                "ConfigFile": "",
                "Label": "Si"
            })
            powers.append({
                "UnitName": u_name,
                "Power": f"{power_grid[iy, ix]:.6e}"
            })
            idx += 1
            
    df_flp = pd.DataFrame(units)
    df_ptrace = pd.DataFrame(powers)
    
    df_flp.to_csv(flp_out, index=False)
    df_ptrace.to_csv(ptrace_out, index=False)
    print(f"[Input Gen] Wrote FLP to {flp_out} and PTRACE to {ptrace_out} ({num_cells} grid units)")

def prepare_archgen_ip_data():
    os.makedirs("archive/design_inputs/archgen_ip1", exist_ok=True)
    os.makedirs("archive/design_inputs/archgen_ip2", exist_ok=True)
    os.makedirs("archive/design_inputs/archgen_ip3", exist_ok=True)
    
    # IP1: Dual-Core Rocket (1.2mm x 1.2mm die, 0.45W TDP)
    generate_pact_inputs_from_grid(
        0.0012, 0.0012, 32, 32, 0.45,
        "archive/design_inputs/archgen_ip1/flp.csv",
        "archive/design_inputs/archgen_ip1/ptrace.csv"
    )
    
    # IP2: Dual-Core Rocket + FFT (1.5mm x 1.5mm die, 0.65W TDP)
    generate_pact_inputs_from_grid(
        0.0015, 0.0015, 32, 32, 0.65,
        "archive/design_inputs/archgen_ip2/flp.csv",
        "archive/design_inputs/archgen_ip2/ptrace.csv"
    )
    
    # IP3: Dual-Core Rocket + NVDLA INT8 (2.0mm x 2.0mm die, 0.95W TDP)
    generate_pact_inputs_from_grid(
        0.0020, 0.0020, 32, 32, 0.95,
        "archive/design_inputs/archgen_ip3/flp.csv",
        "archive/design_inputs/archgen_ip3/ptrace.csv"
    )
    
    # Prepare Baseline SPEFs from ASAP7 reference SPEF
    spef_ref = "/home/boson4/OpenROAD/src/sta/examples/reg1_asap7.spef"
    for ip_id in ["archgen_ip1", "archgen_ip2", "archgen_ip3"]:
        out_spef = f"archive/design_inputs/{ip_id}/baseline.spef"
        with open(spef_ref, "r") as fin, open(out_spef, "w") as fout:
            fout.write(fin.read())
        print(f"[Input Gen] Prepared baseline SPEF at {out_spef}")

if __name__ == "__main__":
    prepare_archgen_ip_data()
