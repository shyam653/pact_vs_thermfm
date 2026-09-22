#!/usr/bin/env python3
"""Quickly inspect the synthetic demo dataset through Therm-FM's loader."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scOT.problems.base import get_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Therm-FM demo dataset sample.")
    parser.add_argument("--data_path", default="demo_data/thermal_steady_tiny")
    args = parser.parse_args()

    dataset = get_dataset(
        dataset="thermal.steady.ThermalSteady3D",
        which="train",
        num_trajectories=-1,
        data_path=args.data_path,
        train_ratio=0.8,
    )
    sample = dataset[0]
    print(f"num_samples: {len(dataset)}")
    print(f"pixel_values: {tuple(sample['pixel_values'].shape)}")
    print(f"labels:       {tuple(sample['labels'].shape)}")
    print(f"input_dim:    {dataset.input_dim}")
    print(f"output_dim:   {dataset.output_dim}")
    print(f"resolution:   {dataset.resolution}")


if __name__ == "__main__":
    main()
