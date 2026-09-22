#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == --help ]]; then
  printf '%s\n' 'Generate and synthesize the complete configured ChipTop.' \
    'Required: CONFIG, CHIPYARD_ROOT and either PLATFORM_ROOT or ORFS_ROOT.' \
    'Optional: OUTPUT_ROOT, GENERATED_DIR, OSS_CAD_SUITE_ROOT,' \
    'YOSYS, OPENROAD, IVERILOG, VVP, PYTHON, SLANG_PLUGIN, ABC_MODE.' \
    'OUTPUT_ROOT must not already exist. See README.md for scope and limitations.'
  exit 0
fi
[[ $# == 0 ]] || { printf 'Unexpected arguments; use --help.\n' >&2; exit 2; }
: "${CONFIG:?Set CONFIG to the generated Scala configuration class}"
export CONFIG
export SYNTHESIS_MODE=${SYNTHESIS_MODE:-mapped}
case $SYNTHESIS_MODE in mapped|preserve-memories) ;; *) printf 'Unknown SYNTHESIS_MODE: %s\n' "$SYNTHESIS_MODE" >&2; exit 2 ;; esac
export ABC_MODE=${ABC_MODE:-default}
case $ABC_MODE in default|direct) ;; *) printf 'Unknown ABC_MODE: %s\n' "$ABC_MODE" >&2; exit 2 ;; esac
: "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to the generated Chipyard checkout}"
export CHIPYARD_ROOT
export GENERATED_DIR=${GENERATED_DIR:-"$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.$CONFIG"}
export RTL_DIR="$GENERATED_DIR/gen-collateral"
export PLATFORM_ROOT=${PLATFORM_ROOT:-${ORFS_ROOT:+"$ORFS_ROOT/flow/platforms/nangate45"}}
: "${PLATFORM_ROOT:?Set PLATFORM_ROOT or ORFS_ROOT for Nangate45}"
export OUTPUT_ROOT=${OUTPUT_ROOT:-"${IP_DIR:-$PWD}/build/$CONFIG-synthesis"}
export SLANG_PLUGIN=${SLANG_PLUGIN:-slang}
export YOSYS=${YOSYS:-${OSS_CAD_SUITE_ROOT:+"$OSS_CAD_SUITE_ROOT/bin/"}yosys}
export IVERILOG=${IVERILOG:-${OSS_CAD_SUITE_ROOT:+"$OSS_CAD_SUITE_ROOT/bin/"}iverilog}
export VVP=${VVP:-${OSS_CAD_SUITE_ROOT:+"$OSS_CAD_SUITE_ROOT/bin/"}vvp}
export OPENROAD=${OPENROAD:-openroad}
export PYTHON=${PYTHON:-python3}
for tool in "$YOSYS" "$OPENROAD" "$IVERILOG" "$VVP" "$PYTHON"; do
  command -v -- "$tool" >/dev/null || { printf 'Missing tool: %s\n' "$tool" >&2; exit 2; }
done

# Preparation refuses an existing output directory and never edits source RTL.
"$PYTHON" "$script_dir/prepare.py"
OUTPUT_ROOT=$(cd -- "$OUTPUT_ROOT" && pwd)
export OUTPUT_ROOT
trap 'code=$?; printf "exit_status=%s\n" "$code" > "$OUTPUT_ROOT/run-status.txt"' EXIT
# An EXIT trap alone can observe a prior status zero on asynchronous termination.
# Make interrupted runs unambiguously unsuccessful while preserving their logs.
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
{
  date -u +%FT%TZ
  "$YOSYS" -V
  "$OPENROAD" -version
  "$IVERILOG" -V
  "$VVP" -V
} > "$OUTPUT_ROOT/tool-versions.txt" 2>&1
(
  cd -- "$OUTPUT_ROOT"
  "$YOSYS" -Q -T -q -l preflight.log -s preflight.ys > preflight.console.log 2>&1
)
# Check the flattened macro frontend early: it exposes missing submodule inputs
# that a hierarchical frontend can retain as unconnected instance ports.
for stage in prepare elaborate; do
  printf 'Starting synthesis stage: %s\n' "$stage"
  (
    cd -- "$OUTPUT_ROOT"
    "$YOSYS" -Q -T -q -l "$stage.log" -s "$stage.ys" > "$stage.console.log" 2>&1
  )
done
bash "$script_dir/macro-map/test.sh"
"$PYTHON" "$script_dir/audit-memories.py"
for stage in map finalize; do
  printf 'Starting synthesis stage: %s\n' "$stage"
  (
    cd -- "$OUTPUT_ROOT"
    "$YOSYS" -Q -T -q -l "$stage.log" -s "$stage.ys" > "$stage.console.log" 2>&1
  )
done
if [[ $SYNTHESIS_MODE == mapped ]]; then
  export EXPECTED_SRAM_MACROS
  EXPECTED_SRAM_MACROS=$("$PYTHON" -c 'import json, os; print(json.load(open(os.environ["OUTPUT_ROOT"]+"/macro-map/inventory.json"))["physical_macro_instances"])')
  "$OPENROAD" -exit -log "$OUTPUT_ROOT/openroad.log" "$script_dir/check.tcl" \
    > "$OUTPUT_ROOT/openroad.console.log" 2>&1
fi
"$PYTHON" "$script_dir/summarize.py"
printf 'Full %s synthesis completed (mode %s): %s\n' "$CONFIG" "$SYNTHESIS_MODE" "$OUTPUT_ROOT"
