#!/usr/bin/env bash

configure_lint() {
  : "${CONFIG:?Set CONFIG to the generated Scala configuration class}"
  export CONFIG
  : "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to the Chipyard checkout containing generated SoC RTL}"
  CHIPYARD_ROOT=$(cd -- "$CHIPYARD_ROOT" && pwd)
  LINT_OUTPUT_ROOT=${LINT_OUTPUT_ROOT:-"${IP_DIR:-$PWD}/build/$CONFIG-lint"}
  case $LINT_OUTPUT_ROOT in /*) ;; *) LINT_OUTPUT_ROOT=$PWD/$LINT_OUTPUT_ROOT ;; esac
  export CHIPYARD_ROOT LINT_OUTPUT_ROOT
  GENERATED_DIR=${GENERATED_DIR:-"$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.$CONFIG"}
  GENERATED_DIR=$(cd -- "$GENERATED_DIR" && pwd)
  export GENERATED_DIR
  rtl=$GENERATED_DIR/gen-collateral
  mems=$rtl/chipyard.harness.TestHarness.$CONFIG.top.mems.v
  extra_sources=()
  if [[ -f "$LINT_OUTPUT_ROOT/source-plan.json" ]]; then
    mapfile -t extra_sources < <(jq -r '.extra_sources[]' "$LINT_OUTPUT_ROOT/source-plan.json")
  fi
  [[ -s "$rtl/ChipTop.sv" && -s "$mems" ]] || {
    printf 'Missing generated ChipTop or original behavioral memory RTL: %s\n' "$rtl" >&2
    return 1
  }
}

resolve_executable() {
  local executable
  executable=$(command -v "$1")
  case $executable in /*) ;; *) executable=$PWD/$executable ;; esac
  printf '%s\n' "$executable"
}

record_sources() {
  local output=$1
  (
    cd -- "$rtl"
    rg --files --no-ignore -g '*.sv' -g '*.v' | LC_ALL=C sort |
      while IFS= read -r file; do sha256sum -- "$file"; done
  ) > "$output/source-sha256.txt"
  local status=0
  (
    cd -- "$rtl"
    rg -n 'lint_(off|on)' -g '*.sv' -g '*.v' .
  ) > "$output/source-lint-directives.txt" || status=$?
  [[ $status == 0 || $status == 1 ]]
}

record_provenance() {
  local output=$1 executable=$2
  shift 2
  local version commit dirty=false
  version=$("$executable" --version)
  commit=$(git -C "$CHIPYARD_ROOT" rev-parse HEAD)
  [[ -z $(git -C "$CHIPYARD_ROOT" status --porcelain --untracked-files=no) ]] || dirty=true
  jq -n --arg started_utc "$(date -u +%FT%TZ)" \
    --arg chipyard_root "$CHIPYARD_ROOT" --arg source_commit "$commit" \
    --argjson source_tracked_changes "$dirty" --arg rtl_root "$rtl" \
    --arg executable "$executable" --arg tool_version "$version" \
    --arg executable_sha256 "$(sha256sum -- "$executable" | cut -d ' ' -f 1)" \
    --arg config "$CONFIG" \
    --args '{started_utc: $started_utc, chipyard_root: $chipyard_root,
      source_commit: $source_commit, source_tracked_changes: $source_tracked_changes,
      rtl_root: $rtl_root, executable: $executable, tool_version: $tool_version,
      executable_sha256: $executable_sha256, top: "ChipTop", config: $config,
      defines: ["SYNTHESIS"], default_timescale: "1ns/1ps",
      memories: "original behavioral RTL", command: $ARGS.positional}' \
    -- "$executable" "$@" > "$output/provenance.json"
}
