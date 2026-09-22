#!/usr/bin/env bash
set -euo pipefail

: "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to the pinned, provisioned Chipyard checkout}"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
CHIPYARD_ROOT=$(cd -- "$CHIPYARD_ROOT" && pwd)
out=${GENERATION_OUTPUT_ROOT:-"$root/build/dual-rocket/generation"}
mkdir -p "$out"
out=$(cd -- "$out" && pwd)
if [[ -e "$out/provenance.txt" ]]; then
    printf 'Refusing to overwrite generation evidence: %s\n' "$out" >&2
    exit 1
fi
expected=e602d917dcc495c58cabe906535e411707096c9c
actual=$(git -C "$CHIPYARD_ROOT" rev-parse HEAD)
[[ "$actual" == "$expected" ]] || { printf 'Unexpected Chipyard revision: %s\n' "$actual" >&2; exit 1; }
[[ -z "$(git -C "$CHIPYARD_ROOT" status --porcelain --untracked-files=no)" ]] || {
    printf 'Chipyard tracked sources are dirty; refusing an ambiguous generation.\n' >&2
    exit 1
}
trap 'code=$?; printf "%s\n" "$code" > "$out/exit-code.txt"' EXIT
unset USE_CHISEL7
export JAVA_TOOL_OPTIONS=${JAVA_TOOL_OPTIONS:-"-Xmx8G -Xss8M"}
{
    date -u '+started_utc=%FT%TZ'
    printf 'chipyard=%s\nCONFIG=DualRocketConfig\nMODEL=TestHarness\nTOP=ChipTop\n' "$actual"
    git -C "$CHIPYARD_ROOT" submodule status
    java -version
    firtool --version
} > "$out/provenance.txt" 2>&1
set +e
/usr/bin/time -v make -C "$CHIPYARD_ROOT/sims/verilator" verilog CONFIG=DualRocketConfig -j"${JOBS:-2}" > "$out/generation.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/make-exit-code.txt"
[[ "$rc" == 0 ]] || exit "$rc"
rtl="$CHIPYARD_ROOT/sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketConfig/gen-collateral"
set +e
(cd -- "$rtl" && sha256sum --check --quiet "$root/docs/dual-rocket/artifacts/rtl.sha256") > "$out/source-check.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/source-check-exit-code.txt"
[[ "$rc" == 0 ]] || exit "$rc"
(
    cd -- "$rtl"
    LC_ALL=C find . -maxdepth 1 -type f \( -name '*.sv' -o -name '*.v' \) -printf '%f\n' | LC_ALL=C sort | xargs sha256sum
) > "$out/rtl.sha256"
cmp "$root/docs/dual-rocket/artifacts/rtl.sha256" "$out/rtl.sha256" > "$out/inventory-check.log" 2>&1
printf 'Generation and published RTL hash check passed. Evidence: %s\n' "$out"
