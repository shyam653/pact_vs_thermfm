# IP3 full-SoC CPU simulation

Fresh simulation of `DualRocketNVDLAConfig` completed at 2026-09-12T19:03:07Z. All **335 configured ISA tests** and **12 configured benchmarks** passed. The broader frozen inventory contains 422 unique programs; raw diagnostics remain nonpassing.

| Group | Total | PASS | FAIL | Cycle timeout | Wall timeout |
| --- | ---: | ---: | ---: | ---: | ---: |
| RV64 ISA inventory | 349 | 340 | 5 | 0 | 4 |
| Configured benchmarks | 12 | 12 | 0 | 0 | 0 |
| Additional scalar benchmarks | 2 | 2 | 0 | 0 | 0 |
| Additional two-hart benchmarks | 3 | 3 | 0 | 0 | 0 |
| Original legacy kernels | 49 | 27 | 20 | 0 | 2 |
| Chipyard C/C++ and two-hart hello | 3 | 3 | 0 | 0 | 0 |
| Explicit two-hart atomic smoke | 1 | 1 | 0 | 0 | 0 |
| Corrected multicore supplements | 3 | 3 | 0 | 0 | 0 |
| **Unique total** | 422 | 391 | 25 | 0 | 6 |

The exact 422 ELF binaries compiled for IP2 were reused. Every complete ELF hash matches IP2's published campaign evidence and the fresh IP3 campaigns; no CPU test was recompiled for IP3. The preserved [build capture](rebuild/capture.json) is historical IP2 evidence. The new [IP3 reuse capture](rebuild/ip3-reuse-capture.json) records current verification of that reuse and the actual IP3 simulator identity. [Compiler commands](rebuild/commands.json), [build inputs](rebuild/inputs.json), and [loadable-section comparison with IP1](rebuild/baseline-loadable-comparison.json) remain available. IP2's source-pin and Python optimization guards were added after the original compilation; the historical capture does not claim a contemporaneous compiler-run hash for the final builder.

[Final outcomes](all-results.tsv), [all attempts](attempts.tsv), [IP1 comparison](baseline-comparison.tsv), and [aggregate evidence](summary.json) retain the actual classifications. All **391 IP1 PASS programs passed again**, with no previous PASS becoming nonpassing. Raw classification differences are:

Every raw result classification matches IP1.

Compared with [IP2](../../../../IP2/docs/reports/cpu/README.md), only
`legacy-ad_matmul-dual` and `legacy-dv_matmul-dual` changed classification:
IP2 reached its cycle limit; IP3 reached the planned 1,800-second wall limit.
Their recorded IP3 wall times are 1800.070 and 1805.017 seconds, including
termination handling. Both were already nonpassing, and every IP2 passing
program passed again. The raw results retain these timeout classifications.

A cycle timeout is the actual TestDriver stop at the recorded cycle limit; a wall timeout is host termination at the recorded time limit. IP1 initially used a 10-million-cycle benchmark ceiling, whereas IP3 uses 2 million for the shorter benchmark partition. Neither timeout classification is converted to a pass.

## Method and limits

The simulator contains the complete dual-Rocket ChipTop with small NVDLA, behavioral memories and DRAMSim2. CPU programs boot against the RTL. `+loadmem` loads ELF contents into simulated memory, so serial-host program transfer is not covered. Accelerator arithmetic, DMA, PLIC polling and deliberate failure controls are documented separately in the [NVDLA report](../nvdla/README.md).

All CPU campaigns use seed 1 and simulator SHA256:

```text
ac906aabe883e14d65b06669b134ca5079d96ddcd462e82b4d0079b08a6cacf5
```

| Campaign | Tests | Workers | Cycle ceiling | Wall limit per test |
| --- | ---: | ---: | ---: | ---: |
| cpu-isa | 349 | 2 | 2,000,000 | 600 seconds |
| cpu-pmp | 1 | 1 | 20,000,000 | 7,200 seconds |
| cpu-bench-shard-1 | 18 | 1 | 2,000,000 | 1,800 seconds |
| cpu-bench-shard-2 | 17 | 1 | 2,000,000 | 1,800 seconds |
| cpu-bench-shard-3 | 18 | 1 | 2,000,000 | 1,800 seconds |
| cpu-bench-shard-4 | 19 | 1 | 2,000,000 | 1,800 seconds |

