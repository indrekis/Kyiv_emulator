#!/usr/bin/env python3
"""Independent exact rational oracle for H115-B23, not an emulator or FP runtime."""
from __future__ import annotations
import argparse
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = HERE / 'inputs' / 'AFFINE_RECURRENCE.k41'
ORACLE = HERE / 'inputs' / 'INDEPENDENT_ORACLE.json'
DATA = {0o100: F(1,4), 0o101:F(1,2), 0o102:F(0),
        0o103:F(0),0o104:F(1,4),0o105:F(7,8),0o106:F(0)}
CODE = [
 (0o01, 0o100, 0o101, 0o102), # u=x+1/2
 (0o11, 0o102, 0o101, 0o100), # x=u*1/2
 (0o01, 0o103, 0o104, 0o103), # t=t+1/4
 (0o02, 0o105, 0o103, 0o106), # d=threshold-t
 (0o31, 0o106, 0o305, 0o306), # fork on d sign
 (0o31, 0o000, 0o300, 0o300), # unconditional loop back
 (0o33, 0o000, 0o000, 0o000), # unexecuted sentinel
]

def exact_fp_word(q: F) -> int:
    q = F(q)
    if q==0:return 0
    sign = (1<<40) if q<0 else 0
    q=abs(q)
    power=0
    while q>=1:
        q/=2
        power+=1
    while q<F(1,2):
        q*=2
        power-=1
    if not -64<power<63:raise ValueError('ORACLE_EXPONENT_RANGE')
    m=q*(1<<40)
    if m.denominator!=1:raise ValueError('ORACLE_NON_DYADIC_INPUT')
    if int(m)&127:raise ValueError('ORACLE_LOWER_MANTISSA_BITS')
    return sign|int(m)|int(power+64)

def machine_command(op,a,b,c):
    if not 0<=op<0o40 or any(not 0<=v<0o10000 for v in (a,b,c)):
        raise ValueError('ORACLE_COMMAND_RANGE')
    return (op<<36)|(a<<24)|(b<<12)|c

def image_words(threshold: F = F(7,8)):
    words={k: exact_fp_word(v) for k,v in DATA.items()}
    words[0o105]=exact_fp_word(threshold)
    words.update({0o300+i:machine_command(*command) for i,command in enumerate(CODE)})
    if len(words)!=14:raise ValueError('ORACLE_IMAGE_SIZE')
    return dict(sorted(words.items()))

def render_image(threshold: F = F(7,8)) -> bytes:
    return ('KYIV41-OCT1\n'+''.join(f'{addr:04o} {val:014o}\n' for addr,val in image_words(threshold).items())).encode('ascii')

def itinerary():
    x=F(1,4)
    t=F(0)
    result=[]
    for n in range(1,5):
        tmp=x+F(1,2)
        x=tmp*F(1,2)
        t+=F(1,4)
        d=F(7,8)-t
        result.append({'iteration':n,'x':str(x),'x_word':f'{exact_fp_word(x):014o}',
                      'tmp':str(tmp),'tmp_word':f'{exact_fp_word(tmp):014o}',
                      't':str(t),'t_word':f'{exact_fp_word(t):014o}',
                      'd':str(d),'d_word':f'{exact_fp_word(d):014o}',
                      'stop':d<0})
    if x!=F(31,64) or result[-1]['stop'] is not True:
        raise ValueError('ORACLE_FINAL_DRIFT')
    return result

def expected_json():
    return {'schema':'KYIV_H115_B23_AFFINE_RECURRENCE_EXACT_V1',
            'type':'new USER program (not historically sourced)',
            'recurrence':'x[n+1]=(x[n]+1/2)/2',
            'initial':'1/4', 'step_count':4, 'entry':'0300','end_pointer':'0306',
            'threshold':'7/8','x_final':'31/64',
            'machine_ram_data_addresses':[f'{x:04o}' for x in DATA],
            'source_image_sha256':hashlib.sha256(render_image()).hexdigest(),
            'machine_dispatches':24,'iterations':itinerary()}

def verify():
    assert IMAGE.read_bytes()==render_image(), 'IMAGE_DIFFERENCE'
    assert json.loads(ORACLE.read_text('utf-8'))==expected_json(), 'ORACLE_DIFFERENCE'
    assert len(CODE)==7 and CODE[-1][0]==0o33
    return expected_json()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify',action='store_true',required=True)
    a=p.parse_args()
    r=verify()
    print(f'H115_B23_ORACLE_PASS|ITERATIONS={len(r["iterations"])}|FINAL={r["x_final"]}|IMAGE_SHA256={r["source_image_sha256"]}')
if __name__=='__main__':main()
