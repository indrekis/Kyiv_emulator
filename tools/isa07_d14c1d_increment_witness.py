#!/usr/bin/env python3
"""D14-C1d: read-only arithmetic reconstruction, NOT a hardware oracle."""
import argparse
from fractions import Fraction
import random

def word(op, a1, a2, a3):
    assert 0 <= op < 0o40 and all(0 <= i < 0o4000 for i in (a1,a2,a3))
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3

MASK41=(1<<41)-1
ROM3040=word(0,0o20,0,0)
assert ROM3040 == (1<<28)
assert Fraction(ROM3040,1<<40) == Fraction(1,1<<12)

def witness(drum, n, b, direction):
    # Source describes the I address n; other NK3000 fields assumed zero.
    raw_nk3000=word(0,n,0,0)
    by_fixed_point=(raw_nk3000 * ROM3040) >> 40
    by_independent_fraction=(Fraction(raw_nk3000,1<<40) *
                             Fraction(ROM3040,1<<40) * (1<<40))
    assert by_independent_fraction.denominator == 1
    delta=int(by_independent_fraction)
    assert delta == by_fixed_point == (n << 12)
    base=word(0o25,direction,drum<<6,b)
    changed=base+delta
    assert changed <= MASK41
    op=(changed >> 36)&0o37
    raw1=(changed >> 24)&0o3777
    raw2=(changed >> 12)&0o3777
    raw3=changed&0o3777
    assert op==0o25 and raw1==direction
    assert raw2==(drum<<6)+n
    assert raw3==b
    return (raw2,(raw2>>6)&7)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--random-cases',type=int,default=200)
    args=ap.parse_args()
    assert args.random_cases>=0
    fixed_n=(1,63,64,137,256,500)
    count=0
    for drum in (1,2):
        for n in fixed_n:
            for b in (0,0o123):
                for direction in (0,1):
                    witness(drum,n,b,direction)
                    count+=1
    assert count==48
    rng=random.Random(0xD14C1D)
    for i in range(args.random_cases):
        witness(rng.choice((1,2)),rng.randrange(501),rng.randrange(0o4000),rng.randrange(2))
        count+=1
    print('D14C1D-SOURCE ROM3040=2^-12 NK3000_I_TO_II=CONDITIONAL')
    for n in fixed_n:
        raw2,digit=witness(1,n,0,1)
        print(f'D14C1D-COUNTEREXAMPLE N={n} A2_OCT={raw2:04o} C1B_DRUM_DIGIT={digit}')
    assert witness(1,64,0,1)[1] == 2
    assert witness(1,256,0,1)[1] == 5
    assert witness(1,500,0,1)[1] == 0
    print(f'D14C1D-WITNESS PASS={count}/{count} ROM_POW2=1 INTERNAL_MAPPING=OPEN '
          'CPU_MUTATION=0 HARDWARE_ORACLE=0')

if __name__=='__main__':
    main()
