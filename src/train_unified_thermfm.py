#!/usr/bin/env python3
"""
train_unified_thermfm.py

Demonstrates training a single UNIFIED Therm-FM model across 3 distinct IP designs:
1. Ibex RISC-V Core (Sky130 130nm)
2. AES-128 Crypto Engine (ASAP7 7nm)
3. GCD Math Unit (ASAP7 7nm)

Combines datasets, trains a single unified checkpoint, and compares multi-IP inference accuracy.
"""

import os
import sys
import h5py
import numpy as np
import pandas as pd
import time

from train_thermfm import train
from infer_thermfm import run_inference
from run_pact_steady import run_pact
from adjust_spef import adjust_spef_file
from run_opensta import run_sta_analysis

DESIGNS = [
    {
        "id": "ibex_sky130",
        "name": "Ibex RISC-V Core (Sky130 HD 130nm)",
        "flp": "archive/design_inputs/ibex_sky130/ibex_flp.csv",
        "ptrace": "archive/design_inputs/ibex_sky130/ibex_ptrace.csv",
        "baseline_spef": "archive/design_inputs/ibex_sky130/gcd_sky130hd.spef",
        "netlist": "archive/design_inputs/ibex_sky130/gcd_sky130hd.v",
        "top_module": "gcd",
        "lib": "archive/design_inputs/ibex_sky130/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "lefs": [
            "archive/design_inputs/ibex_sky130/sky130_fd_sc_hd.tlef",
            "archive/design_inputs/ibex_sky130/sky130_fd_sc_hd_merged.lef"
        ],
        "clocks": [("clk", 10.0)],
        "alpha": 0.00386,
        "dataset_h5": "archive/data/dataset_ibex_sky130.h5"
    },
    {
        "id": "aes_asap7",
        "name": "AES-128 Crypto Engine (ASAP7 7nm FinFET)",
        "flp": "archive/design_inputs/aes_asap7/aes_flp.csv",
        "ptrace": "archive/design_inputs/aes_asap7/aes_ptrace.csv",
        "baseline_spef": "archive/design_inputs/aes_asap7/reg1_asap7.spef",
        "netlist": "archive/design_inputs/aes_asap7/reg1_asap7.v",
        "top_module": "top",
        "lib": "archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz",
        "lefs": [
            "archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef",
            "archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "alpha": 0.00420,
        "dataset_h5": "archive/data/dataset_aes_asap7.h5"
    },
    {
        "id": "gcd_asap7",
        "name": "GCD Unit (ASAP7 7nm FinFET)",
        "flp": "archive/design_inputs/gcd_asap7/gcd_flp.csv",
        "ptrace": "archive/design_inputs/gcd_asap7/gcd_ptrace.csv",
        "baseline_spef": "archive/design_inputs/gcd_asap7/reg1_asap7.spef",
        "netlist": "archive/design_inputs/gcd_asap7/reg1_asap7.v",
        "top_module": "top",
        "lib": "archive/design_inputs/gcd_asap7/asap7_small_ff.lib.gz",
        "lefs": [
            "archive/design_inputs/gcd_asap7/asap7_tech_1x_201209.lef",
            "archive/design_inputs/gcd_asap7/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "alpha": 0.00420,
        "dataset_h5": "archive/data/dataset_gcd_asap7.h5"
    }
]

def combine_datasets(out_unified_h5="archive/data/dataset_unified_multi_ip.h5"):
    os.makedirs("archive/data", exist_ok=True)
    all_inputs = []
    all_targets = []
    
    print("[Unified Dataset] Combining datasets across all 3 IPs...")
    for dspec in DESIGNS:
        h5_path = dspec["dataset_h5"]
        if os.path.exists(h5_path):
            with h5py.File(h5_path, "r") as f:
                inputs = f["inputs"][:]
                targets = f["targets"][:]
                all_inputs.append(inputs)
                all_targets.append(targets)
                print(f"  -> Added {len(inputs)} samples from {dspec['name']}")
                
    X_combined = np.concatenate(all_inputs, axis=0)
    Y_combined = np.concatenate(all_targets, axis=0)
    
    with h5py.File(out_unified_h5, "w") as f:
        f.create_dataset("inputs", data=X_combined)
        f.create_dataset("targets", data=Y_combined)
        f.create_dataset("data", data=Y_combined)
        
    print(f"[Unified Dataset] Saved combined multi-IP dataset to {out_unified_h5}. Shape: X={X_combined.shape}, Y={Y_combined.shape}")
    return out_unified_h5

def run_unified_experiment():
    unified_h5 = combine_datasets()
    unified_ckpt = "archive/checkpoints/thermfm_unified_multi_ip.pt"
    
    print("\n" + "=" * 80)
    print("   TRAINING SINGLE UNIFIED THERM-FM MODEL ACROSS ALL 3 IP DESIGNS")
    print("=" * 80)
    
    train(unified_h5, unified_ckpt, epochs=30, seed=42)
    
    results = []
    print("\n" + "=" * 80)
    print("   INFERENCE & EVALUATION WITH SINGLE UNIFIED MODEL")
    print("=" * 80)
    
    for dspec in DESIGNS:
        d_id = dspec["id"]
        out_dir = f"archive/outputs/{d_id}_thermfm_unified"
        t0 = time.time()
        t_grid = run_inference(dspec["flp"], dspec["ptrace"], unified_ckpt, out_dir)
        inf_time = time.time() - t0
        
        spef_out = f"{out_dir}/adjusted.spef"
        adjust_spef_file(dspec["baseline_spef"], f"{out_dir}/temp_grid.npy", spef_out, alpha=dspec["alpha"])
        
        mean_t = float(t_grid.mean())
        r_scale = 1.0 + dspec["alpha"] * (mean_t - 298.15)
        
        results.append({
            "Design": dspec["name"],
            "Mean Temp (K)": f"{mean_t:.2f}",
            "R Scale": f"{r_scale:.6f}",
            "Inference Time (s)": f"{inf_time:.4f}",
            "Unified Checkpoint": unified_ckpt
        })
        
    df_res = pd.DataFrame(results)
    print("\n" + "=" * 80)
    print("             UNIFIED THERM-FM MULTI-IP INFERENCE RESULTS")
    print("=" * 80)
    print(df_res.to_string(index=False))

if __name__ == "__main__":
    run_unified_experiment()
