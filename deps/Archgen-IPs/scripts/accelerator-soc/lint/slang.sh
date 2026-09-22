#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$here/common.sh"
configure_lint
slang=$(resolve_executable "${SLANG:-slang}")
out=$LINT_OUTPUT_ROOT/slang
mkdir -p -- "$LINT_OUTPUT_ROOT"
mkdir -- "$out"
cd -- "$CHIPYARD_ROOT"
args=(--top ChipTop -D SYNTHESIS -Wextra --timescale 1ns/1ps
  --diag-abs-paths --error-limit 0 --diag-json "$out/diagnostics.json"
  --time-stats "$out/time-stats.json" --Mmodule "$out/module-dependencies.txt"
  -y "$rtl" -Y .sv -Y .v "$rtl/ChipTop.sv" "$mems" "${extra_sources[@]}")
record_provenance "$out" "$slang" "${args[@]}"
record_sources "$out"
status=0
"$slang" "${args[@]}" > "$out/lint.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$out/exit-code.txt"
if [[ -s "$out/diagnostics.json" ]]; then
  jq -e 'type == "array" and
    all(.[]; .severity | IN("error", "fatal", "warning", "note"))' \
    "$out/diagnostics.json" >/dev/null
  jq --argjson exit_code "$status" '{
    exit_code: $exit_code,
    errors: ([.[] | select(.severity == "error" or .severity == "fatal")] | length),
    warnings: ([.[] | select(.severity == "warning")] | length),
    notes: ([.[] | select(.severity == "note")] | length),
    warning_categories: ([.[] | select(.severity == "warning")]
      | group_by(.optionName) | map({category: .[0].optionName, count: length}))
  }' "$out/diagnostics.json" > "$out/summary.json"
else
  printf 'slang did not produce structured diagnostics.\n' >&2
  exit 1
fi
if [[ -f "$out/module-dependencies.txt" ]]; then
  while IFS= read -r file; do sha256sum -- "$file"; done \
    < "$out/module-dependencies.txt" > "$out/dependency-sha256.txt"
fi
integrity_status=0
(cd -- "$rtl" && sha256sum --check --quiet "$out/source-sha256.txt") \
  > "$out/source-integrity.log" 2>&1 || integrity_status=$?
printf '%s\n' "$integrity_status" > "$out/source-integrity-exit-code.txt"
if (( integrity_status != 0 )); then exit "$integrity_status"; fi
if ! jq -e '.errors == 0' "$out/summary.json" >/dev/null; then exit 1; fi
exit "$status"
