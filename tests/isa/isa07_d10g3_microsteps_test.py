#!/usr/bin/env python3
"""Independent 40-bit BCD/microstep invariants and exact Fraction oracle."""
from __future__ import annotations
import argparse
from fractions import Fraction
import importlib.util
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('g3',ROOT/'tools/isa07_d10g3_microsteps.py')
g3=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g3)
G2SPEC=importlib.util.spec_from_file_location('g2',ROOT/'tools/isa07_d10g2_hypotheses.py')
g2=importlib.util.module_from_spec(G2SPEC)
G2SPEC.loader.exec_module(g2)

SEEDS=('0000000000','0000000001','0000000009','1000000000',
       '3000000000','6250000000','5000000000','2500000000',
       '9999999999','1234567890','0009765625','9990234375',
       '8765432109','8888888888')


def oracle_coeff(s,p,rounding):
    f=Fraction(8,10**s)*2**p
    if rounding=='floor': return f.numerator//f.denominator
    return (2*f.numerator+f.denominator)//(2*f.denominator)


def oracle_model(token,p,rnd,terminal):
    acc=0
    n=0
    for s,c in enumerate(token,1):
        reg=oracle_coeff(s,p,rnd)
        for l in range(4):
            if int(c)&(8>>l):
                acc+=reg
                n+=1
            if l<3 or terminal: reg//=2
    return acc>>(p-40),n


def check_one(token):
    rows=g3.bit_schedule(token)
    assert len(rows)==40
    assert [row[0] for row in rows] == list(range(1,41))
    assert [(r[1],r[3]) for r in rows] == [(s,w) for s in range(1,11) for w in (8,4,2,1)]
    assert sum(Fraction(weight,10**s) for _,s,_,weight,active in rows if active)==Fraction(int(token),10**10)
    exact=g3.exact_rational_trace(token)
    assert len(exact)==40 and exact[-1][1]==Fraction(int(token),10**10)
    assert g3.unscaled_literal_rational(token)==Fraction(int(token),8*10**10)
    for p in (40,45,48,64):
        for rnd in ('floor','nearest'):
            for terminal in (True,False):
                m=g3.microstep_model(token,p,rnd,terminal)
                q,count=oracle_model(token,p,rnd,terminal)
                assert m['output']==q and m['conditional_adds']==count
                assert m['load_count']==10 and m['bit_count']==40
                assert m['shift_count']==(40 if terminal else 30)
                assert len(m['events'])==50
                assert sum(e['bit'] for e in m['events'] if e['kind']=='BIT')==count
                assert m['delta_ulps']==q-((int(token)<<40)//10**10)
                # Independent G2 numerical implementation is an extra parity gate.
                assert q==g2.shift_multiplicand(int(token),p,rnd)
                if terminal:
                    m_no=g3.microstep_model(token,p,rnd,False)
                    assert m['output']==m_no['output']
    assert g3.report(token)['hardware_oracle'] is False


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',type=int,default=1000)
    args=ap.parse_args()
    if not 1<=args.cases<=10000: ap.error('--cases must be in 1..10000')
    corpus=list(SEEDS)
    rng=random.Random(0xD10F3)
    corpus.extend(f'{rng.randrange(10**10):010d}' for _ in range(args.cases))
    try:
        for sample in ('','123','12345678901','０'*10,'000000000x','-000000001'):
            try: g3.bit_schedule(sample)
            except ValueError: pass
            else: raise AssertionError('malformed token accepted')
        for sample in corpus: check_one(sample)
        assert g3.microstep_model('6250000000',45,'nearest')['delta_ulps']==-1
        assert g3.microstep_model('6250000000',45,'floor')['delta_ulps']==-1
        assert g3.unscaled_literal_rational('6250000000')==Fraction(5,64)
    except (AssertionError, ValueError) as ex:
        print('D10G3-MICROSTEP FAIL:',ex,file=sys.stderr)
        return 1
    print(f'ISA-07 D10-G3 RESEARCH PASS={len(corpus)}/{len(corpus)} '
          'BCD_BITS=40 PER_DIGIT_RELOAD=10 SHIFT_VARIANTS=30_40 '
          'G2_PARITY=1 INDEPENDENT_FRACTION=1 '
          'E_S_SCALE_AMBIGUITY=EXPLICIT HARDWARE_ORACLE=0 CPU_MUTATION=0')
    return 0

if __name__=='__main__':raise SystemExit(main())
