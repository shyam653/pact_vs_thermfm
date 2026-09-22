#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
DATA_DIR="${DATA_DIR:-demo_data/thermal_steady_tiny}"
OUTPUT_DIR="${OUTPUT_DIR:-demo_outputs}"
DEMO_PYTHONPATH="$ROOT_DIR/demo/pythonpath:$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$OUTPUT_DIR/matplotlib}"
mkdir -p "$MPLCONFIGDIR"
CONFIG_JSON='{
  "dataset": "thermal.steady.ThermalSteady3D",
  "num_trajectories": -1,
  "model_name": "demo",
  "patch_size": 4,
  "num_heads": [2, 4],
  "skip_connections": [1, 0],
  "window_size": 8,
  "mlp_ratio": 2.0,
  "depths": [1, 1],
  "embed_dim": 24,
  "lr": 0.001,
  "weight_decay": 0.000001,
  "lr_scheduler": "cosine",
  "warmup_ratio": 0.0,
  "early_stopping_patience": 20,
  "num_epochs": 3,
  "batch_size": 8,
  "max_grad_norm": 5.0,
  "train_ratio": 0.8
}'

echo "[demo] Generating synthetic steady thermal data..."
"$PYTHON" demo/make_synthetic_thermal_data.py --output_dir "$DATA_DIR"

echo "[demo] Training tiny ScOT model..."
PYTHONPATH="$DEMO_PYTHONPATH" WANDB_MODE=disabled "$PYTHON" demo/run_compat.py scOT/train.py \
  --json_config \
  --config "$CONFIG_JSON" \
  --data_path "$DATA_DIR" \
  --checkpoint_path "$OUTPUT_DIR/checkpoints" \
  --wandb_project_name therm_fm_demo \
  --wandb_run_name tiny_steady \
  --disable_tqdm

MODEL_PATH="$(
  CKPT_ROOT="$OUTPUT_DIR/checkpoints" "$PYTHON" - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["CKPT_ROOT"])
candidates = [
    path
    for path in root.iterdir()
    if path.is_dir()
    and (path / "config.json").is_file()
    and ((path / "model.safetensors").is_file() or (path / "pytorch_model.bin").is_file())
]
if not candidates:
    raise SystemExit(f"No trained model directory found under {root}")
latest = max(candidates, key=lambda path: path.stat().st_mtime)
print(latest)
PY
)"

echo "[demo] Evaluating tiny model..."
PYTHONPATH="$DEMO_PYTHONPATH" "$PYTHON" demo/run_compat.py scOT/evaluate.py \
  --model_path "$MODEL_PATH" \
  --config configs/demo_thermal_steady_tiny.yaml \
  --data_path "$DATA_DIR" \
  --output_dir "$OUTPUT_DIR/eval/tiny_steady" \
  --only_test \
  --per_device_batch_size 8 \
  --save_predictions_mat "$OUTPUT_DIR/eval/tiny_steady/predictions.mat"

echo "[demo] Done."
echo "[demo] Model: $MODEL_PATH"
echo "[demo] Metrics: $OUTPUT_DIR/eval/tiny_steady/test.json"
echo "[demo] Predictions: $OUTPUT_DIR/eval/tiny_steady/predictions.mat"
