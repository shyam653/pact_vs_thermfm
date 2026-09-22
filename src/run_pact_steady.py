#!/usr/bin/env python3
"""
run_pact_steady.py

Runs PACT steady-state thermal simulation (using SuperLU or SPICE/Xyce solver)
for a given floorplan and power trace, producing 2D/3D temperature grid files.
"""

import sys
import os
import argparse
import configparser
import pandas as pd
import numpy as np
import subprocess

PACT_SRC_DIR = os.path.abspath("deps/PACT/src")

def create_pact_lcf(flp_path, ptrace_path, lcf_out, layer_thickness=0.0001):
    """Creates a PACT LCF (Layer Configuration File)."""
    df = pd.DataFrame([{
        "Layer": 0,
        "FloorplanFile": os.path.abspath(flp_path),
        "Thickness (m)": layer_thickness,
        "PtraceFile": os.path.abspath(ptrace_path),
        "LateralHeatFlow": True
    }])
    os.makedirs(os.path.dirname(os.path.abspath(lcf_out)), exist_ok=True)
    df.to_csv(lcf_out, index=False)

def create_pact_config(config_out, ambient_temp_k=318.15):
    """Creates default PACT thermal properties configuration."""
    content = f"""[DEFAULT]
label = 

[Si]
thermalresistivity ((m-k)/w) = 0.0077
specificheatcapacity (j/m^3k) = 1750000

[Init]
ambient = {ambient_temp_k} K
temperature = 273.15 K

[HeatSink]
convection_cap (j/k) = 140.4
convection_r (k/w) = 0.1
heatsink_side (m) = 0.04
heatsink_thickness (m) = 0.001
heatsink_thermalconductivity (w/(m-k)) = 400.0
heatsink_specificheatcapacity (j/m^3k) = 3.55e6
heatspreader_side (m) = 0.02
heatspreader_thickness (m) = 0.001
heatspreader_thermalconductivity (w/(m-k)) = 400.0
heatspreader_specificheatcapacity (j/m^3k) = 3.55e6
"""
    os.makedirs(os.path.dirname(os.path.abspath(config_out)), exist_ok=True)
    with open(config_out, "w") as f:
        f.write(content)

def create_pact_model_params(params_out, grid_rows=32, grid_cols=32, solver_type="SuperLU"):
    """Creates PACT model parameters configuration."""
    if solver_type.lower() == "superlu":
        solver_sec = """[Solver]
name = SuperLU
wrapper = SuperLUSolver.py
"""
    else:
        solver_sec = """[Solver]
name = SPICE_steady
wrapper = SPICESolver_steady.py
ll_steady_solver = KLU
"""

    content = f"""[DEFAULT]
label = 

[Path]

[Simulation]
steady_state = True
steady_state_solver = Solver
transient = False
temperature_dependent = False
convergence = 0.1
layer = 1
temperature_dependent_library = TemperatureDependent.py
number_of_core = 4
init_file = False

{solver_sec}

[Grid]
grid_mode = max
type = Uniform
granularity = Grid
rows = {grid_rows}
cols = {grid_cols}

[VirtualNodes]
center_center = 0.5
bottom_center = 1

[HeatSink]
LateralHeatFlow = True
VerticalHeatFlow = True
library_name = HeatSink_sec
library = HeatSink.py
virtual_node = bottom_center
transient = False
mode = single

[HeatSink_sec]
properties = convection_cap (j/k), convection_r (k/w), heatsink_side (m), heatsink_thickness (m), heatsink_thermalconductivity (w/(m-k)), heatsink_specificheatcapacity (j/m^3k), heatspreader_side (m), heatspreader_thickness (m), heatspreader_thermalconductivity (w/(m-k)), heatspreader_specificheatcapacity (j/m^3k)

[Si]
library_name = Solid
library = Solid.py
transient = False
virtual_node = bottom_center
mode = single

[Solid]
properties = thermalresistivity ((m-k)/w), specificheatcapacity (j/m^3k)
"""
    os.makedirs(os.path.dirname(os.path.abspath(params_out)), exist_ok=True)
    with open(params_out, "w") as f:
        f.write(content)

def run_pact(flp_path, ptrace_path, out_dir, grid_rows=32, grid_cols=32, solver="SuperLU"):
    os.makedirs(out_dir, exist_ok=True)
    
    lcf_file = os.path.abspath(os.path.join(out_dir, "pact.lcf.csv"))
    config_file = os.path.abspath(os.path.join(out_dir, "pact.config"))
    params_file = os.path.abspath(os.path.join(out_dir, "pact.modelParams"))
    grid_out = os.path.abspath(os.path.join(out_dir, "grid_steady.out"))
    
    create_pact_lcf(flp_path, ptrace_path, lcf_file)
    create_pact_config(config_file)
    create_pact_model_params(params_file, grid_rows=grid_rows, grid_cols=grid_cols, solver_type=solver)
    
    cmd = [
        sys.executable,
        os.path.join(PACT_SRC_DIR, "PACT.py"),
        lcf_file,
        config_file,
        params_file,
        "--gridSteadyFile", grid_out
    ]
    
    print(f"[PACT] Running command: {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONPATH"] = PACT_SRC_DIR + ":" + env.get("PYTHONPATH", "")
    
    res = subprocess.run(cmd, cwd=out_dir, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[PACT Error] stdout: {res.stdout}")
        print(f"[PACT Error] stderr: {res.stderr}")
        raise RuntimeError(f"PACT execution failed with return code {res.returncode}")
        
    print(f"[PACT] Simulation completed successfully.")
    
    # Load and format the temperature grid output file (.layer0 or similar)
    layer_file = grid_out + ".layer0"
    if os.path.exists(layer_file):
        temps = np.loadtxt(layer_file)
        temps_2d = temps.reshape((grid_rows, grid_cols))
        np.save(os.path.join(out_dir, "temp_grid.npy"), temps_2d)
        pd.DataFrame(temps_2d).to_csv(os.path.join(out_dir, "temp_grid.csv"), header=False, index=False)
        print(f"[PACT Output] Temperature grid saved (min={temps_2d.min():.2f}K, max={temps_2d.max():.2f}K, mean={temps_2d.mean():.2f}K)")
        return temps_2d
    else:
        print(f"[PACT Warning] Output file {layer_file} not found directly, checking {grid_out}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run PACT steady state thermal solver")
    parser.add_argument("--flp", type=str, default="data/ibex_flp.csv")
    parser.add_argument("--ptrace", type=str, default="data/ibex_ptrace.csv")
    parser.add_argument("--out-dir", type=str, default="outputs/pact_superlu")
    parser.add_argument("--grid-rows", type=int, default=32)
    parser.add_argument("--grid-cols", type=int, default=32)
    parser.add_argument("--solver", type=str, default="SuperLU", choices=["SuperLU", "SPICE"])
    args = parser.parse_args()
    
    run_pact(args.flp, args.ptrace, args.out_dir, grid_rows=args.grid_rows, grid_cols=args.grid_cols, solver=args.solver)
