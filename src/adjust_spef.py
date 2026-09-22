#!/usr/bin/env python3
"""
adjust_spef.py

Adjusts parasitic resistance in a baseline SPEF file based on a 2D/3D temperature grid.
Equation: R(T) = R_ref * [1 + alpha * (T - Tref)]
Reference Tref = 298.15 K (25°C).
Sky130 interconnect thermal coefficient alpha = 0.00386 / K.
"""

import os
import sys
import argparse
import re
import numpy as np

def adjust_spef_file(baseline_spef, temp_grid_path, out_spef, alpha=0.00386, tref=298.15):
    if not os.path.exists(baseline_spef):
        raise FileNotFoundError(f"Baseline SPEF file not found: {baseline_spef}")
        
    if os.path.exists(temp_grid_path):
        if temp_grid_path.endswith(".npy"):
            temp_grid = np.load(temp_grid_path)
        else:
            temp_grid = np.loadtxt(temp_grid_path, delimiter=",")
        mean_t = float(np.mean(temp_grid))
    else:
        print(f"[SPEF Adjuster Warning] Temperature grid {temp_grid_path} not found. Using Tref={tref}K.")
        mean_t = tref
        
    delta_t = mean_t - tref
    scale_factor = 1.0 + alpha * delta_t
    
    print(f"[SPEF Adjuster] Mean Temp = {mean_t:.2f} K (Delta T = {delta_t:+.2f} K) -> R scale factor = {scale_factor:.6f}")
    
    os.makedirs(os.path.dirname(os.path.abspath(out_spef)), exist_ok=True)
    
    # SPEF resistance section matching regex
    # e.g., "1 *1:1 *1:2 4.567"
    res_line_pattern = re.compile(r"^(\d+)\s+(\S+)\s+(\S+)\s+([0-9eE.+-]+)")
    
    in_res_section = False
    modified_count = 0
    
    with open(baseline_spef, "r") as fin, open(out_spef, "w") as fout:
        for line in fin:
            if line.startswith("*RES"):
                in_res_section = True
                fout.write(line)
                continue
            elif line.startswith("*END") or line.startswith("*CAP"):
                in_res_section = False
                fout.write(line)
                continue
                
            if in_res_section:
                m = res_line_pattern.match(line.strip())
                if m:
                    idx_str, node1, node2, r_val_str = m.groups()
                    r_val = float(r_val_str)
                    r_new = r_val * scale_factor
                    fout.write(f"{idx_str} {node1} {node2} {r_new:.6e}\n")
                    modified_count += 1
                else:
                    fout.write(line)
            else:
                fout.write(line)
                
    print(f"[SPEF Adjuster] Adjusted {modified_count} resistance elements -> Saved to {out_spef}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adjust SPEF parasitics using temperature grid")
    parser.add_argument("--baseline-spef", type=str, default="data/ibex_baseline.spef")
    parser.add_argument("--temp-grid", type=str, default="outputs/pact_superlu/temp_grid.npy")
    parser.add_argument("--out-spef", type=str, default="outputs/pact_superlu/adjusted.spef")
    parser.add_argument("--alpha", type=float, default=0.00386, help="Thermal coefficient of resistance")
    parser.add_argument("--tref", type=float, default=298.15, help="Reference temperature in K")
    args = parser.parse_args()
    
    adjust_spef_file(
        baseline_spef=args.baseline_spef,
        temp_grid_path=args.temp_grid,
        out_spef=args.out_spef,
        alpha=args.alpha,
        tref=args.tref
    )
