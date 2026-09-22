# IP3 NVDLA full-SoC simulation

All three full-SoC seeds passed the 22-job numerical workload: **66 accepted job executions**, with both negative controls rejected for their exact intended reasons.

Each normal run executes the same 22 jobs with CPU-calculated expected results on the complete dual-Rocket `DualRocketNVDLAConfig` simulator:

| Engine | Jobs per run | Numerical checks |
| --- | ---: | --- |
| SDP | 16 | Signed INT8 identity, ReLU, positive/negative bias, multiplication, affine arithmetic and saturation across several cube sizes |
| CDP | 2 | Linear lookup-table identity and doubled output with initialized inputs |
| Convolution | 2 | Direct 1x1 C8/K8 dot products through CDMA, CBUF, CSC, CMAC A/B, CACC and SDP |
| PDP | 2 | Signed INT8 maximum/minimum pooling over a 2x2 window |

Each hart completes 11 jobs with serialized accelerator ownership. SDP jobs alternate cached DRAM on hart 0 and the cached on-chip scratchpad on hart 1; CDP, convolution and pooling use DRAM from both harts. The tests compare accelerator output with scalar CPU calculations, check poisoned guards and padding, and exercise coherent DMA. SDP jobs also check the real PLIC pending, claim, device-status clear and completion sequence. The NVDLA interrupt number is compiled from the generated device tree, rather than assumed by the build script.

Before the jobs, firmware verifies SDP capability `0x18` and writes a nonzero value to the absent SDP LUT before requiring zero readback. After every SDP job it requires zero data readback and all five zero LUT counters from the selected register group. These checks exercise the six explicit zero tieoffs added by patch 0003; they do not imply SDP LUT support. The CDP LUT jobs exercise a separate supported datapath.

Two additional controls deliberately corrupt one expected output byte or omit the first engine enable. Both must fail with their precise intended diagnostic; a generic nonzero exit or simulator timeout is insufficient. The corrupted-answer control reported byte 64, got 128 versus expected 129, and exited 255 after 77.898 seconds. The skipped-enable control reported completion timeout at register offset `0x100c`, got 0 versus expected 1, and exited 255 after 392.409 seconds. Neither reached a simulator wall/cycle limit.

## Method and evidence

Normal campaigns use seeds 1, 2 and 3 with 3,000,000-cycle and 2,400-second wall bounds. Each campaign uses one simulator worker. The generated Verilator main does not select `randReset(2)`. The actual build enables seeded Chisel register/memory initialization; runtime seeds are recorded without claiming a different uninitialized-state mode. Tests use freestanding RV64 code, two-hart startup and HTIF output. `+loadmem` initializes simulated DRAM directly; CPUs still execute the boot ROM and programs against full RTL with DRAMSim2.

| Seed | Result | Completed jobs | Host wall seconds |
| --- | --- | ---: | ---: |
| 1 | PASS | 22 | 1747.681 |
| 2 | PASS | 22 | 1022.633 |
| 3 | PASS | 22 | 1267.784 |

Wall times are host simulation elapsed times with other validation work running concurrently. Successful full-SoC logs do not emit a cycle total; the recorded cycle values are bounds, not measured accelerator latency.

The accepted campaigns all use the same compiled source inventory and native simulator, SHA256 `ac906aabe883e14d65b06669b134ca5079d96ddcd462e82b4d0079b08a6cacf5`. Their normal ELF SHA256 is `09a42274e457294119ddc919da9e9f4432e8c404b9cc93b0795a06e7c73a2c56`. The generated device tree SHA256 is `9824c2fa39409c142db699205c8fd35bcd635bfe347cc4aa210259e18addc4dc`; its bytes remained unchanged through final native generation and test execution. Every final-source normal campaign passed on its first attempt, and both final-source controls produced their required diagnostic on their first attempt. No retry campaigns were needed.

