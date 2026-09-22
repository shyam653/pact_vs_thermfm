#!/usr/bin/env bash
# Build a published configuration using the pinned, provisioned Chipyard checkout.
set -euo pipefail
: "${CHIPYARD_ROOT:?Set CHIPYARD_ROOT to a provisioned Chipyard checkout}"
ip=$(realpath "${1:?Usage: build-soc.sh IP_DIRECTORY OUTPUT_DIRECTORY}")
out=$(realpath -m "${2:?Provide a new output directory}")
cy=$(realpath "$CHIPYARD_ROOT")
[[ ! -e "$out" ]] || { echo "Output already exists: $out" >&2; exit 1; }
[[ $(git -C "$cy" rev-parse HEAD) == e602d917dcc495c58cabe906535e411707096c9c ]] || {
  echo 'Unexpected Chipyard revision' >&2; exit 1;
}
mapfile -t configs < <(find "$ip/config" -maxdepth 1 -name '*.scala' -type f)
[[ ${#configs[@]} == 1 ]] || { echo 'Expected exactly one SoC configuration' >&2; exit 1; }
config=$(basename "${configs[0]}" .scala)
case "$config" in
  DualRocketFFTConfig) module=generators/fft-generator ;;
  DualRocketNVDLAConfig) module=generators/nvdla ;;
  *) echo "Unsupported configuration: $config" >&2; exit 1 ;;
esac
git -C "$cy" submodule update --init --recursive "$module"
expected_module=$(git -C "$cy" rev-parse "HEAD:$module")
[[ $(git -C "$cy/$module" rev-parse HEAD) == "$expected_module" ]] || {
  echo 'Accelerator revision differs from the pinned Chipyard HEAD gitlink' >&2; exit 1;
}
untracked_sources=$(git -C "$cy/$module" ls-files --others --exclude-standard -- \
  '*.scala' '*.sbt' '*.v' '*.sv' '*.vh' '*.svh')
[[ -z "$untracked_sources" ]] || {
  printf 'Untracked accelerator source files would enter the build:\n%s\n' "$untracked_sources" >&2
  exit 1
}
destination="$cy/generators/chipyard/src/main/scala/config/$config.scala"
if [[ -e "$destination" ]]; then
  cmp "${configs[0]}" "$destination" || { echo 'Existing configuration differs' >&2; exit 1; }
else
  cp "${configs[0]}" "$destination"
fi
mkdir -p "$out"
trap 'code=$?; printf "%s\n" "$code" > "$out/workflow.exit"' EXIT
# Compare the working tree against exactly HEAD plus the published patch set.
# A temporary index avoids changing the user's index or accepting unrelated edits.
index="$out/expected-generator.index"
GIT_INDEX_FILE="$index" git -C "$cy/$module" read-tree HEAD
shopt -s nullglob
patches=("$ip"/patches/*.patch)
for patch in "${patches[@]}"; do
  GIT_INDEX_FILE="$index" git -C "$cy/$module" apply --cached "$patch"
done
if ! GIT_INDEX_FILE="$index" git -C "$cy/$module" diff --quiet; then
  git -C "$cy/$module" diff --quiet || {
    echo 'Generator contains changes outside the published patch set' >&2; exit 1;
  }
  for patch in "${patches[@]}"; do git -C "$cy/$module" apply "$patch"; done
fi
GIT_INDEX_FILE="$index" git -C "$cy/$module" diff --exit-code
git -C "$cy/$module" diff HEAD --binary > "$out/generator.patch"
for patch in "${patches[@]}"; do sha256sum "$patch"; done > "$out/patches.sha256"
export RISCV=${RISCV:-"$cy/.conda-env/riscv-tools"}
export JAVA_HOME=${JAVA_HOME:-"$cy/.conda-env/lib/jvm"}
export PATH="$JAVA_HOME/bin:$RISCV/bin:$cy/.conda-env/bin:$PATH"
export LD_LIBRARY_PATH="$RISCV/lib:$cy/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$cy/.java_tmp"
export JAVA_TOOL_OPTIONS=${JAVA_TOOL_OPTIONS:-"-Xmx8G -Xss8M -Djava.io.tmpdir=$cy/.java_tmp"}
unset USE_CHISEL7
{
  date -u '+started_utc=%FT%TZ'
  printf 'config=%s\n' "$config"
  git -C "$cy" rev-parse HEAD
  git -C "$cy" status --short
  git -C "$cy" submodule status --recursive
  sha256sum "${configs[0]}" "$cy/build.sbt" "${BASH_SOURCE[0]}"
  java -version
  verilator --version
  riscv64-unknown-elf-gcc --version
} > "$out/provenance.txt" 2>&1
cp "${configs[0]}" "$out/"
set +e
/usr/bin/time -v make -C "$cy/sims/verilator" verilog CONFIG="$config" -j"${JOBS:-2}" > "$out/generation.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/generation.exit"
[[ $rc == 0 ]] || exit "$rc"
set +e
/usr/bin/time -v make -C "$cy/sims/verilator" CONFIG="$config" -j"${JOBS:-2}" > "$out/simulator-build.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/simulator-build.exit"
[[ $rc == 0 ]] || exit "$rc"
sha256sum "$cy/sims/verilator/simulator-chipyard.harness-$config" > "$out/simulator.sha256"
date -u '+finished_utc=%FT%TZ' >> "$out/provenance.txt"
