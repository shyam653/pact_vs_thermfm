#!/usr/bin/env python3
"""
linear_thermal_solver.py

Phase 2: Physical Linear-Conduction Thermal Solver K(g, c) theta = p.
Computes temperature rise theta over ambient for arbitrary 2D grid power map p
and cooling parameter c (convection coefficient h_conv or thermal resistance).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import torch
from typing import Tuple, Optional

class LinearThermalSolver:
    """
    2D Finite-Difference Linear Conduction Solver.
    
    Grid size: H x W
    Physical dimensions: L_x (m), L_y (m), thickness d (m)
    Thermal conductivity: k_si (W/(m K))
    Cooling coefficient: h_conv (W/(m^2 K))
    """
    def __init__(
        self,
        grid_rows: int = 32,
        grid_cols: int = 32,
        chip_size_x: float = 0.0005,  # 0.5 mm
        chip_size_y: float = 0.0005,  # 0.5 mm
        thickness: float = 0.0001,    # 100 um
        k_si: float = 130.0,          # W/(m*K)
        h_conv_default: float = 1000.0 # W/(m^2*K)
    ):
        self.H = grid_rows
        self.W = grid_cols
        self.N = self.H * self.W
        
        self.dx = chip_size_x / self.W
        self.dy = chip_size_y / self.H
        self.d = thickness
        self.k = k_si
        self.h_default = h_conv_default
        
        # Build base internal conductance matrix K_0 (without ambient boundary convection)
        self.K_0, self.area_cell = self._build_internal_conductance()

    def _build_internal_conductance(self) -> Tuple[sp.csr_matrix, float]:
        H, W = self.H, self.W
        dx, dy, d, k = self.dx, self.dy, self.d, self.k
        cell_area = dx * dy
        
        g_x = k * (dy * d) / dx
        g_y = k * (dx * d) / dy
        
        row_list, col_list, data_list = [], [], []
        
        def node_idx(r, c):
            return r * W + c

        for r in range(H):
            for c in range(W):
                curr = node_idx(r, c)
                diag = 0.0
                
                # West
                if c > 0:
                    west = node_idx(r, c - 1)
                    row_list.append(curr); col_list.append(west); data_list.append(-g_x)
                    diag += g_x
                # East
                if c < W - 1:
                    east = node_idx(r, c + 1)
                    row_list.append(curr); col_list.append(east); data_list.append(-g_x)
                    diag += g_x
                # North
                if r > 0:
                    north = node_idx(r - 1, c)
                    row_list.append(curr); col_list.append(north); data_list.append(-g_y)
                    diag += g_y
                # South
                if r < H - 1:
                    south = node_idx(r + 1, c)
                    row_list.append(curr); col_list.append(south); data_list.append(-g_y)
                    diag += g_y
                    
                row_list.append(curr); col_list.append(curr); data_list.append(diag)
                
        K_0 = sp.csr_matrix((data_list, (row_list, col_list)), shape=(self.N, self.N))
        return K_0, cell_area

    def get_K_matrix(self, h_conv: float) -> sp.csr_matrix:
        """K(g, h) = K_0 + h * A_cell * I"""
        g_conv = h_conv * self.area_cell
        K_conv = sp.diags([g_conv] * self.N, format='csr')
        return self.K_0 + K_conv

    def solve(self, power_grid: np.ndarray, h_conv: Optional[float] = None) -> np.ndarray:
        """
        Solves K(g, h) * theta = p for temperature rise theta (in Kelvin).
        power_grid: (H, W) or (B, H, W) power in Watts per cell.
        returns: theta (same shape as power_grid)
        """
        h = h_conv if h_conv is not None else self.h_default
        K = self.get_K_matrix(h)
        
        # Factorize SPD sparse matrix
        solve_func = spla.factorized(K)
        
        if power_grid.ndim == 2:
            p_flat = power_grid.flatten()
            theta_flat = solve_func(p_flat)
            return theta_flat.reshape((self.H, self.W))
        elif power_grid.ndim == 3:
            B = power_grid.shape[0]
            theta_out = np.zeros_like(power_grid)
            for i in range(B):
                p_flat = power_grid[i].flatten()
                theta_out[i] = solve_func(p_flat).reshape((self.H, self.W))
            return theta_out
        else:
            raise ValueError(f"Unsupported power_grid shape: {power_grid.shape}")

    def compute_sensitivity(self, power_grid: np.ndarray, h_conv: Optional[float] = None) -> np.ndarray:
        """
        Computes sensitivity field S = d(theta)/dh = - K^{-1} (dK/dh) theta
        where dK/dh = A_cell * I.
        """
        h = h_conv if h_conv is not None else self.h_default
        K = self.get_K_matrix(h)
        solve_func = spla.factorized(K)
        
        theta = self.solve(power_grid, h_conv=h)
        
        if power_grid.ndim == 2:
            rhs = - self.area_cell * theta.flatten()
            sens_flat = solve_func(rhs)
            return sens_flat.reshape((self.H, self.W))
        else:
            B = power_grid.shape[0]
            sens_out = np.zeros_like(power_grid)
            for i in range(B):
                rhs = - self.area_cell * theta[i].flatten()
                sens_out[i] = solve_func(rhs).reshape((self.H, self.W))
            return sens_out

if __name__ == "__main__":
    solver = LinearThermalSolver(32, 32)
    p_test = np.zeros((32, 32))
    p_test[16, 16] = 1.0 # 1 Watt point heat source at center
    theta = solver.solve(p_test)
    sens = solver.compute_sensitivity(p_test)
    print(f"Linear Thermal Solver test successful.")
    print(f"1W Point Source @ Center: Peak theta = {theta.max():.2f} K, Mean theta = {theta.mean():.4f} K")
    print(f"Sensitivity d(theta)/dh @ Center = {sens[16, 16]:.6e} K / (W/(m^2 K))")
