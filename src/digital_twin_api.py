#!/usr/bin/env python3
"""
digital_twin_api.py

Thermal Digital Twin & Microfluidic Cooling Control API for Therm-FM V2.
Provides real-time dynamic thermal monitoring, spatially non-uniform
cooling channel conditioning (H_cool map), and interactive closed-loop
pump control for high-power 3D AI chip stacks.
"""

import time
import json
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from thermfm_v2_3d import ThermFMV2_3DEngine
from coarse_solver_prior import CoarseThermalSolverPrior

class ThermalDigitalTwinAPI:
    def __init__(self, model_path: Optional[str] = None, die_size_mm: float = 10.0, grid_dim: int = 32):
        self.die_size_mm = die_size_mm
        self.grid_dim = grid_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize Therm-FM V2 Engine
        self.model = ThermFMV2_3DEngine(
            in_channels=5,
            num_layers_3d=1,
            embed_dim=64,
            rank=16,
            use_kirchhoff=True
        ).to(self.device)
        
        if model_path and torch.cuda.is_available():
            ckpt = torch.load(model_path, map_location=self.device)
            if "model_state" in ckpt:
                self.model.load_state_dict(ckpt["model_state"], strict=False)
                
        self.model.eval()
        self.coarse_prior_solver = CoarseThermalSolverPrior(coarse_dim=8, fine_dim=grid_dim).to(self.device)
        
        # Microfluidic cooling state map (h_conv in W/m^2.K)
        # Default baseline liquid cooling = 2000 W/m^2.K
        self.h_cooling_map = torch.full((1, 1, grid_dim, grid_dim), 2000.0, device=self.device)

    def set_microfluidic_cooling(self, cooling_map: torch.Tensor):
        """
        Update spatially non-uniform microfluidic cooling channel flow rates.
        Args:
            cooling_map: (1, 1, grid_dim, grid_dim) spatial convection coefficients.
        """
        self.h_cooling_map = cooling_map.to(self.device)

    def predict_realtime_frame(self, power_map_w: torch.Tensor) -> Dict:
        """
        Evaluate instant thermal distribution for a given dynamic power profile frame.
        Args:
            power_map_w: (1, 1, grid_dim, grid_dim) power density in Watts.
        Returns:
            Dict containing peak_temp_k, avg_temp_k, thermal_map, latency_ms.
        """
        t0 = time.time()
        power_map_w = power_map_w.to(self.device)
        
        # Normalize dummy input tensor (5 channels: power + 4 spatial encodings)
        x_norm = torch.zeros(1, 5, self.grid_dim, self.grid_dim, device=self.device)
        x_norm[:, 0:1] = power_map_w / 10.0 # scale power
        
        with torch.no_grad():
            T_pred_3d, aux = self.model(x_norm, power_map_w)
            T_surf = T_pred_3d[0, 0].cpu().numpy() # 2D surface temp
            
        latency_ms = (time.time() - t0) * 1000.0
        
        peak_t = float(np.max(T_surf))
        avg_t = float(np.mean(T_surf))
        hotspot_coords = np.unravel_index(np.argmax(T_surf), T_surf.shape)
        
        return {
            "peak_temperature_k": peak_t,
            "avg_temperature_k": avg_t,
            "hotspot_coordinate": [int(hotspot_coords[0]), int(hotspot_coords[1])],
            "latency_ms": latency_ms,
            "cooling_pump_status": "NORMAL" if peak_t < 350.0 else "HIGH_FLOW_REQUIRED",
            "thermal_map_sample": T_surf[::8, ::8].tolist() # 4x4 sample grid
        }

    def simulate_dynamic_trace(self, num_frames: int = 10) -> List[Dict]:
        """
        Simulate real-time thermal telemetry across dynamic power trace frames.
        """
        telemetry_log = []
        for f in range(num_frames):
            p_frame = torch.zeros(1, 1, self.grid_dim, self.grid_dim)
            # Dynamic moving hotspot
            cx = (10 + f) % self.grid_dim
            cy = (12 + 2 * f) % self.grid_dim
            p_frame[:, :, cx:cx+4, cy:cy+4] = 3.5 # 3.5W hotspot
            
            frame_res = self.predict_realtime_frame(p_frame)
            frame_res["frame_index"] = f
            telemetry_log.append(frame_res)
            
        return telemetry_log

if __name__ == "__main__":
    twin = ThermalDigitalTwinAPI()
    print("[ThermalDigitalTwinAPI] Initialized real-time streaming twin engine.")
    
    # Test single frame real-time inference
    p_dummy = torch.zeros(1, 1, 32, 32)
    p_dummy[:, :, 14:18, 14:18] = 4.0 # 4 Watt IP core hotspot
    
    res = twin.predict_realtime_frame(p_dummy)
    print(f"Frame Inference: Peak T = {res['peak_temperature_k']:.2f} K, Avg T = {res['avg_temperature_k']:.2f} K, Latency = {res['latency_ms']:.3f} ms")
    
    # Test dynamic trace simulation
    trace_res = twin.simulate_dynamic_trace(num_frames=5)
    print(f"Dynamic Trace Simulation: Processed {len(trace_res)} frames successfully.")
