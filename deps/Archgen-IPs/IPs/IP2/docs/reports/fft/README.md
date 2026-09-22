# FFT simulation results

**All nine normal simulations passed**, using simulator seeds 1, 2 and 3.
Each seed ran the single-hart test, the two-hart test, and Chipyard's original
known-answer FFT test. Together they completed **2,433 transforms**.

The 135-vector corpus includes 94 bounded vectors independently compared with
a direct complex DFT and 41 cases testing finite-width full-scale arithmetic.
The maximum observed component difference in the bounded DFT comparison was
0.9994 output LSB (the declared test bound is 4 LSB). This is a measured result
for this corpus, not a universal precision guarantee.

Repeated transforms, both harts with serialized ownership, partial-frame output
stability, immediate and repeated output reads, and 32/64-bit MMIO accesses all
passed. The separately built corrupted-answer negative control failed for the
intended first-output numerical mismatch, rather than a timeout or tool failure.

`summary.json` contains per-run outcomes, simulator/ELF identities, log hashes
and the numerical reference summary. `build/` retains the complete vector set,
generated header, compiler commands/logs, source hashes and build provenance.
Export rechecked these against the current source and executable bytes. Known
local paths are normalized, with original and exported hashes kept separately.

See [`tests/README.md`](../../../tests/README.md) for reproduction and the
fixed-point overflow/completion contract. These tests exercise the original
behavioral RTL, not a technology-mapped gate-level netlist or fabricated chip.
