#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${CPU_ENV:?Set CPU_ENV}"
LIBGLOSS=$HERE/libgloss-src
BUILD=$HERE/libgloss-build
PINNED=39234a16247ab1fa234821b251f1f1870c3de343
if [[ ! -d "$LIBGLOSS/.git" ]]; then
  git clone --no-checkout https://github.com/ucb-bar/libgloss-htif.git "$LIBGLOSS"
  git -C "$LIBGLOSS" checkout --detach "$PINNED"
fi
[[ $(git -C "$LIBGLOSS" rev-parse HEAD) == "$PINNED" ]]
mkdir -p "$BUILD" "$HERE/logs" "$HERE/bin" "$HERE/disassembly"
cd "$BUILD"
if [[ ! -f Makefile ]]; then
  "$LIBGLOSS/configure" --host=riscv64-unknown-elf --disable-multilib \
    --prefix="$HERE/libgloss-stage" \
    CFLAGS='-O2 -march=rv64imafdc_zicsr_zifencei -mabi=lp64d' \
    > "$HERE/logs/libgloss-configure.log" 2>&1
fi
make -j2 > "$HERE/logs/libgloss-build.log" 2>&1
printf '0\n' > "$HERE/libgloss-build.exit-status"
cd "$HERE"
[[ -e "$HERE/htif.ld" ]] || ln -s "$LIBGLOSS/util/htif.ld" "$HERE/htif.ld"
printf 'test\tbinary\tsuite\n' > "$HERE/chipyard-manifest.tsv"
printf 'test\texit_status\tsource\n' > "$HERE/chipyard-build-results.tsv"
for name in hello cpp-hello mt-hello-dual; do
  compiler=riscv64-unknown-elf-gcc
  src=$CY/tests/$name.c
  specs=$LIBGLOSS/util/htif_nano.specs
  case $name in
    cpp-hello)
      compiler=riscv64-unknown-elf-g++
      src=$CY/tests/cpp-hello.cpp
      specs=$LIBGLOSS/util/htif.specs
      ;;
    mt-hello-dual) src=$HERE/mt-hello-dual.c ;;
  esac
  binary=$HERE/bin/chipyard-$name.riscv
  command=("$compiler" -O2 -Wall -Wextra -fno-common -fno-builtin-printf
    -march=rv64imafdc_zicsr_zifencei -mabi=lp64d -mcmodel=medany
    -I "$HERE/compat" -I "$RISCV/include" -I "$CY/tests"
    -specs="$specs" -static -L "$BUILD" -T "$LIBGLOSS/util/htif.ld"
    "$src" -o "$binary")
  status=0
  {
    printf '%q ' "${command[@]}"
    printf '\n'
    "${command[@]}"
  } > "$HERE/logs/chipyard-$name-resolved.log" 2>&1 || status=$?
  printf '%s\t%s\t%s\n' "$name" "$status" "$src" >> "$HERE/chipyard-build-results.tsv"
  if [[ $status == 0 ]]; then
    printf '%s\t%s\t%s\n' "chipyard-$name" "$binary" chipyard-generic >> "$HERE/chipyard-manifest.tsv"
    riscv64-unknown-elf-objdump -d "$binary" > "$HERE/disassembly/chipyard-$name.dump"
  fi
done
{
  date -u +%FT%TZ
  git -C "$LIBGLOSS" rev-parse HEAD
  git -C "$LIBGLOSS" status --short
  sha256sum "$HERE/build-chipyard.sh" "$HERE/mt-hello-dual.c" "$CY/tests/mt-hello.c" "$HERE/compat/riscv-pk/encoding.h"
  sha256sum "$HERE"/bin/chipyard-*.riscv
} > "$HERE/chipyard-provenance.txt"
cat "$HERE/chipyard-build-results.tsv"
