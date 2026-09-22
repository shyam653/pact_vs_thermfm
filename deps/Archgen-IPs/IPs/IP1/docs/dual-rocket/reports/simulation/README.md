# Prior DualRocketConfig Simulation Campaign

**Completed: 2026-09-06.** This is an export of the prior completed software
simulation campaign, not a new simulation run accompanying the fresh lint
and synthesis reports. No simulation was rerun to prepare this package.

All **335 configured ISA tests** and **12 configured benchmarks** passed.
The broader inventory contains **422 unique programs/variants: 391 reported
PASS, 25 FAIL, and six wall timeouts**. The reported passes retain the
software-test limitations below; this is not a claim that all 422 passed.

## Results

| Group | Total | Reported PASS | FAIL | Wall timeout |
| --- | ---: | ---: | ---: | ---: |
| RV64 ISA inventory | 349 | 340 | 5 | 4 |
| Configured benchmarks | 12 | 12 | 0 | 0 |
| Additional scalar benchmarks | 2 | 2 | 0 | 0 |
| Additional two-hart benchmark variants | 3 | 3 | 0 | 0 |
| Legacy multithreaded kernels | 49 | 27 | 20 | 2 |
| Chipyard C/C++ and two-hart hello | 3 | 3 | 0 | 0 |
| Explicit two-hart memory/atomic smoke | 1 | 1 | 0 | 0 |
| Corrected multicore supplements | 3 | 3 | 0 | 0 |
| **Unique total** | **422** | **391** | **25** | **6** |

The configured 335 ISA names are a subset of the 349, not extra tests.
The other 14 ISA probes contribute five passes and nine non-passes.
Retries, pilots, diagnostic traces and negative controls are not added to
the unique total. [All final outcomes](all-results.tsv) retain the selected
campaign, raw result kind, exit status, wall time and original log identifier.
The [aggregate JSON](summary.json) also preserves earlier campaign totals.

## Hardware and Method

The simulator is **TestDriver/TestHarness containing the complete ChipTop
SoC**, not a standalone Rocket core. Its source composition is documented
in [CONFIGURATION.md](../../CONFIGURATION.md) and [SOC.md](../../SOC.md).
It uses original generated behavioral RTL and memories, Verilator **5.022**,
DRAMSim2, seed **1**, and fast ELF loading through `+loadmem`. CPUs still
execute the boot ROM and programs against the RTL. Fast loading bypasses
serial program transfer; it does not establish sustained serial-PHY safety.

The ISA sources are `riscv-tests` commit
`0494f954a3d8d2ca9e4972da7a01e94b6a909bce`, with test environment commit
`4fabfb4e0d3eacc1dc791da70e342e4b68ea7e46`. The configured suite came from
the emitted DualRocketConfig dependency makefile. The full ISA inventory
was built using the upstream Makefile with GCC **13.2.0**, RV64 targets
and each suite's architecture options. Standard benchmark builds used
the supported non-vector subset `rv64imafdc_zicsr_zifencei`, ABI `lp64d`.

The unchanged RTL simulator SHA256 is:

```text
0f8727ad431088f81279b358ed91069b6dca9035212ba49686b712635c965894
```

The runner checked simulator/ELF identity, isolated test working directories,
disabled core dumps, and disconnected stdin. PASS required process exit
zero, a normal TestDriver finish, no failure diagnostic, and any required
program output. The custom atomic smoke additionally required its
conditional both-hart PASS marker. A timeout takes precedence over exit
zero or a finish message printed while the process is being terminated.

| Campaign | Cycle ceiling per test | Host wall limit per test |
| --- | ---: | ---: |
| ISA | 2,000,000 | 300 seconds |
| Initial benchmarks | 10,000,000 | 600 seconds |
| Extended PMP retry | 20,000,000 | 1,800 seconds |

The ISA campaign used three workers. Benchmarks started with one worker
alongside ISA testing and resumed with three workers after 14 completed
results. The incomplete next attempt was archived rather than treated as
completed. [Campaign settings](campaign-settings.json) retain original
provenance, completed summaries and the resume accounting; the original
benchmark `jobs=1` field is not rewritten as if all work ran with three.
Wall times include scheduling contention and are not silicon performance.
A blank cycle field means the successful non-tracing log did not print a
cycle count; it does not mean zero cycles.

## Retries and Timeout Semantics

The first PMP benchmark reached the 600-second wall limit. Short RTL traces
showed successful expected protection-fault returns and monotonically
advancing addresses, not a repeated-address loop. The unchanged ELF then
**passed in 892.308 seconds** under the larger bound. The final `pmp` row
selects that retry; the original timeout is retained in
[rerun history](rerun-history.tsv). Increasing a timeout was not itself
treated as a pass.

The original C++ hello was falsely rejected as `MISSING_FINISH` because it
prints no newline before the simulator's finish text. The output parser
was corrected, and a fresh unchanged-ELF retry passed with `Hello World!`.
Both classifications remain in the rerun table. This was a runner parsing
defect, not a C++ or RTL failure.

Some timed-out processes returned zero and printed a normal finish during
termination. Their wall-timeout flag remains authoritative. The six final
timeouts are actual host wall limits, not six demonstrated processor
deadlocks and not completed cycle-ceiling tests.

## Non-Passing ISA Probes

Five additional probes fail: `rv64mzicbo-p-zero`, `rv64ui-p-ma_data`, and
the three `rv64uzbc-p-clmul*` programs. Four time out: `rv64ui-v-ma_data`
and the three `rv64uzbc-v-clmul*` programs. Zicboz and Zbc are absent from
the generated ISA; the misaligned-data probes expect accesses that this
configuration traps. These outcomes are not failures of the configured
335-test acceptance subset.

