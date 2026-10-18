#!/usr/bin/env python3
"""GY62/DPS64: exact sign-magnitude fixed-point word vectors, NO CPU model.

BCD payload is ten four-bit decimal nibbles, with the sign separate;
this is NOT a physical punched-tape encoding, and not a rounding oracle.
"""
from fractions import Fraction

FRACTION_BITS = 40
SIGN = 1 << FRACTION_BITS
WORD_LIMIT = SIGN << 1

# (printed mathematical value, ten decimal fractional digits, expected 14-digit octal)
VECTORS = (
    ('+0.625', '6250000000', '12000000000000'),
    ('-0.625', '6250000000', '32000000000000'),
    ('+0.5',   '5000000000', '10000000000000'),
    ('-0.5',   '5000000000', '30000000000000'),
    ('+0.25',  '2500000000', '04000000000000'),
    ('+0',     '0000000000', '00000000000000'),
    ('-0',     '0000000000', '20000000000000'),
)


def fraction_from_decimal_digits(digits: str) -> Fraction:
    assert len(digits) == 10 and digits.isdecimal() and all('0' <= c <= '9' for c in digits)
    return Fraction(int(digits), 10 ** 10)


def bcd_pack(digits: str) -> int:
    assert len(digits) == 10 and all('0' <= c <= '9' for c in digits)
    value = 0
    for character in digits:
        value = (value << 4) | int(character)
    return value


def exact_machine_word(sign: str, decimal_digits: str) -> int:
    assert sign in ('+', '-')
    scaled = fraction_from_decimal_digits(decimal_digits) * SIGN
    if scaled.denominator != 1:
        raise ValueError('NONEXACT: no documentary rounding/underflow oracle')
    if scaled >= SIGN:
        raise ValueError('OUT_OF_RANGE: fixed-point machine magnitude')
    raw = int(scaled) | (SIGN if sign == '-' else 0)
    assert 0 <= raw < WORD_LIMIT
    return raw


def main() -> int:
    successes = 0
    for written, digits, octal in VECTORS:
        raw = exact_machine_word(written[0], digits)
        observed = f'{raw:014o}'
        assert observed == octal, f'{written}: {observed} != {octal}'
        bcd = bcd_pack(digits)
        assert f'{bcd:010x}' == digits, f'BCD packing mismatch: {digits}'
        print(f'D10B-SOURCE-WORD value={written} digits={digits} '
              f'bcd=0x{bcd:010x} oct41={observed} result=PASS')
        successes += 1
    assert successes == 7
    # Reject nonexact value rather than fabricating a rounding mode.
    try:
        exact_machine_word('+', '1000000000')  # 1/10 (inexact in binary)
    except ValueError as e:
        assert str(e).startswith('NONEXACT:')
    else:
        raise AssertionError('inexact decimal 0.1 was silently rounded')
    print('ISA-07 D10B SOURCE VECTORS PASS=7/7 GY62_0625=EXACT '
          'SIGNED_ZERO=ENCODING_ONLY NONEXACT_DECIMAL=OPEN '
          'BCD=TEN_NIBBLES NOT_A_PUNCHED_DEVICE_ORACLE=1')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
