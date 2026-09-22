# Generated dual-Rocket FFT SoC

`chipyard.DualRocketFFTConfig` adds the pinned FFT generator to the same
`WithNHugeCores(2) ++ AbstractConfig` composition used by IP1. This page describes
the emitted hardware, not a proposed future configuration. See the generated
[device tree](artifacts/chipyard.harness.TestHarness.DualRocketFFTConfig.dts),
[memory map](artifacts/chipyard.harness.TestHarness.DualRocketFFTConfig.memmap.json),
and [block diagram](images/block-diagram.png).

| Block | Configuration |
| --- | --- |
| CPUs | Two in-order RV64 Rocket tiles, hart IDs 0 and 1, each with FPU |
| ISA | I/M/A/F/D/C, Zfh, Zba/Zbb/Zbs; Sv39 virtual memory |
| L1 per hart | 32 KiB instruction and 32 KiB data cache, 8 ways each |
| Shared inclusive L2 | 512 KiB, 8 ways, one coherence bank |
| Scratchpad | 64 KiB at `0x08000000` |
| Main memory | 256 MiB external address window at `0x80000000` |
| External memory port | One AXI4 channel, 64-bit data; controller/PHY external |
| Existing control/I/O | UART, CLINT, PLIC, JTAG debug, boot ROM/control, serial TileLink, clock/reset controls |
| Added accelerator | One shared memory-mapped 8-point complex FFT on PBUS |

The scratchpad remains physically present even though its device-tree node is
marked disabled. The PLIC still has only the UART device interrupt: the FFT
has no interrupt. The selected serial TileLink PHY retains the upstream warning
about possible deadlock under heavy traffic. No physical timing, power or
manufacturing signoff is claimed.

## FFT data path and software interface

The generated hierarchy contains `LazyTail`, `Tail`, `Deserialize`, `FFT`,
`DirectFFT`, and `Unscramble`. Eight serially written complex input samples are
assembled into a vector, transformed and reordered, then latched into eight
output holding registers. The FFT adds register storage, not another SRAM macro.

| Address | Access | Meaning |
| --- | --- | --- |
| `0x2400` | Write | Next packed 32-bit complex input sample |
| `0x2408 + 8*i`, `i=0..7` | Read | Packed 32-bit complex output `i` |
| `0x2400..0x24ff` | MMIO aperture | Entire 256-byte decoded peripheral window |

The 16-bit real component occupies bits 31:16; the 16-bit imaginary component
occupies bits 15:0. Both are signed two's-complement fixed point with eight
fractional bits. The FFT is unnormalized. It has no programmable size, start/done
register, interrupt or DMA engine in this configuration. The output holding
registers retain the previous result until a complete new transform arrives.

Software must serialize access across the entire input/output transaction.
Sharing only individual MMIO writes between harts would mix their input frames.
The tests exercise both cores taking ownership in turn; this is one accelerator,
not one private FFT per CPU.

Finite-width intermediate arithmetic wraps rather than saturates. The pinned
complex multiplier also truncates its input pre-add/subtract operations to
16 bits. Full-scale complex inputs can therefore differ from an ideal
infinite-precision DFT. See the [numerical tests and limits](../tests/README.md)
for the exact reference model and the separately checked bounded-input DFT cases.

## Simulation and implementation boundary

`ChipTop` is the hardware DUT. `TestHarness`, `TestDriver`, DRAMSim2, simulated
JTAG and host loading support are simulation infrastructure. Exported RTL retains
these original resources, but lint and synthesis select the `ChipTop` hierarchy.
The external address window is not on-chip DRAM. The input clock is external;
there is no on-chip PLL added by this configuration.
