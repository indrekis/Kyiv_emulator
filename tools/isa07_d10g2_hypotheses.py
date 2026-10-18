#!/usr/bin/env python3
"""ISA-07 D10-G2: exploratory fixed-point models, NOT an IO20 hardware oracle.

Source analogies: DPS64 printed pp.86-90, 105-109, 120-125.
Quantization and right-shift bit-loss rules are COUNTERFACTUAL parameters.
"""
from __future__ import annotations
import argparse
import json
import csv
import io
from fractions import Fraction

DECIMAL_SCALE = 10**10
OUTPUT_BITS = 40
SIGN = 1 << OUTPUT_BITS
CASES = (
    ('zero', 0), ('one-unit', 1), ('digit-nine', 9), ('one-tenth', 1000000000),
    ('three-tenths', 3000000000), ('one-half', 5000000000),
    ('five-eighths', 6250000000), ('one-quarter', 2500000000),
    ('near-one', 9999999999), ('irregular', 1234567890),
    ('small', 87654321), ('middle', 4567890123),
    ('exact-smallest', 9765625), ('exact-near-one', 9990234375),
)


def check(n):
    if type(n) is not int or not 0 <= n < DECIMAL_SCALE:
        raise ValueError('ten-digit unsigned decimal magnitude required')
    return n


def ideal(n):
    return (check(n) << OUTPUT_BITS) // DECIMAL_SCALE


def exact_bit_expansion(n):
    """40 BCD contributions with correct 8,4,2,1 digit weights."""
    check(n)
    total = Fraction()
    for s, digit in enumerate(f'{n:010d}', 1):
        for power in (3, 2, 1, 0):
            if int(digit) & (1 << power):
                total += Fraction(1 << power, 10 ** s)
    return total


def quantize(numerator, denominator, precision, rounding):
    if rounding not in ('floor', 'nearest') or precision < 40 or precision > 128:
        raise ValueError('invalid precision/rounding')
    value = numerator << precision
    if rounding == 'nearest':
        value += denominator // 2
    return value // denominator


def digit_terms(n, precision=45, rounding='floor'):
    """Counterfactual quantize ONE contribution per decimal digit, then sum."""
    check(n)
    total = sum(quantize(int(d), 10**s, precision, rounding)
                for s, d in enumerate(f'{n:010d}', 1))
    return total >> (precision - OUTPUT_BITS)


def bit_terms(n, precision=45, rounding='floor'):
    """Counterfactual quantize EACH active BCD bit contribution, then sum."""
    check(n)
    total = 0
    for s, d in enumerate(f'{n:010d}', 1):
        for bit in (3, 2, 1, 0):
            if int(d) & (1 << bit):
                total += quantize(1 << bit, 10**s, precision, rounding)
    return total >> (precision - OUTPUT_BITS)


def shift_multiplicand(n, precision=45, rounding='floor'):
    """Counterfactual abbreviated-multiplication-like right shift.

    For each decimal digit initialize a fixed-point register with 8*10^-s,
    test its 8,4,2,1 BCD bits MSB-first, and SHIFT RIGHT AFTER each bit.
    Shifts discard low bits of coefficient before the next BCD bit.
    This is intentionally NOT a literal transcription of DPS64's E_(s,1)
    indexing, which does not alone resolve the circuit's bit direction/scale.
    """
    check(n)
    accumulator = 0
    for s, d in enumerate(f'{n:010d}', 1):
        reg = quantize(8, 10**s, precision, rounding)
        digit = int(d)
        for bit in (3, 2, 1, 0):
            if digit & (1 << bit):
                accumulator += reg
            if bit:
                reg >>= 1
    return accumulator >> (precision - OUTPUT_BITS)


def octal(magnitude, negative=False):
    return f'{magnitude | (SIGN if negative else 0):014o}'


def compare(n):
    i = ideal(n)
    return {'n': n, 'ideal': i, 'ideal_octal': octal(i),
            **{f'{name}_P{p}_{rnd}': function(n, p, rnd) - i
               for p in (40, 45, 48)
               for rnd in ('floor', 'nearest')
               for name, function in (
                   ('digit', digit_terms), ('bit', bit_terms),
                   ('shift', shift_multiplicand))}}


def comparison_tsv():
    keys = ['id', 'decimal', 'ideal_octal',
            'digit_P40_floor', 'digit_P40_nearest',
            'digit_P45_floor', 'digit_P45_nearest',
            'bit_P45_floor', 'bit_P45_nearest',
            'shift_P45_floor', 'shift_P45_nearest',
            'shift_P48_floor', 'shift_P48_nearest']
    f = io.StringIO(newline='')
    writer = csv.writer(f, delimiter='\t', lineterminator='\n')
    writer.writerow(keys)
    for label, n in CASES:
        row = compare(n)
        writer.writerow([label, f'{n:010d}', row['ideal_octal']] +
                        [row[k] for k in keys[3:]])
    return f.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--digits', default='6250000000')
    ap.add_argument('--table', action='store_true')
    a = ap.parse_args()
    if a.table:
        print(comparison_tsv(), end='')
        return 0
    if len(a.digits) != 10 or not a.digits.isascii() or not a.digits.isdecimal():
        ap.error('digits must be exactly ten ASCII decimal digits')
    n = int(a.digits)
    print('D10G2-REFERENCE SOURCE_ALGEBRA=1 G5=HYPOTHESIS '
          'SHIFT_MODEL=COUNTERFACTUAL HARDWARE_ORACLE=0 CPU_MUTATION=0')
    print(json.dumps({'decimal':a.digits, 'models':compare(n)}, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
