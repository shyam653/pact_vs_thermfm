#!/usr/bin/env python3
"""Generate a tiny steady-state 3D-IC thermal dataset for local demos.

The generated files follow Therm-FM's steady dataset convention:
  input.mat:  (N, P, L, H, W)
  output.mat: (N, L, H, W)

Channels P are:
  0: normalized x coordinate
  1: normalized y coordinate
  2: normalized z/layer coordinate
  3: synthetic power density

The target temperature field is a simple diffusion-like response to power
density with weak cross-layer coupling. It is not a physical simulator, but it
is structured enough for a quick end-to-end training/evaluation smoke test.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np


def _gaussian_kernel(size: int, sigma: float) -> np.ndarray:
    ax = np.arange(size, dtype=np.float32) - (size - 1) / 2
    xx, yy = np.meshgrid(ax, ax, indexing="xy")
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel /= np.sum(kernel)
    return kernel.astype(np.float32)


def _fft_convolve2d(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Convolve a 2D image with a small kernel using FFT and same-size output."""
    pad_h = image.shape[0] + kernel.shape[0] - 1
    pad_w = image.shape[1] + kernel.shape[1] - 1
    image_fft = np.fft.rfftn(image, s=(pad_h, pad_w))
    kernel_fft = np.fft.rfftn(kernel, s=(pad_h, pad_w))
    full = np.fft.irfftn(image_fft * kernel_fft, s=(pad_h, pad_w)).astype(np.float32)
    start_h = kernel.shape[0] // 2
    start_w = kernel.shape[1] // 2
    return full[start_h : start_h + image.shape[0], start_w : start_w + image.shape[1]]


def _make_power_map(rng: np.random.Generator, layers: int, size: int) -> np.ndarray:
    y, x = np.meshgrid(
        np.linspace(-1.0, 1.0, size, dtype=np.float32),
        np.linspace(-1.0, 1.0, size, dtype=np.float32),
        indexing="ij",
    )
    power = np.zeros((layers, size, size), dtype=np.float32)

    for layer in range(layers):
        num_hotspots = int(rng.integers(1, 4))
        for _ in range(num_hotspots):
            cx = rng.uniform(-0.75, 0.75)
            cy = rng.uniform(-0.75, 0.75)
            amp = rng.uniform(0.7, 1.6)
            sigma = rng.uniform(0.07, 0.18)
            power[layer] += amp * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma**2))

        power[layer] += rng.uniform(0.01, 0.06, size=(size, size)).astype(np.float32)

    max_value = np.max(power)
    if max_value > 0:
        power /= max_value
    return power.astype(np.float32)


def _make_temperature(power: np.ndarray) -> np.ndarray:
    layers, size, _ = power.shape
    near_kernel = _gaussian_kernel(size=9, sigma=1.6)
    far_kernel = _gaussian_kernel(size=17, sigma=3.8)
    temperature = np.zeros_like(power)

    for layer in range(layers):
        local = _fft_convolve2d(power[layer], near_kernel)
        spread = _fft_convolve2d(power[layer], far_kernel)
        temperature[layer] = 35.0 + 42.0 * local + 18.0 * spread

    coupled = temperature.copy()
    for layer in range(layers):
        if layer > 0:
            coupled[layer] += 0.15 * temperature[layer - 1]
        if layer + 1 < layers:
            coupled[layer] += 0.15 * temperature[layer + 1]

    z_boost = np.linspace(0.0, 4.0, layers, dtype=np.float32).reshape(layers, 1, 1)
    return (coupled + z_boost).astype(np.float32)


def build_dataset(samples: int, layers: int, size: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x_coord = np.tile(np.linspace(0.0, 1.0, size, dtype=np.float32), (size, 1))
    y_coord = x_coord.T.copy()
    z_coord = np.linspace(0.0, 1.0, layers, dtype=np.float32)

    inputs = np.zeros((samples, 4, layers, size, size), dtype=np.float32)
    outputs = np.zeros((samples, layers, size, size), dtype=np.float32)

    for idx in range(samples):
        power = _make_power_map(rng, layers=layers, size=size)
        temperature = _make_temperature(power)

        for layer in range(layers):
            inputs[idx, 0, layer] = x_coord
            inputs[idx, 1, layer] = y_coord
            inputs[idx, 2, layer] = z_coord[layer]
            inputs[idx, 3, layer] = power[layer]
        outputs[idx] = temperature

    return inputs, outputs


def write_mat(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("data", data=data, compression="gzip")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a tiny Therm-FM steady demo dataset.")
    parser.add_argument("--output_dir", default="demo_data/thermal_steady_tiny")
    parser.add_argument("--samples", type=int, default=80)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.samples < 20:
        raise ValueError("--samples should be at least 20 so train/val/test splits are non-empty.")
    if args.layers < 1:
        raise ValueError("--layers must be positive.")
    if args.size < 16:
        raise ValueError("--size should be at least 16.")

    output_dir = Path(args.output_dir)
    inputs, outputs = build_dataset(
        samples=args.samples,
        layers=args.layers,
        size=args.size,
        seed=args.seed,
    )

    write_mat(output_dir / "input.mat", inputs)
    write_mat(output_dir / "output.mat", outputs)

    print(f"Wrote demo dataset to: {output_dir.resolve()}")
    print(f"input.mat shape:  {inputs.shape}")
    print(f"output.mat shape: {outputs.shape}")
    print("Dataset key: data")


if __name__ == "__main__":
    main()
