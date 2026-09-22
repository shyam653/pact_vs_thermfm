# Therm-FM Quick Demo

This demo runs Therm-FM without downloading the released Google Drive datasets.
It creates a tiny synthetic steady-state thermal dataset and trains/evaluates a
small ScOT model end to end.

The demo does not modify the main `scOT/` code path.

## What It Generates

```text
demo_data/thermal_steady_tiny/
├── input.mat
└── output.mat

demo_outputs/
├── checkpoints/
└── eval/
```

The generated dataset follows the steady thermal loader convention:

```text
input.mat:  (N, P, L, H, W)
output.mat: (N, L, H, W)
dataset key: data
```

Input channels are normalized `x`, `y`, `z/layer`, and synthetic power density.
The target is a diffusion-like temperature response with weak cross-layer
coupling. It is intended for smoke testing and demos, not physical validation.

## Run

From the repository root:

```bash
bash demo/run_demo.sh
```

If your default `python3` is not the environment with Therm-FM dependencies,
pass the interpreter explicitly:

```bash
PYTHON=/path/to/env/bin/python bash demo/run_demo.sh
```

The script will:

1. Generate synthetic data.
2. Train a tiny ScOT model for a few epochs with Weights & Biases disabled.
3. Evaluate the test split.
4. Save denormalized predictions to `predictions.mat`.

`demo/run_demo.sh` also uses demo-only compatibility helpers for macOS and newer
local Transformers versions. The main `scOT/` source files are not modified.

## Inspect Only

To generate data only:

```bash
python demo/make_synthetic_thermal_data.py
```

To verify that Therm-FM's dataset loader can read it:

```bash
python demo/check_dataset.py
```

Expected sample shape with default settings:

```text
pixel_values: (16, 32, 32)
labels:       (4, 32, 32)
```

## Customize

```bash
python demo/make_synthetic_thermal_data.py \
  --output_dir demo_data/thermal_steady_tiny \
  --samples 80 \
  --layers 4 \
  --size 32 \
  --seed 7
```

You can also change demo paths when running the full script:

```bash
DATA_DIR=demo_data/my_case OUTPUT_DIR=demo_outputs/my_case bash demo/run_demo.sh
```
