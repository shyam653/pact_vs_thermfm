/* SPDX-License-Identifier: Apache-2.0 */
#include <stdint.h>
#include "nvdla.h"

#ifndef NVDLA_IRQ
#error NVDLA_IRQ must come from the generated device tree
#endif
#ifndef NVDLA_NEGATIVE_CONTROL
#define NVDLA_NEGATIVE_CONTROL 0
#endif
#ifndef NVDLA_SKIP_ENABLE
#define NVDLA_SKIP_ENABLE 0
#endif
#define NVDLA_BASE ((uintptr_t)0x10040000)
#define PLIC_BASE ((uintptr_t)0x0c000000)
#define SPIN_LIMIT 2000000u
#ifndef NVDLA_POLL_LIMIT
#define NVDLA_POLL_LIMIT SPIN_LIMIT
#endif
#define BUFFER_SIZE 4096u
#define GUARD_SIZE 64u

extern volatile uint64_t tohost, fromhost;
static volatile uint64_t turn;
static volatile uint64_t jobs_by_hart[2];
static uint8_t src_storage[BUFFER_SIZE] __attribute__((aligned(64)));
static uint8_t dst_storage[BUFFER_SIZE] __attribute__((aligned(64)));
static uint8_t weight_storage[256] __attribute__((aligned(64)));
static uint8_t expected[BUFFER_SIZE] __attribute__((aligned(64)));
static uint64_t syscall_args[8] __attribute__((aligned(64)));
static char message[256];
static unsigned message_length;

#ifdef NVDLA_STANDALONE
/* Optional host harness routes only MMIO; full-SoC builds use real accesses. */
static uint32_t model_read(uintptr_t addr);
static void model_write(uintptr_t addr, uint32_t value);
static inline void fence(void) { __asm__ volatile ("" ::: "memory"); }
static inline uint32_t rd(uintptr_t addr) { return model_read(addr); }
static inline void wr(uintptr_t addr, uint32_t val) { model_write(addr, val); }
#else
static inline void fence(void) { __asm__ volatile ("fence iorw, iorw" ::: "memory"); }
static inline uint32_t rd(uintptr_t addr) { return *(volatile uint32_t *)addr; }
static inline void wr(uintptr_t addr, uint32_t val) { *(volatile uint32_t *)addr = val; }
#endif
static inline uint32_t reg_read(unsigned off) { return rd(NVDLA_BASE + off); }
static inline void reg_write(unsigned off, uint32_t val) { wr(NVDLA_BASE + off, val); }
static void text(const char *s) {
    while (*s && message_length < sizeof(message)-1) message[message_length++] = *s++;
}
static void hex(uint64_t value) {
    static const char digits[] = "0123456789abcdef";
    text("0x");
    for (int i = 60; i >= 0; i -= 4)
        if (message_length < sizeof(message)-1) message[message_length++] = digits[(value >> i) & 15];
}
static void print(void) {
#ifdef NVDLA_STANDALONE
    fwrite(message, 1, message_length, stdout);
    fflush(stdout);
#else
    syscall_args[0] = 64;
    syscall_args[1] = 1;
    syscall_args[2] = (uintptr_t)message;
    syscall_args[3] = message_length;
    fence();
    tohost = (uintptr_t)syscall_args;
    while (!fromhost) { }
    fromhost = 0;
    fence();
#endif
    message_length = 0;
}
static void finish(unsigned code) __attribute__((noreturn));
static void finish(unsigned code) {
#ifdef NVDLA_STANDALONE
    exit(code);
#else
    fence();
    tohost = ((uint64_t)code << 1) | 1;
    for (;;) { }
#endif
}
static void fail(const char *why, unsigned hart, unsigned job, unsigned index,
                 uint64_t got, uint64_t wanted) __attribute__((noreturn));
static void fail(const char *why, unsigned hart, unsigned job, unsigned index,
                 uint64_t got, uint64_t wanted) {
    text("FAIL NVDLA: "); text(why); text(" hart="); hex(hart);
    text(" job="); hex(job); text(" index="); hex(index);
    text(" got="); hex(got); text(" expected="); hex(wanted);
    text("\n"); print(); finish(1);
}
/* All buffers are 64-byte aligned and contain an integral number of words.
 * may_alias permits word access to their uint8_t storage without violating
 * GCC's strict-aliasing rules. Every poison/guard byte remains covered. */
