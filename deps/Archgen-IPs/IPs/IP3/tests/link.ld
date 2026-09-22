OUTPUT_ARCH("riscv")
ENTRY(_start)
PHDRS
{
  init PT_LOAD FLAGS(5);
  host PT_LOAD FLAGS(6);
  code PT_LOAD FLAGS(5);
  data PT_LOAD FLAGS(6);
}
SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) } :init
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) } :host
  . = ALIGN(0x1000);
  .text : { *(.text .text.*) } :code
  .rodata : { *(.rodata .rodata.*) } :code
  . = ALIGN(0x1000);
  .data : { *(.data .data.*) } :data
  .sdata : { __global_pointer$ = . + 0x800; *(.sdata .sdata.*) } :data
  . = ALIGN(64);
  __bss_start = .;
  .bss : { *(.sbss .sbss.*) *(.bss .bss.*) *(COMMON) } :data
  . = ALIGN(64);
  __bss_end = .;
  .stack (NOLOAD) : { __stack_bottom = .; . = . + 32768; __stack_top = .; } :data
  _end = .;
}
