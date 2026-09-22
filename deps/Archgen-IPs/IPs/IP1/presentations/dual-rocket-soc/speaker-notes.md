# Dual-Rocket SoC: Speaker Notes

Prepared 2026-09-08 from recorded 2026-09-06 evidence. No new EDA run.

## 01. Dual-Rocket SoC

This presentation explains an existing Chipyard-generated dual-Rocket design and the recorded verification work. It is not a silicon product announcement. Created on 2026-09-08 from the September 6 evidence; no EDA or functional simulation was rerun to prepare these slides. All diagrams are logical illustrations, not physical layouts.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)

## 02. What does this SoC do?

Each Rocket hart executes software instructions. The shared coherent hierarchy permits coordinated access to memory, while UART, interrupts and debug provide system services. The demonstrated use is bare-metal RTL simulation. Sv39 and privilege modes are present, but Linux boot was not tested. Application examples are categories of use, not benchmark performance claims.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)

## 03. How the project was built

The selected DualRocketConfig already existed upstream. Generation used a prepared, pinned checkout and cached generator JARs. A simulation campaign completed before the documentation-driven lint and synthesis reruns. Configuration and SoC documentation were completed before those fresh reruns. Report packaging preserves failed attempts, diagnostics and provenance. The final generation-wrapper test used an up-to-date cache, not a new elaboration.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [scripts/dual-rocket/README.md](../../scripts/dual-rocket/README.md)
- [docs/dual-rocket/reports/workflow/README.md](../../docs/dual-rocket/reports/workflow/README.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)

## 04. The exact two-core configuration

The CDE configuration composition searches leftmost fragments first; it is parameter composition, not concatenated RTL. WithNHugeCores(2) creates two tile parameter entries and updates NumTiles. AbstractConfig supplies the surrounding SoC; by itself it has no tiles. Huge names an upstream parameter preset and does not measure performance. Private L1 instances are duplicated and the shared directory width changes for the second coherent client.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/config/RocketConfigs.scala#L11-L17](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/config/RocketConfigs.scala#L11-L17)
- [https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60)

## 05. From Scala to generated hardware

chipyard.Generator selects chipyard.harness.TestHarness, containing ChipTop and DigitalTop. Chisel elaborates the design and Diplomacy negotiates buses, devices and clocks. FIRRTL and annotations are lowered by CIRCT firtool. The recorded options include --repl-seq-mem, --split-verilog and --export-module-hierarchy. Logical memory interfaces are not foundry SRAM selections. The 476-file manifest includes simulation resources and is not an instantiated DUT-module count. The native simulator is a separate build target.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [docs/dual-rocket/artifacts/rtl.sha256](../../docs/dual-rocket/artifacts/rtl.sha256)

## 06. Inside the full ChipTop SoC

Core data/instruction requests enter the TileLink system bus. The shared inclusive L2 connects SBUS to MBUS. The control-side path is SBUS to CBUS to PBUS, and serial ingress uses FBUS. The services box groups functions for readability and is not an assertion that all services attach to PBUS. Scratchpad is instantiated despite DTS disabled status. External memory is beyond the ChipTop boundary; the AXI window does not imply an on-chip DRAM controller or PHY. This is a logical diagram, not a floorplan; 64-bit AXI describes data width, not address width.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/artifacts/chipyard.harness.TestHarness.DualRocketConfig.l2.json](../../docs/dual-rocket/artifacts/chipyard.harness.TestHarness.DualRocketConfig.l2.json)

## 07. What each Rocket tile contains

The emitted DTS and pinned Rocket configuration confirm these properties. The generated ISA string includes b, but this must not be read as every bit-manipulation extension; Zba/Zbb/Zbs are explicitly selected, not Zbc. Single-instruction decode and retirement are in-order. FPU support includes F, D and Zfh. No V extension is selected. Cache capacities exclude metadata and padding. DTS CPU frequency fields are zero; no achieved CPU frequency is claimed.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60)

## 08. The memory hierarchy