typedef uint64_t buffer_word __attribute__((__may_alias__));
#ifdef __cplusplus
static_assert(BUFFER_SIZE % sizeof(buffer_word) == 0, "whole buffer words");
#else
_Static_assert(BUFFER_SIZE % sizeof(buffer_word) == 0, "whole buffer words");
#endif
static void initialize_buffers(volatile uint8_t *src, volatile uint8_t *dst) {
    volatile buffer_word *source = (volatile buffer_word *)src;
    volatile buffer_word *destination = (volatile buffer_word *)dst;
    buffer_word *reference = (buffer_word *)expected;
    for (unsigned i = 0; i < BUFFER_SIZE / sizeof(buffer_word); ++i) {
        source[i] = UINT64_C(0x3c3c3c3c3c3c3c3c);
        destination[i] = UINT64_C(0xa5a5a5a5a5a5a5a5);
        reference[i] = UINT64_C(0xa5a5a5a5a5a5a5a5);
    }
}
static void check_buffer(const char *why, unsigned hart, unsigned job,
                         volatile uint8_t *dst) {
    volatile buffer_word *destination = (volatile buffer_word *)dst;
    const buffer_word *reference = (const buffer_word *)expected;
    for (unsigned i = 0; i < BUFFER_SIZE / sizeof(buffer_word); ++i) {
        uint64_t got = destination[i], wanted = reference[i];
        if (got != wanted) {
            /* Character access to the captured words preserves byte order on
             * both the RISC-V target and the standalone host. Scan in address
             * order to retain the original first-mismatch byte diagnosis. */
            const unsigned char *g = (const unsigned char *)&got;
            const unsigned char *w = (const unsigned char *)&wanted;
            for (unsigned byte = 0; byte < sizeof(buffer_word); ++byte)
                if (g[byte] != w[byte])
                    fail(why, hart, job, i * sizeof(buffer_word) + byte, g[byte], w[byte]);
        }
    }
}
void trap_fail(uint64_t cause, uint64_t epc, uint64_t value) {
    text("FAIL NVDLA trap cause="); hex(cause); text(" pc="); hex(epc);
    text(" value="); hex(value); text("\n"); print(); finish(2);
}
static void wait_turn(unsigned wanted, unsigned hart) {
    for (unsigned spin = 0; spin < SPIN_LIMIT; ++spin)
        if (__atomic_load_n(&turn, __ATOMIC_ACQUIRE) == wanted) return;
    fail("ownership timeout", hart, wanted, 0, turn, wanted);
}
static void poll(unsigned off, uint32_t mask, uint32_t wanted, unsigned hart, unsigned job) {
    uint32_t got = 0;
    for (unsigned spin = 0; spin < NVDLA_POLL_LIMIT; ++spin) {
        got = reg_read(off);
        if ((got & mask) == wanted) return;
    }
    fail("completion timeout", hart, job, off, got, wanted);
}

/* nv_small has no SDP LUT. Its explicit zero tieoffs cover data readback and
 * the five counters captured when the selected register group completes.
 * This is separate from the supported CDP LUT exercised below.
 */
static void check_absent_sdp_lut(unsigned hart, unsigned job) {
    static const unsigned offsets[] = {
        SDP_S_LUT_ACCESS_DATA_0,
        SDP_D_PERF_LUT_UFLOW_0, SDP_D_PERF_LUT_OFLOW_0,
        SDP_D_PERF_LUT_HYBRID_0, SDP_D_PERF_LUT_LE_HIT_0,
        SDP_D_PERF_LUT_LO_HIT_0
    };
    for (unsigned i = 0; i < sizeof(offsets) / sizeof(offsets[0]); ++i) {
        uint32_t got = reg_read(offsets[i]);
        if (got != 0) fail("absent SDP LUT readback", hart, job, offsets[i], got, 0);
    }
}

static void check_small_configuration(unsigned hart) {
    uint32_t version = reg_read(NVDLA_CFGROM_CFGROM_HW_VERSION_0);
    if (version != 0x10001) fail("hardware version", hart, 0, 0, version, 0x10001);
    uint32_t atomic = reg_read(NVDLA_CFGROM_CFGROM_SDP_RDMA_BASE_ATOMIC_M_0);
    if (atomic != 8) fail("small memory atom", hart, 0, 0, atomic, 8);
    uint32_t capability = reg_read(NVDLA_CFGROM_CFGROM_SDP_CAP_COMPAT_0);
    if (capability != 0x18) fail("small SDP capability", hart, 0,
                                NVDLA_CFGROM_CFGROM_SDP_CAP_COMPAT_0, capability, 0x18);
    /* Write a nonzero value to absent LE-table entry zero, then read it.
     * The selected small implementation must return its defined zero.
     */
    reg_write(SDP_S_LUT_ACCESS_CFG_0, 1u << SDP_S_LUT_ACCESS_CFG_0_LUT_ACCESS_TYPE_SHIFT);
    reg_write(SDP_S_LUT_ACCESS_DATA_0, 0xa55a);
    reg_write(SDP_S_LUT_ACCESS_CFG_0, 0);
    fence();
    check_absent_sdp_lut(hart, 0);
}

/* CPU oracle: no data or expected results are derived from accelerator output.
 * Atomic channel groups contain eight INT8 elements in nv_small. Padding
 * between rows/surfaces and guards must remain at their poison values. */
struct test_case { unsigned width, height, channels; int bias, scale, relu; };
static const struct test_case cases[] = {
    {1, 1, 8, 0, 1, 0},       /* identity incl. signed extremes */
    {3, 2, 8, 0, 1, 1},       /* ReLU */
    {8, 2, 16, 7, 1, 0},      /* positive bias + upper saturation */
    {17, 3, 24, -9, 1, 0},    /* negative bias + lower saturation, bursts */
    {8, 3, 16, 0, 2, 0},      /* multiplication with both saturations */
    {3, 2, 24, 0, -1, 0},     /* signed negative multiplication */
    {17, 2, 8, 4, 3, 1},      /* affine followed by ReLU */
    {8, 2, 16, 13, 0, 0},     /* zero result must overwrite poison */
};
#define CASE_COUNT (sizeof(cases)/sizeof(cases[0]))

