#!/usr/bin/env python3
"""
kirchhoff_transform.py

Version 2 Physical Physics Module: Kirchhoff Transformation Engine for
Non-Linear Temperature-Dependent Thermal Conductivity k(T) = k_0 * (T_0 / T)^m.

Converts non-linear heat conduction equations:
  div( k(T) grad(T) ) = -p
into linear heat conduction equations in apparent potential U:
  div( k_0 grad(U) ) = -p

Provides PyTorch and NumPy differentiable forward (T -> U) and inverse (U -> T) operators.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Union

class KirchhoffTransform(nn.Module):
    """
    Kirchhoff Transformation Module for Silicon Conduction Physics.
    
    k_0: reference thermal conductivity at T_0 (default 148.0 W/(m K) for Si)
    T_0: reference temperature (default 298.15 K)
    m  : exponent for temperature degradation (default 1.33 for silicon phonon scattering)
    """
    def __init__(
        self,
        k_0: float = 148.0,
        T_0: float = 298.15,
        m: float = 1.33
    ):
        super().__init__()
        self.k_0 = k_0
        self.T_0 = T_0
        self.m = m
        self.exponent = 1.0 - m # -0.33
        self.inv_exponent = 1.0 / self.exponent # -3.030303

    def forward_transform(self, T: Union[torch.Tensor, np.ndarray]) -> Union[torch.Tensor, np.ndarray]:
        """
        Converts absolute temperature T (K) -> apparent linear potential U (K).
        U = (T_0 / (1 - m)) * [ (T / T_0)^(1 - m) - 1 ]
        """
        if isinstance(T, torch.Tensor):
            T_clamped = torch.clamp(T, min=100.0)
            ratio = T_clamped / self.T_0
            U = (self.T_0 / self.exponent) * (torch.pow(ratio, self.exponent) - 1.0)
            return U
        else:
            T_clamped = np.maximum(T, 100.0)
            ratio = T_clamped / self.T_0
            U = (self.T_0 / self.exponent) * (np.power(ratio, self.exponent) - 1.0)
            return U

    def inverse_transform(self, U: Union[torch.Tensor, np.ndarray]) -> Union[torch.Tensor, np.ndarray]:
        """
        Converts apparent linear potential U (K) -> absolute non-linear temperature T (K).
        T = T_0 * [ 1 + (1 - m) * U / T_0 ]^(1 / (1 - m))
        """
        if isinstance(U, torch.Tensor):
            # Clamp U >= 0 for physical temperature rise over T_0
            U_clamped = torch.clamp(U, min=0.0, max=500.0)
            term = 1.0 + (self.exponent * U_clamped) / self.T_0
            term_clamped = torch.clamp(term, min=0.1)
            T = self.T_0 * torch.pow(term_clamped, self.inv_exponent)
            return T
        else:
            U_clamped = np.clip(U, 0.0, 500.0)
            term = 1.0 + (self.exponent * U_clamped) / self.T_0
            term_clamped = np.maximum(term, 0.1)
            T = self.T_0 * np.power(term_clamped, self.inv_exponent)
            return T

    def get_conductivity(self, T: Union[torch.Tensor, np.ndarray]) -> Union[torch.Tensor, np.ndarray]:
        """Calculates temperature-dependent conductivity k(T) = k_0 * (T_0 / T)^m"""
        if isinstance(T, torch.Tensor):
            return self.k_0 * torch.pow(self.T_0 / torch.clamp(T, min=100.0), self.m)
        else:
            return self.k_0 * np.power(self.T_0 / np.maximum(T, 100.0), self.m)

if __name__ == "__main__":
    transform = KirchhoffTransform()
    T_true = np.array([298.15, 350.0, 400.0, 450.0, 500.0])
    U_apparent = transform.forward_transform(T_true)
    T_recovered = transform.inverse_transform(U_apparent)
    k_vals = transform.get_conductivity(T_true)
    
    print("=== Kirchhoff Transformation Engine Test ===")
    for t, u, trec, k in zip(T_true, U_apparent, T_recovered, k_vals):
        print(f"T_real = {t:.2f} K | U_linear = {u:.2f} K | T_rec = {trec:.2f} K | k(T) = {k:.2f} W/(m K)")
        
    err = np.max(np.abs(T_true - T_recovered))
    print(f"Max Reconstruction Error: {err:.6e} K")