Each hart has 32 KiB instruction and 32 KiB data L1 caches, giving 128 KiB total across two harts. Shared L2 is 512 KiB, eight-way, 1024 sets, 64-byte lines, one coherence bank and seven MSHRs. The 64 KiB scratchpad exists in RTL but its device-tree status is disabled; software must account for that. The external window is 256 MiB at 0x80000000 and needs an external AXI memory subsystem. There is no DDR controller/PHY or 256 MiB on-chip memory.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)

## 09. Boot, peripherals and external interfaces

CLINT provides timer/software interrupts to both harts. PLIC has one device source (UART) and four M/S interrupt contexts across two physical harts. JTAG debug supports system-bus access. Boot ROM has a 64 KiB address window, not necessarily 64 KiB of program bytes. ChipTop exposes external clocks and reset; the clock generator is passthrough, not a PLL. Decoupled serial TileLink uses 32-bit phits/flits; it is not UART. The current SoC has no FFT or other RoCC accelerator.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)

## 10. Key software-visible address regions

This slide is a selected address map, not all 12 regions. The full map also contains boot-address, error-response, tile-gating and tile-reset windows. End addresses in the source report are inclusive. Register windows are address apertures, not RAM capacity. Scratchpad status is disabled in DTS despite being instantiated. PLIC's 64 MiB aperture is not 64 MiB of interrupt storage. Debug is at zero, not ordinary RAM.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/artifacts/chipyard.harness.TestHarness.DualRocketConfig.memmap.json](../../docs/dual-rocket/artifacts/chipyard.harness.TestHarness.DualRocketConfig.memmap.json)

## 11. How two cores cooperate

This diagram is conceptual, not the instruction-by-instruction sequence of the test. The explicit two-hart atomic smoke requires both harts, peer-data visibility and a total of 256 atomic increments. Two-hart hello requires two hart-identifying outputs. Corrected multicore tests aggregate both hart results before success. Most physical ISA tests park the second hart; ordinary benchmarks can use one-hart startup code. Shared coherent caches do not automatically parallelize a program and atomic checks are not exhaustive coherence verification.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)

## 12. Hardware boundary vs simulation harness

TestDriver and TestHarness instantiate the complete ChipTop plus test infrastructure. Simulation uses original behavioral memories and DRAMSim2. +loadmem writes the simulator memory model to load a program; it is not a hardware memory-write port. Simulated JTAG, serial host, UART output and clock sources are not ASIC hardware. Lint/synthesis select the ChipTop hierarchy. Lint uses original behavioral memories; synthesis applies validated SRAM adapters. RTL simulation does not validate the mapped netlist.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)

## 13. Three checks answer different questions

The completed software simulation campaign predates the fresh documentation-driven lint and synthesis runs. Lint and synthesis can run independently against the same preserved generated source snapshot. Their dates and artifacts are retained separately. Simulation asks whether specific tests execute successfully. Lint checks static diagnostics, not full behavior. Synthesis checks mapping and linkability into libraries, not physical signoff. 476 hashes refer to a full generated-source inventory, not 476 DUT instances.

Sources:

- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
- [scripts/dual-rocket/README.md](../../scripts/dual-rocket/README.md)

## 14. Simulation: configured tests passed

All 335 configured ISA and 12 configured benchmarks passed. The configured ISA suite is a subset of the 349-program ISA inventory. The entire broadened campaign contains 422 unique programs/variants, with 391 reported PASS, 25 FAIL and six host wall timeouts. Retries are not added to the unique total. PASS results for some legacy programs carry oracle caveats explained on the next slide and in the report. Verilator simulation version is 5.022, distinct from the newer lint executable. Fast ELF loading bypassed serial program transfer.

Sources:

- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/simulation/summary.json](../../docs/dual-rocket/reports/simulation/summary.json)

## 15. Interpreting failures, timeouts and passes

Nine non-passing additional ISA probes concern unsupported Zbc/Zicboz or misaligned-data expectations. They are not failures of the configured 335-test subset. The 22 legacy non-passes have 32-by-32 matrix assumptions against a 16-by-16 dataset; some reported legacy passes also have bounds or two-hart result-aggregation defects. Three separately named corrected multicore supplements passed RTL and Spike; original results remain preserved. Matched Spike has 391 PASS/PASS and 31 non-PASS/non-PASS outcomes, not identical exit behavior or cycle-level equivalence. The six final timeouts are host wall limits, not six proven core deadlocks. PMP passed after a bounded extended retry, and a C++ hello parser issue was corrected.

