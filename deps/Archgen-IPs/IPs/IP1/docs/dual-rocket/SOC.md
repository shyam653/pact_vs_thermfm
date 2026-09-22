# DualRocketConfig SoC Inventory

This inventory describes the hardware emitted by the exact composition and
commits in [CONFIGURATION.md](CONFIGURATION.md). It is based on the generated
device tree, memory map, L2 metadata, memory-interface file, top-level RTL,
and pinned generator definitions. It is not a proposed future configuration.

Archived generated evidence: [device tree](artifacts/chipyard.harness.TestHarness.DualRocketConfig.dts),
[memory map](artifacts/chipyard.harness.TestHarness.DualRocketConfig.memmap.json),
and [L2 metadata](artifacts/chipyard.harness.TestHarness.DualRocketConfig.l2.json).

## Processor Tiles

| Property | Emitted configuration |
| --- | --- |
| CPU count | Two Rocket tiles, hart IDs 0 and 1 |
| Integer architecture | RV64; single-instruction decode/retirement, in-order Rocket |
| Integer extensions | I, M, A, C; Zba, Zbb, Zbs enabled |
| Floating point | F and D, plus Zfh half precision; FPU present in each tile |
| Virtual memory | Sv39; machine, supervisor and user support |
| PMP | Eight entries per hart, four-byte granularity |
| Hardware execute breakpoints | One per hart |
| L1 instruction cache, per hart | 32 KiB, 8 ways, 64 sets, 64-byte blocks |
| L1 data cache, per hart | 32 KiB, 8 ways, 64 sets, 64-byte blocks |
| L1 D-cache implementation | Blocking configuration, `nMSHRs=0` |
| Instruction/data TLBs | 32 entries each, as reported by the DTS |

Both CPU nodes advertise this exact generated ISA string:

```text
rv64imafdcbzicsr_zifencei_zihpm_zfh_zba_zbb_zbs_xrocket
```

Do not interpret its `b` as support for every bit-manipulation extension.
The selected preset explicitly enables Zba/Zbb/Zbs, not Zbc. There is no
V vector extension, Zicboz, or Svnapot in this configuration. `xrocket` is
the generated Rocket-specific extension identifier, not a generic Spike
plugin. An unsupported-feature test can pass by accepting a trap; a test
name alone is not proof of extension support.

