#!/usr/bin/env python3
"""G2 exact-source algebra + independent integer oracle vs candidate models."""
import argparse
from fractions import Fraction
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import isa07_d10g2_hypotheses as m

def require(p,msg):
    if not p: raise AssertionError(msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',type=int,default=1000)
    a=ap.parse_args()
    require(1 <= a.cases <= 5000,'cases must be 1..5000')
    require(len(m.CASES)==14,'fixture count drift')
    rng=random.Random(0xD10B2)
    nums=[n for _,n in m.CASES]+[rng.randrange(m.DECIMAL_SCALE) for _ in range(a.cases)]
    source=0
    distinguish=0
    signs=0
    for n in nums:
        # Independent reference, not calling m.ideal() for expected.
        expected=(n * (1 << 40)) // (10**10)
        require(m.ideal(n)==expected,'ideal oracle mismatch '+str(n))
        require(m.exact_bit_expansion(n)==Fraction(n,10**10),
                'source BCD expansion mismatch '+str(n))
        for p in (40,45,48):
            for rnd in ('floor','nearest'):
                for func in (m.digit_terms,m.bit_terms,m.shift_multiplicand):
                    candidate=func(n,p,rnd)
                    require(0 <= candidate < (1<<40),
                            f'candidate range {n} {p} {rnd} {func.__name__}')
        require(int(m.octal(expected, True),8)==((1<<40)|expected),'negative sign')
        require(int(m.octal(expected, False),8)==expected,'positive sign')
        signs+=1
        if m.digit_terms(n,45,'floor')!=m.shift_multiplicand(n,45,'floor'):
            distinguish+=1
        source+=1
    require(distinguish>0,'independent quantization and per-shift loss collapsed')
    # Regression witnesses that show why correct exact values cannot alone
    # prove constant encoding or discarded per-shift bits.
    n=6250000000
    require(m.ideal(n)==0o12000000000000,'exact 0.625 source code')
    require(m.digit_terms(n,45,'floor')==m.ideal(n)-1,
            'P45 digit floor 0.625 signature')
    require(m.digit_terms(n,45,'nearest')==m.ideal(n),
            'P45 digit nearest 0.625 signature')
    require(m.shift_multiplicand(n,45,'nearest')==m.ideal(n)-1,
            'shift-loss signature')
    require(m.comparison_tsv().startswith('id\tdecimal\tideal_octal\t'),
            'TSV regression')
    for bad in (-1,10**10,1.2,'100'):
        try: m.ideal(bad)
        except ValueError: continue
        raise AssertionError('bad magnitude accepted: '+repr(bad))
    print(f'ISA-07 D10-G2 RESEARCH PASS={source}/{len(nums)} '
          'EXACT_BCD=1 INDEPENDENT_ORACLE=1 QUANTIZATION_VS_SHIFT=1 '
          'G5_DATAPATH=SOURCE_CONTEXT_NOT_IO20_ORACLE '
          'HARDWARE_ORACLE=0 CPU_MUTATION=0')
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (AssertionError,ValueError) as e:
        print('D10G2-TEST FAIL',str(e),file=sys.stderr);raise SystemExit(1)
