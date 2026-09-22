# IP3 integration and validation scope

`DualRocketNVDLAConfig` composes `WithNVDLA("small", synthRAMs=false)`,
`WithNHugeCores(2)`, and the same `AbstractConfig` as IP1. IP3 is a separate
NVDLA SoC; it does not inherit IP2's FFT.

## Pinned implementation

| Source | Revision |
| --- | --- |
| Chipyard | `e602d917dcc495c58cabe906535e411707096c9c` |
| NVDLA wrapper | `d99ffdc79bbf9b86c6cad0c278a785d5802c8209` |
| Nested NVIDIA hardware | `8e06b1b9d85aab65b40d43d08eec5ea4681ff715` |

The wrapper already includes generated `vsrc/small` RTL. Its make target
combines those sources; rebuilding NVIDIA's historical RTL generator is not
needed to build this exact pinned implementation. The nested hardware checkout
supplies upstream references and license text.

## New blocks and connections

The `nv_small` implementation has INT8 convolution hardware (CDMA, 128-KiB
CBUF, CSC, two CMAC partitions, and CACC), SDP elementwise arithmetic, PDP
pooling, CDP lookup/local-response-normalization hardware, MCIF DMA, CFGROM,
and interrupt/control logic. The two CMAC partitions together implement
atomic channel/kernel dimensions C=8, K=8. Supported modes must be read from
the selected configuration; the full upstream register header also names
features that this small implementation does not contain.

In particular, the small SDP has BS/BN arithmetic and output conversion but
no SDP Y/LUT engine. The recorded integration patch defines its absent LUT
data/statistic readbacks as zero. CDP has a separate implemented LUT used by
the numerical tests.

* A 256-KiB **register aperture**, `0x10040000`–`0x1007ffff`, connects to PBUS
  through a TileLink width/fragment adapter and TileLink-to-APB bridge.
  This is address space, not 256 KiB of register storage.
* A 64-bit AXI4 DBB master connects through AXI buffers, ID indexing,
  fragmentation, user removal, AXI-to-TileLink conversion, and a TileLink
  buffer to SBUS. This system-side connection allows coherent requests
  through the existing CPU/L2 hierarchy.
* One NVDLA interrupt enters the subsystem interrupt bus and PLIC. Software
  test compilation derives source ID 1 from the generated DTS; UART uses source 2.
* NVDLA uses the synchronous SBUS domain. The wrapper assumes SBUS, PBUS,
  and interrupt logic share a clock. IP1's synchronous base configuration
  satisfies this assumption; no asynchronous domain has been added.
* There is no secondary CVSRAM AXI interface in the small configuration,
  and no BDMA engine selected by this implementation.

The emitted [device tree](artifacts/chipyard.harness.TestHarness.DualRocketNVDLAConfig.dts)
confirms harts 0/1, 32-KiB instruction and data caches per hart, a 512-KiB
shared L2, the 64-KiB scratchpad aperture at `0x08000000`, and the 256-MiB
external-memory window at `0x80000000`. The scratchpad is marked disabled
in the DTS memory-node status for operating-system memory discovery; the
[generated hierarchy](../rtl/top_module_hierarchy.json) contains its
`TLRAM_ScratchpadBank` hardware. Both scratchpad and external-memory accesses
pass from SBUS through L2 to MBUS; the scratchpad is not a direct SBUS endpoint.
The DTS also identifies UART, CLINT, PLIC,
boot ROM, JTAG debug, and clock/reset controls.

## Recorded wrapper fixes

`patches/0001-define-small-nvdla-axi-address-upper-bits.patch` explicitly
zero-extends nv_small's 32-bit memory addresses in its 64-bit wrapper outputs.
The upstream file otherwise connects only bits 31:0, leaving 63:32 undriven.

`patches/0002-define-nvdla-dbb-axi-metadata.patch` initializes all DBB request
fields, then sets incrementing burst mode and the real address/data fields.
The pinned AXI bundle has burst/lock/cache/protection/QoS fields without
defaults; the upstream wrapper leaves them unspecified. The patch keeps
normal nonexclusive requests and zero sideband metadata.

