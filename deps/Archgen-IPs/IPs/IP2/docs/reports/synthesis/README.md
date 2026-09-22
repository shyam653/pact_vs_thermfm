# Measured independent checkpoint synthesis

`DualRocketFFTConfig`: **PASS**. The complete mapped ChipTop passed Yosys checks and OpenROAD linking with 194 SRAM macros.

This run reused the origin’s verified pre-ABC checkpoint, RTL elaboration and SRAM comparison evidence. ABC mapping, residual-cell checks, macro counts and OpenROAD linking were executed independently with `strash; &get -n; &nf; &put`. The origin’s default ABC run is separate; this report does not assert its completion. The same direct mapping mode must be used for area comparisons.

Native binary, source, checkpoint, script and library hashes were checked before and after the independent run. Historical documentation mismatches, if any, are recorded explicitly in checkpoint_reuse. Selected files replace machine paths with aliases; raw-artifacts.json identifies original evidence. No timing constraints, timing closure, placement, routing or full-SoC formal equivalence are claimed.

The original default ABC attempt was deliberately stopped with SIGTERM at 2026-09-12 14:30:29 UTC after both independent mappings passed. It exited with status 1 and recorded `ABC failed with status F` following that signal. Partial raw logs remain preserved; `original-default-attempt` records the outcome and unchanged native hashes from the earlier in-run observation through the post-stop observation. That first observation occurred after original synthesis began and is not represented as pre-run evidence.