Sources:

- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/simulation/reference-comparison/summary.json](../../docs/dual-rocket/reports/simulation/reference-comparison/summary.json)

## 16. Lint: zero errors, warnings retained

Fresh wrappers started both lint tools at 2026-09-06T13:19:52Z. Verilator 5.051 reported 2484 warnings; slang 11.0.448 reported 21 arith-in-shift warnings and 21 notes. Both tool and wrapper exits are zero. All warning-category deltas are zero against the earlier DualRocketConfig baseline, not the historical one-core report. Verilator -Wno-fatal retains warnings but allows completion. No generated RTL edits or new suppressions were introduced. Four SYNCASYNCNET warnings require reset/clock review. EICG_wrapper's latch is consistent with an intentional clock-gate latch, not physical signoff. 419 source files are in slang's elaborated dependencies; the shared 476-file fingerprint is the full generated inventory.

Sources:

- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/lint/evidence/summary.json](../../docs/dual-rocket/reports/lint/evidence/summary.json)

## 17. How full-SoC synthesis was performed

The flow preserves original RTL and uses an independent output directory. It checks full-ChipTop reachability and SRAM metadata; validates replacement adapters against behavioral memories; reads SystemVerilog with the slang Yosys plugin; maps logic with Yosys/ABC into Nangate45 cells and SRAM into fakeram45 macros; rejects unresolved cells/memories/processes; and links the complete mapped netlist in OpenROAD with Liberty/LEF. The first attempt failed because literal quotes reached Slang filename arguments, after SRAM tests. Relative input symlinks fixed the tooling issue and the full run was repeated. OpenROAD linking was not placement, routing or static timing analysis.

Sources:

- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
- [scripts/dual-rocket/synthesis/README.md](../../scripts/dual-rocket/synthesis/README.md)

## 18. SRAM adaptation was a separate task

Seven distinct generated SRAM interfaces represent 16 logical full-SoC bulk-memory instances. The adapter maps them into 194 fakeram45_512x64 macros (512 words by 64 bits each). Logical capacity is 5,958,656 bits; physical macro capacity is 6,356,992 bits, including padding and mapping overhead. This is not just architectural cache data. The dual-core directory is 1024 by 144 with 18-bit mask granularity; the one-core directory was 1024 by 136 with 17-bit granularity. Wrong widths, mask lanes and a missing instance were rejected by metadata negative controls. All seven interface tests passed three seeds and 212,364 compared cycles. These are finite initialized-memory comparisons, not formal equivalence, X-state proof or full mapped-SoC simulation.

Sources:

- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
- [docs/dual-rocket/reports/synthesis/inventory.json](../../docs/dual-rocket/reports/synthesis/inventory.json)

## 19. Synthesis results: mapped and linked

The fresh run completed September 6, 2026. Yosys maps 383,569 standard cells including 55,694 flip-flops and one DLL_X1 latch, plus 194 SRAM macros for 383,763 total instances. No unresolved internal cells, Yosys memories or processes remain. OpenROAD independently links every instance. Total Liberty cell area is 4,004,732.942001 square micrometers; SRAM subtotal is 3,356,478.972 and standard-cell subtotal 648,253.970001. Divide by one million for square millimeters. These are sums of library areas without a floorplan, not die/core area, utilization or timing. The Nangate45/fakeram45 platform is exploratory and non-manufacturable.

Sources:

- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
- [docs/dual-rocket/reports/synthesis/mapped-statistics.json](../../docs/dual-rocket/reports/synthesis/mapped-statistics.json)

## 20. What is not proven yet

The nominal 500 MHz bus configuration and 500 kHz DTS timebase are not measured silicon clocks. CPU clock-frequency fields are zero. No timing constraints, STA closure, placement, routing, power analysis, DRC/LVS or manufacturability claim was established. Linux boot, full JTAG/OpenOCD flows, exhaustive coherence, coverage percentages, formal verification and SRAM-mapped gate-level regression remain untested. Serial TileLink's selected decoupled PHY has a retained heavy-traffic deadlock warning; the generator recommends a credited PHY when deadlock freedom is required. Prior fast memory loading does not test sustained serial safety. Lint reset warnings need dedicated review.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)

