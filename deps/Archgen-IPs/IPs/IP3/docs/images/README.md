# NVDLA block diagram

`block-diagram-v3.png` shows `DualRocketNVDLAConfig`. Orange marks additions
relative to IP1. It is a simplified architectural view: connectors at the
NVDLA group boundary summarize the MCIF DMA and APB control paths. The PLIC
connection carries one device interrupt. Clock/reset and debug distribution
are summarized instead of drawing individual wires.

The built-in image generation tool produced this PNG. The initial prompt is
in `prompt.txt`; `edit-prompt.txt` records the readability correction. The image
does not represent physical placement, timing closure or test results.

`memory-topology-edit-prompt.txt` records the correction verified against
`DigitalTop.sv`: SBUS → L2 → MBUS, branching to scratchpad and the AXI memory
port. `bus-label-edit-prompt.txt` records the combined CBUS/PBUS label; NVDLA
control and UART attach to PBUS while CLINT and PLIC attach to CBUS. The
original intermediate images are retained outside the publication. The final
PNG preserves both corrections and has been visually inspected.
