#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${CPU_ENV:?Set CPU_ENV}"
TESTS=$CY/toolchains/riscv-tools/riscv-tests
BM=$TESTS/benchmarks
mkdir -p "$HERE/bin" "$HERE/logs" "$HERE/disassembly" "$HERE/patches"
cd "$HERE"

record_patch() {
  local before=$1 after=$2 label=$3 status=0
  diff -u --label "a/$label" --label "b/$label" "$before" "$after" > "$HERE/patches/$(basename "$label").patch" || status=$?
  [[ $status == 0 || $status == 1 ]]
}
record_patch "$TESTS/mt/vvadd1.c" "$HERE/vvadd1.c" mt/vvadd1.c
record_patch "$BM/mt-matmul/mt-matmul.c" "$HERE/mt-matmul.c" benchmarks/mt-matmul/mt-matmul.c
OPTS=(-DPREALLOCATE=1 -mcmodel=medany -static -std=gnu99 -O2 -ffast-math
  -fno-common -fno-builtin-printf -fno-tree-loop-distribute-patterns
  -Wno-implicit-int -Wno-implicit-function-declaration
  -march=rv64imafdc_zicsr_zifencei -mabi=lp64d
  -I "$TESTS/env" -I "$BM/common")
LINK=(-static -nostdlib -nostartfiles -lm -lgcc -T "$BM/common/test.ld")
printf 'test\tbinary\tsuite\n' > "$HERE/manifest.tsv"
printf 'test\texit_status\tkernel\tharness\n' > "$HERE/build-results.tsv"
failed=0

build_one() {
  local name=$1 kernel=$2 harness=$3 includes=$4
  local binary=$HERE/bin/$name.riscv
  local command=(riscv64-unknown-elf-gcc "${OPTS[@]}" -I "$includes"
    -o "$binary" "$kernel" "$harness" "$BM/common/syscalls.c"
    "$HERE/../crt-dual.S" "${LINK[@]}")
  local status=0
  {
    printf '%q ' "${command[@]}"
    printf '\n'
    "${command[@]}"
  } > "$HERE/logs/$name.log" 2>&1 || status=$?
  printf '%s\t%s\t%s\t%s\n' "$name" "$status" "$kernel" "$harness" >> "$HERE/build-results.tsv"
  if [[ $status == 0 ]]; then
    printf '%s\t%s\t%s\n' "$name" "$binary" corrected-mt-supplement >> "$HERE/manifest.tsv"
    riscv64-unknown-elf-objdump -d "$binary" > "$HERE/disassembly/$name.dump"
  else
    failed=1
  fi
}

build_one corrected-legacy-vvadd1-dual "$HERE/vvadd1.c" "$BM/mt-vvadd/mt-vvadd.c" "$BM/mt-vvadd"
build_one corrected-mt-matmul-dual "$BM/mt-matmul/matmul.c" "$HERE/mt-matmul.c" "$BM/mt-matmul"
build_one corrected-legacy-ae_matmul-dual "$TESTS/mt/ae_matmul.c" "$HERE/mt-matmul.c" "$BM/mt-matmul"

{
  date -u +%FT%TZ
  git -C "$TESTS" rev-parse HEAD
  git -C "$TESTS" status --short
  riscv64-unknown-elf-gcc --version
} > "$HERE/provenance.txt"
sha256sum "$HERE/build.sh" "$HERE/vvadd1.c" "$HERE/mt-matmul.c" \
  "$TESTS/mt/vvadd1.c" "$TESTS/mt/ae_matmul.c" \
  "$BM/mt-matmul/matmul.c" "$BM/mt-matmul/mt-matmul.c" \
  "$BM/mt-matmul/dataset.h" "$BM/mt-vvadd/mt-vvadd.c" "$BM/mt-vvadd/dataset.h" \
  "$BM/common/syscalls.c" "$BM/common/util.h" "$BM/common/test.ld" \
  "$HERE/../crt-dual.S" > "$HERE/source-sha256.txt"
sha256sum "$HERE"/bin/*.riscv > "$HERE/binary-sha256.txt"
sha256sum --check --quiet "$HERE/../binary-sha256.txt" > "$HERE/original-binary-integrity.log" 2>&1
cat "$HERE/build-results.tsv"
exit "$failed"
