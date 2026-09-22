/* Freestanding HTIF test using the riscv-tests env/p memory map. */
  .section .text.init,"ax",@progbits
  .align 6
  .globl _start
_start:
  csrr s0, mhartid
  csrwi mie, 0
  la t0, trap_handler
  csrw mtvec, t0
  li t0, 2
  bgeu s0, t0, park

  /* Separate cache lines must become visible to the other coherent tile. */
  la s1, hart_markers
  slli t0, s0, 6
  add s1, s1, t0
  li t1, 0x12340000
  add t1, t1, s0
  sd t1, 0(s1)
  fence rw, rw
  li s2, 1
  sll s2, s2, s0
  la t0, arrived
  amoor.d.aqrl zero, s2, (t0)
  li t2, 65536
wait_arrived:
  ld t1, 0(t0)
  li t3, 3
  beq t1, t3, check_peer
  addi t2, t2, -1
  bnez t2, wait_arrived
  li a0, 1
  j fail

check_peer:
  fence r, rw
  xori t0, s0, 1
  slli t1, t0, 6
  la t2, hart_markers
  add t2, t2, t1
  ld t3, 0(t2)
  li t4, 0x12340000
  add t4, t4, t0
  beq t3, t4, atomic_start
  li a0, 2
  j fail

atomic_start:
  la t0, shared_counter
  li t1, 1
  li t2, 128
atomic_loop:
  amoadd.d.aqrl zero, t1, (t0)
  addi t2, t2, -1
  bnez t2, atomic_loop
  la t0, finished
  amoor.d.aqrl zero, s2, (t0)
  li t2, 65536
wait_finished:
  ld t1, 0(t0)
  li t3, 3
  beq t1, t3, check_counter
  addi t2, t2, -1
  bnez t2, wait_finished
  li a0, 3
  j fail

check_counter:
  fence r, rw
  la t0, shared_counter
  ld t1, 0(t0)
  li t2, 256
  beq t1, t2, mark_passed
  li a0, 4
  j fail

mark_passed:
  la t0, passed
  amoor.d.aqrl zero, s2, (t0)
  bnez s0, park
  li t2, 65536
wait_passed:
  ld t1, 0(t0)
  li t3, 3
  beq t1, t3, print_success
  addi t2, t2, -1
  bnez t2, wait_passed
  li a0, 5
  j fail

print_success:
  fence rw, rw
  la t0, write_request
  la t1, tohost
  sd t0, 0(t1)
  la t0, fromhost
wait_print:
  ld t2, 0(t0)
  beqz t2, wait_print
  sd zero, 0(t0)
  fence rw, rw
  li t0, 1
  sd t0, 0(t1)
  j park

  .align 2
trap_handler:
  li a0, 6
fail:
  slli a0, a0, 1
  ori a0, a0, 1
  la t0, tohost
  fence rw, rw
  sd a0, 0(t0)
park:
  j park

  .section .tohost,"aw",@progbits
  .align 6
  .global tohost
tohost: .dword 0
  .size tohost, 8
  .align 6
  .global fromhost
fromhost: .dword 0
  .size fromhost, 8

  .section .data,"aw",@progbits
  .align 6
hart_markers:
  .dword 0
  .zero 56
  .dword 0
  .zero 56
arrived: .dword 0
  .align 6
shared_counter: .dword 0
  .align 6
finished: .dword 0
  .align 6
passed: .dword 0
  .align 6
write_request:
  .dword 64, 1, success_message, success_message_end-success_message
  .dword 0, 0, 0, 0
success_message:
  .ascii "PASS dual-hart: hart0+hart1, peer data visible, 256 atomic increments\n"
success_message_end:
