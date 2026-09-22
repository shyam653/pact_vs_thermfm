export CY="$CHIPYARD_ROOT"
export RISCV="${RISCV:-$CY/.conda-env/riscv-tools}"
export PATH="$RISCV/bin:$CY/.conda-env/bin:$PATH"
export LD_LIBRARY_PATH="$RISCV/lib:$CY/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
