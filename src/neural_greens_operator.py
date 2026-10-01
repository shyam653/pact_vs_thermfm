#!/usr/bin/env python3
"""
neural_greens_operator.py

Version 2 Neural Operator Module: Rank-R Neural Green's Function Operator (NGO).
Represents the thermal impulse response operator G(x, x'; g, c) in factorized low-rank form:
  G(x, x') = sum_{r=1}^R phi_r(x) * psi_r(x')

Yields instantaneous sub-millisecond thermal field predictions theta(x) = G * p
for arbitrary dynamic power trace profiles without deep model re-inference.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
from typing import Dict, Tuple, Optional

class NeuralGreensOperator(nn.Module):
    """
    Rank-R Factorized Neural Green's Operator.
    
    in_channels : input feature channels (floorplan geometry, cooling parameters)
    rank        : basis rank R (default 16 basis components)
    grid_rows   : H (default 32)
    grid_cols   : W (default 32)
    """
    def __init__(
        self,
        embed_dim: int = 64,
        rank: int = 16,
        grid_rows: int = 32,
        grid_cols: int = 32
    ):
        super().__init__()
        self.rank = rank
        self.H = grid_rows
        self.W = grid_cols
        self.N = self.H * self.W
        
        # Spatial Basis Field Generator phi_r(x) -> (B, R, H, W)
        self.phi_head = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(),
            nn.Conv2d(embed_dim, rank, kernel_size=1)
        )
        
        # Source Weight Field Generator psi_r(x') -> (B, R, H, W)
        self.psi_head = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(),
            nn.Conv2d(embed_dim, rank, kernel_size=1)
        )
        
        # Scale parameter for stable initial output
        self.scale_gain = nn.Parameter(torch.tensor(0.01))
        
        # Initialize last conv weights to small values
        nn.init.normal_(self.phi_head[-1].weight, std=0.01)
        nn.init.normal_(self.psi_head[-1].weight, std=0.01)

    def forward(self, z: torch.Tensor, p: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        z: (B, embed_dim, H, W) backbone spatial features
        p: (B, 1, H, W) or (B, H, W) power map in Watts
        returns:
            theta_pred: (B, 1, H, W) predicted thermal rise
            aux: dict containing basis fields phi and psi
        """
        if p.ndim == 3:
            p = p.unsqueeze(1)
            
        B = z.shape[0]
        
        # 1. Decode basis fields phi_r(x) and source weights psi_r(x')
        phi = self.phi_head(z) # (B, R, H, W)
        psi = self.psi_head(z) # (B, R, H, W)
        
        # 2. Compute inner product coefficients w_r = <psi_r, p>
        psi_flat = psi.view(B, self.rank, -1) # (B, R, N)
        p_flat = p.view(B, 1, -1)             # (B, 1, N)
        
        w = torch.bmm(psi_flat, p_flat.transpose(1, 2)).squeeze(2) # (B, R)
        
        # 3. Superpose spatial response theta(x) = scale * sum_r w_r * phi_r(x)
        w_expanded = w.view(B, self.rank, 1, 1) # (B, R, 1, 1)
        theta_pred = self.scale_gain * torch.sum(w_expanded * phi, dim=1, keepdim=True) # (B, 1, H, W)
        
        aux = {
            "phi": phi,
            "psi": psi,
            "w_weights": w
        }
        
        return theta_pred, aux

    def fast_kernel_eval(self, phi: torch.Tensor, psi: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        """
        Ultra-fast cached kernel evaluation (< 0.5 ms) when backbone features Z (and thus phi, psi)
        are cached for a fixed chip geometry, and only power trace p updates dynamically.
        """
        B = p.shape[0]
        if p.ndim == 3:
            p = p.unsqueeze(1)
            
        psi_flat = psi.view(B, self.rank, -1)
        p_flat = p.view(B, 1, -1)
        w = torch.bmm(psi_flat, p_flat.transpose(1, 2)).squeeze(2)
        w_expanded = w.view(B, self.rank, 1, 1)
        return self.scale_gain * torch.sum(w_expanded * phi, dim=1, keepdim=True)

if __name__ == "__main__":
    ngo = NeuralGreensOperator(embed_dim=64, rank=16, grid_rows=32, grid_cols=32)
    z_dummy = torch.randn(4, 64, 32, 32)
    p_dummy = torch.randn(4, 1, 32, 32).abs()
    
    theta_pred, aux = ngo(z_dummy, p_dummy)
    print("=== Neural Green's Operator (NGO) Module Test ===")
    print(f"Predicted theta shape: {theta_pred.shape}")
    print(f"Spatial basis phi shape: {aux['phi'].shape}, Source weight psi shape: {aux['psi'].shape}")
