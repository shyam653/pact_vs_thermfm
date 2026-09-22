#!/usr/bin/env python3
"""
generate_archgen_datasets.py

Generates 3D steady-state thermal ground-truth datasets for the 3 Archgen IPs
using original PACT SuperLU solver.
"""

import os
import sys
import numpy as np
import h5py
import pandas as pd
from tqdm import tqdm

from generate_dataset import create_design_dataset

ARCHGEN_IPS = [
    {
        "id": "archgen_ip1",
        "name": "IP1: Dual-Core RV64 Rocket SoC (DualRocketConfig)",
        "flp": "archive/design_inputs/archgen_ip1/flp.csv",
        "ptrace": "archive/design_inputs/archgen_ip1/ptrace.csv",
        "out_h5": "archive/data/dataset_archgen_ip1.h5"
    },
    {
        "id": "archgen_ip2",
        "name": "IP2: Dual-Core RV64 Rocket SoC + 8-Point FFT",
        "flp": "archive/design_inputs/archgen_ip2/flp.csv",
        "ptrace": "archive/design_inputs/archgen_ip2/ptrace.csv",
        "out_h5": "archive/data/dataset_archgen_ip2.h5"
    },
    {
        "id": "archgen_ip3",
        "name": "IP3: Dual-Core RV64 Rocket SoC + NVDLA INT8 Engines",
        "flp": "archive/design_inputs/archgen_ip3/flp.csv",
        "ptrace": "archive/design_inputs/archgen_ip3/ptrace.csv",
        "out_h5": "archive/data/dataset_archgen_ip3.h5"
    }
]

def build_all_datasets(num_samples=200):
    for ip_spec in ARCHGEN_IPS:
        print(f"\n==========================================================================")
        print(f"   [PACT Dataset Gen] Building thermal ground-truth dataset for {ip_spec['name']}...")
        print(f"==========================================================================")
        create_design_dataset(ip_spec["flp"], ip_spec["ptrace"], num_samples=num_samples, grid_size=32, out_h5=ip_spec["out_h5"])

if __name__ == "__main__":
    build_all_datasets(num_samples=200)

