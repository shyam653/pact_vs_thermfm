#!/usr/bin/env python3
"""Start the fixed benchmark partition when the two-worker ISA campaign ends."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

repo = Path(__file__).resolve().parents[2]
campaign = repo / "build/IP3/cpu-isa"
while not (campaign / "summary.json").is_file():
    time.sleep(30)
summary = json.loads((campaign / "summary.json").read_text())
if summary["total"] != 349:
    raise RuntimeError("ISA campaign is incomplete")
simulator = Path("${CHIPYARD_ROOT}/sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig")
expected = "ac906aabe883e14d65b06669b134ca5079d96ddcd462e82b4d0079b08a6cacf5"
if hashlib.sha256(simulator.read_bytes()).hexdigest() != expected:
    raise RuntimeError("Official simulator bytes changed; do not mix CPU campaigns")
command = ["python3", str(repo / "IPs/IP2/scripts/run-regression.py"),
           str(repo / "build/cpu-rebuilt/bench-short.tsv"), str(repo / "build/IP3/cpu-bench"),
           "--simulator", str(simulator), "--chipyard-root", "${CHIPYARD_ROOT}",
           "--jobs", "2", "--max-cycles", "2000000", "--timeout", "1800", "--seed", "1"]
(repo / "build/IP3/cpu-bench-launch-command.json").write_text(json.dumps(command, indent=2) + "\n")
with (repo / "build/IP3/cpu-bench-driver.log").open("w") as log:
    result = subprocess.run(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT)
(repo / "build/IP3/cpu-bench-driver.exit").write_text(str(result.returncode) + "\n")
raise SystemExit(result.returncode)