static int sample(unsigned index, unsigned job) {
    static const int extremes[8] = {-128, -127, -1, 0, 1, 63, 126, 127};
    if (index < 8) return extremes[index];
    return (int)((index * 73u + job * 29u + 11u) & 255u) - 128;
}
static uint8_t oracle(int input, const struct test_case *c) {
    int value = (input + c->bias) * c->scale;
    if (c->relu && value < 0) value = 0;
    if (value > 127) value = 127;
    if (value < -128) value = -128;
    return (uint8_t)value;
}
static void run_job(unsigned hart, unsigned job) {
    const struct test_case *c = &cases[job / 2];
    unsigned bank = job & 1u;
    unsigned stride = (c->width * 8u + 63u) & ~63u;
    unsigned surface = stride * c->height;
    /* Hart 0 uses cached DRAM; hart 1 uses cached on-chip scratchpad. */
    volatile uint8_t *src = hart ? (volatile uint8_t *)0x08001000 : src_storage;
    volatile uint8_t *dst = hart ? (volatile uint8_t *)0x08003000 : dst_storage;
    initialize_buffers(src, dst);
    unsigned elem = 0;
    for (unsigned g = 0; g < c->channels / 8u; ++g)
        for (unsigned y = 0; y < c->height; ++y)
            for (unsigned x = 0; x < c->width; ++x)
                for (unsigned k = 0; k < 8; ++k) {
                    unsigned offset = GUARD_SIZE + g * surface + y * stride + x * 8u + k;
                    int value = sample(elem++, job);
                    src[offset] = (uint8_t)value;
                    expected[offset] = oracle(value, c);
                }
    if (NVDLA_NEGATIVE_CONTROL && job == 0) expected[GUARD_SIZE] ^= 1u;
    fence(); /* Make CPU dirty cache data visible to coherent DMA requests. */

    unsigned context = hart * 2u; /* Generated M/S contexts for each Rocket hart. */
    uintptr_t claim = PLIC_BASE + 0x200004u + context * 0x1000u;
    wr(PLIC_BASE + NVDLA_IRQ * 4u, 1);
    wr(PLIC_BASE + 0x2000u + context * 0x80u, 1u << NVDLA_IRQ);
    wr(claim - 4u, 0);
    reg_write(GLB_S_INTR_MASK_0, 0xffffffffu ^ (1u << bank));
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    poll(GLB_S_INTR_STATUS_0, 3u, 0, hart, job);
    reg_write(SDP_S_POINTER_0, bank);
    reg_write(SDP_RDMA_S_POINTER_0, bank);

    reg_write(SDP_RDMA_D_DATA_CUBE_WIDTH_0, c->width - 1u);
    reg_write(SDP_RDMA_D_DATA_CUBE_HEIGHT_0, c->height - 1u);
    reg_write(SDP_RDMA_D_DATA_CUBE_CHANNEL_0, c->channels - 1u);
    reg_write(SDP_RDMA_D_SRC_BASE_ADDR_LOW_0, (uintptr_t)src + GUARD_SIZE);
    reg_write(SDP_RDMA_D_SRC_BASE_ADDR_HIGH_0, 0);
    reg_write(SDP_RDMA_D_SRC_LINE_STRIDE_0, stride);
    reg_write(SDP_RDMA_D_SRC_SURFACE_STRIDE_0, surface);
    reg_write(SDP_RDMA_D_BRDMA_CFG_0, 1); /* Bias/multiplier from registers. */
    reg_write(SDP_RDMA_D_NRDMA_CFG_0, 1);
    reg_write(SDP_RDMA_D_ERDMA_CFG_0, 1);
    reg_write(SDP_RDMA_D_FEATURE_MODE_CFG_0, 0); /* Offline INT8 -> INT8. */
    reg_write(SDP_RDMA_D_SRC_DMA_CFG_0, 1); /* MCIF, no CVSRAM in nv_small. */
    reg_write(SDP_D_DATA_CUBE_WIDTH_0, c->width - 1u);
    reg_write(SDP_D_DATA_CUBE_HEIGHT_0, c->height - 1u);
    reg_write(SDP_D_DATA_CUBE_CHANNEL_0, c->channels - 1u);
    reg_write(SDP_D_DST_BASE_ADDR_LOW_0, (uintptr_t)dst + GUARD_SIZE);
    reg_write(SDP_D_DST_BASE_ADDR_HIGH_0, 0);
    reg_write(SDP_D_DST_LINE_STRIDE_0, stride);
    reg_write(SDP_D_DST_SURFACE_STRIDE_0, surface);
    /* BS pipeline: ALU sum -> multiplication -> optional ReLU. */
    reg_write(SDP_D_DP_BS_CFG_0, (2u << 2) | (c->relu ? 0u : (1u << 6)));
    reg_write(SDP_D_DP_BS_ALU_CFG_0, 0);
    reg_write(SDP_D_DP_BS_ALU_SRC_VALUE_0, (uint16_t)c->bias);
    reg_write(SDP_D_DP_BS_MUL_CFG_0, 0);
    reg_write(SDP_D_DP_BS_MUL_SRC_VALUE_0, (uint16_t)c->scale);
    reg_write(SDP_D_DP_BN_CFG_0, 1);
    reg_write(SDP_D_DP_EW_CFG_0, 1);
    reg_write(SDP_D_FEATURE_MODE_CFG_0, 0);
    reg_write(SDP_D_DST_DMA_CFG_0, 1);
    reg_write(SDP_D_DST_BATCH_STRIDE_0, 0);
    reg_write(SDP_D_DATA_FORMAT_0, 0);
    reg_write(SDP_D_CVT_OFFSET_0, 0);
    reg_write(SDP_D_CVT_SCALE_0, 1);
    reg_write(SDP_D_CVT_SHIFT_0, 0);
    fence();
    if (!NVDLA_SKIP_ENABLE) {
        reg_write(SDP_RDMA_D_OP_ENABLE_0, 1);
        reg_write(SDP_D_OP_ENABLE_0, 1);
    }
    poll(GLB_S_INTR_STATUS_0, 3u, 1u << bank, hart, job);
    fence();

    uint32_t pending = 0;
    for (unsigned spin = 0; spin < SPIN_LIMIT; ++spin) {
        pending = rd(PLIC_BASE + 0x1000u);
        if (pending & (1u << NVDLA_IRQ)) break;
    }
    if (!(pending & (1u << NVDLA_IRQ))) fail("PLIC pending", hart, job, 0, pending, 1u << NVDLA_IRQ);
    unsigned irq = rd(claim);
    if (irq != NVDLA_IRQ) fail("PLIC claim", hart, job, 0, irq, NVDLA_IRQ);
    reg_write(GLB_S_INTR_STATUS_0, 1u << bank);
    poll(GLB_S_INTR_STATUS_0, 3u, 0, hart, job);
    fence();
    wr(claim, irq);
    wr(PLIC_BASE + 0x2000u + context * 0x80u, 0);
    fence();

    check_buffer("numerical/guard mismatch", hart, job, dst);
    elem = 0;
    for (unsigned g = 0; g < c->channels / 8u; ++g)
        for (unsigned y = 0; y < c->height; ++y)
            for (unsigned x = 0; x < c->width; ++x)
                for (unsigned k = 0; k < 8; ++k) {
                    unsigned offset = GUARD_SIZE + g * surface + y * stride + x * 8u + k;
                    uint8_t wanted = (uint8_t)sample(elem++, job);
                    if (src[offset] != wanted) fail("source overwritten", hart, job, offset, src[offset], wanted);
                }
    check_absent_sdp_lut(hart, job);
    text("PASS NVDLA job="); hex(job); text(" hart="); hex(hart);
    text(" elements="); hex(elem); text("\n"); print();
}

