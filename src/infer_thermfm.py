#!/usr/bin/env python3
"""
infer_thermfm.py

Runs inference using a trained Therm-FM model checkpoint (or released model)
for a given floorplan and power trace, producing 2D temperature grid files.
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import torch

from train_thermfm import ThermFMModel

def run_inference(flp_path, ptrace_path, ckpt_path, out_dir, grid_size=32, ambient_k=318.15, device_str=None):
    os.makedirs(out_dir, exist_ok=True)
    
    if device_str is None:
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)
    
    df_flp = pd.read_csv(flp_path)
    df_ptrace = pd.read_csv(ptrace_path)
    
    # Reconstruct power map 2D grid
    power_map = df_ptrace["Power"].astype(float).values.reshape((grid_size, grid_size))
    
    die_w = float(df_flp["Length (m)"].iloc[0]) * grid_size
    die_h = float(df_flp["Width (m)"].iloc[0]) * grid_size
    dx = die_w / grid_size
    dy = die_h / grid_size
    
    x_coords = np.linspace(0, die_w, grid_size)
    y_coords = np.linspace(0, die_h, grid_size)
    xx, yy = np.meshgrid(x_coords, y_coords)
    z_coords = np.zeros_like(xx)
    power_density = power_map / (dx * dy)
    
    # Input tensor shape: (1, 4, H, W)
    x_input = np.stack([xx, yy, z_coords, power_density], axis=0)[np.newaxis, :, :, :]
    x_tensor = torch.tensor(x_input, dtype=torch.float32).to(device)
    
    if os.path.exists(ckpt_path):
        print(f"[Therm-FM Infer] Loading checkpoint from {ckpt_path} (Device={device})...")
        ckpt = torch.load(ckpt_path, map_location="cpu")
        variant = ckpt.get("variant", "B")
        model = ThermFMModel(in_channels=4, out_channels=1, variant=variant)
        model.load_state_dict(ckpt["state_dict"])
    else:
        print(f"[Therm-FM Infer] Checkpoint {ckpt_path} not found. Using initialized weights (Device={device}).")
        model = ThermFMModel(in_channels=4, out_channels=1, variant="B")
        
    model.to(device)
    model.eval()
    with torch.no_grad():
        pred_delta_t = model(x_tensor).squeeze().cpu().numpy() # (H, W)
        
    pred_temp_k = np.clip(pred_delta_t + ambient_k, 298.15, 450.0)
    
    np.save(os.path.join(out_dir, "temp_grid.npy"), pred_temp_k)
    pd.DataFrame(pred_temp_k).to_csv(os.path.join(out_dir, "temp_grid.csv"), header=False, index=False)
    print(f"[Therm-FM Output] Temp grid saved to {out_dir} (min={pred_temp_k.min():.2f}K, max={pred_temp_k.max():.2f}K, mean={pred_temp_k.mean():.2f}K)")
    return pred_temp_k


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Therm-FM inference runner")
    parser.add_argument("--flp", type=str, default="data/ibex_flp.csv")
    parser.add_argument("--ptrace", type=str, default="data/ibex_ptrace.csv")
    parser.add_argument("--ckpt", type=str, default="checkpoints/thermfm_custom_run1.pt")
    parser.add_argument("--out-dir", type=str, default="outputs/thermfm_run1")
    parser.add_argument("--grid-size", type=int, default=32)
    args = parser.parse_args()
    
    run_inference(args.flp, args.ptrace, args.ckpt, args.out_dir, grid_size=args.grid_size)
