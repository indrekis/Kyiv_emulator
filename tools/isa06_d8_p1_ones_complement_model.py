#!/usr/bin/env python3
"""ISA-06 D8-P1: a candidate 41-bit one's-complement model, NOT hardware."""
import argparse
import random

SIGN = 1 << 40
MAG = SIGN - 1
FULL = (SIGN << 1) - 1


def encode(a):
    """External sign-magnitude word into *candidate* one's-complement word."""
    assert 0 <= a <= FULL
    return a if not a & SIGN else SIGN | ((~a) & MAG)


def decode(a):
    """Candidate internal word to external sign-magnitude code."""
    assert 0 <= a <= FULL
    return a if not a & SIGN else SIGN | ((~a) & MAG)


def add(a, b):
    u = encode(a) + encode(b)
    u = (u & FULL) + (u >> 41)  # end-around carry, at most one extra bit
    return decode(u)


def subtract(a, b):
    return decode(((encode(a) + (FULL ^ encode(b))) & FULL) +
                  ((encode(a) + (FULL ^ encode(b))) >> 41))


def val(a):
    return -(a & MAG) if a & SIGN else (a & MAG)


def external(x, negzero=False):
    return ((SIGN if negzero else 0) if x == 0 else
            ((SIGN | (-x)) if x < 0 else x))

CASES = [
    ('plus_zero_plus_zero', 0, 0, 0),
    ('plus_zero_minus_zero', 0, SIGN, SIGN),
    ('minus_zero_plus_zero', SIGN, 0, SIGN),
    ('minus_zero_minus_zero', SIGN, SIGN, SIGN),
    ('plus_five_minus_five', 5, SIGN | 5, SIGN),
    ('minus_five_plus_five', SIGN | 5, 5, SIGN),
]

def check():
    for title,a,b,want in CASES:
        got=add(a,b)
        assert got==want, (title, hex(got),hex(want))
        print(f'POLICY-MODEL {title:26} result={"-0" if got==SIGN else "+0"}')
    for n in [0, 1, 5, 727, MAG // 2]:
        for sign in [0,SIGN]:
            x=sign | n
            assert subtract(x,x)==SIGN, ('equal_subtraction',x)
    rng=random.Random(0x4b494556)
    for _ in range(20000):
        a=rng.randrange(-100000,100001)
        b=rng.randrange(-100000,100001)
        ca=external(a)
        cb=external(b)
        result=add(ca,cb)
        expected=external(a+b, negzero=(a+b==0 and (a<0 or b<0)))
        assert result==expected,(a,b,hex(result),hex(expected))
    print('MODEL-CHECK PASS candidate_zeros=6 equal_subtraction=10 random_nonoverflow=20000')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--check',action='store_true')
    ns=p.parse_args()
    if ns.check:check()
    else:
        for name,a,b,_ in CASES:print(f'{name}: {add(a,b):011o}')
