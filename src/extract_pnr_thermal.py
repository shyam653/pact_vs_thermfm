#!/usr/bin/env python3
"""
extract_pnr_thermal.py

Parses physical cell instance locations (X, Y) from post-PNR DEF files
for all 3 Archgen IPs, and extracts post-PNR physical floorplans (flp.csv)
and power density traces (ptrace.csv).
"""

import os
import sys
import re
import pandas as pd
import numpy as np

def parse_def_placements(def_path):
    die_area = None
    units = 1000.0 # Default DBU per micron
    components = []
    
    with open(def_path, "r") as f:
        in_components = False
        for line in f:
            line = line.strip()
            if line.startswith("UNITS DISTANCE MICRONS"):
                m = re.search(r"MICRONS\s+(\d+)", line)
                if m:
                    units = float(m.group(1))
            elif line.startswith("DIEAREA"):
                m = re.findall(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)", line)
                if len(m) >= 2:
                    die_area = (float(m[0][0]) / units, float(m[0][1]) / units, float(m[1][0]) / units, float(m[1][1]) / units)
            elif line.startswith("COMPONENTS"):
                in_components = True
            elif line.startswith("END COMPONENTS"):
                in_components = False
            elif in_components and line.startswith("-"):
                # Format: - inst_name macro_name + PLACED ( X Y ) Orient ;
                parts = line.split()
                inst_name = parts[1]
                macro_name = parts[2]
                x_val, y_val = 0.0, 0.0
                if "+" in parts and "PLACED" in parts:
                    p_idx = parts.index("PLACED")
                    try:
                        x_val = float(parts[p_idx + 2]) / units
                        y_val = float(parts[p_idx + 3]) / units
                    except Exception:
                        pass
                components.append({
                    "instance": inst_name,
                    "macro": macro_name,
                    "x": x_val,
                    "y": y_val
                })
                
    if die_area is None:
        die_area = (0.0, 0.0, 120.0, 120.0)
        
    return die_area, components

def create_post_pnr_thermal_inputs(ip_id, pnr_dir, grid_rows=32, grid_cols=32, total_power_w=0.5):
    def_path = os.path.join(pnr_dir, "post_pnr.def")
    flp_out = os.path.join(pnr_dir, "post_pnr_flp.csv")
    ptrace_out = os.path.join(pnr_dir, "post_pnr_ptrace.csv")
    
    die_area, comps = parse_def_placements(def_path)
    die_w_um = max(die_area[2] - die_area[0], 100.0)
    die_h_um = max(die_area[3] - die_area[1], 100.0)
    
    die_w_m = die_w_um * 1e-6
    die_h_m = die_h_um * 1e-6
    
    dx = die_w_m / grid_cols
    dy = die_h_m / grid_rows
    
    # Map cell placements to 2D power grid density
    power_grid = np.full((grid_rows, grid_cols), total_power_w / (grid_rows * grid_cols))
    
    for c in comps:
        rel_x = min(max((c["x"] - die_area[0]) / die_w_um, 0.0), 0.99)
        rel_y = min(max((c["y"] - die_area[1]) / die_h_um, 0.0), 0.99)
        
        gx = int(rel_x * grid_cols)
        gy = int(rel_y * grid_rows)
        
        # Add localized placement power spike around cell placement
        power_grid[gy, gx] += 0.05 * total_power_w
        
    units_list = []
    powers_list = []
    
    idx = 0
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            u_name = f"unit_{idx}"
            units_list.append({
                "UnitName": u_name,
                "X": f"{ix * dx:.6e}",
                "Y": f"{iy * dy:.6e}",
                "Length (m)": f"{dx:.6e}",
                "Width (m)": f"{dy:.6e}",
                "ConfigFile": "",
                "Label": "Si"
            })
            powers_list.append({
                "UnitName": u_name,
                "Power": f"{power_grid[iy, ix]:.6e}"
            })
            idx += 1
            
    pd.DataFrame(units_list).to_csv(flp_out, index=False)
    pd.DataFrame(powers_list).to_csv(ptrace_out, index=False)
    print(f"[Post-PNR Thermal] Extracted {len(comps)} placed instances from {def_path} -> Saved FLP & PTRACE to {pnr_dir}")

def extract_all_pnr_thermal_inputs():
    pnr_configs = [
        ("archgen_ip1", "archive/pnr/archgen_ip1", 0.45),
        ("archgen_ip2", "archive/pnr/archgen_ip2", 0.65),
        ("archgen_ip3", "archive/pnr/archgen_ip3", 0.95)
    ]
    for ip_id, pnr_dir, power_w in pnr_configs:
        create_post_pnr_thermal_inputs(ip_id, pnr_dir, total_power_w=power_w)

if __name__ == "__main__":
    extract_all_pnr_thermal_inputs()
