#!/usr/bin/env python3
"""
train_thermfm_research.py

Comprehensive Research Training & Evaluation Script.
Executes training and few-shot evaluation across:
1. thermfm_scratch: ScOT backbone (T) trained from scratch
2. thermfm_frozen_basis: ScOT backbone (T) frozen + Physical Sensitivity Decoder
3. thermfm_finetune_basis: ScOT backbone (T) trainable + Physical Sensitivity Decoder
4. unet_fno_baseline: Custom U-Net/FNO 253K model (separate baseline)
5. linear_pde_solver: Pure physical PDE linear conduction solver K(g,c) theta = p

Tracks all required metrics:
- MAE (K), RMSE (K), Max Hotspot Error (K), Relative L2 Error
- Computational time & parameter count
- Saves model checkpoints and JSON results.
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
from typing import Dict, Tuple, Optional, List

# Local imports
sys.path.insert(0, os.path.abspath("src"))
from dataset_utils import GroupedDatasetSplitter, ZeroLeakageScaler, compute_thermal_metrics
from sensitivity_decoder import PhysicalSensitivityDecoder, SimpleCNNBackbone
from thermfm_model_wrapper import ThermFMSensitivityDecoder
from linear_thermal_solver import LinearThermalSolver

class HDF5ThermalDataset(Dataset):
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
            
        self.x = torch.tensor(scaler.transform_x(x_data[indices]), dtype=torch.float32)
        self.y_raw = torch.tensor(y_data[indices], dtype=torch.float32)
        self.y_norm = torch.tensor(scaler.transform_y(y_data[indices]), dtype=torch.float32)
        self.c_tensor = torch.full((len(indices), 1), c_conv, dtype=torch.float32)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        return {
            "x": self.x[idx],
            "y_raw": self.y_raw[idx],
            "y_norm": self.y_norm[idx],
            "c_target": self.c_tensor[idx]
        }

def build_model(variant_name: str, in_channels: int = 5, embed_dim: int = 64) -> Tuple[nn.Module, int]:
    if variant_name == "thermfm_scratch":
        model = ThermFMSensitivityDecoder(model_scale="T", in_channels=in_channels, freeze_backbone=False)
    elif variant_name == "thermfm_frozen_basis":
        model = ThermFMSensitivityDecoder(model_scale="T", in_channels=in_channels, freeze_backbone=True)
    elif variant_name == "thermfm_finetune_basis":
        model = ThermFMSensitivityDecoder(model_scale="T", in_channels=in_channels, freeze_backbone=False)
    elif variant_name == "unet_fno_baseline":
        model = PhysicalSensitivityDecoder(in_channels=in_channels, embed_dim=embed_dim)
    else:
        raise ValueError(f"Unknown variant: {variant_name}")
        
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[{variant_name}] Total params: {total_params:,}, Trainable params: {trainable_params:,}")
    return model, trainable_params

def train_epoch(model, dataloader, optimizer, scaler, device) -> float:
    model.train()
    total_loss = 0.0
    
    for batch in dataloader:
        x = batch["x"].to(device)
        y_norm = batch["y_norm"].to(device)
        c_target = batch["c_target"].to(device)
        
        optimizer.zero_grad()
        pred_norm, aux = model(x, c_target)
        
        # Loss = L1 + L2 + Hotspot loss
        l1_loss = F.l1_loss(pred_norm, y_norm)
        l2_loss = F.mse_loss(pred_norm, y_norm)
        
        # Hotspot value loss
        max_pred = torch.max(pred_norm.view(pred_norm.shape[0], -1), dim=1)[0]
        max_true = torch.max(y_norm.view(y_norm.shape[0], -1), dim=1)[0]
        hotspot_loss = F.l1_loss(max_pred, max_true)
        
        loss = l1_loss + 0.5 * l2_loss + 0.2 * hotspot_loss
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * x.size(0)
        
    return total_loss / len(dataloader.dataset)

def evaluate(model, dataloader, scaler, device) -> Dict[str, float]:
    model.eval()
    all_preds_k = []
    all_trues_k = []
    
    with torch.no_grad():
        for batch in dataloader:
            x = batch["x"].to(device)
            y_raw = batch["y_raw"].to(device)
            c_target = batch["c_target"].to(device)
            
            pred_norm, aux = model(x, c_target)
            pred_k = scaler.inverse_transform_y(pred_norm)
            
            all_preds_k.append(pred_k.cpu())
            all_trues_k.append(y_raw.cpu())
            
    y_pred_all = torch.cat(all_preds_k, dim=0)
    y_true_all = torch.cat(all_trues_k, dim=0)
    
    metrics = compute_thermal_metrics(y_true_all, y_pred_all)
    return metrics

def run_experiment(
    variant_name: str,
    dataset_name: str,
    epochs: int = 50,
    batch_size: int = 16,
    lr: float = 1e-3,
    sample_limit: Optional[int] = None
) -> Dict:
    print(f"\n================ Running Experiment: {variant_name} on {dataset_name} ================")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    h5_path = f"archive/data/{dataset_name}.h5"
    split_meta_path = f"scratch/{dataset_name.replace('dataset_', '')}_splits.pt"
    
    if not os.path.exists(split_meta_path):
        print(f"Error: split metadata {split_meta_path} not found. Run prepare_dataset_splits.py first.")
        return {}
        
    split_meta = torch.load(split_meta_path)
    train_idx = split_meta["train_idx"]
    val_idx = split_meta["val_idx"]
    test_idx = split_meta["test_idx"]
    
    if sample_limit is not None and sample_limit < len(train_idx):
        train_idx = train_idx[:sample_limit]
        print(f"Few-shot experiment: Limited training samples to {len(train_idx)}")
        
    scaler = ZeroLeakageScaler()
    scaler.mean_x = split_meta["mean_x"]
    scaler.std_x = split_meta["std_x"]
    scaler.mean_y = split_meta["mean_y"]
    scaler.std_y = split_meta["std_y"]
    
    train_dataset = HDF5ThermalDataset(h5_path, train_idx, scaler)
    val_dataset = HDF5ThermalDataset(h5_path, val_idx, scaler)
    test_dataset = HDF5ThermalDataset(h5_path, test_idx, scaler)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    start_time = time.time()
    
    if variant_name == "linear_pde_solver":
        print("Evaluating Calibrated Physical Linear PDE Solver K(g,c) theta = p...")
        solver = LinearThermalSolver(32, 32)
        
        with h5py.File(h5_path, 'r') as f:
            x_data = f['inputs'][:] if 'inputs' in f else f['x'][:]
            y_data = f['targets'][:] if 'targets' in f else f['y'][:]
            
        if x_data.ndim == 5 and x_data.shape[2] == 1:
            x_data = np.squeeze(x_data, axis=2)
        if y_data.ndim == 5 and y_data.shape[2] == 1:
            y_data = np.squeeze(y_data, axis=2)
            
        # Fit scale gamma on train set
        x_train = x_data[train_idx]
        y_train = y_data[train_idx]
        pde_train_means = []
        for i in range(len(train_idx)):
            p_map = x_train[i, 0]
            theta_p = solver.solve(p_map)
            pde_train_means.append(np.mean(theta_p))
            
        gamma = float(np.mean(y_train) / (np.mean(pde_train_means) + 1e-8))
        print(f"Calibrated physical PDE scale gamma (fit on TRAIN): {gamma:.6e}")
        
        x_test = x_data[test_idx]
        y_test = y_data[test_idx]
        all_preds = []
        all_trues = []
        
        for i in range(len(test_idx)):
            p_map = x_test[i, 0]
            theta_pred = solver.solve(p_map) * gamma
            all_preds.append(theta_pred[np.newaxis, np.newaxis, :, :])
            all_trues.append(y_test[i:i+1])
            
        y_pred_tensor = torch.tensor(np.concatenate(all_preds, axis=0), dtype=torch.float32)
        y_true_tensor = torch.tensor(np.concatenate(all_trues, axis=0), dtype=torch.float32)
        
        test_metrics = compute_thermal_metrics(y_true_tensor, y_pred_tensor)
        train_time = time.time() - start_time
        trainable_params = 0
    else:
        model, trainable_params = build_model(variant_name, in_channels=5)
        model.to(device)
        optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-4)
        
        best_val_mae = float('inf')
        best_model_state = None
        
        for epoch in range(1, epochs + 1):
            train_loss = train_epoch(model, train_loader, optimizer, scaler, device)
            val_metrics = evaluate(model, val_loader, scaler, device)
            
            if val_metrics["mae_k"] < best_val_mae:
                best_val_mae = val_metrics["mae_k"]
                best_model_state = model.state_dict().copy()
                
            if epoch % 10 == 0 or epoch == epochs:
                print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Val MAE: {val_metrics['mae_k']:.4f}K | Val Hotspot Error: {val_metrics['max_hotspot_error_k']:.4f}K")
                
        train_time = time.time() - start_time
        
        model.load_state_dict(best_model_state)
        test_metrics = evaluate(model, test_loader, scaler, device)
        
        os.makedirs("scratch/checkpoints", exist_ok=True)
        ckpt_path = f"scratch/checkpoints/{variant_name}_{dataset_name.replace('dataset_', '')}.pt"
        torch.save({"model_state": best_model_state, "scaler": scaler}, ckpt_path)
        print(f"Saved checkpoint to {ckpt_path}")

    print(f"\n--- Final Test Evaluation ({variant_name}) ---")
    print(f"MAE: {test_metrics['mae_k']:.4f} K")
    print(f"RMSE: {test_metrics['rmse_k']:.4f} K")
    print(f"Max Hotspot Error: {test_metrics['max_hotspot_error_k']:.4f} K")
    print(f"Hotspot Loc Error: {test_metrics['hotspot_loc_error_k']:.4f} K")
    print(f"Relative L2 Error: {test_metrics['rel_l2_error']:.6f}")
    print(f"Training Time: {train_time:.2f} s")
    
    results = {
        "variant": variant_name,
        "dataset": dataset_name,
        "sample_limit": len(train_idx),
        "trainable_params": trainable_params,
        "train_time_sec": train_time,
        "metrics": test_metrics
    }
    
    os.makedirs("scratch/results", exist_ok=True)
    res_path = f"scratch/results/{variant_name}_{dataset_name.replace('dataset_', '')}_{len(train_idx)}samples.json"
    with open(res_path, 'w') as f:
        json.dump(results, f, indent=2)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Therm-FM Research Training & Evaluation")
    parser.add_argument("--variant", type=str, default="thermfm_frozen_basis",
                        choices=["thermfm_scratch", "thermfm_frozen_basis", "thermfm_finetune_basis", "unet_fno_baseline", "linear_pde_solver"])
    parser.add_argument("--dataset", type=str, default="dataset_calibrated_phys",
                        choices=["dataset_calibrated_phys", "dataset_unified_archgen_ips"])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--sample-limit", type=int, default=None)
    args = parser.parse_args()
    
    run_experiment(
        variant_name=args.variant,
        dataset_name=args.dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        sample_limit=args.sample_limit
    )

if __name__ == "__main__":
    main()
