/* Minimal freestanding two-hart startup with coherent BSS initialization. */
    .section .text.init,"ax",@progbits
    .balign 64
    .globl _start
_start:
    csrwi mie, 0
    csrr s0, mhartid
    li t0, 2
    bgeu s0, t0, park
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    la sp, __stack_bottom
    addi t0, s0, 1
    slli t0, t0, 14
    add sp, sp, t0
    la t0, trap_entry
    csrw mtvec, t0
    bnez s0, wait_init
    la t0, __bss_start
    la t1, __bss_end
clear_bss:
    bgeu t0, t1, release_init
    sd zero, 0(t0)
    addi t0, t0, 8
    j clear_bss
release_init:
    fence rw, rw
    la t0, initialized
    li t1, 1
    sd t1, 0(t0)
wait_init:
    la t0, initialized
    ld t1, 0(t0)
    beqz t1, wait_init
    fence r, rw
    mv a0, s0
    call test_main
    j park
    .balign 4
trap_entry:
    csrr a0, mcause
    csrr a1, mepc
    csrr a2, mtval
    call trap_fail
park:
    j park

    .section .tohost,"aw",@progbits
    .balign 64
    .global tohost
    .type tohost,@object
    .size tohost,8
tohost: .dword 0
    .balign 64
    .global fromhost
    .type fromhost,@object
    .size fromhost,8
fromhost: .dword 0

    .section .data,"aw",@progbits
    .balign 64
initialized: .dword 0
