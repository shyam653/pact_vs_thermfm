#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$here/common.sh"
configure_lint
verilator=$(resolve_executable "${VERILATOR:-verilator}")
out=$LINT_OUTPUT_ROOT/verilator
mkdir -p -- "$LINT_OUTPUT_ROOT"
mkdir -- "$out"
mkdir -- "$out/obj_dir"
cd -- "$out"
args=(--lint-only --top-module ChipTop -DSYNTHESIS --timescale 1ns/1ps
  -Wall -Wno-fatal --diagnostics-sarif
  --diagnostics-sarif-output "$out/diagnostics.sarif"
  --Mdir "$out/obj_dir" -y "$rtl" +libext+.sv+.v "$rtl/ChipTop.sv" "$mems")
record_provenance "$out" "$verilator" "${args[@]}"
record_sources "$out"
status=0
"$verilator" "${args[@]}" > "$out/lint.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$out/exit-code.txt"
if [[ -s "$out/diagnostics.sarif" ]]; then
  jq -e '(.runs | type == "array" and length > 0) and
    all(.runs[]; (.results | type == "array") and
      all(.results[]; .level | IN("error", "warning", "note", "none")))' \
    "$out/diagnostics.sarif" >/dev/null
  jq --argjson exit_code "$status" '{
    exit_code: $exit_code,
    errors: ([.runs[].results[] | select(.level == "error")] | length),
    warnings: ([.runs[].results[] | select(.level == "warning")] | length),
    notes: ([.runs[].results[] | select(.level == "note")] | length),
    warning_categories: ([.runs[].results[] | select(.level == "warning")]
      | group_by(.ruleId) | map({category: .[0].ruleId, count: length}))
  }' "$out/diagnostics.sarif" > "$out/summary.json"
else
  printf 'Verilator did not produce structured diagnostics.\n' >&2
  exit 1
fi
integrity_status=0
(cd -- "$rtl" && sha256sum --check --quiet "$out/source-sha256.txt") \
  > "$out/source-integrity.log" 2>&1 || integrity_status=$?
printf '%s\n' "$integrity_status" > "$out/source-integrity-exit-code.txt"
if (( integrity_status != 0 )); then exit "$integrity_status"; fi
if ! jq -e '.errors == 0' "$out/summary.json" >/dev/null; then exit 1; fi
exit "$status"
