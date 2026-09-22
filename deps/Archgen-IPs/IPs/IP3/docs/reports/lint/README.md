# Corrected full-SoC lint evidence

`DualRocketNVDLAConfig`, top `ChipTop`: **0 errors** in both tools. Verilator reports **5,944 warnings**; slang reports **86 warnings and 23 notes**. Both exit zero and source-integrity checks pass on all 529 published HDL files. Verilator uses the recorded `--max-num-width 1048576`, matching Chipyard's native Makefile for the wide generated TileLink monitor constants.

Patch 0003 defines the six absent SDP LUT readback inputs with typed zeros. This removes six missing-input warnings and addresses the 176 undriven bits found by the required flattened synthesis CHECK on the earlier RTL. The small SDP LUT datapath remains absent; the separate CDP LUT remains implemented. Earlier lint and failed synthesis evidence are retained as history and are superseded for the corrected source.

The remaining warning message multiset is unchanged. All 852 messages saying “not driven” also explicitly say “nor used.” Slang reports zero unconnected inputs and 63 unconnected outputs. The five implicit nets are unused constant tieoffs for the absent CVSRAM interface. Active DBB address upper bits and AXI burst/sideband metadata have explicit definitions from patches 0001 and 0002.

All 1,592 width warnings occur in bundled NVIDIA RTL: 937 truncations assign unsized X constants, 64 expand X/Z constants, and 591 concern ordinary extension. Reviewed MCIF address/outstanding-count arithmetic, SDP mask population counts and CSB register decoding use the expected widening; no width warning points to the integration wrapper or external bridge. Exact examples and locations are in `warning-triage.json`.

The single latch warning is the inherited debug clock-gate enable latch in `EICG_wrapper.v`, byte-identical to IP1/IP2. No NVDLA datapath latch is reported. The constant-only `ALWNEVER` signal has no consumers, and the pixel-format case supplies defaults before the case. Five clock/reset usage warnings remain visible; this is not clock-domain-crossing signoff.

Lint is one acceptance gate. Corrected-source flattened synthesis checks, SRAM comparisons, residual-cell and memory-contract audits, and full-SoC numerical/CPU simulations provide separate evidence. The warning review does not prove every optional accelerator mode.
