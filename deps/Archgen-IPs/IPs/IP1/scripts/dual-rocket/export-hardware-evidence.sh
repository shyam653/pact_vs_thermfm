#!/usr/bin/env bash
set -euo pipefail

: "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to the checkout used for generation}"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
prefix=chipyard.harness.TestHarness.DualRocketConfig
generated="$CHIPYARD_ROOT/sims/verilator/generated-src/$prefix"
out=${HARDWARE_EVIDENCE_ROOT:-"$root/docs/dual-rocket/artifacts"}
[[ ! -e "$out" ]] || { printf 'Refusing to overwrite evidence: %s\n' "$out" >&2; exit 1; }
[[ $(git -C "$CHIPYARD_ROOT" rev-parse HEAD) == e602d917dcc495c58cabe906535e411707096c9c ]]
jq -e '.cpus | has("cpu@0") and has("cpu@1") and (has("cpu@2") | not)' "$generated/$prefix.json" >/dev/null
mkdir -p "$out"
out=$(cd -- "$out" && pwd)
for suffix in dts json memmap.json l2.json top.mems.conf; do
    cp -- "$generated/$prefix.$suffix" "$out/$prefix.$suffix"
done
(
    cd -- "$generated/gen-collateral"
    LC_ALL=C find . -maxdepth 1 -type f \( -name '*.sv' -o -name '*.v' \) -printf '%f\n' |
        LC_ALL=C sort | while IFS= read -r file; do sha256sum -- "$file"; done
) > "$out/rtl.sha256"
[[ $(wc -l < "$out/rtl.sha256") == 476 ]]
(
    cd -- "$out"
    sha256sum -- "$prefix.dts" "$prefix.json" "$prefix.memmap.json" "$prefix.l2.json" "$prefix.top.mems.conf" rtl.sha256
) > "$out/artifacts.sha256"
printf 'Exported hardware metadata and 476 RTL hashes: %s\n' "$out"
