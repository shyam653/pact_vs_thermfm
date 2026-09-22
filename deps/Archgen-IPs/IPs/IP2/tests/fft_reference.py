#!/usr/bin/env python3
"""Independent recursive reference for the pinned eight-point fixed-point FFT.

Vectors are computed from inputs, never from simulator outputs. The recursive
Cooley-Tukey decomposition differs from the hardware's explicit lane network.
Nonoverflow cases are additionally checked against an O(N^2) complex DFT.
"""

import argparse
import cmath
import hashlib
import json
import math
from pathlib import Path
import random


FFT_REVISION = "e361f229b5574931f555b10e1b48f2769c07832c"
N = 8
TWIDDLE_FRAC = 17
SCALE = 1 << TWIDDLE_FRAC
SEED = 0x46544654


def signed(value, width=16):
    return (value + (1 << (width - 1))) % (1 << width) - (1 << (width - 1))


def packed(value):
    real, imag = value
    return ((real & 0xffff) << 16) | (imag & 0xffff)


def twiddle(k, n):
    # FixedPoint literals use nearest integer. At these angles there are no ties.
    return (math.floor(math.cos(2 * math.pi * k / n) * SCALE + .5),
            math.floor(-math.sin(2 * math.pi * k / n) * SCALE + .5))


def multiply(value, factor):
    # The pinned dsptools implementation uses three multipliers. Its signed
    # 16-bit input pre-add/subtract operations wrap before multiplication.
    # Model this explicitly; a normal unbounded complex multiply is incorrect
    # for full-scale inputs. Products retain all 17 twiddle fractional bits.
    a, b = value
    c, d = factor
    ac_ad = a * signed(c + d, 19)
    ad_bd = signed(a + b) * d
    bc_ac = signed(b - a) * c
    return ac_ad - ad_bd, ac_ad + bc_ac


def fft(values):
    if len(values) == 1:
        return list(values)
    even = fft(values[::2])
    odd = fft(values[1::2])
    upper, lower = [], []
    for k, (e, o) in enumerate(zip(even, odd)):
        product = multiply(o, twiddle(k, len(values)))
        # Both butterfly outputs independently arithmetic-shift down to Q8,
        # then keep 16 bits. In particular, floor(-x) != -floor(x).
        upper.append(tuple(signed(((a << TWIDDLE_FRAC) + b) >> TWIDDLE_FRAC)
                           for a, b in zip(e, product)))
        lower.append(tuple(signed(((a << TWIDDLE_FRAC) - b) >> TWIDDLE_FRAC)
                           for a, b in zip(e, product)))
    return upper + lower


def dft(values):
    return [sum(complex(*v) * cmath.exp(-2j * math.pi * k * m / N)
                for m, v in enumerate(values)) for k in range(N)]


def cases():
    result = []

    def add(name, values, dft_check=True):
        assert len(values) == N
        assert all(-32768 <= x <= 32767 for v in values for x in v)
        result.append({"name": name, "input": values, "dft_check": dft_check})

    add("zero", [(0, 0)] * N)
    add("dc_real", [(256, 0)] * N)
    add("dc_imag_negative", [(0, -256)] * N)
    for lane in range(N):
        for label, impulse in (("real", (256, 0)), ("complex", (-173, 91))):
            values = [(0, 0)] * N
            values[lane] = impulse
            add(f"impulse_{label}_{lane}", values)
    for frequency in range(N):
        add(f"tone_{frequency}", [(round(256 * math.cos(2 * math.pi * frequency * m / N)),
                                  round(256 * math.sin(2 * math.pi * frequency * m / N)))
                                 for m in range(N)])
    add("upstream_tone", [(181, -181), (0, -256), (-181, -181), (-256, 0),
                          (-181, 181), (0, 256), (181, 181), (256, 0)])
    add("one_lsb", [(1, -1), (0, 1), (-1, 0), (1, 1),
                    (-1, -1), (0, 0), (1, 0), (0, -1)])
    add("alternating", [(1024 if m % 2 else -1024, 0) for m in range(N)])
    for label, value in (("maximum", 32767), ("minimum", -32768)):
        for lane in (0, 1, 7):
            values = [(0, 0)] * N
            values[lane] = (value, value)
            add(f"{label}_complex_{lane}", values, False)
        add(f"{label}_dc", [(value, value)] * N, False)
    add("alternating_extrema", [(32767, -32768) if m % 2 else (-32768, 32767)
                                 for m in range(N)], False)
    rng = random.Random(SEED)
    for i in range(64):
        add(f"random_bounded_{i:02d}", [(rng.randint(-512, 511), rng.randint(-512, 511))
                                      for _ in range(N)])
    for i in range(32):
        add(f"random_fullscale_{i:02d}", [(rng.randint(-32768, 32767), rng.randint(-32768, 32767))
                                        for _ in range(N)], False)
    return result


def generate(output):
    vectors = cases()
    max_error = 0.0
    for case in vectors:
        expected = fft(case["input"])
        case["expected"] = expected
        if case["dft_check"]:
            error = max(abs(component - reference)
                        for value, ideal in zip(expected, dft(case["input"]))
                        for component, reference in zip(value, (ideal.real, ideal.imag)))
            assert error <= 4.0, f"independent DFT disagrees: {case['name']}: {error}"
            max_error = max(max_error, error)
    upstream = next(case for case in vectors if case["name"] == "upstream_tone")
    assert [packed(v) for v in upstream["expected"]] == [0, 0, 0, 0xffff0000, 0, 0, 0, 0x05a8fa57]
    lines = ["/* Generated by fft_reference.py; do not edit. */", "#ifndef FFT_VECTORS_H",
             "#define FFT_VECTORS_H", f"#define FFT_CASE_COUNT {len(vectors)}u",
             "struct fft_case { const char *name; uint32_t input[8]; uint32_t expected[8]; };",
             "static const struct fft_case fft_cases[FFT_CASE_COUNT] = {"]
    for case in vectors:
        inputs = ", ".join(f"0x{packed(v):08x}u" for v in case["input"])
        expected = ", ".join(f"0x{packed(v):08x}u" for v in case["expected"])
        lines.append(f'    {{ "{case["name"]}", {{ {inputs} }}, {{ {expected} }} }},')
    lines += ["};", "#endif", ""]
    output.mkdir(parents=True, exist_ok=True)
    header = "\n".join(lines)
    (output / "fft_vectors.h").write_text(header)
    report = {"fft_revision": FFT_REVISION, "points": N, "component_width": 16,
              "component_fraction_bits": 8, "twiddle_fraction_bits": TWIDDLE_FRAC,
              "random_seed": SEED, "cases": len(vectors),
              "independent_dft_cases": sum(c["dft_check"] for c in vectors),
              "max_independent_dft_component_error_lsb": max_error,
              "dft_component_error_limit_lsb": 4,
              "upstream_known_answer_verified": True,
              "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "header_sha256": hashlib.sha256(header.encode()).hexdigest(),
              "vectors": vectors}
    (output / "reference.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "vectors"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    generate(parser.parse_args().output)
