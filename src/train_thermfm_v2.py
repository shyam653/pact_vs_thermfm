#!/usr/bin/env python3
"""
train_thermfm_v2.py

Version 2 Research Training & Benchmark Evaluation Suite.
Evaluates Therm-FM Version 2 Engine featuring:
- Kirchhoff non-linear thermal potential transformation
- Factorized Neural Green's Operator (NGO)
- 3D-IC Multi-Layer Thermal Stack predictions

Compares Version 1 (Linear Sensitivity Decoder) vs Version 2 (Kirchhoff + NGO).
"""

import os
import sys
import time
import json
import argparse
import h5py
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import Dict, Tuple, Optional

# Local imports
sys.path.insert(0, os.path.abspath("src"))
from dataset_utils import GroupedDatasetSplitter, ZeroLeakageScaler, compute_thermal_metrics
from kirchhoff_transform import KirchhoffTransform
from thermfm_v2_3d import ThermFMV2_3DEngine

class HDF5ThermalDatasetV2(Dataset):
    def __init__(self, h5_path: str, indices: np.ndarray, scaler: ZeroLeakageScaler, c_conv: float = 1000.0):
        self.h5_path = h5_path
        self.indices = indices
        self.scaler = scaler
        self.c_conv = c_conv
        
        with h5py.File(h5_path, 'r') as f:
            if 'inputs' in f:
                x_data = f['inputs'][:]
                y_data = f['targets'][:]
            elif 'x' in f:
                x_data = f['x'][:]
                y_data = f['y'][:]
            else:
                raise KeyError(f"Keys in {h5_path}: {list(f.keys())}")
                
        if x_data.ndim == 5 and x_data.shape[2] == 1:
            x_data = np.squeeze(x_data, axis=2)
        if y_data.ndim == 5 and y_data.shape[2] == 1:
            y_data = np.squeeze(y_data, axis=2)
            
        self.x_raw_p = torch.tensor(x_data[indices, 0:1, :, :], dtype=torch.float32) # raw power map in Watts
        self.x_norm = torch.tensor(scaler.transform_x(x_data[indices]), dtype=torch.float32)
        self.y_raw = torch.tensor(y_data[indices], dtype=torch.float32)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        return {
            "x_norm": self.x_norm[idx],
            "p_raw": self.x_raw_p[idx],
            "y_raw": self.y_raw[idx]
        }

