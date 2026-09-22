# Supplemental engine simulation

Both archived runs passed 22 numerical jobs: 16 SDP arithmetic jobs,
2 CDP lookup jobs, 2 INT8 convolution jobs and 2 max/min pooling jobs.
Verilator used randomized initial state with seeds 1 and 17. The AXI model
injects periodic read/write/address backpressure. See `summary.json` for
source/RTL/executable hashes and the exact scope.

This model instantiates only `nvdla_small`, with an APB driver and an AXI
memory model. The interrupt-controller behavior is emulated. These results
do not establish Rocket software execution, PLIC integration or cache
coherence; those require the same jobs to pass in the full IP3 SoC simulator.

`build.log` retains upstream RTL diagnostics. `final-harness-build.log`
records recompilation/relinking of the final reset-safe harness. The initial
reset handling mistake and its correction are recorded in `summary.json`.
No engine numerical mismatch was waived or converted to a passing result.
