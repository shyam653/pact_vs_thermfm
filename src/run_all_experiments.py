#!/usr/bin/env python3
"""
run_all_experiments.py

Master Experiment Runner for Therm-FM Model Research.
Executes all planned benchmark matrix experiments and few-shot sweeps.
Saves unified results table to scratch/all_experiments_results.json.
"""

import os
import sys
import json
import time
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
from train_thermfm_research import run_experiment

def main():
    print("==========================================================================")
    print("      MASTER EXPERIMENT RUNNER: Therm-FM Model Research & Adaptation      ")
    print("==========================================================================")
    
    os.makedirs("scratch/results", exist_ok=True)
    all_results = []
    
    # 1. Baseline Experiments on Calibrated Physical Dataset (150 samples)
    variants = [
        "unet_fno_baseline",
        "linear_pde_solver",
        "thermfm_scratch",
        "thermfm_frozen_basis",
        "thermfm_finetune_basis"
    ]
    
    dataset_cal = "dataset_calibrated_phys"
    print(f"\n>>> Step 1: Running Benchmark Matrix on {dataset_cal} <<<")
    for var in variants:
        res = run_experiment(
            variant_name=var,
            dataset_name=dataset_cal,
            epochs=20 if var != "linear_pde_solver" else 0,
            batch_size=16,
            lr=1e-3
        )
        if res:
            all_results.append(res)
            
    # 2. Few-Shot Label Efficiency Sweep (Phase 8)
    sample_budgets = [10, 25, 50]
    few_shot_variants = ["unet_fno_baseline", "thermfm_frozen_basis", "thermfm_scratch"]
    
    print(f"\n>>> Step 2: Running Few-Shot Label Efficiency Sweep <<<")
    for budget in sample_budgets:
        for var in few_shot_variants:
            res = run_experiment(
                variant_name=var,
                dataset_name=dataset_cal,
                epochs=20,
                batch_size=min(8, budget),
                lr=1e-3,
                sample_limit=budget
            )
            if res:
                all_results.append(res)
                
    # 3. Multi-IP Unified Dataset Evaluation (600 samples)
    dataset_unified = "dataset_unified_archgen_ips"
    print(f"\n>>> Step 3: Running Multi-IP Evaluation on {dataset_unified} <<<")
    for var in ["unet_fno_baseline", "thermfm_frozen_basis", "thermfm_finetune_basis"]:
        res = run_experiment(
            variant_name=var,
            dataset_name=dataset_unified,
            epochs=15,
            batch_size=32,
            lr=1e-3
        )
        if res:
            all_results.append(res)

    # Save aggregated JSON results
    out_json = "scratch/all_experiments_results.json"
    with open(out_json, "w") as f:
        json.dump(all_results, f, indent=2)
        
    print(f"\n================ All Experiments Completed Successfully! ================")
    print(f"Unified results saved to {out_json}")

if __name__ == "__main__":
    main()
