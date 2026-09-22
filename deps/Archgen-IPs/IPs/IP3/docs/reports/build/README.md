# RTL generation and corrected native simulator build

Generation, native simulator make and the overall wrapper each finished with
exit zero. This build includes all three published integration patches:
explicit AXI address/metadata fields and defined zero readbacks for the
absent small SDP LUT. Native make compiled the C++ model and linked the
simulator in 11 minutes 31.44 seconds with two build jobs. This is an
observation of this provisioned workspace, not a clean toolchain bootstrap.

The first and repeated native generation produced the same 529 HDL source
files, hierarchy, memory configuration and DTS. The final byte recheck also
includes the original Rocket license copied by the exporter: 532 files in
total. `final-generation-recheck.json` records that check before compilation
finished; the separate exit files establish subsequent build completion.
`generation-change-audit.json` compares the archived original build with the
corrected build: only `nvdla_small.preprocessed.v` changed among those 532
files. The generated DTS is unchanged.

`provenance.txt` records pins, installed configuration, worktree state, tool
versions and start/end timestamps. `generator.patch` records the complete
three-patch source delta; `patches.sha256` identifies the exact published
patch bytes. `simulator.sha256` identifies the corrected binary used for the
accepted full-SoC CPU and NVDLA campaigns. The matching configuration is
also copied here. Earlier simulator results remain separate in the
[hardware history](../hardware-history/README.md) and
[interrupted CPU history](../cpu-original-native/README.md).

The complete build logs retain upstream warnings. The native Makefile uses
its normal external-IP flags, including `--max-num-width 1048576`; it omits
`--assert`. The [assertion audit](../assertions/README.md) explains active
procedural protocol checks and excluded vendor assertion macros. Build
success alone is not functional verification; accepted simulation evidence
is in the neighboring reports.

Export changes only the known workspace and Chipyard path byte sequences to
`${REPO_ROOT}` and `${CHIPYARD_ROOT}`. `export-hashes.json` records original and
exported SHA-256 values; original HDL and license bytes remain unchanged.
