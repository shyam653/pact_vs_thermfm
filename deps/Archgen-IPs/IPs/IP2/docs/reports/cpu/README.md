# IP2 full-SoC CPU simulation

Fresh simulation of `DualRocketFFTConfig` completed on 2026-09-12. All **335 configured ISA tests** and **12 configured benchmarks** passed. The broader frozen inventory contains 422 unique programs; its raw outcomes are reported below without converting known diagnostics into passes.

| Group | Total | PASS | FAIL | Cycle timeout | Wall timeout |
| --- | ---: | ---: | ---: | ---: | ---: |
| RV64 ISA inventory | 349 | 340 | 5 | 0 | 4 |
| Configured benchmarks | 12 | 12 | 0 | 0 | 0 |
| Additional scalar benchmarks | 2 | 2 | 0 | 0 | 0 |
| Additional two-hart benchmarks | 3 | 3 | 0 | 0 | 0 |
| Original legacy kernels | 49 | 27 | 20 | 2 | 0 |
| Chipyard C/C++ and two-hart hello | 3 | 3 | 0 | 0 | 0 |
| Explicit two-hart atomic smoke | 1 | 1 | 0 | 0 | 0 |
| Corrected multicore supplements | 3 | 3 | 0 | 0 | 0 |
| **Unique total** | **422** | **391** | **25** | **2** | **4** |

The full 422-name inventory is the same as IP1. Current rebuilt executables have identical allocated code/data section sets to the preserved IP1 programs, excluding GNU build-ID notes; complete ELF hashes differ for 419 programs. Each new run records its actual ELF hash. The archived compiler commands and copied build templates are retained. Source-pin and Python optimization guards were added to the builder after compilation; the final builder hash is [captured at evidence-export time](rebuild/capture.json) and is not presented as a contemporaneous compile-time hash. See [rebuild evidence](rebuild/inputs.json) and [loadable comparison](rebuild/baseline-loadable-comparison.json).

[Final outcomes](all-results.tsv), [all attempts](attempts.tsv), [IP1 comparison](baseline-comparison.tsv), and [aggregate evidence](summary.json) retain classifications and identity. All 391 programs reported PASS in IP1 passed again. No previous PASS became nonpassing. Raw diagnostic classifications differ as follows:

| Test | IP1 | IP2 |
| --- | --- | --- |
| `legacy-ad_matmul-dual` | WALL_TIMEOUT | CYCLE_TIMEOUT |
| `legacy-dv_matmul-dual` | WALL_TIMEOUT | CYCLE_TIMEOUT |

The IP2 benchmark cycle ceiling is 2 million, while IP1 used 10 million for its initial benchmark campaign. A cycle timeout is the actual TestDriver stop after 2,000,001 cycles; a wall timeout is host termination at the recorded time limit. These known diagnostics remain nonpassing, and neither mechanism is relabeled as a pass.

## Method and limits

The simulator contains the complete dual-Rocket ChipTop with the FFT block, behavioral memories and DRAMSim2. CPU software runs through the boot ROM against the RTL. `+loadmem` loads ELF contents directly into simulated memory, so this campaign does not exercise serial-host program transfer. Accelerator computation is checked separately in the [FFT report](../fft/README.md).

All campaigns use seed 1 and the same simulator SHA256:

```text
5945b691918e61aaf05431f07b8f40cdf87e6431ab4981e310c188a8b38fbd5c
```

| Campaign | Tests | Workers | Cycle ceiling | Wall limit per test |
| --- | ---: | ---: | ---: | ---: |
| ISA | 349 | 2 | 2,000,000 | 300 seconds |
| Benchmarks, excluding PMP | 72 | 3 | 2,000,000 | 600 seconds |
| Extended PMP | 1 | 1 | 20,000,000 | 1,800 seconds |

PMP ran separately and overlapped the other campaigns; it passed in 1013.445 seconds. Host times include scheduling contention and are not processor performance measurements. A blank cycle field means the non-tracing log did not print a cycle count.

PASS requires exit zero, normal Verilog `$finish`, absence of failure markers and every declared required output string. A host timeout remains a timeout even if termination prints a finish message or returns zero. These exported campaigns contain one attempt per test; no final outcome depends on a retry.

## Diagnostic and software-oracle qualification

The generated 335-test ISA subset excludes the extra Zicboz/Zbc and misaligned-data probes that failed or timed out in IP1. These features/access expectations remain outside this configuration. A `v` test suffix denotes the virtual-memory environment, not vector instructions. A passing `rv64ssvnapot-p-napot` accepts the unsupported page fault and does not establish Svnapot support.

The 49 original legacy matrix/vector kernels retain the [IP1 oracle audit](../../../../IP1/docs/dual-rocket/reports/simulation/README.md): 22 matrix variants have incompatible dataset geometry; some reported passes have out-of-bounds accesses or incomplete two-hart success aggregation. The `ce_matmul` output bounds, `vvadd1` tail accesses, original matrix wrapper, and hart-0-only `bc_matmul`/`dc_matmul` cases remain qualified. Their raw outcomes are preserved. The three separately named corrected supplements retain their own results.

The explicit dual-hart smoke requires both harts, peer-data visibility and 256 atomic increments; two-hart hello requires both hart-identifying outputs. Physical ISA tests park the secondary hart, while virtual-memory tests run background traffic on it. Original benchmark names beginning `mt-` do not alone prove both harts participated; additional `-dual` variants use the two-hart startup.

IP1's Spike comparison and diagnostic traces are inherited reference evidence, not fresh IP2 Spike runs. Matching software-test outcomes do not establish exhaustive ISA/coherence/peripheral verification. This campaign does not cover Linux, external JTAG/debug, gate-level timing, physical signoff, formal proof or coverage percentages.

## Evidence and replay

Compact command files, full non-tracing simulation logs, per-test results, campaign metadata and summaries are included under `campaigns/`. Binary executables, generated simulator build trees and DRAMSim working files are external artifacts. Nine failing legacy programs emitted non-UTF8 bytes. The exporter preserves those bytes and replaces only workspace path bytes; these logs are intentionally not forced through a text decoder. An initial incomplete export was retained locally and the successful export rerun after correcting that handling. Absolute workspace paths are replaced with `${REPO_ROOT}`, `${CHIPYARD_ROOT}` and `${CAMPAIGN_ROOT}/<campaign>` identifiers. [Export hashes](export-hashes.json) distinguish original bytes from portable exported bytes.

Use the [shared CPU workflow](../../../../../scripts/cpu-regression/README.md) to rebuild the pinned inventory. The campaign manifests and commands document the exact test split and bounds used here. The [exporter](../../../../../scripts/cpu-regression/summarize.py) checks all 422 identities, the emitted configured-name sets, simulator/ELF identity, PASS log requirements and IP1 regressions before reporting acceptance.
