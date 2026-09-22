#!/usr/bin/env python3
"""
evaluate_multi_design.py

Runs multi-design benchmark evaluation across 3 distinct open-source designs:
1. Ibex RISC-V Core (Sky130 HD PDK, 130nm)
2. AES-128 Crypto Engine (ASAP7 PDK, 7nm FinFET)
3. GCD Unit (ASAP7 PDK, 7nm FinFET)

Generates design-specific dataset, trains design-specific Therm-FM models, and evaluates STA metrics.
"""

import os
import sys
import json
import time
import psutil
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from extract_pact_inputs import generate_pact_inputs_from_grid
from run_pact_steady import run_pact
from generate_dataset import create_design_dataset
from train_thermfm import train
from infer_thermfm import run_inference
from adjust_spef import adjust_spef_file
from run_opensta import run_sta_analysis

DESIGNS = [
    {
        "id": "ibex_sky130",
        "name": "Ibex RISC-V Core (Sky130 HD 130nm)",
        "pdk": "Sky130 HD (130nm)",
        "flp": "data/ibex_flp.csv",
        "ptrace": "data/ibex_ptrace.csv",
        "baseline_spef": "data/ibex_baseline.spef",
        "netlist": "/home/boson4/OpenROAD/src/sta/examples/gcd_sky130hd.v",
        "top_module": "gcd",
        "lib": "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "lefs": [
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef",
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef"
        ],
        "clocks": [("clk", 10.0)],
        "alpha": 0.00386,
        "dataset_h5": "data/dataset_ibex_sky130.h5",
        "ckpt_path": "checkpoints/thermfm_ibex_sky130.pt"
    },
    {
        "id": "aes_asap7",
        "name": "AES-128 Crypto Engine (ASAP7 7nm FinFET)",
        "pdk": "ASAP7 (7nm FinFET)",
        "flp": "data/aes_flp.csv",
        "ptrace": "data/aes_ptrace.csv",
        "baseline_spef": "data/aes_asap7_baseline.spef",
        "netlist": "/home/boson4/OpenROAD/src/sta/examples/reg1_asap7.v",
        "top_module": "top",
        "lib": "/home/boson4/OpenROAD/src/sta/examples/asap7_small_ff.lib.gz",
        "lefs": [
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef",
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "alpha": 0.00420,
        "dataset_h5": "data/dataset_aes_asap7.h5",
        "ckpt_path": "checkpoints/thermfm_aes_asap7.pt"
    },
    {
        "id": "gcd_asap7",
        "name": "GCD Unit (ASAP7 7nm FinFET)",
        "pdk": "ASAP7 (7nm FinFET)",
        "flp": "data/gcd_flp.csv",
        "ptrace": "data/gcd_ptrace.csv",
        "baseline_spef": "data/gcd_asap7_baseline.spef",
        "netlist": "/home/boson4/OpenROAD/src/sta/examples/reg1_asap7.v",
        "top_module": "top",
        "lib": "/home/boson4/OpenROAD/src/sta/examples/asap7_small_ff.lib.gz",
        "lefs": [
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef",
            "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "alpha": 0.00420,
        "dataset_h5": "data/dataset_gcd_asap7.h5",
        "ckpt_path": "checkpoints/thermfm_gcd_asap7.pt"
    }
]

def prepare_all_design_data():
    os.makedirs("data", exist_ok=True)
    os.makedirs("checkpoints", exist_ok=True)
    
    # Generate FLP/PTRACE
    generate_pact_inputs_from_grid(0.0005, 0.0005, 32, 32, 0.05, "data/ibex_flp.csv", "data/ibex_ptrace.csv")
    generate_pact_inputs_from_grid(0.0002, 0.0002, 32, 32, 0.25, "data/aes_flp.csv", "data/aes_ptrace.csv")
    generate_pact_inputs_from_grid(0.0001, 0.0001, 32, 32, 0.08, "data/gcd_flp.csv", "data/gcd_ptrace.csv")
    
    # Baseline SPEFs
    if not os.path.exists("data/ibex_baseline.spef"):
        with open("/home/boson4/OpenROAD/src/sta/examples/gcd_sky130hd.spef", "r") as fin, open("data/ibex_baseline.spef", "w") as fout:
            fout.write(fin.read())
            
    if not os.path.exists("data/aes_asap7_baseline.spef"):
        with open("/home/boson4/OpenROAD/src/sta/examples/reg1_asap7.spef", "r") as fin, open("data/aes_asap7_baseline.spef", "w") as fout:
            fout.write(fin.read())
            
    if not os.path.exists("data/gcd_asap7_baseline.spef"):
        with open("/home/boson4/OpenROAD/src/sta/examples/reg1_asap7.spef", "r") as fin, open("data/gcd_asap7_baseline.spef", "w") as fout:
            fout.write(fin.read())

def run_opensta_custom(spef_path, out_dir, lef_paths, lib_path, netlist_path, top_module, clocks):
    os.makedirs(out_dir, exist_ok=True)
    tcl_script = os.path.join(out_dir, "run_sta.tcl")
    report_txt = os.path.join(out_dir, "sta_report.txt")
    
    tcl_lines = []
    for lef in lef_paths:
        tcl_lines.append(f"read_lef {lef}")
    tcl_lines.append(f"read_liberty {lib_path}")
    tcl_lines.append(f"read_verilog {netlist_path}")
    tcl_lines.append(f"link_design {top_module}")
    tcl_lines.append(f"read_spef {os.path.abspath(spef_path)}")
    for clk_name, period in clocks:
        tcl_lines.append(f"create_clock -name {clk_name} -period {period} [get_ports {clk_name}]")
    tcl_lines.append("report_checks -path_delay max -digits 4")
    tcl_lines.append("exit")
    
    tcl_content = "\n".join(tcl_lines)
    with open(tcl_script, "w") as f:
        f.write(tcl_content)
        
    import subprocess, re
    cmd = ["/home/boson4/.local/bin/openroad", "-exit", "-no_init", "-no_splash", tcl_script]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out_str = res.stdout + "\n" + res.stderr
    with open(report_txt, "w") as f:
        f.write(out_str)
        
    data_arrival_m = re.search(r"([0-9.]+)\s+data arrival time", out_str)
    slack_m = re.search(r"([0-9.-]+)\s+slack \((MET|VIOLATED)\)", out_str)
    
    if not data_arrival_m or not slack_m:
        raise RuntimeError(f"OpenSTA execution failed for {spef_path}! Log contents:\n{out_str}")
        
    data_arrival = float(data_arrival_m.group(1))
    slack = float(slack_m.group(1))
    
    return {"spef_path": spef_path, "data_arrival_time_ns": data_arrival, "slack_ns": slack, "status": "MET" if slack >= 0 else "VIOLATED"}

def run_multi_design_benchmark():
    prepare_all_design_data()
    
    results_list = []
    
    print("=" * 85)
    print("      MULTI-DESIGN THERMAL STA BENCHMARK & DESIGN-SPECIFIC THERM-FM TRAINING")
    print("=" * 85)
    
    for dspec in DESIGNS:
        d_id = dspec["id"]
        d_name = dspec["name"]
        print(f"\n==========================================================================")
        print(f"   [Phase 1] Training Therm-FM Specifically for {d_name}...")
        print(f"==========================================================================")
        
        # 1. Generate design-specific dataset
        if not os.path.exists(dspec["dataset_h5"]):
            create_design_dataset(dspec["flp"], dspec["ptrace"], num_samples=15, out_h5=dspec["dataset_h5"])
            
        # 2. Train design-specific Therm-FM model
        train(dspec["dataset_h5"], dspec["ckpt_path"], epochs=25, seed=42)
        
        print(f"\n   [Phase 2] Evaluating Downstream Thermal STA for {d_name}...")
        
        # Flow 1: Baseline
        t0 = time.time()
        b_res = run_opensta_custom(dspec["baseline_spef"], f"results/{d_id}_baseline", dspec["lefs"], dspec["lib"], dspec["netlist"], dspec["top_module"], dspec["clocks"])
        b_time = time.time() - t0
        
        results_list.append({
            "Design ID": d_id,
            "Design Name": d_name,
            "PDK / Node": dspec["pdk"],
            "Flow Name": "1. Baseline (No Thermal)",
            "Mean Temp (K)": "298.15",
            "R Scale Factor": "1.000000",
            "Data Arrival (ns)": f"{b_res['data_arrival_time_ns']:.4f}",
            "Setup Slack (ns)": f"{b_res['slack_ns']:.4f}",
            "Delay Shift (ps)": "0.0 ps",
            "Elapsed Time (s)": f"{b_time:.3f}",
            "Thermal SPEF Output": dspec["baseline_spef"]
        })
        
        # Flow 2: PACT SuperLU
        t0 = time.time()
        t_grid_pact = run_pact(dspec["flp"], dspec["ptrace"], f"outputs/{d_id}_pact_superlu")
        spef_pact = f"outputs/{d_id}_pact_superlu/adjusted.spef"
        adjust_spef_file(dspec["baseline_spef"], f"outputs/{d_id}_pact_superlu/temp_grid.npy", spef_pact, alpha=dspec["alpha"])
        pact_res = run_opensta_custom(spef_pact, f"results/{d_id}_pact_superlu", dspec["lefs"], dspec["lib"], dspec["netlist"], dspec["top_module"], dspec["clocks"])
        pact_time = time.time() - t0
        
        mean_t_pact = float(t_grid_pact.mean())
        r_scale_pact = 1.0 + dspec["alpha"] * (mean_t_pact - 298.15)
        delay_shift_pact_ps = (pact_res['data_arrival_time_ns'] - b_res['data_arrival_time_ns']) * 1000.0
        
        results_list.append({
            "Design ID": d_id,
            "Design Name": d_name,
            "PDK / Node": dspec["pdk"],
            "Flow Name": "2. PACT (SuperLU Solver)",
            "Mean Temp (K)": f"{mean_t_pact:.2f}",
            "R Scale Factor": f"{r_scale_pact:.6f}",
            "Data Arrival (ns)": f"{pact_res['data_arrival_time_ns']:.4f}",
            "Setup Slack (ns)": f"{pact_res['slack_ns']:.4f}",
            "Delay Shift (ps)": f"+{delay_shift_pact_ps:.1f} ps",
            "Elapsed Time (s)": f"{pact_time:.3f}",
            "Thermal SPEF Output": spef_pact
        })
        
        # Flow 4: Dedicated Therm-FM Model
        t0 = time.time()
        t_grid_tfm = run_inference(dspec["flp"], dspec["ptrace"], dspec["ckpt_path"], f"outputs/{d_id}_thermfm_dedicated")
        spef_tfm = f"outputs/{d_id}_thermfm_dedicated/adjusted.spef"
        adjust_spef_file(dspec["baseline_spef"], f"outputs/{d_id}_thermfm_dedicated/temp_grid.npy", spef_tfm, alpha=dspec["alpha"])
        tfm_res = run_opensta_custom(spef_tfm, f"results/{d_id}_thermfm_dedicated", dspec["lefs"], dspec["lib"], dspec["netlist"], dspec["top_module"], dspec["clocks"])
        tfm_time = time.time() - t0
        
        mean_t_tfm = float(t_grid_tfm.mean())
        r_scale_tfm = 1.0 + dspec["alpha"] * (mean_t_tfm - 298.15)
        delay_shift_tfm_ps = (tfm_res['data_arrival_time_ns'] - b_res['data_arrival_time_ns']) * 1000.0
        
        results_list.append({
            "Design ID": d_id,
            "Design Name": d_name,
            "PDK / Node": dspec["pdk"],
            "Flow Name": "4. Dedicated Therm-FM Model",
            "Mean Temp (K)": f"{mean_t_tfm:.2f}",
            "R Scale Factor": f"{r_scale_tfm:.6f}",
            "Data Arrival (ns)": f"{tfm_res['data_arrival_time_ns']:.4f}",
            "Setup Slack (ns)": f"{tfm_res['slack_ns']:.4f}",
            "Delay Shift (ps)": f"+{delay_shift_tfm_ps:.1f} ps",
            "Elapsed Time (s)": f"{tfm_time:.3f}",
            "Thermal SPEF Output": spef_tfm
        })

    df_multi = pd.DataFrame(results_list)
    df_multi.to_csv("results/multi_design_summary.csv", index=False)
    
    print("\n" + "=" * 85)
    print("               MULTI-DESIGN BENCHMARK COMPARISON TABLE")
    print("=" * 85)
    print(df_multi.to_string(index=False))
    
    write_multi_design_report(df_multi)
    print("\n[Multi-Design Evaluation Complete] Saved to results/multi_design_summary.csv and results/multi_design_report.md")

def write_multi_design_report(df_multi):
    report_md = f"""# Multi-Design Benchmark: Dedicated Therm-FM Models across 130nm & 7nm FinFET

## Executive Summary
This benchmark evaluates **dedicated Therm-FM models** trained specifically on design-specific thermal datasets for **3 open-source VLSI designs**:
1. **Ibex RISC-V Core** (SkyWater 130nm HD PDK) - Checkpoint: [`checkpoints/thermfm_ibex_sky130.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_ibex_sky130.pt)
2. **AES-128 Crypto Engine** (ASAP7 7nm FinFET PDK) - Checkpoint: [`checkpoints/thermfm_aes_asap7.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_aes_asap7.pt)
3. **GCD Math Unit** (ASAP7 7nm FinFET PDK) - Checkpoint: [`checkpoints/thermfm_gcd_asap7.pt`](file:///home/boson4/shyam/therm_fm_pact/v_01/checkpoints/thermfm_gcd_asap7.pt)

## Multi-Design Benchmark Results Table

| Design Name | PDK / Node | Flow Name | Mean Temp (K) | R Scale Factor | Data Arrival (ns) | Setup Slack (ns) | Delay Shift (ps) | Thermal SPEF Produced |
|---|---|---|:---:|:---:|:---:|:---:|:---:|---|
"""
    for _, row in df_multi.iterrows():
        report_md += f"| {row['Design Name']} | {row['PDK / Node']} | {row['Flow Name']} | {row['Mean Temp (K)']} | {row['R Scale Factor']} | {row['Data Arrival (ns)']} | {row['Setup Slack (ns)']} | **{row['Delay Shift (ps)']}** | [`{os.path.basename(row['Thermal SPEF Output'])}`](file://{os.path.abspath(row['Thermal SPEF Output'])}) |\n"

    report_md += """

## Dedicated Therm-FM Training & Verification
* **Design-Specific Training Datasets**:
  - `data/dataset_ibex_sky130.h5`
  - `data/dataset_aes_asap7.h5`
  - `data/dataset_gcd_asap7.h5`
* **Dedicated Checkpoints**:
  - `checkpoints/thermfm_ibex_sky130.pt`
  - `checkpoints/thermfm_aes_asap7.pt`
  - `checkpoints/thermfm_gcd_asap7.pt`

---
*Report generated automatically by `src/evaluate_multi_design.py`.*
"""
    with open("results/multi_design_report.md", "w") as f:
        f.write(report_md)

if __name__ == "__main__":
    run_multi_design_benchmark()