/* Bounded adaptation of Chipyard tests/nvdla.c's CDP LUT transaction.
 * Signed input x is converted to x+128, looked up in f(t)=gain*t,
 * then converted back by subtracting gain*128 with INT8 saturation.
 * Square-sum and input-times-LUT multiplication are intentionally bypassed.
 */
static void run_cdp(unsigned hart, unsigned job) {
    unsigned gain = hart + 1u;
    volatile uint8_t *src = src_storage;
    volatile uint8_t *dst = dst_storage;
    initialize_buffers(src, dst);
    struct test_case c = {8, 2, 16, 0, (int)gain, 0};
    for (unsigned i = 0; i < 256; ++i) {
        int input = sample(i, job);
        src[GUARD_SIZE + i] = (uint8_t)input;
        expected[GUARD_SIZE + i] = oracle(input, &c);
    }
    fence();
    reg_write(GLB_S_INTR_MASK_0, 0xffffffffu);
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    reg_write(CDP_S_POINTER_0, hart);
    reg_write(CDP_RDMA_S_POINTER_0, hart);
    reg_write(CDP_S_LUT_ACCESS_CFG_0, 0x30000); /* LO table, write, index 0. */
    for (unsigned i = 0; i <= 256; ++i) reg_write(CDP_S_LUT_ACCESS_DATA_0, i * gain);
    reg_write(CDP_S_LUT_ACCESS_CFG_0, 0x20000); /* LE table, write, index 0. */
    for (unsigned i = 0; i <= 64; ++i) reg_write(CDP_S_LUT_ACCESS_DATA_0, i * gain);
    reg_write(CDP_S_LUT_LE_START_LOW_0, 0);
    reg_write(CDP_S_LUT_LE_START_HIGH_0, 0);
    reg_write(CDP_S_LUT_LE_END_LOW_0, 64);
    reg_write(CDP_S_LUT_LE_END_HIGH_0, 0);
    reg_write(CDP_S_LUT_LO_START_LOW_0, 0);
    reg_write(CDP_S_LUT_LO_START_HIGH_0, 0);
    reg_write(CDP_S_LUT_LO_END_LOW_0, 256);
    reg_write(CDP_S_LUT_LO_END_HIGH_0, 0);
    reg_write(CDP_S_LUT_CFG_0, 1); /* Linear LE; choose LE if both hit. */
    reg_write(CDP_S_LUT_INFO_0, 0);
    reg_write(CDP_S_LUT_LE_SLOPE_SHIFT_0, 0);
    reg_write(CDP_S_LUT_LE_SLOPE_SCALE_0, 0);
    reg_write(CDP_S_LUT_LO_SLOPE_SHIFT_0, 0);
    reg_write(CDP_S_LUT_LO_SLOPE_SCALE_0, 0);
    reg_write(CDP_D_DATIN_OFFSET_0, 0x80); /* Signed INT8 -128. */
    reg_write(CDP_D_DATIN_SCALE_0, 1);
    reg_write(CDP_D_DATIN_SHIFTER_0, 0);
    reg_write(CDP_D_DATOUT_OFFSET_0, 128u * gain);
    reg_write(CDP_D_DATOUT_SCALE_0, 1);
    reg_write(CDP_D_DATOUT_SHIFTER_0, 0);
    reg_write(CDP_D_FUNC_BYPASS_0, 3);
    reg_write(CDP_D_LRN_CFG_0, 0);
    reg_write(CDP_D_DATA_FORMAT_0, 0);
    reg_write(CDP_D_NAN_FLUSH_TO_ZERO_0, 0);
    reg_write(CDP_D_DST_BASE_ADDR_LOW_0, (uintptr_t)dst + GUARD_SIZE);
    reg_write(CDP_D_DST_BASE_ADDR_HIGH_0, 0);
    reg_write(CDP_D_DST_LINE_STRIDE_0, 64);
    reg_write(CDP_D_DST_SURFACE_STRIDE_0, 128);
    reg_write(CDP_D_DST_DMA_CFG_0, 1);
    reg_write(CDP_RDMA_D_DATA_CUBE_WIDTH_0, 7);
    reg_write(CDP_RDMA_D_DATA_CUBE_HEIGHT_0, 1);
    reg_write(CDP_RDMA_D_DATA_CUBE_CHANNEL_0, 15);
    reg_write(CDP_RDMA_D_SRC_BASE_ADDR_LOW_0, (uintptr_t)src + GUARD_SIZE);
    reg_write(CDP_RDMA_D_SRC_BASE_ADDR_HIGH_0, 0);
    reg_write(CDP_RDMA_D_SRC_LINE_STRIDE_0, 64);
    reg_write(CDP_RDMA_D_SRC_SURFACE_STRIDE_0, 128);
    reg_write(CDP_RDMA_D_SRC_DMA_CFG_0, 1);
    reg_write(CDP_RDMA_D_DATA_FORMAT_0, 0);
    fence();
    reg_write(CDP_RDMA_D_OP_ENABLE_0, 1);
    reg_write(CDP_D_OP_ENABLE_0, 1);
    poll(GLB_S_INTR_STATUS_0, 12u, 1u << (hart + 2u), hart, job);
    reg_write(GLB_S_INTR_STATUS_0, 1u << (hart + 2u));
    poll(GLB_S_INTR_STATUS_0, 12u, 0, hart, job);
    fence();
    check_buffer("CDP numerical/guard mismatch", hart, job, dst);
    for (unsigned i = 0; i < 256; ++i) {
        uint8_t wanted = (uint8_t)sample(i, job);
        if (src[GUARD_SIZE + i] != wanted)
            fail("CDP source overwritten", hart, job, i, src[GUARD_SIZE + i], wanted);
    }
    text("PASS NVDLA CDP LUT job="); hex(job); text(" gain="); hex(gain);
    text(" elements=256\n"); print();
}

