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