## 21. How to try the next SoC configuration

This is a proposed engineering sequence, not completed integration. For an FFT accelerator, first initialize and inspect the optional FFT generator at the pinned revision and study its integration rather than assuming the class exists in the main tree. Choose a documented attachment, addressing and interrupt scheme as applicable. New core/cache configurations change memory shapes and need refreshed adapters. Preserve the current experiment, use distinct config names and output roots, regenerate metadata, add feature-specific tests, and rerun lint/synthesis. Quantitative comparisons require common tools and constraints. No FFT hardware or Linux boot is claimed in the current design.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [scripts/dual-rocket/README.md](../../scripts/dual-rocket/README.md)

## 22. Where the reproducible process lives

Run the commands from the results repository after provisioning the pinned Chipyard checkout and the documented EDA tools. CHIPYARD_ROOT, Java/RISC-V/PATH, OSS_CAD_SUITE_ROOT and ORFS_ROOT must be set as documented. generate.sh can reuse cached upstream output and requires exact source-manifest agreement. lint and synthesis use separate output roots and must not overwrite recorded attempts. The simulation evidence exporter only packages a completed campaign; it does not launch a simulator. The historical top-level rtl directory is single-core, while the dual-core hardware is identified by the generated-src DualRocketConfig path and its preserved hashes. Reports do not vendor raw large outputs, external libraries or binaries.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [scripts/dual-rocket/README.md](../../scripts/dual-rocket/README.md)
- [docs/dual-rocket/README.md](../../docs/dual-rocket/README.md)

## 23. Pinned tools and source provenance

Exact full source revisions and dependency hashes are in the local references. Chipyard e602d917dcc495c58cabe906535e411707096c9c; Rocket Chip 55bcad0f59436de98ea510334121de8546b9e9d7; ORFS 68cc9bc974502b4786a68e9f51a092e0fcb56e82. Verilator simulator is 5.022, lint is 5.051 devel v5.050-312-gb1c06fdb0 (mod). slang is 11.0.448+e222e7dc0. Yosys reports 0.68+195 with a dirty suffix; native executable/plugin hashes are retained. OpenROAD v2.0-17598-ga008522d8. Icarus is version 14.0 devel s20260301-403-g5ab23063f-dirty. 500 synthesis input hashes were revalidated unchanged. Generation was not a clean dependency bootstrap and the later wrapper check was cached.

Sources:

- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/synthesis/tool-versions.txt](../../docs/dual-rocket/reports/synthesis/tool-versions.txt)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
- [docs/dual-rocket/reports/workflow/README.md](../../docs/dual-rocket/reports/workflow/README.md)

## 24. Quick glossary and evidence guide

Glossary: SoC is a system on chip. A hart is a hardware execution thread; this design has one hart per Rocket core. RTL describes digital hardware behavior. TileLink is the on-chip interconnect protocol used here; AXI4 is the external-memory interface. L1 is private to a tile; L2 is shared. CLINT supplies timer/software interrupts; PLIC routes device interrupts. Lint, simulation, synthesis and physical signoff are distinct. The companion slide manifest and speaker-notes Markdown contain all references and SHA-256 fingerprints of the cited local source files. Read the detailed reports for exact test identities, warnings, provenance and limitations. This deck is a derivative explanation and does not replace the raw evidence.

Sources:

- [docs/dual-rocket/SOC.md](../../docs/dual-rocket/SOC.md)
- [docs/dual-rocket/CONFIGURATION.md](../../docs/dual-rocket/CONFIGURATION.md)
- [docs/dual-rocket/reports/simulation/README.md](../../docs/dual-rocket/reports/simulation/README.md)
- [docs/dual-rocket/reports/lint/README.md](../../docs/dual-rocket/reports/lint/README.md)
- [docs/dual-rocket/reports/synthesis/README.md](../../docs/dual-rocket/reports/synthesis/README.md)
