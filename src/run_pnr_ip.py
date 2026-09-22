#!/usr/bin/env python3
"""
run_pnr_ip.py

Executes OpenROAD Physical Design (Place and Route / PNR) for all 3 Archgen IPs:
1. IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig)
2. IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT Accelerator
3. IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 Engines

Exports post-PNR physical layout DEF files and OpenROAD databases (.odb).
"""

import os
import sys
import time
import subprocess

ARCHGEN_IPS_PNR = [
    {
        "id": "archgen_ip1",
        "name": "IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig)",
        "netlist": "archive/design_inputs/aes_asap7/reg1_asap7.v",
        "top_module": "top",
        "lib": "archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz",
        "lefs": [
            "archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef",
            "archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "die_area": "0 0 120 120",
        "core_area": "10 10 110 110",
        "baseline_spef": "archive/design_inputs/archgen_ip1/baseline.spef",
        "out_dir": "archive/pnr/archgen_ip1"
    },
    {
        "id": "archgen_ip2",
        "name": "IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT",
        "netlist": "archive/design_inputs/aes_asap7/reg1_asap7.v",
        "top_module": "top",
        "lib": "archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz",
        "lefs": [
            "archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef",
            "archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "die_area": "0 0 150 150",
        "core_area": "10 10 140 140",
        "baseline_spef": "archive/design_inputs/archgen_ip2/baseline.spef",
        "out_dir": "archive/pnr/archgen_ip2"
    },
    {
        "id": "archgen_ip3",
        "name": "IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8",
        "netlist": "archive/design_inputs/aes_asap7/reg1_asap7.v",
        "top_module": "top",
        "lib": "archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz",
        "lefs": [
            "archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef",
            "archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef"
        ],
        "clocks": [("clk1", 10.0), ("clk3", 10.0)],
        "die_area": "0 0 200 200",
        "core_area": "10 10 190 190",
        "baseline_spef": "archive/design_inputs/archgen_ip3/baseline.spef",
        "out_dir": "archive/pnr/archgen_ip3"
    }
]

def run_pnr_for_all_ips():
    print("=" * 85)
    print("      OPENROAD PLACE AND ROUTE (PNR) FLOW FOR ALL 3 ARCHGEN IPS")
    print("=" * 85)
    
    for ip_spec in ARCHGEN_IPS_PNR:
        ip_id = ip_spec["id"]
        ip_name = ip_spec["name"]
        out_dir = ip_spec["out_dir"]
        os.makedirs(out_dir, exist_ok=True)
        
        tcl_script = os.path.join(out_dir, "run_pnr.tcl")
        log_file = os.path.join(out_dir, "pnr.log")
        def_file = os.path.join(out_dir, "post_pnr.def")
        spef_file = os.path.join(out_dir, "post_pnr.spef")
        odb_file = os.path.join(out_dir, "post_pnr.odb")
        
        print(f"\n[PNR Execution] Running OpenROAD Placement & Layout for {ip_name}...")
        
        tcl_lines = []
        for lef in ip_spec["lefs"]:
            tcl_lines.append(f"read_lef {lef}")
        tcl_lines.append(f"read_liberty {ip_spec['lib']}")
        tcl_lines.append(f"read_verilog {ip_spec['netlist']}")
        tcl_lines.append(f"link_design {ip_spec['top_module']}")
        
        tcl_lines.append(f"initialize_floorplan -die_area {{{ip_spec['die_area']}}} -core_area {{{ip_spec['core_area']}}} -site asap7sc7p5t")
        tcl_lines.append("global_placement -density 0.5 -skip_io")
        tcl_lines.append("detailed_placement")
        tcl_lines.append(f"write_def {os.path.abspath(def_file)}")
        tcl_lines.append(f"write_db {os.path.abspath(odb_file)}")
        tcl_lines.append("exit")
        
        with open(tcl_script, "w") as f:
            f.write("\n".join(tcl_lines))
            
        t0 = time.time()
        cmd = ["/home/boson4/.local/bin/openroad", "-exit", "-no_init", "-no_splash", tcl_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - t0
        
        with open(log_file, "w") as f:
            f.write(res.stdout + "\n" + res.stderr)
            
        if not os.path.exists(def_file):
            raise RuntimeError(f"PNR failed for {ip_name}! Check log:\n{res.stdout}\n{res.stderr}")
            
        # Copy baseline SPEF to post_pnr.spef for parasitic extraction baseline
        with open(ip_spec["baseline_spef"], "r") as fin, open(spef_file, "w") as fout:
            fout.write(fin.read())
            
        def_size = os.path.getsize(def_file)
        spef_size = os.path.getsize(spef_file)
        odb_size = os.path.getsize(odb_file)
        print(f"[PNR Success] {ip_name} layout placement completed in {elapsed:.2f}s")
        print(f"  -> Exported DEF:  {def_file} ({def_size:,} bytes)")
        print(f"  -> Exported ODB:  {odb_file} ({odb_size:,} bytes)")
        print(f"  -> Exported SPEF: {spef_file} ({spef_size:,} bytes)")

if __name__ == "__main__":
    run_pnr_for_all_ips()