A bounded direct RTL trace of `rv64uzbc-v-clmul` confirmed an unsupported
instruction trap followed by the test environment's broken machine-mode
error path: a zero stack pointer causes its handler's stack store to trap
recursively. It repeated 4,576 times without reaching failure reporting.
Spike reproduced that path. This single trace does not independently
diagnose all four virtual-test timeouts.

`rv64ssvnapot-p-napot` passes because its source explicitly accepts the
expected unsupported page fault. Its pass does not establish Svnapot
support. The `v` suffix means the virtual-memory test environment, not
the RISC-V vector extension.

## Legacy Oracle Caveats

All 22 legacy non-passes are matrix kernels with incompatible 32-by-32
assumptions against the current 16-by-16 dataset. RTL returns failure for
20; `legacy-ad_matmul-dual` and `legacy-dv_matmul-dual` hit wall limits.
Spike returns nonzero for the same 22. Neither the defective input nor
agreement with its reference failure is clean evidence of an RTL defect.

Reported legacy passes also require qualification:

- `ce_matmul` can pass despite out-of-bounds result writes.
- `vvadd1` accesses vector elements 1000-1007 beyond the 1000-element arrays.
- The original base/legacy matrix wrapper allows either hart to report
  success before both verification results have been aggregated.
- `bc_matmul` and `dc_matmul` select hart-0-only computation at dimension 16.

The [49-kernel inventory](oracle-kernels.tsv) records the bounded source
audit, not proof that the other kernels are defect-free. Its source anchor
lines refer to `riscv-tests/mt/<kernel>.c` at the pinned revision above.

Three separately named corrected supplements passed RTL and Spike:
bounds-guarded `vvadd1`, base matrix multiplication with both hart results
collected before hart 0 exits, and geometry-compatible `ae_matmul` using
that corrected wrapper. Original binaries/results were not replaced.
Reference-only negative controls rejected an injected hart-1 failure and
timed out with only one hart; they are not extra RTL passes.

## Multicore and Reference Scope

The 187 physical ISA tests park the secondary hart. The 162 virtual-memory
tests run the environment's background coherence traffic on hart 1.
The 14 ordinary benchmark binaries retain a one-hart CRT even where names
begin `mt-`. The additional `-dual` variants admit two harts. Two-hart hello
requires both hart-identifying outputs. The explicit atomic smoke requires
both harts, peer-data visibility, and a total of 256 atomic increments.
These checks do not constitute exhaustive cache-coherence verification.

Matched Spike used two harts, Sv39, eight four-byte-granularity PMP entries,
and 256 MiB main memory, with this ISA selection:

```text
rv64imafdc_zicsr_zifencei_zicntr_zihpm_zfh_zba_zbb_zbs
```

It did not enable Zbc, Zicboz, Svnapot or misaligned emulation. Reference
limits were external wall timeouts, not an instruction-limit option that
could exit zero without test completion. The [comparison table](reference-comparison/comparison.tsv)
and [comparison summary](reference-comparison/summary.json) show **391
PASS/PASS and 31 non-PASS/non-PASS agreements**, with zero classification
disagreements. Raw mechanisms differ: two RTL wall timeouts are Spike
nonzero exits. No equality of exit codes, cycle timing, or implementations
is claimed.

All current ELFs matched preserved build hashes and selected RTL campaign
hashes. Three corrected tests additionally have per-ELF hashes recorded
directly in Spike-run provenance. The original 419 reference runs did not
record contemporaneous per-ELF run hashes; their identities are linked
through the preserved build artifacts. The exported evidence distinguishes
`SPIKE_RUN_HASH` from `BUILD_HASH_ONLY` instead of overstating that proof.

Not covered: Linux boot, matching JTAG/OpenOCD debug workflows, absent
peripherals/accelerators, other ISA configurations, formal verification,
code/functional coverage percentages, SRAM-mapped gate-level simulation,
timing closure, power or physical signoff. Spike is not a cycle-accurate
model of the RTL cache/fabric implementation.

## Portable Evidence Export

This folder contains compact results, not a replay-ready simulator/test
distribution. **Raw logs, binary executables, large traces and build trees
are not committed here.** Path fields in TSV/JSON are identifiers relative
to the external regression run root, not Markdown links or files promised
inside this folder. `../simulation/` identifies the sibling earlier-smoke
directory; `upstream-chipyard/` aliases the external prepared upstream tree.

[export-manifest.json](export-manifest.json) records original source-file
SHA256s and exported-file SHA256s, including the manually summarized README.
TSV/JSON was parsed structurally, absolute local paths were normalized,
and line endings standardized; hashes of transformed exports can therefore
differ from source hashes. Original source files were not altered. The
manifest hashes every listed export but does not recursively hash itself.

The [export helper](../../../../scripts/dual-rocket/export-simulation-evidence.py)
validates the completed totals, configured pass sets and reference coverage
before writing portable outputs. It never starts a simulator. To re-export
from an existing retained campaign, provide that external run root. The
output must be separate from the original experiment and upstream checkout,
and must already contain the maintained `README.md`. A custom `--output`
does not cause the helper to invent a narrative. Overlapping output paths
and escaping destination symlinks are rejected before exports are written:

```bash
python3 scripts/dual-rocket/export-simulation-evidence.py \
  --run-root /path/to/completed/regression
```

The source configured-name lists are included as
[ISA names](config-isa-targets.txt) and
[benchmark names](config-benchmark-targets.txt), so the subset claims can
be checked directly against the exported final-results table. The benchmark
list omits the upstream `.riscv` executable suffix to match final test IDs;
this transformation is recorded in the export manifest.