`patches/0003-define-small-sdp-lut-readbacks.patch` connects five 32-bit LUT
status inputs and one 16-bit LUT data input to explicit zeros in the small
SDP register instance. The upstream small implementation omits these six
connections because it has no SDP LUT datapath. Flattened synthesis exposed
176 undriven readback bits and failed its required `check -assert` gate.
The patch defines those absent-feature readbacks without adding a LUT engine
or changing the implemented CDP LUT. The corrected RTL is rebuilt and tested
separately from the preserved earlier attempts.

## Memories and physical implementation

`synthRAMs=false` selects simple synthesizable behavioral RAM arrays under
`vsrc/small/vmod/rams/fpga/model`. Despite the directory name, these files
do not instantiate FPGA block-RAM primitives. The alternate `synth` wrappers
refer to missing `nv_ram_*_logic` providers in this pinned source list.

The CBUF uses 64 instances of `nv_ram_rws_256x64`: 128 KiB in total, with
independent read and write addresses. IP1's installed single-port 1RW SRAM
macros cannot directly implement this 1R1W behavior. A synthesis report must
explicitly identify any logical memories left unmapped and cannot claim
completed memory-macro implementation or timing closure from an incomplete
macro mapping. Simulation uses the original behavioral arrays.

## Numerical workload

`tests/nvdla_test.c` is intended to run on both real Rocket harts in the full
SoC simulator. It has independent CPU arithmetic expectations, finite
completion loops, DMA buffer guards and a nonzero exit on mismatch/timeout.
It checks the selected SDP capability, verifies that an absent SDP LUT entry
reads zero after a nonzero write, and checks the six defined readbacks after
each completed SDP job in both register groups.

* Sixteen SDP jobs cover identity, signed ReLU, positive and negative bias,
  positive/negative/zero multiplication, affine arithmetic and signed INT8
  saturation. Shapes exercise one and multiple channel groups, strided rows,
  and memory bursts. Harts alternate ownership; hart 0 uses cached DRAM and
  hart 1 cached scratchpad. The PLIC pending/claim/clear path is checked.
* Two CDP jobs program linear tables for identity and doubled output. They
  check LUT programming, CDP DMA, input/output conversion and saturation.
  The square-sum and input-times-LUT multiplier stages are bypassed, so these
  jobs do not validate local-response-normalization arithmetic.
* Two direct 1x1 convolution jobs use one spatial position, C=8 and K=8.
  CPU dot products check eight output channels per job across CDMA, CBUF,
  CSC, both CMAC partitions, CACC and SDP output conversion.
* Two PDP jobs perform signed INT8 max and min pooling over a 2x2 window,
  independently comparing each of eight channels against CPU extrema.
* A corrupted expected value and a skipped operation-enable build are
  deliberate negative controls. They must fail for the intended mismatch
  and completion-timeout reasons; they are never counted as passing jobs.

Interrupt coverage is limited to polling PLIC pending state and checking
claim, device-status clearing, and completion. Machine interrupts remain
disabled (`mie=0`), so CPU interrupt trap delivery is untested. CDP,
convolution, and PDP completion checks poll device status with the device
interrupt masked. The convolution cases cover one spatial position and one
C=8/K=8 channel/kernel group, without padding, strided windows, batching,
weight reuse, or accumulator-overflow cases. CDP coverage uses linear LUTs
with the LRN square-sum and multiplier stages bypassed; PDP coverage uses
one unpadded 2x2 max/min window and excludes average pooling.

The optional standalone model uses the same jobs with an APB/AXI harness
and periodic memory backpressure. Its PLIC is emulated and it has no Rocket
CPUs or caches. Its results supplement the required full-SoC run and cannot
replace CPU/coherence/interrupt integration evidence.

This document describes intended coverage. Only archived simulation results
establish which jobs passed. It is not a complete neural-network inference
benchmark or exhaustive verification of every accelerator mode.
