#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${CPU_ENV:?Set CPU_ENV}"
TESTS=$CY/toolchains/riscv-tools/riscv-tests
BM=$TESTS/benchmarks
CFG=$CY/sims/verilator/generated-src/chipyard.harness.TestHarness.${CONFIG}/chipyard.harness.TestHarness.${CONFIG}.d
mkdir -p "$HERE/bin" "$HERE/logs" "$HERE/disassembly"
cd "$HERE"

{
  date -u +%FT%TZ
  git -C "$CY" rev-parse HEAD
  git -C "$TESTS" rev-parse HEAD
  git -C "$TESTS" status --short
  riscv64-unknown-elf-gcc --version
  printf 'Source: %s\nGenerated configuration: %s\n' "$TESTS" "$CFG"
} > "$HERE/provenance.txt"
make --no-print-directory -s -f "$BM/Makefile" -f "$HERE/inventory.mk" print-benchmarks > "$HERE/available-benchmarks.txt"
make --no-print-directory -s -f "$TESTS/mt/Makefile" -f "$HERE/inventory.mk" print-benchmarks XLEN=64 > "$HERE/available-mt.txt"
make --no-print-directory -s -f "$CFG" -f "$HERE/inventory.mk" print-configured-benchmarks > "$HERE/configured-benchmarks.txt"
printf 'test\tsuite\texit_status\tbinary\tsource\tharts_admitted\n' > "$HERE/build-results.tsv"
printf 'test\tsuite\tbinary\tsource\tharts_admitted\n' > "$HERE/runnable-manifest.tsv"
printf 'test\tbinary\tsuite\n' > "$HERE/manifest.tsv"
: > "$HERE/runnable-binaries.txt"
printf 'test\treason\n' > "$HERE/excluded.tsv"
OPTS=(-DPREALLOCATE=1 -mcmodel=medany -static -std=gnu99 -O2 -ffast-math
  -fno-common -fno-builtin-printf -fno-tree-loop-distribute-patterns
  -Wno-implicit-int -Wno-implicit-function-declaration
  -march=rv64imafdc_zicsr_zifencei -mabi=lp64d
  -I "$TESTS/env" -I "$BM/common")
LINK=(-static -nostdlib -nostartfiles -lm -lgcc -T "$BM/common/test.ld")

build_one() {
  local name=$1 suite=$2 source=$3 harts=$4 crt=$5
  shift 5
  local binary=$HERE/bin/$name.riscv
  local command=(riscv64-unknown-elf-gcc "${OPTS[@]}" -o "$binary"
    "$@" "$BM/common/syscalls.c" "$crt" "${LINK[@]}")
  local status=0
  {
    printf '%q ' "${command[@]}"
    printf '\n'
    "${command[@]}"
  } > "$HERE/logs/$name.log" 2>&1 || status=$?
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$suite" "$status" "$binary" "$source" "$harts" >> "$HERE/build-results.tsv"
  if [[ $status == 0 ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$suite" "$binary" "$source" "$harts" >> "$HERE/runnable-manifest.tsv"
    printf '%s\t%s\t%s\n' "$name" "$binary" "$suite" >> "$HERE/manifest.tsv"
    printf '%s\n' "$binary" >> "$HERE/runnable-binaries.txt"
    riscv64-unknown-elf-objdump -d "$binary" > "$HERE/disassembly/$name.dump"
  fi
}

shopt -s nullglob
while IFS= read -r name; do
  if [[ $name == vec-* ]]; then
    printf '%s\tRequires the RISC-V V extension; selected SoC DTS has no V extension.\n' "$name" >> "$HERE/excluded.tsv"
    continue
  fi
  suite=benchmark-extra
  while IFS= read -r configured; do
    [[ $configured == "$name.riscv" ]] && suite=benchmark-configured
  done < "$HERE/configured-benchmarks.txt"
  build_one "$name" "$suite" "$BM/$name" 1 "$BM/common/crt.S" \
    -I "$BM/$name" "$BM/$name"/*.c "$BM/$name"/*.S
done < "$HERE/available-benchmarks.txt"

for name in mt-vvadd mt-matmul mt-memcpy; do
  build_one "$name-dual" benchmark-dual "$BM/$name" 2 "$HERE/crt-dual.S" \
    -I "$BM/$name" "$BM/$name"/*.c "$BM/$name"/*.S
done

while IFS= read -r name; do
  if [[ $name == vvadd* ]]; then
    harness=mt-vvadd
  else
    harness=mt-matmul
  fi
  build_one "legacy-$name-dual" legacy-mt "$TESTS/mt/$name.c" 2 "$HERE/crt-dual.S" \
    -I "$BM/$harness" "$TESTS/mt/$name.c" "$BM/$harness/$harness.c"
done < "$HERE/available-mt.txt"

sha256sum "$HERE"/bin/*.riscv > "$HERE/binary-sha256.txt"
sha256sum "$HERE/build.sh" "$HERE/crt-dual.S" "$BM/common/crt.S" "$CFG" > "$HERE/build-input-sha256.txt"
printf 'Runnable binaries: '
wc -l < "$HERE/runnable-binaries.txt"
printf 'Build failures: '
awk -F '\t' 'NR>1 && $3 != 0 {n++} END {print n+0}' "$HERE/build-results.tsv"