/* Direct 1x1 INT8 convolution: one spatial position, C=8, K=8.
 * All 64 kernel bytes are independently generated in kernel-major order.
 * CPU dot products verify the full CDMA/CBUF/CSC/CMAC/CACC/SDP path.
 */
static void run_conv(unsigned hart, unsigned job) {
    volatile uint8_t *src = src_storage;
    volatile uint8_t *dst = dst_storage;
    volatile uint8_t *weights = weight_storage;
    initialize_buffers(src, dst);
    for (unsigned i = 0; i < sizeof(weight_storage); ++i) weights[i] = 0;
    for (unsigned c = 0; c < 8; ++c) src[GUARD_SIZE + c] = (uint8_t)((int)c - 4 + (int)hart);
    for (unsigned k = 0; k < 8; ++k) {
        int sum = 0;
        for (unsigned c = 0; c < 8; ++c) {
            int w = (int)((k + 2u*c + hart) % 5u) - 2;
            weights[GUARD_SIZE + k*8u + c] = (uint8_t)w;
            sum += ((int)c - 4 + (int)hart) * w;
        }
        if (sum > 127) sum = 127;
        if (sum < -128) sum = -128;
        expected[GUARD_SIZE + k] = (uint8_t)sum;
    }
    fence();
    reg_write(GLB_S_INTR_MASK_0, 0xffffffffu);
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    reg_write(CDMA_S_POINTER_0, hart);
    reg_write(CSC_S_POINTER_0, hart);
    reg_write(CMAC_A_S_POINTER_0, hart);
    reg_write(CMAC_B_S_POINTER_0, hart);
    reg_write(CACC_S_POINTER_0, hart);
    reg_write(SDP_S_POINTER_0, hart);
    reg_write(SDP_RDMA_S_POINTER_0, hart);

    reg_write(CDMA_S_ARBITER_0, 0x3000f);
    reg_write(CDMA_D_MISC_CFG_0, 0); /* Direct INT8, no reuse, release data/weights. */
    reg_write(CDMA_D_DATAIN_FORMAT_0, 0);
    reg_write(CDMA_D_DATAIN_SIZE_0_0, 0);
    reg_write(CDMA_D_DATAIN_SIZE_1_0, 7);
    reg_write(CDMA_D_DATAIN_SIZE_EXT_0_0, 0);
    reg_write(CDMA_D_PIXEL_OFFSET_0, 0);
    reg_write(CDMA_D_DAIN_RAM_TYPE_0, 1);
    reg_write(CDMA_D_DAIN_ADDR_HIGH_0_0, 0);
    reg_write(CDMA_D_DAIN_ADDR_LOW_0_0, (uintptr_t)src + GUARD_SIZE);
    reg_write(CDMA_D_DAIN_ADDR_HIGH_1_0, 0);
    reg_write(CDMA_D_DAIN_ADDR_LOW_1_0, 0);
    reg_write(CDMA_D_LINE_STRIDE_0, 8);
    reg_write(CDMA_D_SURF_STRIDE_0, 8);
    reg_write(CDMA_D_DAIN_MAP_0, 0x10001);
    reg_write(CDMA_D_BATCH_NUMBER_0, 0);
    reg_write(CDMA_D_BATCH_STRIDE_0, 0);
    reg_write(CDMA_D_ENTRY_PER_SLICE_0, 0);
    reg_write(CDMA_D_FETCH_GRAIN_0, 0);
    reg_write(CDMA_D_WEIGHT_FORMAT_0, 0);
    reg_write(CDMA_D_WEIGHT_SIZE_0_0, 7);
    reg_write(CDMA_D_WEIGHT_SIZE_1_0, 7);
    reg_write(CDMA_D_WEIGHT_RAM_TYPE_0, 1);
    reg_write(CDMA_D_WEIGHT_ADDR_HIGH_0, 0);
    reg_write(CDMA_D_WEIGHT_ADDR_LOW_0, (uintptr_t)weights + GUARD_SIZE);
    reg_write(CDMA_D_WEIGHT_BYTES_0, 64);
    reg_write(CDMA_D_WMB_BYTES_0, 0);
    reg_write(CDMA_D_MEAN_FORMAT_0, 0);
    reg_write(CDMA_D_CVT_CFG_0, 0);
    reg_write(CDMA_D_CONV_STRIDE_0, 0);
    reg_write(CDMA_D_ZERO_PADDING_0, 0);
    reg_write(CDMA_D_ZERO_PADDING_VALUE_0, 0);
    reg_write(CDMA_D_BANK_0, 0); /* One bank each for data and weights. */
    reg_write(CDMA_D_CYA_0, 0);

    reg_write(CSC_D_MISC_CFG_0, 0);
    reg_write(CSC_D_DATAIN_FORMAT_0, 0);
    reg_write(CSC_D_DATAIN_SIZE_EXT_0_0, 0);
    reg_write(CSC_D_DATAIN_SIZE_EXT_1_0, 7);
    reg_write(CSC_D_BATCH_NUMBER_0, 0);
    reg_write(CSC_D_ENTRY_PER_SLICE_0, 0);
    reg_write(CSC_D_WEIGHT_FORMAT_0, 0);
    reg_write(CSC_D_WEIGHT_SIZE_EXT_0_0, 0);
    reg_write(CSC_D_WEIGHT_SIZE_EXT_1_0, 0x70007);
    reg_write(CSC_D_WEIGHT_BYTES_0, 64);
    reg_write(CSC_D_WMB_BYTES_0, 0);
    reg_write(CSC_D_DATAOUT_SIZE_0_0, 0);
    reg_write(CSC_D_DATAOUT_SIZE_1_0, 7);
    reg_write(CSC_D_ATOMICS_0, 0);
    reg_write(CSC_D_RELEASE_0, 0);
    reg_write(CSC_D_CONV_STRIDE_EXT_0, 0);
    reg_write(CSC_D_DILATION_EXT_0, 0);
    reg_write(CSC_D_ZERO_PADDING_0, 0);
    reg_write(CSC_D_ZERO_PADDING_VALUE_0, 0);
    reg_write(CSC_D_BANK_0, 0);
    reg_write(CSC_D_PRA_CFG_0, 0);
    reg_write(CSC_D_CYA_0, 0);
    reg_write(CMAC_A_D_MISC_CFG_0, 0);
    reg_write(CMAC_B_D_MISC_CFG_0, 0);
    reg_write(CACC_D_MISC_CFG_0, 0);
    reg_write(CACC_D_DATAOUT_SIZE_0_0, 0);
    reg_write(CACC_D_DATAOUT_SIZE_1_0, 7);
    reg_write(CACC_D_DATAOUT_ADDR_0, (uintptr_t)dst + GUARD_SIZE);
    reg_write(CACC_D_BATCH_NUMBER_0, 0);
    reg_write(CACC_D_LINE_STRIDE_0, 8);
    reg_write(CACC_D_SURF_STRIDE_0, 8);
    reg_write(CACC_D_DATAOUT_MAP_0, 0x10001);
    reg_write(CACC_D_CLIP_CFG_0, 0);
    reg_write(CACC_D_CYA_0, 0);

    reg_write(SDP_RDMA_D_BRDMA_CFG_0, 1);
    reg_write(SDP_RDMA_D_NRDMA_CFG_0, 1);
    reg_write(SDP_RDMA_D_ERDMA_CFG_0, 1);
    reg_write(SDP_RDMA_D_FEATURE_MODE_CFG_0, 1);
    reg_write(SDP_D_DATA_CUBE_WIDTH_0, 0);
    reg_write(SDP_D_DATA_CUBE_HEIGHT_0, 0);
    reg_write(SDP_D_DATA_CUBE_CHANNEL_0, 7);
    reg_write(SDP_D_DST_BASE_ADDR_LOW_0, (uintptr_t)dst + GUARD_SIZE);
    reg_write(SDP_D_DST_BASE_ADDR_HIGH_0, 0);
    reg_write(SDP_D_DST_LINE_STRIDE_0, 8);
    reg_write(SDP_D_DST_SURFACE_STRIDE_0, 8);
    reg_write(SDP_D_DP_BS_CFG_0, 1);
    reg_write(SDP_D_DP_BN_CFG_0, 1);
    reg_write(SDP_D_DP_EW_CFG_0, 1);
    reg_write(SDP_D_FEATURE_MODE_CFG_0, 1); /* Input directly from CACC. */
    reg_write(SDP_D_DST_DMA_CFG_0, 1);
    reg_write(SDP_D_DST_BATCH_STRIDE_0, 0);
    reg_write(SDP_D_DATA_FORMAT_0, 0);
    reg_write(SDP_D_CVT_OFFSET_0, 0);
    reg_write(SDP_D_CVT_SCALE_0, 1);
    reg_write(SDP_D_CVT_SHIFT_0, 0);
    fence();
    /* Consumers first, then upstream convolution producer. */
    reg_write(SDP_D_OP_ENABLE_0, 1);
    reg_write(CACC_D_OP_ENABLE_0, 1);
    reg_write(CMAC_A_D_OP_ENABLE_0, 1);
    reg_write(CMAC_B_D_OP_ENABLE_0, 1);
    reg_write(CSC_D_OP_ENABLE_0, 1);
    reg_write(CDMA_D_OP_ENABLE_0, 1);
    poll(GLB_S_INTR_STATUS_0, 3u, 1u << hart, hart, job);
    fence();
    check_buffer("convolution dot-product/guard mismatch", hart, job, dst);
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    text("PASS NVDLA convolution 1x1 C8 K8 hart="); hex(hart);
    text(" outputs=8\n"); print();
}

