#!/usr/bin/env bash
set -euo pipefail
map_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${OUTPUT_ROOT:?Run synthesis/run.sh, or set OUTPUT_ROOT to a prepared output directory}"
iverilog=${IVERILOG:-iverilog}
vvp=${VVP:-vvp}
out="$OUTPUT_ROOT/macro-map"
"$iverilog" -g2012 -DSYNTHESIS -s test_sram -o "$out/test_sram.vvp" \
  "$map_dir/test_sram.sv" "$out/chipyard_sram_macros.v" \
  "$map_dir/fakeram45_sim.v" "$out/gold_mems.v" \
  > "$out/compile.log" 2>&1
for seed in 1 827361 2147483647; do
  printf 'SEED=%s\n' "$seed"
  "$vvp" "$out/test_sram.vvp" "+SEED=$seed"
done | tee "$out/test_sram.log"
