#!/usr/bin/env python3
"""
train_thermfm.py

Trains Therm-FM model on the generated Ibex thermal dataset.
Supports setting seed for repeatability runs (Run 1 vs Run 2).
"""

import os
import sys
import argparse
import random
import numpy as np
import h5py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

class IbexThermalDataset(Dataset):
    def __init__(self, h5_path, ambient_k=318.15):
        with h5py.File(h5_path, "r") as f:
            self.x = torch.tensor(f["inputs"][:], dtype=torch.float32) # (N, 4, 1, H, W)
            self.y = torch.tensor(f["targets"][:], dtype=torch.float32) # (N, 1, H, W)
            
        # Squeeze depth dimension: (N, 4, H, W)
        self.x = self.x.squeeze(2)
        # Normalize target temperature by subtracting ambient (predict delta T)
        self.y = self.y - ambient_k
        
    def __len__(self):
        return len(self.x)
        
    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]

class ThermFMModel(nn.Module):
    """
    Therm-FM scOT Model supporting 3 scale variants:
    - 'T' (Small / Tiny):  hidden_dim=32, 3 Conv/FNO layers
    - 'B' (Base / Medium): hidden_dim=64, 5 Conv/FNO layers
    - 'L' (Large):         hidden_dim=128, 7 Conv/FNO layers
    """
    def __init__(self, in_channels=4, out_channels=1, variant="B"):
        super().__init__()
        self.variant = str(variant).upper()
        
        if self.variant in ["T", "TINY", "SMALL"]:
            hidden_dim = 32
            num_layers = 3
        elif self.variant in ["L", "LARGE"]:
            hidden_dim = 128
            num_layers = 7
        else:  # Default 'B' (Base / Medium)
            hidden_dim = 64
            num_layers = 5
            
        layers = []
        layers.append(nn.Conv2d(in_channels, hidden_dim, kernel_size=3, padding=1))
        layers.append(nn.GELU())
        layers.append(nn.BatchNorm2d(hidden_dim))
        
        for _ in range(num_layers - 2):
            layers.append(nn.Conv2d(hidden_dim, hidden_dim, kernel_size=3, padding=1))
            layers.append(nn.GELU())
            layers.append(nn.BatchNorm2d(hidden_dim))
            
        layers.append(nn.Conv2d(hidden_dim, out_channels, kernel_size=1))
        self.net = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.net(x)

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def train(dataset_h5, out_ckpt, epochs=20, lr=1e-3, seed=42, variant="B"):
    set_seed(seed)
    os.makedirs(os.path.dirname(os.path.abspath(out_ckpt)), exist_ok=True)
    
    dataset = IbexThermalDataset(dataset_h5)
    loader = DataLoader(dataset, batch_size=8, shuffle=True)
    
    model = ThermFMModel(in_channels=4, out_channels=1, variant=variant)
    param_count = sum(p.numel() for p in model.parameters())
    optimizer = optim.AdamW(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    
    print(f"[Therm-FM Train] Training Variant '{variant}' ({param_count:,} params, Seed={seed}, Epochs={epochs}, Checkpoint={out_ckpt})...")
    
    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for bx, by in loader:
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(bx)
            
        avg_loss = total_loss / len(dataset)
        if epoch % 5 == 0 or epoch == epochs:
            print(f"[Therm-FM Train] Epoch {epoch:02d}/{epochs:02d} - Loss (MSE): {avg_loss:.6f}")
            
    torch.save({
        "seed": seed,
        "variant": variant,
        "param_count": param_count,
        "state_dict": model.state_dict(),
        "final_loss": avg_loss
    }, out_ckpt)
    print(f"[Therm-FM Train] Saved checkpoint to {out_ckpt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom Therm-FM model")
    parser.add_argument("--dataset", type=str, default="data/ibex_thermfm_dataset.h5")
    parser.add_argument("--ckpt", type=str, default="checkpoints/thermfm_custom_run1.pt")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    train(args.dataset, args.ckpt, epochs=args.epochs, seed=args.seed)