The 72 shorter benchmarks were divided into four disjoint groups using descending IP2 host runtimes and assignment to the least-loaded group. Historical group totals were 1360.873, 1351.825, 1358.476 and 1364.085 seconds. All original manifest fields and ELF identities remained identical. The [partition evidence](scheduling/partition/partition-provenance.json) records every weight, assignment and hash. ISA completion contributes two worker slots; each explicitly coordinated NVDLA release can contribute one additional slot immediately, even before ISA finishes. Benchmark scheduling uses at most four heavy workers. The earlier ISA/PMP phase briefly overlapped a fifth EDA/accelerator worker. [Scheduling events](scheduling/partition/scheduling-events.jsonl), [the scheduler](scheduling/queue-cpu-bench-shards.py) and exact commands preserve the actual benchmark schedule. The [original idle queue](scheduling/idle-queue-replaced/change.json) and [first idle shard scheduler](scheduling/idle-shardqueue-replaced/change.json) were replaced before any benchmark launched; both code and event histories are retained, and neither replacement interrupted a simulation.

PMP ran separately and passed in 3504.706 seconds. Host times include contention with other verification work and are not CPU performance measurements. A blank cycle field means the non-tracing log did not print a cycle count. These campaigns contain exactly one attempt per test and no retry-dependent final outcomes.

The initial PMP and benchmark wall limits were selected conservatively from [historical pre-correction host runtimes](rebuild/pmp-wall-bound-analysis.json): 70 completed virtual tests on the original native showed a median ratio to IP2 of 3.469 and a maximum of 4.463. Applying the maximum to IP2's PMP time projected about 4523 seconds; the initial 7200-second limit provided additional margin. These observations guided host timeouts and do not measure processor performance or count toward corrected-native acceptance. The [interrupted original-native campaign](../cpu-original-native/README.md) is preserved separately; every final result above comes from the corrected simulator.

PASS requires exit zero, native Verilog `$finish`, absence of simulator failure markers and every declared required output string. A host timeout remains a timeout even if termination prints a finish message or returns zero. The upstream NVDLA native build omits `--assert`; generated Chipyard procedural monitors and TestDriver failure checks remain active, while vendor macro-gated assertions and coverage constructs are excluded. The [assertion-scope audit](../assertions/README.md) records the actual generated C++ evidence and remaining empty assertion-helper instances.

## Diagnostic and software-oracle qualification

The configured 335-test ISA subset excludes the extra Zicboz/Zbc and misaligned-data probes that failed or timed out in IP1. Those features and access expectations remain outside this configuration. A `v` suffix denotes the virtual-memory environment, not vector instructions. A passing `rv64ssvnapot-p-napot` accepts the unsupported page fault and does not establish Svnapot support.

The 49 original legacy matrix/vector kernels retain the [IP1 oracle audit](../../../../IP1/docs/dual-rocket/reports/simulation/README.md): 22 matrix variants have incompatible dataset geometry; some reported passes have out-of-bounds accesses or incomplete two-hart success aggregation. The `ce_matmul` output bounds, `vvadd1` tail accesses, original matrix wrapper, and hart-0-only `bc_matmul`/`dc_matmul` cases remain qualified. Raw outcomes and the three separately named corrected supplements are preserved.

The explicit dual-hart smoke requires both harts, peer-data visibility and 256 atomic increments. Two-hart hello requires both hart-identifying outputs. Physical ISA tests park the secondary hart; virtual-memory tests run background traffic on it. Original names beginning `mt-` alone do not prove both harts participated; additional `-dual` variants use the two-hart startup.

IP1's Spike comparison and diagnostic traces are inherited reference evidence, not fresh IP3 Spike runs. Matching software-test outcomes do not establish exhaustive ISA, coherence or peripheral verification. These campaigns do not cover Linux, external JTAG/debug, gate-level timing, physical signoff, formal proof or coverage percentages.

## Evidence and replay

Full non-tracing logs, commands, per-test results and campaign metadata are retained under `campaigns/`. 9 logs contain non-UTF8 bytes; the exporter preserves them and normalizes only workspace path bytes. Binary ELFs, simulator build trees and DRAMSim working files remain external artifacts. Portable paths use `${REPO_ROOT}`, `${CHIPYARD_ROOT}` and `${CAMPAIGN_ROOT}/<campaign>`. [Export hashes](export-hashes.json) distinguish original from exported bytes; historical rebuild hashes are carried forward unchanged with their matching files.

Use the [shared CPU workflow](../../../../../scripts/cpu-regression/README.md) to rebuild the pinned inventory. The archived manifests and commands provide the exact test split and limits. The [CPU exporter](../../../../../scripts/cpu-regression/summarize.py) checks all 422 identities, generated configured-test sets, simulator/ELF identity, PASS log requirements and IP1 regressions before accepting the report.