The earlier byte-loop implementation exceeded its initial 900-second wall limit after five completed SDP jobs. A bounded instruction trace located continuing execution in buffer initialization. The final source initializes and compares the same 4,096 bytes with aligned 64-bit accesses; mismatched words are scanned in address order to report the exact first differing byte. The buffer-access optimization leaves valid-element calculations and checks, DMA register programming and interrupt checks unchanged. A focused C/C++ probe checked every byte position with varied bit positions, and a fresh standalone model passed all 22 jobs for both standalone seeds. The [firmware history](../firmware-history/README.md) preserves the original sources, build provenance, timeout, trace analysis and equivalence evidence; that obsolete source/ELF attempt is excluded from the accepted final-source counts.

The intermediate native model passed one 22-job seed and both controls before synthesis exposed 176 undriven bits in absent-SDP-LUT readbacks. The corrected RTL ties only those six inputs to typed zero, and the final firmware adds the checks described above. [Hardware history](../hardware-history/README.md) preserves that earlier model's actual passing/failing outcomes and source/native identities. They are excluded from final acceptance. A fresh [final-source helper probe](../helper-equivalence-final/README.md) confirms the unchanged buffer helpers in the strengthened firmware.

From the repository root, reproduce the accepted campaigns against the generated device tree and native simulator as follows. Set `CY` to the pinned Chipyard checkout and `RISCV_GCC` to its RISC-V compiler, then use a fresh output directory for each command. The frozen [test README](../../../tests/README.md) and the commands below record the final full-SoC campaign bounds.

```bash
python3 IPs/IP3/scripts/build-nvdla-tests.py \
  --dts "$CY/sims/verilator/generated-src/chipyard.harness.TestHarness.DualRocketNVDLAConfig/chipyard.harness.TestHarness.DualRocketNVDLAConfig.dts" \
  --chipyard-root "$CY" --cc "$RISCV_GCC" --output build/IP3/nvdla-tests-sdp-tieoff

for seed in 1 2 3; do
  python3 IPs/IP2/scripts/run-regression.py \
    build/IP3/nvdla-tests-sdp-tieoff/manifest.tsv "build/IP3/nvdla-sdp-tieoff-seed$seed" \
    --chipyard-root "$CY" \
    --simulator "$CY/sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig" \
    --jobs 1 --max-cycles 3000000 --timeout 2400 --seed "$seed"
done

python3 IPs/IP2/scripts/run-regression.py \
  build/IP3/nvdla-tests-sdp-tieoff/negative-control.tsv build/IP3/nvdla-sdp-tieoff-controls \
  --chipyard-root "$CY" \
  --simulator "$CY/sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig" \
  --jobs 1 --max-cycles 3000000 --timeout 2400 --seed 1
```

The control runner returns nonzero for the intended failures; inspect their exact archived diagnostics before interpreting that exit status.

[Aggregate evidence](summary.json) records every selected and prior attempt, exact job markers, simulator/ELF/source hashes, compiled DTS identity and negative-control diagnostics. `campaigns/` contains complete command files, logs, results, settings and manifests. `build/` contains compiler commands/logs and the exact compiled device tree; binaries and native build trees remain external artifacts. Original and portable exported bytes have separate [hashes](export-hashes.json).

The separate [CPU regression report](../cpu/README.md) covers the frozen CPU software inventory. The [standalone report](../standalone/README.md) is supplemental APB/AXI-model evidence using the same numerical source; it does not replace these CPU, coherent fabric or PLIC checks.

## Coverage limits

PLIC operations are polled with CPU interrupt enables clear. Interrupt-trap delivery and a Linux driver are not tested. Convolution covers one 1x1 spatial point at C=K=8, without a full network, larger kernels, Winograd, batching or compressed weights. CDP uses linear LUTs with square-sum and input-times-LUT multiplication bypassed; it does not validate local-response-normalization arithmetic. Pooling covers maximum/minimum, not average mode or every padding/stride case.

This is INT8 `nv_small`; the bundled large INT16, BDMA and CVSRAM traces are not directly applicable. See [upstream applicability](../../UPSTREAM_TESTS.md) and [integration details](../../INTEGRATION.md). Generated Chipyard procedural monitor stops remain active, while selected upstream vendor assertion/coverage checks are excluded; see the [assertion-scope audit](../assertions/README.md). These bounded numerical checks do not establish exhaustive functional coverage, formal proof, gate-level behavior, timing or physical signoff.
