# Measured NVDLA SoC logic synthesis

`DualRocketNVDLAConfig`, complete `ChipTop`, finished with exit zero and **PASS_LOGIC_MAPPING_WITH_GENERIC_MEMORIES** on the corrected published RTL. All source/workflow input hashes and all six observed native tool/plugin identities remain unchanged. The exact ABC sequence was `strash; &get -n; &nf; &put`.

The netlist contains **719,385 standard cells, 194 mapped CPU SRAM macros and 201 generic memory cells**. The generic memories contain **1,210,363 bits**, including small CPU/SoC arrays and constant ROMs as well as accelerator RAM. NVDLA CBUF is exactly **64 × 256×64 = 128 KiB**. The mapped portion reports **4,741,582.202001 µm²**, excluding generic-memory storage area. These are exploratory Nangate45/fakeram45 results.

Both original-memory and macro-backed full-SoC hierarchy/CHECK gates pass. Every generated SRAM interface passed all three fresh simulation seeds: **212,364 compared cycles** across seven interfaces. The strict residual-cell audit admits only actual standard-cell/SRAM Liberty cell types plus `$mem_v2`.

The actual-flow cleanup audit preserves all 3,904 module interfaces, 411 original memory declarations and 836 memory-cell type/parameter sets while eliminating internal logic in 76 output-free TileLink monitors. The same mandatory `check -assert` follows cleanup. The separate final audit compares **all 4,221 parameters in all 201 memories exactly before and after ABC**, including INIT, clock, transparency, collision and X masks. Both audits pass on the corrected source. This is structural/parameter evidence, not formal surrounding-logic equivalence.

`memory-lowering-summary.json` reconciles the earlier 199-array/1,151,042-bit inventory with the final 201 cells: five constant mux tables become ROMs, three serial-TL phit arrays disappear during optimization, and 21 stored-word widths shrink. The pre/post-ABC audit covers the final collected contracts. Native RTL numerical/CPU simulations are a separate acceptance gate.

**OpenROAD linking is not run.** The remaining generic memories require compatible physical macros, including independent read/write port contracts, before full SRAM technology mapping, complete physical area or physical linking can be claimed. No timing constraints, timing closure, placement or routing are provided.

Three earlier incomplete/failed attempts and the historical cleanup diagnostic are preserved with explicit source differences and raw hashes. In particular, the flattened CHECK rejected 176 undriven SDP LUT readback bits in the earlier RTL; patch 0003 supplies the absent-feature inputs with typed zeros. The successful corrected flow repeats every required gate and reuses none of those earlier acceptance results.