static void run_pdp(unsigned hart, unsigned job) {
    volatile uint8_t *src = src_storage;
    volatile uint8_t *dst = dst_storage;
    initialize_buffers(src, dst);
    /* One 2x2 window with 8 channels, no padding: max on hart 0, min on 1. */
    for (unsigned c = 0; c < 8; ++c) {
        int best = hart ? 127 : -128;
        for (unsigned pixel = 0; pixel < 4; ++pixel) {
            int value = sample(pixel * 8u + c, job);
            src[GUARD_SIZE + pixel * 8u + c] = (uint8_t)value;
            if (hart ? value < best : value > best) best = value;
        }
        expected[GUARD_SIZE + c] = (uint8_t)best;
    }
    fence();
    reg_write(GLB_S_INTR_MASK_0, 0xffffffffu);
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    reg_write(PDP_S_POINTER_0, hart);
    reg_write(PDP_RDMA_S_POINTER_0, hart);
    reg_write(PDP_RDMA_D_DATA_CUBE_IN_WIDTH_0, 1);
    reg_write(PDP_RDMA_D_DATA_CUBE_IN_HEIGHT_0, 1);
    reg_write(PDP_RDMA_D_DATA_CUBE_IN_CHANNEL_0, 7);
    reg_write(PDP_RDMA_D_FLYING_MODE_0, 1);
    reg_write(PDP_RDMA_D_SRC_BASE_ADDR_LOW_0, (uintptr_t)src + GUARD_SIZE);
    reg_write(PDP_RDMA_D_SRC_BASE_ADDR_HIGH_0, 0);
    reg_write(PDP_RDMA_D_SRC_LINE_STRIDE_0, 16);
    reg_write(PDP_RDMA_D_SRC_SURFACE_STRIDE_0, 32);
    reg_write(PDP_RDMA_D_SRC_RAM_CFG_0, 1);
    reg_write(PDP_RDMA_D_DATA_FORMAT_0, 0);
    reg_write(PDP_RDMA_D_OPERATION_MODE_CFG_0, 0);
    reg_write(PDP_RDMA_D_POOLING_KERNEL_CFG_0, 1);
    reg_write(PDP_RDMA_D_POOLING_PADDING_CFG_0, 0);
    reg_write(PDP_RDMA_D_PARTIAL_WIDTH_IN_0, 0x100401);
    reg_write(PDP_D_DATA_CUBE_IN_WIDTH_0, 1);
    reg_write(PDP_D_DATA_CUBE_IN_HEIGHT_0, 1);
    reg_write(PDP_D_DATA_CUBE_IN_CHANNEL_0, 7);
    reg_write(PDP_D_DATA_CUBE_OUT_WIDTH_0, 0);
    reg_write(PDP_D_DATA_CUBE_OUT_HEIGHT_0, 0);
    reg_write(PDP_D_DATA_CUBE_OUT_CHANNEL_0, 7);
    reg_write(PDP_D_OPERATION_MODE_CFG_0, 0x10u | (hart ? 2u : 1u));
    reg_write(PDP_D_PARTIAL_WIDTH_IN_0, 0x100401);
    reg_write(PDP_D_PARTIAL_WIDTH_OUT_0, 0);
    reg_write(PDP_D_POOLING_KERNEL_CFG_0, 0x101);
    reg_write(PDP_D_POOLING_PADDING_CFG_0, 0);
    reg_write(PDP_D_SRC_BASE_ADDR_LOW_0, (uintptr_t)src + GUARD_SIZE);
    reg_write(PDP_D_SRC_BASE_ADDR_HIGH_0, 0);
    reg_write(PDP_D_SRC_LINE_STRIDE_0, 16);
    reg_write(PDP_D_SRC_SURFACE_STRIDE_0, 32);
    reg_write(PDP_D_DST_BASE_ADDR_LOW_0, (uintptr_t)dst + GUARD_SIZE);
    reg_write(PDP_D_DST_BASE_ADDR_HIGH_0, 0);
    reg_write(PDP_D_DST_LINE_STRIDE_0, 8);
    reg_write(PDP_D_DST_SURFACE_STRIDE_0, 8);
    reg_write(PDP_D_DST_RAM_CFG_0, 1);
    reg_write(PDP_D_DATA_FORMAT_0, 0);
    fence();
    reg_write(PDP_RDMA_D_OP_ENABLE_0, 1);
    reg_write(PDP_D_OP_ENABLE_0, 1);
    poll(GLB_S_INTR_STATUS_0, 48u, 1u << (hart + 4u), hart, job);
    fence();
    check_buffer("pooling numerical/guard mismatch", hart, job, dst);
    reg_write(GLB_S_INTR_STATUS_0, 0xffffffffu);
    text("PASS NVDLA PDP 2x2 "); text(hart ? "min" : "max");
    text(" outputs=8\n"); print();
}

