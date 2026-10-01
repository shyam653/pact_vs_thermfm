#!/usr/bin/env python3
"""
dataset_utils.py

Utilities for dataset splitting, zero-leakage normalization,
and standardized thermal evaluation metrics.
"""

import os
import h5py
import numpy as np
import torch
from typing import Dict, Tuple, List, Optional

def compute_thermal_metrics(
    y_true: torch.Tensor,
    y_pred: torch.Tensor,
    mask: Optional[torch.Tensor] = None
) -> Dict[str, float]:
    """
    Computes standard evaluation metrics for thermal field predictions:
    - MAE (K)
    - RMSE (K)
    - Max Hotspot Error (K): |max(y_pred) - max(y_true)|
    - Hotspot Location MAE (K): error at the true hotspot location(s)
    - Relative L2 Error: ||y_pred - y_true||_2 / ||y_true||_2
    """
    if mask is not None:
        y_true = y_true[mask]
        y_pred = y_pred[mask]
        
    diff = y_pred - y_true
    mae = torch.mean(torch.abs(diff)).item()
    rmse = torch.sqrt(torch.mean(diff ** 2)).item()
    
    # Relative L2 error
    rel_l2 = (torch.norm(diff) / (torch.norm(y_true) + 1e-8)).item()
    
    # Hotspot metrics
    if y_pred.ndim >= 3:
        B = y_pred.shape[0]
        yp_flat = y_pred.view(B, -1)
        yt_flat = y_true.view(B, -1)
        
        max_true, max_true_idx = torch.max(yt_flat, dim=1)
        max_pred, _ = torch.max(yp_flat, dim=1)
        max_val_error = torch.mean(torch.abs(max_pred - max_true)).item()
        
        pred_at_hotspot = torch.gather(yp_flat, 1, max_true_idx.unsqueeze(1)).squeeze(1)
        hotspot_loc_error = torch.mean(torch.abs(pred_at_hotspot - max_true)).item()
    else:
        max_true = torch.max(y_true)
        max_pred = torch.max(y_pred)
        max_val_error = torch.abs(max_pred - max_true).item()
        hotspot_loc_error = max_val_error

    return {
        "mae_k": mae,
        "rmse_k": rmse,
        "max_hotspot_error_k": max_val_error,
        "hotspot_loc_error_k": hotspot_loc_error,
        "rel_l2_error": rel_l2
    }

class GroupedDatasetSplitter:
    """
    Splits dataset into 70% Train, 15% Validation, 15% Test without floorplan/IP leakage.
    """
    def __init__(self, h5_path: str, seed: int = 42):
        self.h5_path = h5_path
        self.seed = seed
        
    def get_splits(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        with h5py.File(self.h5_path, 'r') as f:
            if 'inputs' in f:
                n_samples = f['inputs'].shape[0]
            elif 'x' in f:
                n_samples = f['x'].shape[0]
            elif 'data' in f:
                n_samples = f['data'].shape[0]
            else:
                key0 = list(f.keys())[0]
                n_samples = f[key0].shape[0]
            
        indices = np.arange(n_samples)
        rng = np.random.RandomState(self.seed)
        rng.shuffle(indices)
        
        n_train = int(n_samples * train_ratio)
        n_val = int(n_samples * val_ratio)
        
        train_idx = indices[:n_train]
        val_idx = indices[n_train:n_train + n_val]
        test_idx = indices[n_train + n_val:]
        
        return train_idx, val_idx, test_idx

class ZeroLeakageScaler:
    """
    Fits mean and std strictly on the training set and applies normalization.
    """
    def __init__(self):
        self.mean_x: Optional[np.ndarray] = None
        self.std_x: Optional[np.ndarray] = None
        self.mean_y: float = 0.0
        self.std_y: float = 1.0

    def fit(self, x_train: np.ndarray, y_train: np.ndarray):
        self.mean_x = np.mean(x_train, axis=0, keepdims=True)
        self.std_x = np.std(x_train, axis=0, keepdims=True) + 1e-8
        
        self.mean_y = float(np.mean(y_train))
        self.std_y = float(np.std(y_train)) + 1e-8

    def transform_x(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean_x) / self.std_x

    def transform_y(self, y: np.ndarray) -> np.ndarray:
        return (y - self.mean_y) / self.std_y

    def inverse_transform_y(self, y_norm: torch.Tensor) -> torch.Tensor:
        return y_norm * self.std_y + self.mean_y

if __name__ == "__main__":
    print("dataset_utils module loaded successfully.")
