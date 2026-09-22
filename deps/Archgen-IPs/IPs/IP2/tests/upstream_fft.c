/* SPDX-License-Identifier: Apache-2.0
 * Execute Chipyard's unmodified tests/fft.c with this freestanding startup.
 * The only printf format used by that source is %x; no libc is required.
 */
#include <stdarg.h>
#include "runtime.h"
#define main upstream_fft_main
#include "fft.c"
#undef main

int printf(const char *format, ...) {
    va_list args;
    va_start(args, format);
    while (*format) {
        if (*format == '%' && format[1] == 'x') {
            hex(va_arg(args, unsigned));
            format += 2;
        } else {
            char character[2] = {*format++, 0};
            text(character);
        }
    }
    va_end(args);
    print();
    return 0;
}

void test_main(unsigned hart) {
    if (hart) for (;;) { }
    finish(upstream_fft_main() ? 1 : 0);
}
