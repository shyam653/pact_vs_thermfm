# Supplemental standalone NVDLA simulation

A fresh native model build of the corrected RTL and final numerical source passed all 22 jobs for seeds **1** and **17**. Each run completed **16,762 engine-model cycles**. The complete 22-job marker sequence was checked against the numerical inventory, alongside exit zero and the final standalone PASS marker.

The shared boot helper verifies version, memory atom, SDP capability `0x18`, and zero absent-SDP-LUT readback after a nonzero write. Every SDP job also requires zero LUT data and all five zero counters in its selected register group. The separate supported CDP LUT identity/doubling jobs still pass.

This model instantiates `nvdla_small` with an APB driver and a backpressured AXI memory harness. Hart-labelled jobs run sequentially in the host harness; there are no Rocket CPUs or caches, and PLIC behavior is emulated. These results supplement the separate full-SoC campaign rather than establishing CPU, coherence or physical PLIC behavior.

Unlike the full-SoC generated main, this harness explicitly receives `+verilator+rand+reset+2`; both seed commands are preserved in [results](summary.json). [Build provenance](provenance.json) binds the corrected exported RTL, final numerical source/header/harness, Verilator version and exact fresh build command. Native SHA256 is recorded with the results. Compiler output, build exit and both full logs are included; binaries and object files remain external artifacts.

The earlier scalar source and pre-correction model evidence remain in [firmware history](../firmware-history/README.md) and [hardware history](../hardware-history/README.md). Their original results are not represented as runs of this revised source/model. [Export hashes](export-hashes.json) retain original and portable byte identities. Paths use `${REPO_ROOT}`, `${CHIPYARD_ROOT}` and `${STANDALONE_BUILD}` placeholders.
