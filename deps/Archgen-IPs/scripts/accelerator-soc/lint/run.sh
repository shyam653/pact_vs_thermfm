#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$here/common.sh"
configure_lint
for dependency in jq rg sha256sum git; do command -v "$dependency" >/dev/null; done
command -v "${VERILATOR:-verilator}" >/dev/null
command -v "${SLANG:-slang}" >/dev/null
mkdir -p -- "$(dirname -- "$LINT_OUTPUT_ROOT")"
mkdir -- "$LINT_OUTPUT_ROOT"
python3 "$here/../source_plan.py" --generated-dir "$GENERATED_DIR" --config "$CONFIG" \
  --output "$LINT_OUTPUT_ROOT/source-plan.json"

# Sequential by default: accelerator designs can exceed this host's RAM in parallel.
verilator_status=0
slang_status=0
bash "$here/verilator.sh" || verilator_status=$?
bash "$here/slang.sh" || slang_status=$?
printf 'Verilator workflow exit: %s; slang workflow exit: %s\n' "$verilator_status" "$slang_status"
jq -n --argjson verilator "$verilator_status" --argjson slang "$slang_status" \
  '{verilator: $verilator, slang: $slang}' > "$LINT_OUTPUT_ROOT/workflow-exits.json"
if [[ -f "$LINT_OUTPUT_ROOT/verilator/summary.json" && -f "$LINT_OUTPUT_ROOT/slang/summary.json" ]]; then
  jq -n --slurpfile verilator "$LINT_OUTPUT_ROOT/verilator/summary.json" \
    --slurpfile slang "$LINT_OUTPUT_ROOT/slang/summary.json" \
    '{verilator: $verilator[0], slang: $slang[0]}' > "$LINT_OUTPUT_ROOT/summary.json"
  if [[ -n ${LINT_BASELINE_ROOT:-} ]]; then bash "$here/compare.sh"; fi
fi
if (( verilator_status != 0 || slang_status != 0 )); then exit 1; fi