void test_main(unsigned hart) {
    if (hart > 1) for (;;) { }
    if (hart == 0) check_small_configuration(hart);
    for (unsigned job = hart; job < CASE_COUNT * 2u; job += 2u) {
        wait_turn(job, hart);
        run_job(hart, job);
        ++jobs_by_hart[hart];
        __atomic_store_n(&turn, job + 1u, __ATOMIC_RELEASE);
    }
    const unsigned cdp_job = CASE_COUNT * 2u + hart;
    wait_turn(cdp_job, hart);
    run_cdp(hart, cdp_job);
    ++jobs_by_hart[hart];
    __atomic_store_n(&turn, cdp_job + 1u, __ATOMIC_RELEASE);
    const unsigned conv_job = (CASE_COUNT + 1u) * 2u + hart;
    wait_turn(conv_job, hart);
    run_conv(hart, conv_job);
    ++jobs_by_hart[hart];
    __atomic_store_n(&turn, conv_job + 1u, __ATOMIC_RELEASE);
    const unsigned pdp_job = (CASE_COUNT + 2u) * 2u + hart;
    wait_turn(pdp_job, hart);
    run_pdp(hart, pdp_job);
    ++jobs_by_hart[hart];
    __atomic_store_n(&turn, pdp_job + 1u, __ATOMIC_RELEASE);
    if (hart) for (;;) { }
    wait_turn((CASE_COUNT + 3u) * 2u, hart);
    for (unsigned h = 0; h < 2; ++h)
        if (jobs_by_hart[h] != CASE_COUNT + 3u) fail("hart coverage", hart, 0, h, jobs_by_hart[h], CASE_COUNT + 3u);
    text("PASS NVDLA dual-hart: 16 SDP + 2 CDP + 2 convolution + 2 pooling jobs, coherent DMA, guards, PLIC\n");
    print(); finish(0);
}
