#!/usr/bin/env bash
set -e

ORFS_DIR="/home/boson4/diffusion/external/OpenROAD-flow-scripts/flow"
export PATH="/home/boson4/diffusion/envs/eda/bin:/home/boson4/.local/bin:$PATH"

export FLOW_HOME="$ORFS_DIR"
export DESIGN_CONFIG="$ORFS_DIR/designs/sky130hd/ibex/config.mk"
export DESIGN_NAME="ibex_core"
export PLATFORM="sky130hd"
export RESULTS_DIR="$ORFS_DIR/results/sky130hd/ibex/base"
export LOG_DIR="$ORFS_DIR/logs/sky130hd/ibex/base"
export REPORTS_DIR="$ORFS_DIR/reports/sky130hd/ibex/base"
export OBJECTS_DIR="$ORFS_DIR/objects/sky130hd/ibex/base"
export SCRIPTS_DIR="$ORFS_DIR/scripts"
export UTILS_DIR="$ORFS_DIR/utils"
export PYTHON_EXE="python3"

export LIB_FILES="$ORFS_DIR/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
export TECH_LEF="$ORFS_DIR/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef"
export SC_LEF="$ORFS_DIR/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef"
export SYNTH_SCRIPT="$ORFS_DIR/scripts/synth.tcl"
export ABC_DRIVER_CELL="sky130_fd_sc_hd__buf_1"
export ABC_LOAD_IN_FF="10"
export MIN_BUF_CELL_AND_PORTS="sky130_fd_sc_hd__buf_1 A X"
export TIEHI_CELL_AND_PORT="sky130_fd_sc_hd__conb_1 HI"
export TIELO_CELL_AND_PORT="sky130_fd_sc_hd__conb_1 LO"
export SYNTH_INSBUF=1
export SYNTH_WRAPPED_OPERATORS=0
export SWAP_ARITH_OPERATORS=0
export LATCH_MAP_FILE="$ORFS_DIR/platforms/sky130hd/cells_latch_hd.v"
export CLKGATE_MAP_FILE="$ORFS_DIR/platforms/sky130hd/cells_clkgate_hd.v"
export ADDER_MAP_FILE="$ORFS_DIR/platforms/sky130hd/cells_adders_hd.v"
export DFF_MAP_FILE=""
export DFF_LIB_FILE=""
export POS_CLKGATE_AND_PORTS=""
export NEG_CLKGATE_AND_PORTS=""

export KEEP_VARS=0
export SYNTH_HIERARCHICAL=0
export SYNTH_HIER_SEPARATOR="/"
export SYNTH_GUT=0
export SYNTH_MOCK_LARGE_MEMORIES=0
export SYNTH_KEEP_MOCKED_MEMORIES=0
export SYNTH_MEMORY_MAX_BITS=65536
export SYNTH_MINIMUM_KEEP_SIZE=0
export SYNTH_SKIP_KEEP=0
export SYNTH_BLACKBOXES=""
export SYNTH_CHECKPOINT=""
export SYNTH_KEEP_MODULES=""
export SYNTH_OPERATIONS_ARGS=""
export SYNTH_RETIME_MODULES=""
export ABC_AREA=0
export RECOVER_POWER=0

mkdir -p "$RESULTS_DIR" "$LOG_DIR" "$REPORTS_DIR" "$OBJECTS_DIR"

echo "[Ibex Synth] Running Yosys synthesis..."
yosys -c "$SYNTH_SCRIPT" 2>&1 | tee "$LOG_DIR/1_2_yosys.log"
echo "[Ibex Synth] Synthesis complete! Check $RESULTS_DIR/1_2_yosys.v"