def run_v2_experiment(
    dataset_name: str = "dataset_calibrated_phys",
    epochs: int = 25,
    batch_size: int = 16,
    lr: float = 1e-3,
    use_kirchhoff: bool = True,
    sample_limit: Optional[int] = None
) -> Dict:
    print(f"\n================ Running Version 2 Experiment (Kirchhoff={use_kirchhoff}) on {dataset_name} ================")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    h5_path = f"archive/data/{dataset_name}.h5"
    split_meta_path = f"scratch/{dataset_name.replace('dataset_', '')}_splits.pt"
    
    if not os.path.exists(split_meta_path):
        print(f"Error: split metadata {split_meta_path} not found.")
        return {}
        
    split_meta = torch.load(split_meta_path)
    train_idx = split_meta["train_idx"]
    val_idx = split_meta["val_idx"]
    test_idx = split_meta["test_idx"]
    
    if sample_limit is not None and sample_limit < len(train_idx):
        train_idx = train_idx[:sample_limit]
        print(f"Version 2 Few-Shot Experiment: Limited training samples to {len(train_idx)}")
        
    scaler = ZeroLeakageScaler()
    scaler.mean_x = split_meta["mean_x"]
    scaler.std_x = split_meta["std_x"]
    scaler.mean_y = split_meta["mean_y"]
    scaler.std_y = split_meta["std_y"]
    
    train_dataset = HDF5ThermalDatasetV2(h5_path, train_idx, scaler)
    val_dataset = HDF5ThermalDatasetV2(h5_path, val_idx, scaler)
    test_dataset = HDF5ThermalDatasetV2(h5_path, test_idx, scaler)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Build Therm-FM Version 2 Engine
    model = ThermFMV2_3DEngine(
        in_channels=5,
        num_layers_3d=1,
        embed_dim=64,
        rank=16,
        use_kirchhoff=use_kirchhoff
    ).to(device)
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[Therm-FM V2] Total params: {total_params:,}, Trainable params: {trainable_params:,}")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    
    start_time = time.time()
    best_val_mae = float('inf')
    best_model_state = None
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        
        for batch in train_loader:
            x_norm = batch["x_norm"].to(device)
            p_raw = batch["p_raw"].to(device)
            y_raw = batch["y_raw"].to(device) # target temperature in K
            
            optimizer.zero_grad()
            
            # Forward pass: returns T_3d_real (B, 1, 32, 32) in Kelvin
            T_pred_3d, aux = model(x_norm, p_raw)
            T_pred = T_pred_3d[:, 0:1, :, :]
            
            # Loss evaluated directly in physical Temperature domain (K)
            l1_loss = F.l1_loss(T_pred, y_raw)
            l2_loss = F.mse_loss(T_pred, y_raw)
            
            max_pred = torch.max(T_pred.view(T_pred.shape[0], -1), dim=1)[0]
            max_true = torch.max(y_raw.view(y_raw.shape[0], -1), dim=1)[0]
            hotspot_loss = F.l1_loss(max_pred, max_true)
            
            loss = l1_loss + 0.01 * l2_loss + 0.2 * hotspot_loss
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * x_norm.size(0)
            
        train_loss = total_loss / len(train_dataset)
        
        # Validation
        model.eval()
        val_preds, val_trues = [], []
        with torch.no_grad():
            for batch in val_loader:
                x_norm = batch["x_norm"].to(device)
                p_raw = batch["p_raw"].to(device)
                y_raw = batch["y_raw"].to(device)
                
                T_pred_3d, _ = model(x_norm, p_raw)
                T_pred = T_pred_3d[:, 0:1, :, :]
                
                val_preds.append(T_pred.cpu())
                val_trues.append(y_raw.cpu())
                
        val_metrics = compute_thermal_metrics(torch.cat(val_trues, dim=0), torch.cat(val_preds, dim=0))
        
        if val_metrics["mae_k"] < best_val_mae:
            best_val_mae = val_metrics["mae_k"]
            best_model_state = model.state_dict().copy()
            
        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Val MAE: {val_metrics['mae_k']:.4f}K | Val Hotspot Error: {val_metrics['max_hotspot_error_k']:.4f}K")
            
    train_time = time.time() - start_time
    
    # Test evaluation
    model.load_state_dict(best_model_state)
    model.eval()
    test_preds, test_trues = [], []
    with torch.no_grad():
        for batch in test_loader:
            x_norm = batch["x_norm"].to(device)
            p_raw = batch["p_raw"].to(device)
            y_raw = batch["y_raw"].to(device)
            
            T_pred_3d, _ = model(x_norm, p_raw)
            T_pred = T_pred_3d[:, 0:1, :, :]
            
            test_preds.append(T_pred.cpu())
            test_trues.append(y_raw.cpu())
            
    test_metrics = compute_thermal_metrics(torch.cat(test_trues, dim=0), torch.cat(test_preds, dim=0))
    
    os.makedirs("scratch/checkpoints", exist_ok=True)
    ckpt_path = f"scratch/checkpoints/thermfm_v2_kirchhoff_{dataset_name.replace('dataset_', '')}.pt"
    torch.save({"model_state": best_model_state}, ckpt_path)
    
    print(f"\n--- Final Version 2 Test Evaluation (Kirchhoff={use_kirchhoff}) ---")
    print(f"MAE: {test_metrics['mae_k']:.4f} K")
    print(f"RMSE: {test_metrics['rmse_k']:.4f} K")
    print(f"Max Hotspot Error: {test_metrics['max_hotspot_error_k']:.4f} K")
    print(f"Hotspot Loc Error: {test_metrics['hotspot_loc_error_k']:.4f} K")
    print(f"Relative L2 Error: {test_metrics['rel_l2_error']:.6f}")
    print(f"Training Time: {train_time:.2f} s")
    
    results = {
        "version": "v2",
        "use_kirchhoff": use_kirchhoff,
        "dataset": dataset_name,
        "sample_limit": len(train_idx),
        "trainable_params": trainable_params,
        "train_time_sec": train_time,
        "metrics": test_metrics
    }
    
    os.makedirs("scratch/results", exist_ok=True)
    res_path = f"scratch/results/v2_{dataset_name.replace('dataset_', '')}_{len(train_idx)}samples.json"
    with open(res_path, 'w') as f:
        json.dump(results, f, indent=2)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Therm-FM Version 2 Training & Evaluation")
    parser.add_argument("--dataset", type=str, default="dataset_calibrated_phys",
                        choices=["dataset_calibrated_phys", "dataset_unified_archgen_ips"])
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--disable-kirchhoff", action="store_true")
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit number of training samples for few-shot evaluation")
    args = parser.parse_args()
    
    run_v2_experiment(
        dataset_name=args.dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        use_kirchhoff=not args.disable_kirchhoff,
        sample_limit=args.sample_limit
    )

if __name__ == "__main__":
    main()
