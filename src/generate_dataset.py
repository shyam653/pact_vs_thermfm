#!/usr/bin/env python3
"""
generate_dataset.py

Generates design-specific thermal datasets of varied power density distributions
and runs PACT SuperLU to calculate ground-truth temperature fields for Therm-FM training.
"""

import os
import sys
import argparse
import numpy as np
import h5py
import pandas as pd
from tqdm import tqdm

from run_pact_steady import run_pact

def create_design_dataset(flp_path, ptrace_path, num_samples=30, grid_size=32, out_h5="data/dataset.h5"):
    os.makedirs(os.path.dirname(os.path.abspath(out_h5)), exist_ok=True)
    scratch_dir = f"scratch/dataset_{os.path.basename(out_h5).split('.')[0]}"
    os.makedirs(scratch_dir, exist_ok=True)
    
    df_flp = pd.read_csv(flp_path)
    df_ptrace = pd.read_csv(ptrace_path)
    
    base_power = df_ptrace["Power"].astype(float).values.reshape((grid_size, grid_size))
    total_base_power = np.sum(base_power)
    if total_base_power == 0:
        total_base_power = 0.05
        
    die_w = float(df_flp["Length (m)"].iloc[0]) * grid_size
    die_h = float(df_flp["Width (m)"].iloc[0]) * grid_size
    dx = die_w / grid_size
    dy = die_h / grid_size
    
    x_coords = np.linspace(0, die_w, grid_size)
    y_coords = np.linspace(0, die_h, grid_size)
    xx, yy = np.meshgrid(x_coords, y_coords)
    z_coords = np.zeros_like(xx)
    
    inputs_list = []
    targets_list = []
    
    print(f"[Dataset Gen] Generating {num_samples} design-specific thermal samples for {out_h5}...")
    np.random.seed(42)
    
    for idx in tqdm(range(num_samples)):
        # Generate random hotspot power maps around base floorplan power
        num_hotspots = np.random.randint(1, 4)
        power_map = np.copy(base_power)
        
        for _ in range(num_hotspots):
            cx = np.random.uniform(0.1, 0.9) * grid_size
            cy = np.random.uniform(0.1, 0.9) * grid_size
            sigma = np.random.uniform(2.0, 6.0)
            amp = np.random.uniform(0.01, 0.1) * total_base_power
            
            for iy in range(grid_size):
                for ix in range(grid_size):
                    d2 = (ix - cx)**2 + (iy - cy)**2
                    power_map[iy, ix] += amp * np.exp(-d2 / (2 * sigma**2))
                    
        scale_p = np.random.uniform(0.8, 1.5)
        power_map = power_map * scale_p
        
        # Save temp FLP and PTRACE
        units = []
        powers = []
        u_idx = 0
        for iy in range(grid_size):
            for ix in range(grid_size):
                u_name = f"unit_{u_idx}"
                units.append({
                    "UnitName": u_name,
                    "X": f"{ix*dx:.6e}",
                    "Y": f"{iy*dy:.6e}",
                    "Length (m)": f"{dx:.6e}",
                    "Width (m)": f"{dy:.6e}",
                    "ConfigFile": "",
                    "Label": "Si"
                })
                powers.append({
                    "UnitName": u_name,
                    "Power": f"{power_map[iy, ix]:.6e}"
                })
                u_idx += 1
                
        flp_file = f"{scratch_dir}/sample_{idx}_flp.csv"
        ptrace_file = f"{scratch_dir}/sample_{idx}_ptrace.csv"
        pd.DataFrame(units).to_csv(flp_file, index=False)
        pd.DataFrame(powers).to_csv(ptrace_file, index=False)
        
        out_sample_dir = f"{scratch_dir}/sample_{idx}_out"
        temp_2d = run_pact(flp_file, ptrace_file, out_sample_dir, grid_rows=grid_size, grid_cols=grid_size, solver="SuperLU")
        
        if temp_2d is None:
            continue
            
        power_density = power_map / (dx * dy)
        channels = np.stack([xx, yy, z_coords, power_density], axis=0)[:, np.newaxis, :, :]
        target_temp = temp_2d[np.newaxis, :, :]
        
        inputs_list.append(channels)
        targets_list.append(target_temp)
        
    X_data = np.array(inputs_list, dtype=np.float32)
    Y_data = np.array(targets_list, dtype=np.float32)
    
    with h5py.File(out_h5, "w") as f:
        f.create_dataset("inputs", data=X_data)
        f.create_dataset("targets", data=Y_data)
        f.create_dataset("data", data=Y_data)
        
    print(f"[Dataset Gen] Saved dataset {out_h5}. Shapes: X={X_data.shape}, Y={Y_data.shape}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate design-specific dataset for Therm-FM")
    parser.add_argument("--flp", type=str, default="data/ibex_flp.csv")
    parser.add_argument("--ptrace", type=str, default="data/ibex_ptrace.csv")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--out-h5", type=str, default="data/dataset.h5")
    args = parser.parse_args()
    
    create_design_dataset(args.flp, args.ptrace, num_samples=args.samples, out_h5=args.out_h5)
