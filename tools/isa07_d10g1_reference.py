#!/usr/bin/env python3
"""D10-G1 research-only reference. NO hardware/CPU behavior claims.

DPS64 (1964), printed pp.120-121: ten BCD digits, forty bit positions,
E_s = 10^-s / 2^(40-4s), x_i = 2*x_(i-1) + a_i*E_s.

Finite-precision E_s encodings are COUNTERFACTUAL research models.
"""
import argparse
from fractions import Fraction
import json

BITS = 40
DIGITS = 10
SIGN_BIT = 1 << BITS
SCALE = 10 ** DIGITS
EXACT_DIVISOR = 5 ** DIGITS
P_VALUES = (40, 48, 64, 72, 80, 88)


def check_digits(digits):
    if not isinstance(digits, str) or len(digits) != DIGITS or any(c not in '0123456789' for c in digits):
        raise ValueError('expected exactly ten ASCII decimal digits')
    return digits


def bcd_bits(digits):
    check_digits(digits)
    return tuple((int(c) >> k) & 1 for c in digits for k in (3, 2, 1, 0))


def equivalent(s):
    if not 1 <= s <= DIGITS:
        raise ValueError('s outside 1..10')
    # Printed DPS64 p.121 notation E_s = 10^-s / 2^(n-4s), n=40.
    return Fraction(1, (10 ** s) * (2 ** (BITS - 4*s)))


def exact_recurrence(digits):
    x = Fraction(0, 1)
    for i, bit in enumerate(bcd_bits(digits), 1):
        s = (i+3)//4
        x = 2*x + bit*equivalent(s)
    return x


def ideal_word(digits, negative=False):
    """D10-F2 ideal final truncation; does not model intermediate register precision."""
    n = int(check_digits(digits))
    magnitude = (n << 30)//EXACT_DIVISOR
    return magnitude | (SIGN_BIT if negative else 0)


def approximate_constant(s, precision, mode):
    if precision < BITS or precision > 160:
        raise ValueError('hypothetical precision outside 40..160')
    if mode not in ('floor', 'nearest'):
        raise ValueError('unknown E_s encoding policy')
    scaled = equivalent(s) * (1 << precision)
    q, r = divmod(scaled.numerator, scaled.denominator)
    if mode == 'nearest' and 2*r >= scaled.denominator:
        q += 1
    return int(q)


def finite_precision_word(digits, precision, mode, negative=False):
    """Hypothetical E_s quantization at P fractional bits.

    P-bit integer recurrence is evaluated EXACTLY with unbounded Python ints;
    the arithmetic is NOT limited to a P-bit historical Kyiv register.
    Output uses a final floor to 40 magnitude bits. This deliberately isolates
    constant accuracy, not all possible hardware carry/shift effects.
    """
    bits = bcd_bits(digits)
    constants = tuple(approximate_constant(s, precision, mode) for s in range(1, DIGITS+1))
    accum = 0
    for i, bit in enumerate(bits):
        accum = 2*accum + bit*constants[i//4]
    magnitude = accum >> (precision-BITS)
    if not 0 <= magnitude < (1 << BITS):
        raise OverflowError('hypothetical accumulator cannot fit 40-bit output')
    return magnitude | (SIGN_BIT if negative else 0)


def vector(digits):
    digits = check_digits(digits)
    ideal = ideal_word(digits)
    values = {'digits':digits, 'ideal_octal':f'{ideal:014o}',
              'ideal_exact':int(digits)%EXACT_DIVISOR==0,
              'models':{}}
    for precision in P_VALUES:
        for mode in ('floor','nearest'):
            try:
                approx = finite_precision_word(digits,precision,mode)
                values['models'][f'P{precision}_{mode}'] = {
                    'delta_ulps':approx-ideal, 'octal':f'{approx:014o}'}
            except OverflowError:
                values['models'][f'P{precision}_{mode}'] = {'overflow':True}
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--digits', default='6250000000')
    p.add_argument('--constants',action='store_true')
    args=p.parse_args()
    v=vector(args.digits)
    if exact_recurrence(args.digits)!=Fraction(int(args.digits),SCALE):
        raise RuntimeError('source recurrence algebra failed')
    print('D10G1-REFERENCE SOURCE_RECURRENCE=EXACT_RATIONAL '
          'HARDWARE_ORACLE=0 CPU_MUTATION=0 FINITE_PRECISION=HYPOTHETICAL')
    if args.constants:
        v['constants']={f'E{s}':{
            'fraction':str(equivalent(s)),
            'P40_floor':approximate_constant(s,40,'floor'),
            'P80_floor':approximate_constant(s,80,'floor'),
            'P80_nearest':approximate_constant(s,80,'nearest')}
            for s in range(1,11)}
    print(json.dumps(v,indent=2,sort_keys=True))

if __name__=='__main__': main()
