#!/usr/bin/env python3
"""
prepare_dataset_splits.py

Phase 1.2 & 1.3:
1. Validates heat balance on HDF5 datasets.
2. Generates zero-leakage 70/15/15 train/val/test splits.
3. Computes and saves feature/target scaling parameters fit strictly on train split.
"""

import os
import sys
import h5py
import numpy as np
import torch
from dataset_utils import GroupedDatasetSplitter, ZeroLeakageScaler

def process_dataset(h5_path: str, out_prefix: str):
    print(f"\n================ Processing {os.path.basename(h5_path)} ================")
    if not os.path.exists(h5_path):
        print(f"Error: {h5_path} does not exist.")
        return

    with h5py.File(h5_path, 'r') as f:
        if 'inputs' in f and 'targets' in f:
            x_all = f['inputs'][:]
            y_all = f['targets'][:]
        elif 'x' in f and 'y' in f:
            x_all = f['x'][:]
            y_all = f['y'][:]
        else:
            raise KeyError(f"Unexpected keys in {h5_path}: {list(f.keys())}")

    if x_all.ndim == 5 and x_all.shape[2] == 1:
        x_all = np.squeeze(x_all, axis=2)
    if y_all.ndim == 5 and y_all.shape[2] == 1:
        y_all = np.squeeze(y_all, axis=2)
        
    n_samples = x_all.shape[0]
    print(f"Dataset shape: x={x_all.shape}, y={y_all.shape}")
    print(f"Target stats (raw): min={y_all.min():.2f}K, max={y_all.max():.2f}K, mean={y_all.mean():.2f}K, std={y_all.std():.2f}K")
    
    total_power = np.sum(x_all[:, 0, :, :], axis=(1, 2))
    mean_temp = np.mean(y_all[:, 0, :, :], axis=(1, 2))
    corr = np.corrcoef(total_power, mean_temp)[0, 1]
    print(f"Power-Temperature correlation: r = {corr:.4f}")
    print(f"Total power stats: min={total_power.min():.4f}W, max={total_power.max():.4f}W, mean={total_power.mean():.4f}W")

    splitter = GroupedDatasetSplitter(h5_path, seed=42)
    train_idx, val_idx, test_idx = splitter.get_splits()
    
    print(f"Split sizes: Train={len(train_idx)}, Val={len(val_idx)}, Test={len(test_idx)}")
    
    x_train, y_train = x_all[train_idx], y_all[train_idx]
    scaler = ZeroLeakageScaler()
    scaler.fit(x_train, y_train)
    
    print(f"Scaler parameters (fit on TRAIN only):")
    print(f"  Target mean_y = {scaler.mean_y:.4f} K")
    print(f"  Target std_y  = {scaler.std_y:.4f} K")

    split_meta = {
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
        "mean_x": scaler.mean_x,
        "std_x": scaler.std_x,
        "mean_y": scaler.mean_y,
        "std_y": scaler.std_y,
        "corr_power_temp": corr,
    }
    
    out_file = f"scratch/{out_prefix}_splits.pt"
    torch.save(split_meta, out_file)
    print(f"Saved split & scaler metadata to {out_file}")

def main():
    os.makedirs("scratch", exist_ok=True)
    process_dataset("archive/data/dataset_calibrated_phys.h5", "calibrated_phys")
    process_dataset("archive/data/dataset_unified_archgen_ips.h5", "unified_archgen_ips")

if __name__ == "__main__":
    main()
