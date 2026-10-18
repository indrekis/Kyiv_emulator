#!/usr/bin/env python3
"""ISA-07 D10-G3: abstract IO20 microstep hypothesis, NOT hardware trace.

DPS64 printed pp.120-122: 40 BCD bits; conditional accumulate,
right-shift multiplicand, reload decimal position equivalents.
The 8x preload and per-shift finite precision are INFERRED/COUNTERFACTUAL.
All arithmetic is integer or exact Fraction; no CPU or hardware encoding.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json

DIGITS = 10
DEN = 10**DIGITS
OUT_BITS = 40


def require_token(token):
    if (not isinstance(token, str) or len(token) != DIGITS or
            not token.isascii() or any(c not in '0123456789' for c in token)):
        raise ValueError('exactly ten ASCII decimal digits required')
    return token


def quantize(numerator, denominator, p, rounding):
    if not isinstance(p, int) or p < 40 or p > 128 or rounding not in ('floor','nearest'):
        raise ValueError('invalid precision or coefficient policy')
    scaled = numerator << p
    if rounding == 'nearest':
        scaled += denominator // 2
    return scaled // denominator


def bit_schedule(token):
    """Source-grounded 10x4 bits; 8,4,2,1 is source/BCD weight order.

    Returns (i, decimal_position, within_digit_index, weight, one_bit).
    No assertion about actual shift pulses, micro-clock durations, card signal.
    """
    require_token(token)
    return tuple((4*(s-1)+l+1, s, l, 8 >> l, bool(int(c) & (8 >> l)))
                 for s,c in enumerate(token,1) for l in range(4))


def exact_rational_trace(token):
    total = Fraction(0)
    result=[]
    for i,s,l,weight,bit in bit_schedule(token):
        if bit:
            total += Fraction(weight,10**s)
        result.append((i,total))
    assert total == Fraction(int(token), DEN)
    return result


def microstep_model(token, p=45, rounding='nearest', terminal_shift=True):
    """Working right-shift class with 8*10^-s reloaded per decimal digit.

    terminal_shift controls whether the expendable 4th shift is counted,
    not whether the reloaded-next-digit result changes. NOT a gate-level sim.
    """
    require_token(token)
    events=[]
    acc=0
    shifts=0
    additions=0
    for s,char in enumerate(token,1):
        reg=quantize(8,10**s,p,rounding)
        events.append({'kind':'LOAD','s':s,'coefficient':reg})
        digit=int(char)
        for l in range(4):
            i=4*(s-1)+l+1
            weight=8 >> l
            bit=bool(digit & weight)
            before=reg
            if bit:
                acc+=reg
                additions+=1
            do_shift=(l < 3 or terminal_shift)
            if do_shift:
                reg >>= 1
                shifts+=1
            events.append({'kind':'BIT','i':i,'s':s,'l':l+1,
                           'weight':weight,'bit':int(bit),'addend':before if bit else 0,
                           'acc':acc,'shifted':int(do_shift),
                           'post_shift':reg,'terminal':int(l==3)})
    magnitude=acc >> (p-OUT_BITS)
    ideal=(int(token) << OUT_BITS)//DEN
    assert len(events)==50
    return {'digits':token,'precision':p,'rounding':rounding,
            'terminal_shift':int(terminal_shift),
            'load_count':DIGITS,'bit_count':40,'conditional_adds':additions,
            'shift_count':shifts,'accumulator':acc,'output':magnitude,
            'output_octal':f'{magnitude:014o}', 'ideal_output':ideal,
            'delta_ulps':magnitude-ideal,'events':events}


def unscaled_literal_rational(token):
    """COUNTEREXAMPLE: literally E_(s,1)=10^-s then halving with MSB first.

    Without an unprinted scale or reversed bit-order this yields |x|/8.
    This only rejects the *uncompensated* reading, not the source text.
    """
    require_token(token)
    acc=Fraction(0)
    for _,s,l,_,bit in bit_schedule(token):
        if bit:
            acc+=Fraction(1,10**s * (1 << l))
    return acc


def report(token, p=45, rounding='nearest', terminal_shift=True):
    m=microstep_model(token,p,rounding,terminal_shift)
    result={k:v for k,v in m.items() if k!='events'}
    literal=unscaled_literal_rational(token)
    exact=Fraction(int(token),DEN)
    result['literal_msb_unscaled']=str(literal)
    result['source_exact']=str(exact)
    result['unscaled_is_eighth']=literal == exact/8
    result['trace_kind']='ABSTRACT_SOURCE_ORDER_NOT_HARDWARE_CLOCK'
    result['hardware_oracle']=False
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--digits',default='6250000000')
    ap.add_argument('--precision',type=int,default=45)
    ap.add_argument('--rounding',choices=('nearest','floor'),default='nearest')
    ap.add_argument('--terminal-shift',choices=('yes','no'),default='yes')
    ap.add_argument('--trace',action='store_true')
    a=ap.parse_args()
    try:
        data=report(a.digits,a.precision,a.rounding,a.terminal_shift=='yes')
        if a.trace:
            data['events']=microstep_model(a.digits,a.precision,a.rounding,a.terminal_shift=='yes')['events']
    except ValueError as e:
        ap.error(str(e))
    print('D10G3-REFERENCE SOURCE_BCD_40=1 SHIFT_FAMILY=INFERRED '
          'EQUIVALENT_SCALE=PROVISIONAL CLOCK_TIMING=OPEN HARDWARE_ORACLE=0 CPU_MUTATION=0')
    print(json.dumps(data,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
