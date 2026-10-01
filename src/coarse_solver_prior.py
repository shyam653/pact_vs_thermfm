#!/usr/bin/env python3
"""
coarse_solver_prior.py

Multi-Fidelity Physics-Informed Operator Learning Module for Therm-FM V2.
Computes a lightweight $8 \times 8$ finite-difference physical temperature prior
in < 0.1 ms and interpolates it to fine resolution (32 x 32) to condition the
neural operator to predict high-frequency spatial thermal residuals:

    theta_fine = Interp(theta_coarse) + ThermFM_refine(P, theta_coarse)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class CoarseThermalSolverPrior(nn.Module):
    def __init__(self, coarse_dim: int = 8, fine_dim: int = 32, k_si: float = 148.0, h_conv: float = 10.0, t_amb: float = 300.0):
        super().__init__()
        self.coarse_dim = coarse_dim
        self.fine_dim = fine_dim
        self.k_si = k_si
        self.h_conv = h_conv
        self.t_amb = t_amb
        
        # Learnable spatial scale for finite difference prior matching
        self.prior_scale = nn.Parameter(torch.tensor(1.0))
        self.prior_bias = nn.Parameter(torch.tensor(0.0))

    def forward(self, p_raw: torch.Tensor, h_map: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            p_raw: Raw power map (B, 1, H, W) in Watts.
            h_map: Optional spatial convection coefficient map (B, 1, H, W).
        Returns:
            theta_coarse_interp: (B, 1, H, W) coarse physics prior in Kelvin.
        """
        B, C, H, W = p_raw.shape
        
        # Downsample power map to coarse resolution (8 x 8)
        p_coarse = F.adaptive_avg_pool2d(p_raw, (self.coarse_dim, self.coarse_dim))
        
        if h_map is not None:
            h_coarse = F.adaptive_avg_pool2d(h_map, (self.coarse_dim, self.coarse_dim))
        else:
            h_coarse = torch.full_like(p_coarse, self.h_conv)
            
        # Fast GPU Jacobi iterations for coarse 2D thermal conduction (8 x 8 grid = 64 nodes)
        # Poisson PDE: -k * grad^2(T) + h * (T - T_amb) = P / area
        dx = 0.01 / self.coarse_dim # 10 mm die size
        area = dx * dx
        q_vol = p_coarse / area # W/m^2
        
        T_coarse = torch.full_like(p_coarse, self.t_amb)
        
        # 10 Jacobi iterations on 8x8 grid run in < 0.05 ms
        for _ in range(12):
            T_padded = F.pad(T_coarse, (1, 1, 1, 1), mode='replicate')
            T_neighbors = (T_padded[:, :, :-2, 1:-1] + T_padded[:, :, 2:, 1:-1] +
                           T_padded[:, :, 1:-1, :-2] + T_padded[:, :, 1:-1, 2:])
            
            denom = 4.0 * self.k_si / (dx * dx) + h_coarse
            num = (self.k_si / (dx * dx)) * T_neighbors + h_coarse * self.t_amb + q_vol
            T_coarse = num / denom
            
        # Upsample coarse solution back to fine resolution (32 x 32) via bilinear interpolation
        T_coarse_interp = F.interpolate(T_coarse, size=(H, W), mode='bilinear', align_corners=False)
        
        # Calibrate prior scale
        T_coarse_calibrated = self.t_amb + (T_coarse_interp - self.t_amb) * self.prior_scale + self.prior_bias
        return T_coarse_calibrated

if __name__ == "__main__":
    solver = CoarseThermalSolverPrior()
    dummy_p = torch.zeros(4, 1, 32, 32)
    dummy_p[:, :, 10:15, 10:15] = 2.5 # 2.5W hotspot
    prior = solver(dummy_p)
    print(f"[CoarseThermalSolverPrior] Output shape: {prior.shape}, Min T: {prior.min().item():.2f} K, Max T: {prior.max().item():.2f} K")
