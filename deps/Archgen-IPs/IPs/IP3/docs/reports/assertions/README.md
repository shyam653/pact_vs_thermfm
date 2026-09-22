# IP3 simulation assertion scope

The pinned Chipyard Makefile selects external-IP flags for NVDLA and omits Verilator `--assert`. This does **not** disable the generated Chipyard procedural monitor checks: the final model's C++ retains TileLink failure messages followed by `VL_STOP_MT`. TestDriver's cycle/failure stops also use procedural `$fatal`.

The [source inventory](source-inventory.json) covers all 529 exported HDL files. After comments and strings are stripped, it contains no explicit SystemVerilog `assert` or `assume` construct and 148 vendor `cover property` constructs. Those cover points require `ENABLE_FUNCPOINT`, which the [actual translation command](actual-verilator-command.txt) does not define.

Vendor `defs.v` defines `SYNTHESIS`; `ASSERT_ON` is absent. Preprocessing the vendor RTL with the actual simulation defines leaves zero active SVA constructs. Most vendor assertion-helper instances are excluded. Two clock-gate `nv_assert_no_x` instances remain, but the [selected helper definition](active-empty-vendor-helper.v) contains only ports and parameters, without checking logic. Adding `--assert` alone cannot enable excluded preprocessor branches. No coverage percentage or complete upstream vendor-assertion run is claimed.

The [small probe](probe.sv) was translated with and without `--assert` using the installed Verilator. Both generated models retain `PROC_ERROR` and `PROC_FATAL`; only the model built with `--assert` retains `ASSERT_ERROR`. This was a code-generation experiment, not an additional SoC simulation. [Commands](commands.json) and generated [without-assert](probe-without-assert.cpp)/[with-assert](probe-with-assert.cpp) code are preserved.

[Native monitor excerpts](native-monitor-evidence.json) identify actual generated C++ files by hash and show memory-port and system-bus checks retained in the official model. Their source hashes were rechecked after the native build completed. [Audit metadata](summary.json) records the simulator hash, tool version, source hashes, preprocessing command/result and capture times. The behavioral NVDLA software-oracle campaigns are documented separately in the numerical report.

Workspace and probe paths use `${REPO_ROOT}`, `${CHIPYARD_ROOT}` and `${PROBE_ROOT}` placeholders. To repeat the tiny experiment, copy `probe.sv` to `${PROBE_ROOT}/check.sv`, then run the preserved commands with real directories/tool paths. Full preprocessed vendor output and native model trees remain external artifacts; their hashes are retained. [Export hashes](export-hashes.json) distinguish original and portable bytes.

The HDL inventory, vendor preprocessing and native monitor evidence were recaptured for the corrected model containing the explicit SDP readback tieoffs. The small installed-Verilator tool-semantics probe is retained from its original capture; metadata distinguishes that time from the fresh model audit and completed native hash recheck.
