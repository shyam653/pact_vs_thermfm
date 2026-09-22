# Full-SoC lint

Both linters completed on the generated `ChipTop` hierarchy with **zero errors**.
All 488 recorded source hashes were checked again after final RTL generation;
they matched. The simulation harness is retained in the source inventory but
is not selected as the hardware top.

| Tool | Errors | Warnings | IP1 warnings |
| --- | --- | --- | --- |
| Verilator | 0 | 2,581 | 2,484 |
| slang | 0 | 21 | 21 |

The extra 97 Verilator warnings are retained in the diagnostic inventory.
Warnings include unused signals, empty pin connections, mixed reset use,
filename/style warnings, and the existing clock-gate latch. The 21 slang
warnings concern arithmetic within shift expressions. Zero errors does not
mean warning-free RTL or exhaustive functional correctness.

`summary.json`, `workflow-exits.json`, per-tool diagnostics/provenance, source
hashes and export hashes preserve the actual evidence. No new source-level
lint suppressions were added. The shared reproduction entrypoint is
[`scripts/accelerator-soc/lint`](../../../../../scripts/accelerator-soc/lint/README.md).
