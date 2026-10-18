#!/usr/bin/env python3
"""Independent mathematical/property gate for proposed D10-G1 reference model.
No C++ CPU, emulator modification, hardware oracle or real electronic trace.
"""
import argparse
from fractions import Fraction
from pathlib import Path
import random
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import isa07_d10g1_reference as model


def check(ok, message):
    if not ok: raise AssertionError(message)


def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=1000);args=p.parse_args()
    check(1<=args.cases<=10000,'cases must be 1..10000')
    check(tuple(model.bcd_bits('8000000000')[:4])==(1,0,0,0),'MSB BCD bit order')
    check(tuple(model.bcd_bits('0000000001')[-4:])==(0,0,0,1),'LSB BCD bit order')
    check(model.equivalent(1)==Fraction(1,10*2**36),'E1 exact')
    check(model.equivalent(10)==Fraction(1,10**10),'E10 exact')
    for bad in ('','0.6250000000','625000000','+6250000000','123456789A','１２３４５６７８９０'):
        try: model.bcd_bits(bad)
        except ValueError: pass
        else: raise AssertionError('bad BCD accepted: '+repr(bad))
    cases=('0000000000','0000000001','0000000010','0000000100',
           '1000000000','3000000000','5000000000','6250000000',
           '2500000000','9999999999','1234567890','9876543210',
           '0009765625','9990234375')
    rng=random.Random(0xD10A1)
    cases += tuple(f'{rng.randrange(10**10):010d}' for _ in range(args.cases))
    floor_80_error=[]
    nearest_80_error=[]
    floor_40_error=[]
    for digits in cases:
        n=int(digits)
        # Entirely independent integer formula for ideal output:
        expected=(n*2**40)//10**10
        check(model.ideal_word(digits)==expected, 'ideal integer conversion '+digits)
        check(model.ideal_word(digits,True)==expected|(1<<40), 'sign parity '+digits)
        check(model.exact_recurrence(digits)==Fraction(n,10**10),'printed equation '+digits)
        check((n%9765625==0)==(Fraction(n*2**40,10**10).denominator==1),
              'exact criterion '+digits)
        for precision in model.P_VALUES:
            for mode in ('floor','nearest'):
                try: out=model.finite_precision_word(digits,precision,mode)
                except OverflowError:
                    check(precision<=64 and mode=='nearest','unexpected overflow case')
                    continue
                check(0<=out<2**40,'model overflow '+digits)
                check(model.finite_precision_word(digits,precision,mode,True)==out|(1<<40),
                      'quant sign preservation')
                if mode=='floor':
                    check(out<=expected,'floored positive constants cannot overshoot')
        floor_40_error.append(model.finite_precision_word(digits,40,'floor')-expected)
        floor_80_error.append(model.finite_precision_word(digits,80,'floor')-expected)
        nearest_80_error.append(model.finite_precision_word(digits,80,'nearest')-expected)
    # 40-bit E_s constant codes cannot even reproduce simple exact input fractions.
    check(model.finite_precision_word('6250000000',40,'floor')!=model.ideal_word('6250000000'),
          'naive P40 should fail calibration')
    check(model.finite_precision_word('6250000000',80,'floor')==model.ideal_word('6250000000')-1,
          'P80 floor produces 1-ULP loss on exact .625 (model, not hardware)')
    check(model.finite_precision_word('6250000000',80,'nearest')==model.ideal_word('6250000000'),
          'P80 nearest constants restore .625 (model, not hardware)')
    check(min(floor_40_error)<-1_000_000,'P40 should be demonstrably poor')
    check(min(floor_80_error)>=-1 and max(floor_80_error)==0,'P80 floor bound')
    check(min(nearest_80_error)>=0 and max(nearest_80_error)<=1,'P80 nearest bound')
    check(any(x==-1 for x in floor_80_error),'need P80-floor non-identity witness')
    check(any(x==1 for x in nearest_80_error),'need P80-nearest non-identity witness')
    print(f'ISA-07 D10-G1 REFERENCE PASS={len(cases)}/{len(cases)} '
          'EXACT_RECURRENCE=1 P40_NAIVE_REJECTED=1 '
          'P80_FLOOR_DELTA=-1..0 P80_NEAREST_DELTA=0..1 '
          'HARDWARE_ORACLE=0 CPU_MUTATION=0')

if __name__=='__main__':main()
