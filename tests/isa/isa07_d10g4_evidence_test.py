#!/usr/bin/env python3
"""D10-G4 research-only gate: exact BCD math, source-matrix integrity, G3 parity.
No historical IO20 rounding oracle, no CPU execution, no source mutation.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
from random import Random
import sys

ROOT=Path(__file__).resolve().parents[2]

def load(path,name):
    spec=spec_from_file_location(name,path)
    mod=module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=1000)
    ap.add_argument('--local-only',action='store_true',help='skip native-repo D10-G3 parity (local fixture testing only)')
    args=ap.parse_args()
    if not 0 <= args.cases <= 10000: ap.error('bad cases')
    g4=load(ROOT/'tools/isa07_d10g4_evidence.py','d10g4_evidence')
    old=ROOT/'tools/isa07_d10g3_microsteps.py'
    if not args.local_only and not old.is_file():
        print('D10G4-RESEARCH FAIL missing pinned D10-G3',file=sys.stderr);return 1
    g3=None if args.local_only else load(old,'d10g3_microsteps')
    must=('ПЧ1','ПЧ2','У<0>Р1','У<0>Р2','У<0>См','+Ч2,+Ч3','У<1>Р1','УЭ','ИКОп')
    if tuple(row[0] for row in g4.SIGNALS)!=must or len(g4.SIGNALS)!=9:
        print('D10G4-RESEARCH FAIL signal matrix shape');return 1
    fixed=('0000000000','0000000001','0000000002','1000000000','3000000000',
           '6250000000','5000000000','2500000000','9999999999','9999999998',
           '1234567890','8765432100','0009765625','9990234375')
    rnd=Random(0xD10A4)
    tokens=list(fixed)+[f'{rnd.randrange(10**10):010d}' for _ in range(args.cases)]
    try:
        for token in tokens:
            exact=Fraction(int(token),10**10)
            # Independent positional-digit oracle, not BCD bit breakdown.
            digit_oracle=sum((Fraction(int(ch),10**s) for s,ch in enumerate(token,1)),Fraction(0))
            assert digit_oracle==exact==g4.bcd_total(token)
            val=(int(token)*(1<<40))//10**10
            assert val==g4.diagnostic(token)['ideal_truncated_40']
            for p in (40,45,48,64):
                for rounding in ('floor','nearest'):
                    x=g4.shifted_model(token,p,False,rounding)
                    y=g4.shifted_model(token,p,True,rounding)
                    assert x['output']==y['output'] and x['shifts']==30 and y['shifts']==40
                    if g3 is not None:
                        m=g3.microstep_model(token,p,rounding,True)
                        assert y['output']==m['output'] and y['adds']==m['conditional_adds']
            if g3 is not None:
                assert g3.unscaled_literal_rational(token)==exact/8
        assert g4.shifted_model('6250000000',45,True,'nearest')['delta_ulps']==-1
        for invalid in ('','1','1'*11,'٠'*10,'12345a7890',' 1234567890'):
            try: g4.bcd_total(invalid)
            except ValueError: pass
            else: raise AssertionError('invalid BCD accepted')
        txt=g4.signal_tsv()
        assert txt.startswith('signal\topcode20_numeric\topcode21_commands')
        assert '\t—\t—\t' in txt
    except (AssertionError,ValueError) as err:
        print('D10G4-RESEARCH FAIL',str(err),file=sys.stderr);return 1
    count=len(tokens)
    print(f'ISA-07 D10-G4 RESEARCH PASS={count}/{count} '
          'TABLE5_SELECTED=9/9 FRACTION_ORACLE=1 SHIFT30_40_EQ=1 '
          f'G3_PARITY={1 if g3 is not None else "SKIPPED"} '
          'E_S_LOCATION=OPEN CLOCK_TRACE=OPEN IO20_UNCHANGED=1 HARDWARE_ORACLE=0')
    return 0

if __name__=='__main__': raise SystemExit(main())
