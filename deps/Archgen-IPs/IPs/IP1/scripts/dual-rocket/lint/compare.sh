#!/usr/bin/env bash
set -euo pipefail
: "${LINT_OUTPUT_ROOT:?Set LINT_OUTPUT_ROOT to the completed lint output}"
: "${LINT_BASELINE_ROOT:?Set LINT_BASELINE_ROOT to the previous lint output}"
jq -n --slurpfile baseline_verilator "$LINT_BASELINE_ROOT/verilator/diagnostics.sarif" \
  --slurpfile baseline_slang "$LINT_BASELINE_ROOT/slang/summary.json" \
  --slurpfile current_verilator "$LINT_OUTPUT_ROOT/verilator/summary.json" \
  --slurpfile current_slang "$LINT_OUTPUT_ROOT/slang/summary.json" '
  def compare($before; $after): {
    baseline_warnings: $before.warnings, current_warnings: $after.warnings,
    warning_delta: ($after.warnings - $before.warnings),
    current_errors: $after.errors, current_exit_code: $after.exit_code,
    rules: ([$before.warning_categories[].category, $after.warning_categories[].category]
      | unique | map(. as $category | {
        category: $category,
        baseline: ([$before.warning_categories[] | select(.category == $category) | .count][0] // 0),
        current: ([$after.warning_categories[] | select(.category == $category) | .count][0] // 0)
      } | . + {delta: (.current - .baseline)}))
  };
  ($baseline_verilator[0] | {
    warnings: ([.runs[].results[] | select(.level == "warning")] | length),
    warning_categories: ([.runs[].results[] | select(.level == "warning")]
      | group_by(.ruleId) | map({category: .[0].ruleId, count: length}))
  }) as $before |
  {verilator: compare($before; $current_verilator[0]),
   slang: compare($baseline_slang[0]; $current_slang[0])}
' > "$LINT_OUTPUT_ROOT/comparison.json"
