/* SPDX-License-Identifier: Apache-2.0
 * Freestanding HTIF output. Only the hart owning the test may print/finish.
 * Include in one translation unit, with start.S and link.ld.
 */
#ifndef IP_TEST_RUNTIME_H
#define IP_TEST_RUNTIME_H
#include <stdint.h>
extern volatile uint64_t tohost, fromhost;
static uint64_t syscall_args[8] __attribute__((aligned(64)));
static char message[256];
static unsigned message_length;
static inline void fence(void) { __asm__ volatile ("fence iorw, iorw" ::: "memory"); }
static void text(const char *s) {
    while (*s && message_length < sizeof(message) - 1) message[message_length++] = *s++;
}
static void hex(uint64_t x) {
    const char *digits = "0123456789abcdef";
    text("0x");
    for (int shift = 60; shift >= 0; shift -= 4)
        if (message_length < sizeof(message) - 1) message[message_length++] = digits[(x >> shift) & 15];
}
static void print(void) {
    syscall_args[0] = 64;
    syscall_args[1] = 1;
    syscall_args[2] = (uintptr_t)message;
    syscall_args[3] = message_length;
    fence();
    tohost = (uintptr_t)syscall_args;
    while (!fromhost) { }
    fromhost = 0;
    fence();
    message_length = 0;
}
static void finish(unsigned code) __attribute__((noreturn));
static void finish(unsigned code) {
    fence();
    tohost = ((uint64_t)code << 1) | 1;
    for (;;) { }
}
void trap_fail(uint64_t cause, uint64_t epc, uint64_t value) {
    text("FAIL trap cause="); hex(cause); text(" pc="); hex(epc);
    text(" value="); hex(value); text("\n"); print(); finish(2);
}
#endif
