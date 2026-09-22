"""Demo-only runtime compatibility shims.

This file is loaded automatically by Python when `demo/pythonpath` is placed on
PYTHONPATH. It keeps the demo runnable on macOS without changing Therm-FM's
main source files.
"""

import os

import psutil


if not hasattr(psutil.Process, "cpu_affinity"):

    def _cpu_affinity(self):
        return list(range(os.cpu_count() or 1))

    psutil.Process.cpu_affinity = _cpu_affinity
