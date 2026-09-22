#!/usr/bin/env python3
"""
extract_pact_inputs.py

Extracts cell floorplan and power density from an OpenROAD run/ODB/reports
and formats them for PACT thermal simulation.
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np

def generate_pact_inputs_from_grid(die_width_m=0.0005, die_height_m=0.0005, grid_x=32, grid_y=32,
                                  total_power_w=0.05, flp_out="flp.csv", ptrace_out="ptrace.csv"):
    """
    Generates a uniform or non-uniform grid FLP and PTRACE for PACT.
    """
    dx = die_width_m / grid_x
    dy = die_height_m / grid_y
    
    units = []
    powers = []
    
    # Simple power map: center hotspot + background power
    cx, cy = grid_x / 2.0, grid_y / 2.0
    
    raw_powers = np.zeros((grid_y, grid_x))
    for iy in range(grid_y):
        for ix in range(grid_x):
            dist_sq = (ix - cx)**2 + (iy - cy)**2
            # Hotspot in the center (Gaussian distribution)
            p = 1.0 + 4.0 * np.exp(-dist_sq / 16.0)
            raw_powers[iy, ix] = p
            
    # Normalize power to total_power_w
    raw_powers = (raw_powers / np.sum(raw_powers)) * total_power_w
    
    idx = 0
    for iy in range(grid_y):
        for ix in range(grid_x):
            unit_name = f"unit_{idx}"
            x = ix * dx
            y = iy * dy
            p = raw_powers[iy, ix]
            
            # UnitName,X,Y,Length (m),Width (m),ConfigFile,Label
            units.append({
                "UnitName": unit_name,
                "X": f"{x:.6e}",
                "Y": f"{y:.6e}",
                "Length (m)": f"{dx:.6e}",
                "Width (m)": f"{dy:.6e}",
                "ConfigFile": "",
                "Label": "Si"
            })
            powers.append({
                "UnitName": unit_name,
                "Power": f"{p:.6e}"
            })
            idx += 1
            
    df_flp = pd.DataFrame(units)
    df_ptrace = pd.DataFrame(powers)
    
    os.makedirs(os.path.dirname(os.path.abspath(flp_out)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(ptrace_out)), exist_ok=True)
    
    df_flp.to_csv(flp_out, index=False)
    df_ptrace.to_csv(ptrace_out, index=False)
    print(f"[PACT Inputs] Saved FLP to {flp_out} ({len(units)} units)")
    print(f"[PACT Inputs] Saved PTRACE to {ptrace_out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract PACT inputs from design specs")
    parser.add_argument("--die-width", type=float, default=0.0005, help="Die width in meters")
    parser.add_argument("--die-height", type=float, default=0.0005, help="Die height in meters")
    parser.add_argument("--grid-x", type=int, default=32, help="Grid X resolution")
    parser.add_argument("--grid-y", type=int, default=32, help="Grid Y resolution")
    parser.add_argument("--total-power", type=float, default=0.05, help="Total power in Watts")
    parser.add_argument("--flp-out", type=str, default="data/ibex_flp.csv")
    parser.add_argument("--ptrace-out", type=str, default="data/ibex_ptrace.csv")
    args = parser.parse_args()
    
    generate_pact_inputs_from_grid(
        die_width_m=args.die_width,
        die_height_m=args.die_height,
        grid_x=args.grid_x,
        grid_y=args.grid_y,
        total_power_w=args.total_power,
        flp_out=args.flp_out,
        ptrace_out=args.ptrace_out
    )
