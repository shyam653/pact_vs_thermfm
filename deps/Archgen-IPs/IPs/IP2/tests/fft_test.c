/* SPDX-License-Identifier: Apache-2.0 */
#include <stdint.h>
#include "runtime.h"
#include "fft_vectors.h"

#ifndef FFT_HARTS
#define FFT_HARTS 2u
#endif
#ifndef FFT_NEGATIVE_CONTROL
#define FFT_NEGATIVE_CONTROL 0
#endif
#define FFT_REPEATS 2u
#define FFT_BASE ((uintptr_t)0x2400)
#define SPIN_LIMIT 2000000u

static volatile uint64_t turn;
static volatile uint64_t jobs_by_hart[2];
static void fail(const char *why, unsigned hart, unsigned job, unsigned lane,
                 uint64_t got, uint64_t expected) __attribute__((noreturn));
static void fail(const char *why, unsigned hart, unsigned job, unsigned lane,
                 uint64_t got, uint64_t expected) {
    text("FAIL FFT: "); text(why); text(" hart="); hex(hart);
    text(" job="); hex(job); text(" lane="); hex(lane);
    text(" got="); hex(got); text(" expected="); hex(expected); text("\n");
    print();
    finish(1);
}
static uint64_t read_lane(unsigned lane, int wide) {
    uintptr_t address = FFT_BASE + 8u * (lane + 1u);
    if (wide) return *(volatile uint64_t *)address;
    return *(volatile uint32_t *)address;
}
static void write_point(uint32_t value, int wide) {
    if (wide) *(volatile uint64_t *)FFT_BASE = 0xa5a5a5a500000000ull | value;
    else *(volatile uint32_t *)FFT_BASE = value;
}
static void wait_turn(unsigned wanted, unsigned hart) {
    for (unsigned spin = 0; spin < SPIN_LIMIT; ++spin) {
        if (__atomic_load_n(&turn, __ATOMIC_ACQUIRE) == wanted) return;
    }
    fail("ownership timeout", hart, wanted, 0, turn, wanted);
}
void test_main(unsigned hart) {
    if (hart >= FFT_HARTS) for (;;) { }
    if (hart == 0) {
        for (unsigned lane = 0; lane < 8; ++lane) {
            uint64_t got = read_lane(lane, 1);
            if (got) fail("reset output", hart, 0, lane, got, 0);
        }
    }
    const unsigned total = FFT_CASE_COUNT * FFT_HARTS * FFT_REPEATS;
    for (unsigned job = hart; job < total; job += FFT_HARTS) {
        wait_turn(job, hart);
        const unsigned index = (job / FFT_HARTS) % FFT_CASE_COUNT;
        const struct fft_case *c = &fft_cases[index];
        uint32_t previous[8];
        for (unsigned lane = 0; lane < 8; ++lane) previous[lane] = read_lane(lane, 0);
        for (unsigned lane = 0; lane < 7; ++lane) write_point(c->input[lane], job & 1u);
        fence();
        /* Seven samples must not publish a partial vector. */
        for (unsigned lane = 0; lane < 8; ++lane) {
            uint64_t got = read_lane(lane, 1);
            if (got != previous[lane]) fail("partial frame changed output", hart, job, lane, got, previous[lane]);
        }
        write_point(c->input[7], job & 1u);
        fence();
        /* Read immediately after the eighth write, with no expected-value polling.
         * The peripheral bus transactions exceed this combinational core's short
         * deserializer/output-register latency. Reverse order every other job. */
        for (unsigned step = 0; step < 8; ++step) {
            unsigned lane = (job & 2u) ? 7u - step : step;
            uint64_t expected = c->expected[lane];
            if (FFT_NEGATIVE_CONTROL && job == 0 && lane == 0) expected ^= 1u;
            uint64_t got = read_lane(lane, job & 1u);
            if (got != expected) {
                text(c->name); text(" ");
                fail("numerical mismatch", hart, job, lane, got, expected);
            }
            /* Result reads are non-destructive; also checks reserved upper bits. */
            got = read_lane(lane, 1);
            if (got != expected) fail("unstable result", hart, job, lane, got, expected);
        }
        jobs_by_hart[hart]++;
        fence();
        __atomic_store_n(&turn, job + 1u, __ATOMIC_RELEASE);
    }
    if (hart) for (;;) { }
    wait_turn(total, hart);
    for (unsigned owner = 0; owner < FFT_HARTS; ++owner)
        if (jobs_by_hart[owner] != FFT_CASE_COUNT * FFT_REPEATS)
            fail("hart coverage", hart, total, owner, jobs_by_hart[owner], FFT_CASE_COUNT * FFT_REPEATS);
    text(FFT_HARTS == 2 ? "PASS FFT dual-hart" : "PASS FFT single-hart");
    text(": bit-exact vectors, partial frames, repeated jobs, 32/64-bit MMIO; jobs=");
    hex(total); text("\n"); print(); finish(0);
}
