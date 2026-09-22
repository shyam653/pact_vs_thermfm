#!/usr/bin/env python3
"""
run_opensta.py

Runs OpenROAD STA (OpenSTA) timing analysis for a given SPEF file
and exports structured JSON and text timing reports.
"""

import os
import sys
import argparse
import json
import re
import subprocess

OPENROAD_BIN = "/home/boson4/.local/bin/openroad"
LIB_PATH = "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
LEF_TECH = "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef"
LEF_CELLS = "/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef"
NETLIST_PATH = "/home/boson4/OpenROAD/src/sta/examples/gcd_sky130hd.v"

def run_sta_analysis(spef_path, out_dir, clock_period=10.0):
    os.makedirs(out_dir, exist_ok=True)
    
    tcl_script = os.path.join(out_dir, "run_sta.tcl")
    report_txt = os.path.join(out_dir, "sta_report.txt")
    report_json = os.path.join(out_dir, "sta_report.json")
    
    tcl_content = f"""
read_liberty {LIB_PATH}
read_lef {LEF_TECH}
read_lef {LEF_CELLS}
read_verilog {NETLIST_PATH}
link_design gcd
read_spef {os.path.abspath(spef_path)}
create_clock -name clk -period {clock_period} [get_ports clk]

puts "=== STA REPORT START ==="
report_checks -path_delay max -digits 4
report_worst_slack -max
report_tns
puts "=== STA REPORT END ==="
"""

    with open(tcl_script, "w") as f:
        f.write(tcl_content)
        
    cmd = [OPENROAD_BIN, "-exit", "-no_init", "-no_splash", tcl_script]
    print(f"[OpenSTA] Analyzing {spef_path}...")
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    out_str = res.stdout + "\n" + res.stderr
    
    with open(report_txt, "w") as f:
        f.write(out_str)
        
    # Extract metrics using regex
    data_arrival_m = re.search(r"([0-9.]+)\s+data arrival time", out_str)
    slack_m = re.search(r"([0-9.-]+)\s+slack \((MET|VIOLATED)\)", out_str)
    wns_m = re.search(r"worst slack ([0-9.-]+)", out_str)
    tns_m = re.search(r"tns ([0-9.-]+)", out_str)
    
    data_arrival = float(data_arrival_m.group(1)) if data_arrival_m else None
    slack = float(slack_m.group(1)) if slack_m else None
    wns = float(wns_m.group(1)) if wns_m else (slack if slack is not None else 0.0)
    tns = float(tns_m.group(1)) if tns_m else 0.0
    
    results = {
        "spef_path": spef_path,
        "clock_period_ns": clock_period,
        "data_arrival_time_ns": data_arrival,
        "slack_ns": slack,
        "wns_ns": wns,
        "tns_ns": tns,
        "status": "MET" if (slack is not None and slack >= 0) else "VIOLATED"
    }
    
    with open(report_json, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"[OpenSTA Result] Arrival={data_arrival} ns | Slack={slack} ns | WNS={wns} ns | TNS={tns} ns")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OpenSTA timing analysis")
    parser.add_argument("--spef", type=str, default="data/ibex_baseline.spef")
    parser.add_argument("--out-dir", type=str, default="results/baseline")
    parser.add_argument("--period", type=float, default=10.0)
    args = parser.parse_args()
    
    run_sta_analysis(args.spef, args.out_dir, clock_period=args.period)
