# Full-SoC synthesis and netlist link

Set `CONFIG`, `CHIPYARD_ROOT`, `OUTPUT_ROOT` (new directory), and either
`PLATFORM_ROOT` or `ORFS_ROOT`. Optional overrides: `GENERATED_DIR`, `IP_DIR`,
`OSS_CAD_SUITE_ROOT`, `YOSYS`, `OPENROAD`, `IVERILOG`, `VVP`, `PYTHON`,
`SLANG_PLUGIN`, `SYNTHESIS_MODE`, `ABC_MODE`. Executable overrides identify a bare command or absolute path,
not a shell command containing arguments. See the parent README for a command.

Required external inputs are generated RTL/hierarchy/memory metadata, Yosys with
slang and ABC, OpenROAD, Icarus Verilog, and Nangate45 standard-cell plus
`fakeram45_512x64` Liberty and LEF files. No tool binaries or PDK files are copied
into the repository. Their actual versions and hashes are recorded per run.

`ABC_MODE=direct` selects the explicit, hashed script `strash; &get -n; &nf; &put`
for either synthesis mode. It omits the default mapper's SAT-heavy optimizations;
all hierarchy, residual-cell, memory and final checks still apply. `ABC_MODE=default`
retains Yosys's default mapping script. Provenance and summary identify the selected
mode. Compare area only with the same optimization mode, source scope and libraries.

`prepare.py` derives every SRAM geometry, mask width, and hierarchy instance
count from the configuration's own `top.mems.conf`, `top_module_hierarchy.json`,
and original generated interfaces. It accepts power-of-two depths >=2 and
single `rw`/`mrw` ports. Unsupported ports, metadata keys, or changed interface
grammar fail before synthesis. There is no fixed IP1 inventory or macro count.
Every accepted interface gets a generated wrapper, renamed original golden
model, and comparison-test instantiation. The wrapper uses the existing IP1
registered-read-address contract; simulation against the actual original
memory is mandatory before mapping.

Stages:

1. Check metadata/source providers, generate isolated aliases/wrappers/testbench,
   and record input/tool provenance.
2. Yosys preflight checks one generated macro interface, then the complete
   macro-backed flattened frontend and original-memory hierarchical frontend
   must pass their checks. Checking the flattened frontend early exposes missing
   submodule inputs before longer simulation or mapping work.
3. Icarus compares **every**
   generated SRAM interface with the actual original model for seeds 1, 827361,
   and 2147483647, including complete initialization, mask-lane isolation,
   held-address writes, bank boundaries, idle cycles, and random operations.
4. Audit remaining behavioral memories in actual elaborated RTLIL. Arrays over
   8192 bits each fail with an explicit inventory before standard-cell expansion;
   they require an additional verified adapter. This particularly protects
   accelerator memories embedded in bundled RTL, which are not described in
   Chipyard's `top.mems.conf`. Smaller remaining arrays may map to standard cells.
5. Require the metadata-derived macro count, lower only provably enabled output
   buffers, reject remaining tristates, synthesize, and map through ABC.
6. Assert a fully mapped hierarchy and matching macro count, then link against
   external Liberty/LEF in OpenROAD. The flattened physical count must agree.
7. Require all SRAM seed/interface comparisons, memory audit and link checks;
   verify source inputs have not changed; produce measured summary and hashes.

Each frontend performs `hierarchy -check`, records statistics before and after
`opt_clean -purge`, and runs the same mandatory `check -assert`. Early cleanup
removes unused synthesis-only monitor state before the expensive check; no
source RTL or functional output is removed by an explicit exclusion list.
The original-memory frontend also retains before/after cleanup RTLIL for the
independent structural audit. Provenance records the complete stage order and
the summary includes both frontend statistics.

All generated stages, logs, RTLIL intermediates, mapped netlists, statistics,
SRAM comparisons, inventory, source plan, linked ODB and provenance remain under
`OUTPUT_ROOT`. A failed run returns nonzero and preserves its directory. There
is no resume mode: use a fresh directory for a rerun. Large intermediates and
external libraries should not be published to Git; review and path-normalize
compact evidence for publication.

Nangate45/fakeram45 mapping gives exploratory non-manufacturable area estimates.
OpenROAD linking is not placement or routing. There are no timing constraints,
timing-closure, power or physical-signoff claims. SRAM simulation is finite,
not formal equivalence, and mapping does not establish SoC functionality.

## Memory-preserving logic mapping

`SYNTHESIS_MODE=preserve-memories` is the explicit option for accelerator SRAMs
that lack a compatible physical macro. The CPU's supported generated SRAMs
still use the verified adapters. Yosys collects all remaining memories into
`$mem_v2` cells and maps surrounding logic with the same standard-cell library;
`memory_map` is deliberately omitted, preserving independent read/write ports
and collision semantics. Remaining generic memories are inventoried from the
actual synthesized hierarchy with dimensions and read/write port counts.
Only `$mem_v2` may remain as an internal cell type after logic mapping. The final
cell audit allows only cell names actually declared in the standard-cell and SRAM
Liberty files, plus `$mem_v2` in this mode. An unresolved accelerator blackbox
fails the run even when OpenROAD is skipped.

Outputs are named `ChipTop-logic-mapped.v` and `.json`; the Verilog still contains
behavioral memories. `preserved-memories.json` records each generic memory.
The summary status is `PASS_LOGIC_MAPPING_WITH_GENERIC_MEMORIES`, distinct from
complete technology mapping. OpenROAD linking is **not run**, and the report
explicitly excludes generic SRAM storage area from mapped area. No NVDLA SRAM
technology mapping, complete physical area or physical-link claim is made.
The default `mapped` mode continues to reject unsupported large arrays.