The cache geometry and arithmetic options are set by
[WithNHugeCores](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/Configs.scala#L15-L60).
Core defaults, including single-instruction decode/retirement, are in
[RocketCoreParams](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/rocket/RocketCore.scala#L15-L69).
The `cpu@0` and `cpu@1` nodes independently confirm the ISA, PMP, MMU,
breakpoint, TLB and cache properties above.

## Shared Memory System

| Resource | Configuration |
| --- | --- |
| Shared inclusive L2 | 512 KiB, unified, 8 ways, 1024 sets, 64-byte blocks |
| L2 coherence banks | One bank; four internal 64-bit data subbanks |
| L2 directory | Two coherent clients; 1024 x 144-bit logical memory |
| L2 MSHRs | Seven, as reported by the DTS |
| On-chip scratchpad | 64 KiB at `0x08000000`, on the memory bus |
| External main-memory window | 256 MiB at `0x80000000` |
| External memory interface | One AXI4 channel, 64-bit data, 32-bit addresses, 4-bit IDs |

The L2 metadata covers both main memory and the on-chip scratchpad. Its two
directory clients represent the coherent tile clients, not all fabric
requesters. The generation client map also lists instruction fetches,
debug and serial-link requesters. Those counts must not be confused.

The scratchpad's DTS node has `status = "disabled"`. This does **not** mean
the SRAM was removed: the memory map exposes its read/write/execute,
cacheable range; L2 metadata includes it; and the generated DUT contains
the `8192 x 64` scratchpad interface. Software using the DTS must account
for that status instead of assuming it is ordinary enabled boot RAM.

External DRAM capacity is an address-window contract. There is no 256 MiB
on-chip RAM, DDR controller, or DDR PHY inside ChipTop. The RTL harness
supplies the external memory model; an implemented system needs a suitable
external AXI memory subsystem.

## Buses

The coherent hierarchy uses TileLink buses with eight-byte data beats and
64-byte cache blocks. The generated external memory port is AXI4.

| Bus | Role and connection |
| --- | --- |
| SBUS | Tile/system fabric; connects toward the coherence manager and CBUS |
| Coherence manager | Shared inclusive L2 between SBUS and MBUS |
| MBUS | Backing-memory path to scratchpad and external memory conversion |
| CBUS | Control-side path from SBUS toward PBUS |
| PBUS | Peripheral path, including UART |
| FBUS | Front-side ingress, including the serial TileLink client, into SBUS |

Connections follow the pinned
[bus topology](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/subsystem/BusTopology.scala#L80-L112)
and [base bus parameters](https://github.com/chipsalliance/rocket-chip/blob/55bcad0f59436de98ea510334121de8546b9e9d7/src/main/scala/subsystem/Configs.scala#L30-L55).
This is the existing hierarchical shared-bus system, not a newly designed
network-on-chip or a pair of independent single-core SoCs.

## Address Map

Ranges below use inclusive end addresses, from the emitted memory map and
DTS. Register-window size is not storage capacity.

| Start | End | Size | Device/resource |
| --- | --- | --- | --- |
| `0x00000000` | `0x00000fff` | 4 KiB | Debug module |
| `0x00001000` | `0x00001fff` | 4 KiB | Boot-address register window |
| `0x00003000` | `0x00003fff` | 4 KiB | Error-response device |
| `0x00010000` | `0x0001ffff` | 64 KiB window | Boot ROM, read/execute |
| `0x00100000` | `0x00100fff` | 4 KiB | Tile clock-gater controls |
| `0x00110000` | `0x00110fff` | 4 KiB | Tile reset-setter controls |
| `0x02000000` | `0x0200ffff` | 64 KiB | CLINT |
| `0x02010000` | `0x02010fff` | 4 KiB | Inclusive L2 control registers |
| `0x08000000` | `0x0800ffff` | 64 KiB | On-chip scratchpad |
| `0x0c000000` | `0x0fffffff` | 64 MiB window | PLIC |
| `0x10020000` | `0x10020fff` | 4 KiB | SiFive-compatible UART |
| `0x80000000` | `0x8fffffff` | 256 MiB | External main-memory window |

The CLINT supplies software and timer interrupts to both harts. The PLIC
has one device interrupt source, UART interrupt 1, and M/S interrupt
contexts for each CPU. The generator's printed `4 harts` interrupt-map
heading refers to those four contexts; it does not mean four physical
CPU harts. There are no external top-level interrupt inputs selected.

The debug module exposes JTAG and system-bus access, with eight abstract
data words. A custom boot input and boot-address register support the
existing boot-selection mechanism. The Boot ROM window is 64 KiB, but
that is not a claim that its program occupies all 64 KiB.

## Interfaces and Limits

The emitted `ChipTop.sv` exposes UART RX/TX, one AXI memory interface,
custom boot, JTAG TCK/TMS/TDI/TDO/reset, chip reset, `clock_uncore`, a clock
tap, and one serial TileLink interface with a separate `serial_tl_0_clock_in`
input. The serial link uses 32-bit phits
and flits with decoupled ready/valid handshakes; it is not a one-bit UART.

The selected PHY is `DecoupledExternalSyncSerialPhyParams`. The generator
warns that it can deadlock under heavy traffic and recommends
`CreditedSourceSyncSerialPhyParams` when deadlock freedom is required.
The warning was retained, not waived or fixed. A short functional smoke
test, or a fast memory-loading regression, does not establish sustained
serial-link safety. The exact selection is in
[AbstractConfig's serial interface](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/config/AbstractConfig.scala#L80-L89).

No GPIO bank, I2C controller, SPI flash controller, Ethernet/NIC, block
device, RoCC accelerator, vector unit, or additional external MMIO master
or slave port was selected. Base-config binders for optional devices do
not instantiate those devices unless their parameters enable them.

Bus frequency settings are nominally 500 MHz and the DTS timebase is
500 kHz. The DTS CPU `clock-frequency` fields are zero, so they must not
be quoted as measured CPU clocks. ChipTop takes an external uncore clock;
the passthrough clock generator is not an on-chip PLL. The generated uncore
group uses synchronous reset, while JTAG has its separate reset interface.
These settings are generation/simulation intent, not a timing-closure or
silicon-frequency result.

## DUT Versus Simulation

The hardware analysis boundary is **ChipTop**, including both Rocket tiles,
shared L2, scratchpad, interconnect, boot/debug/interrupt logic, UART, serial
adapter and I/O cells. `ChipTop` instantiates `DigitalTop` as its system;
see the pinned [ChipTop implementation](https://github.com/ucb-bar/chipyard/blob/e602d917dcc495c58cabe906535e411707096c9c/generators/chipyard/src/main/scala/ChipTop.scala#L16-L33).

`TestHarness` and `TestDriver` surround the DUT for simulation. DRAMSim2/
SimDRAM backing memory, SimJTAG, UART stdout integration, simulated serial
host support, and unsynthesizable clock sources are test infrastructure,
not included ASIC hardware. The generated `htif` DTS node describes the
simulation host interface; it is not an additional memory-mapped silicon
peripheral in the address table. `+loadmem` is a simulator loading shortcut,
not a fabricated hardware memory-write port.

Synthesis must also distinguish logical SRAM interfaces from technology
macros. Compared with the one-core design, the directory grows from
`1024 x 136` to `1024 x 144` bits, with mask granularity changing from 17
to 18 bits; private L1 array instances are duplicated. Reusing the old
single-core SRAM adapter without checking these widths would be incorrect.
The emitted `NAME.top.mems.conf` is the source of interface shapes. Macro
selection, padding, validation and technology-specific results belong in
the separate synthesis report, not in architectural cache-capacity claims.

Functional RTL simulation uses the original behavioral memories. It does
not by itself verify a technology-mapped netlist, foundry SRAM timing,
pad-ring implementation, power, placement/routing, or timing closure.
