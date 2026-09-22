#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == --help ]]; then
  printf '%s\n' 'Generate and synthesize the complete DualRocketConfig ChipTop.' \
    'Required: CHIPYARD_ROOT and either PLATFORM_ROOT or ORFS_ROOT.' \
    'Optional: OUTPUT_ROOT, GENERATED_DIR, OSS_CAD_SUITE_ROOT,' \
    'YOSYS, OPENROAD, IVERILOG, VVP, PYTHON, SLANG_PLUGIN.' \
    'OUTPUT_ROOT must not already exist. See README.md for scope and limitations.'
  exit 0
fi
[[ $# == 0 ]] || { printf 'Unexpected arguments; use --help.\n' >&2; exit 2; }
: "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to the generated Chipyard checkout}"
export CHIPYARD_ROOT
export GENERATED_DIR=${GENERATED_DIR:-"$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketConfig"}
export RTL_DIR="$GENERATED_DIR/gen-collateral"
export PLATFORM_ROOT=${PLATFORM_ROOT:-${ORFS_ROOT:+"$ORFS_ROOT/flow/platforms/nangate45"}}
: "${PLATFORM_ROOT:?Set PLATFORM_ROOT or ORFS_ROOT for Nangate45}"
export OUTPUT_ROOT=${OUTPUT_ROOT:-"$PWD/dual-rocket-synthesis"}
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
bash "$script_dir/macro-map/test.sh"
for stage in elaborate prepare map finalize; do
  printf 'Starting synthesis stage: %s\n' "$stage"
  (
    cd -- "$OUTPUT_ROOT"
    "$YOSYS" -Q -T -q -l "$stage.log" -s "$stage.ys" > "$stage.console.log" 2>&1
  )
done
"$OPENROAD" -exit -log "$OUTPUT_ROOT/openroad.log" "$script_dir/check.tcl" \
  > "$OUTPUT_ROOT/openroad.console.log" 2>&1
"$PYTHON" "$script_dir/summarize.py"
printf 'Full DualRocketConfig synthesis and OpenROAD linking completed: %s\n' "$OUTPUT_ROOT"
