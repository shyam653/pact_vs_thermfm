#!/usr/bin/env python3
"""
diagnose_pact_zero_power.py

Phase 1.1 diagnostic script to test PACT at zero power (P=0.0W)
under both SuperLU and SPICE solvers, and examine ambient temperature handling.
"""

import os
import sys
import numpy as np
import pandas as pd

# Ensure src path is accessible
sys.path.insert(0, os.path.abspath("src"))
from run_pact_steady import run_pact

def create_zero_power_ptrace(flp_path, out_ptrace_path):
    df_flp = pd.read_csv(flp_path)
    if "UnitName" in df_flp.columns:
        unit_names = df_flp["UnitName"].values
    elif "Unit" in df_flp.columns:
        unit_names = df_flp["Unit"].values
    else:
        unit_names = [f"unit_{i}" for i in range(len(df_flp))]
    
    df_ptrace = pd.DataFrame({
        "UnitName": unit_names,
        "Power": [0.0] * len(unit_names)
    })
    os.makedirs(os.path.dirname(os.path.abspath(out_ptrace_path)), exist_ok=True)
    df_ptrace.to_csv(out_ptrace_path, index=False)
    print(f"Created zero power trace at {out_ptrace_path} with {len(unit_names)} units.")

def main():
    print("=== Phase 1.1: Diagnosing PACT Zero-Power & Ambient Handling ===")
    
    flp_path = "archive/data/ibex_flp.csv"
    zero_ptrace_path = "scratch/zero_ibex_ptrace.csv"
    
    if not os.path.exists(flp_path):
        print(f"Error: floorplan file {flp_path} not found.")
        return

    create_zero_power_ptrace(flp_path, zero_ptrace_path)
    
    for solver in ["SuperLU", "SPICE"]:
        for ambient_k in [298.15, 318.15]:
            out_dir = f"scratch/pact_test_zero_{solver}_{int(ambient_k)}"
            print(f"\n--- Testing Solver: {solver}, Ambient: {ambient_k} K ---")
            try:
                temp_grid = run_pact(
                    flp_path=flp_path,
                    ptrace_path=zero_ptrace_path,
                    out_dir=out_dir,
                    grid_rows=32,
                    grid_cols=32,
                    solver=solver,
                    ambient_temp_k=ambient_k
                )
                if temp_grid is not None:
                    print(f"Result for {solver} @ {ambient_k}K: min={temp_grid.min():.4f}K, max={temp_grid.max():.4f}K, mean={temp_grid.mean():.4f}K")
                    print(f"Difference from ambient ({ambient_k}K): mean diff = {temp_grid.mean() - ambient_k:.4f}K")
            except Exception as e:
                print(f"Failed to run PACT for {solver} @ {ambient_k}K: {e}")

if __name__ == "__main__":
    main()
