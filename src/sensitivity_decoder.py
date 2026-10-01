#!/usr/bin/env python3
"""
sensitivity_decoder.py

Phase 2 & Phase 5: Geometry-Conditioned Thermal Response Basis & Sensitivity Decoder.
Given input power & floorplan maps (x) and cooling parameter (c),
predicts 2D thermal field theta using basis generation, sensitivity extrapolation,
and physical PDE decoding.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional

class SimpleCNNBackbone(nn.Module):
    """
    Encoder backbone to extract spatial features Z from input maps (floorplan, power).
    Used as baseline feature extractor before integrating official Therm-FM backbone.
    """
    def __init__(self, in_channels: int = 5, embed_dim: int = 64):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, embed_dim, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(embed_dim)
        self.conv3 = nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, H, W)
        h = F.relu(self.bn1(self.conv1(x)))
        h = F.relu(self.bn2(self.conv2(h)))
        h = F.relu(self.bn3(self.conv3(h)))
        return h # (B, embed_dim, H, W)

class PhysicalSensitivityDecoder(nn.Module):
    """
    Geometry-Conditioned Thermal-Response Basis & Sensitivity Decoder.
    
    Generates:
    1. Base thermal field prediction theta_0 (at reference cooling c_0)
    2. Cooling sensitivity field S = d(theta)/dc
    3. Residual refinement delta(Z, c_target)
    
    Final prediction:
    hat_theta(c_target) = theta_0 + (c_target - c_0) * S + delta(Z, c_target)
    """
    def __init__(
        self,
        backbone: Optional[nn.Module] = None,
        in_channels: int = 5,
        embed_dim: int = 64,
        c_ref: float = 1000.0 # W/(m^2 K) reference cooling
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.c_ref = c_ref
        self.backbone = backbone if backbone is not None else SimpleCNNBackbone(in_channels, embed_dim)
        
        # Base thermal field head
        self.head_theta0 = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(),
            nn.Conv2d(embed_dim, 1, kernel_size=1)
        )
        
        # Sensitivity field head d(theta)/dc
        self.head_sensitivity = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(),
            nn.Conv2d(embed_dim, 1, kernel_size=1)
        )
        
        # Cooling condition MLP to embed target c
        self.cooling_mlp = nn.Sequential(
            nn.Linear(1, 32),
            nn.ReLU(),
            nn.Linear(32, embed_dim)
        )
        
        # Residual correction head
        self.head_residual = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(),
            nn.Conv2d(embed_dim, 1, kernel_size=1)
        )

    def forward(
        self,
        x: torch.Tensor,
        c_target: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        x: (B, C, H, W) input features (power, floorplan geometry)
        c_target: (B, 1) target cooling coefficient (e.g. h_conv)
        returns:
            pred_theta: (B, 1, H, W) final thermal field
            aux_dict: dict of intermediate fields (theta_0, sensitivity, residual)
        """
        B, _, H, W = x.shape
        device = x.device
        
        if c_target is None:
            c_target = torch.full((B, 1), self.c_ref, device=device)
            
        # 1. Feature extraction
        z = self.backbone(x) # (B, embed_dim, H, W)
        
        # 2. Base thermal field & Sensitivity field
        theta_0 = self.head_theta0(z)           # (B, 1, H, W)
        sensitivity = self.head_sensitivity(z) # (B, 1, H, W)
        
        # 3. Cooling delta (normalized relative to c_ref)
        delta_c = (c_target - self.c_ref) / 1000.0 # (B, 1)
        delta_c_spatial = delta_c.view(B, 1, 1, 1).expand(B, 1, H, W)
        
        # 4. Residual feature fusion
        c_embed = self.cooling_mlp(delta_c) # (B, embed_dim)
        z_fused = z + c_embed.view(B, self.embed_dim, 1, 1)
        residual = self.head_residual(z_fused) # (B, 1, H, W)
        
        # 5. Physics-guided sensitivity composition
        pred_theta = theta_0 + delta_c_spatial * sensitivity + residual
        
        aux = {
            "theta_0": theta_0,
            "sensitivity": sensitivity,
            "residual": residual,
            "c_target": c_target
        }
        
        return pred_theta, aux

if __name__ == "__main__":
    model = PhysicalSensitivityDecoder()
    x_dummy = torch.randn(4, 5, 32, 32)
    c_dummy = torch.tensor([[1000.0], [1500.0], [800.0], [1200.0]])
    out, aux = model(x_dummy, c_dummy)
    print("PhysicalSensitivityDecoder module test successful.")
    print(f"Output shape: {out.shape}")
    print(f"theta_0 shape: {aux['theta_0'].shape}, sensitivity shape: {aux['sensitivity'].shape}, residual shape: {aux['residual'].shape}")
