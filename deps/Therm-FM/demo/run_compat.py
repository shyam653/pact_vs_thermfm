#!/usr/bin/env python3
"""Run Therm-FM scripts with demo-only compatibility patches.

This wrapper is intentionally outside `scOT/`. It lets the quick demo run on
newer local environments while keeping the project source unchanged.
"""

from __future__ import annotations

import argparse
import inspect
import runpy
import sys
from pathlib import Path


def patch_training_arguments() -> None:
    import scOT.trainer as trainer

    cls = trainer.TrainingArguments
    original_init = cls.__init__
    params = inspect.signature(original_init).parameters

    if "evaluation_strategy" in params or "eval_strategy" not in params:
        return

    def compatible_init(self, *args, **kwargs):
        if "evaluation_strategy" in kwargs and "eval_strategy" not in kwargs:
            kwargs["eval_strategy"] = kwargs.pop("evaluation_strategy")
        # The quick demo should run in constrained local sandboxes where
        # PyTorch multiprocessing shared memory may be blocked.
        kwargs["dataloader_num_workers"] = 0
        return original_init(self, *args, **kwargs)

    cls.__init__ = compatible_init


def patch_trainer_compute_loss() -> None:
    import scOT.trainer as trainer

    original_compute_loss = trainer.Trainer.compute_loss
    params = inspect.signature(original_compute_loss).parameters
    if "num_items_in_batch" in params:
        return

    def compatible_compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        return original_compute_loss(
            self,
            model,
            inputs,
            return_outputs=return_outputs,
        )

    trainer.Trainer.compute_loss = compatible_compute_loss


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Therm-FM script with demo compatibility patches.")
    parser.add_argument("script", help="Script path relative to the repository root, e.g. scOT/train.py")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    patch_training_arguments()
    patch_trainer_compute_loss()

    script_path = repo_root / parsed.script
    sys.argv = [str(script_path), *parsed.args]
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
