#!/usr/bin/env python3
"""Independent Python integer oracle for D10-F3 text/plan stages; no CPU."""
import argparse
from dataclasses import dataclass
from pathlib import Path
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE={
    '+0.6250000000':'12000000000000', '-0.6250000000':'32000000000000',
    '+0.5000000000':'10000000000000', '-0.5000000000':'30000000000000',
    '+0.2500000000':'04000000000000', '+0.0000000000':'00000000000000',
    '-0.0000000000':'20000000000000',
}

def oracle(token):
    sign=token.startswith('-')
    digits=token.lstrip('+-')
    if digits.startswith('0.'):
        digits=digits[2:]
    assert len(digits)==10 and digits.isascii() and digits.isdigit(),repr(token)
    q,r=divmod(int(digits)*(1<<40),10**10)
    word=f'{q | ((1<<40) if sign else 0):014o}'
    if token in SOURCE: assert word==SOURCE[token],('primary-source exact conflict',token)
    return word,r!=0

@dataclass(frozen=True)
class Case:
    label:str
    mode:str
    data:bytes
    status:str
    values:tuple=()
    start:int=0
    offset:int=0
    count:int=0

CASES=[
 Case('token-pos-exact','token',b'+0.6250000000','EXACT',('+0.6250000000',)),
 Case('token-neg-exact','token',b'-0.6250000000','EXACT',('-0.6250000000',)),
 Case('token-pos-zero','token',b'0000000000','EXACT',('+0.0000000000',)),
 Case('token-neg-zero','token',b'-0000000000','EXACT',('-0.0000000000',)),
 Case('token-pos-trunc','token',b'+0.1000000000','TRUNCATED',('+0.1000000000',)),
 Case('token-neg-trunc','token',b'-0.1000000000','TRUNCATED',('-0.1000000000',)),
 Case('token-min','token',b'0000000001','TRUNCATED',('+0.0000000001',)),
 Case('token-max','token',b'9999999999','TRUNCATED',('+0.9999999999',)),
 Case('token-malformed','token',b'0.625','INVALID_TOKEN'),
 Case('token-exponent','token',b'1e-10','INVALID_TOKEN'),
 Case('token-integer-one','token',b'1.0000000000','INVALID_TOKEN'),
 Case('token-non-ascii','token','０.1000000000'.encode(),'INVALID_TOKEN'),
 Case('token-carriage','token',b'1000000000\r','INVALID_TOKEN'),
 Case('record-exact','record',b'6250000000 -5000000000','EXACT',('+0.6250000000','-0.5000000000')),
 Case('record-trunc','record',b'6250000000\t-1000000000','TRUNCATED',('+0.6250000000','-0.1000000000')),
 Case('record-two-trunc','record',b'1000000000 3000000000','TRUNCATED',('+0.1000000000','+0.3000000000')),
 Case('record-empty','record',b'\t  ','EMPTY_RECORD'),
 Case('record-invalid-after-trunc','record',b'1000000000 bad','INVALID_TOKEN'),
 Case('record-invalid-after-exact','record',b'6250000000 bad','INVALID_TOKEN'),
 Case('record-control','record',b'6250000000\r 1000000000','INVALID_TOKEN'),
 Case('plan-exact','plan',b'6250000000 -5000000000\n','EXACT',('+0.6250000000','-0.5000000000'),count=2),
 Case('plan-trunc','plan',b'1000000000 6250000000\n','TRUNCATED',('+0.1000000000','+0.6250000000'),count=2),
 Case('plan-trunc-second-line','plan',b'6250000000\n3000000000\n','TRUNCATED',('+0.6250000000','+0.3000000000'),count=2),
 Case('plan-trunc-first-line','plan',b'1000000000\n6250000000\n','TRUNCATED',('+0.1000000000','+0.6250000000'),count=2),
 Case('plan-trunc-excluded-surplus','plan',b'6250000000 1000000000\n','EXACT',('+0.6250000000',),count=1),
 Case('plan-trunc-stored-surplus','plan',b'1000000000 6250000000\n','TRUNCATED',('+0.1000000000',),count=1),
 Case('plan-bad-surplus','plan',b'6250000000 bad\n','INVALID_TOKEN',count=1),
 Case('plan-bad-after-trunc','plan',b'1000000000 bad\n','INVALID_TOKEN',count=1),
 Case('plan-trunc-then-error','plan',b'1000000000\nBAD\n','INVALID_TOKEN',count=2),
 Case('plan-trunc-then-short','plan',b'1000000000\n','SHORT_INPUT',count=2),
 Case('plan-empty-second','plan',b'1000000000\n\n','EMPTY_RECORD',count=2),
 Case('plan-selected-line','plan',b'ignore\nxxx1000000000 -6250000000\n','TRUNCATED',('+0.1000000000','-0.6250000000'),start=1,offset=3,count=2),
 Case('plan-crlf','plan',b'1000000000\r\n-5000000000\r\n','TRUNCATED',('+0.1000000000','-0.5000000000'),count=2),
 Case('plan-offset-too-far','plan',b'1000000000\n','INVALID_FIRST_OFFSET',offset=100,count=1),
 Case('plan-missing-line','plan',b'1000000000\n','MISSING_START_LINE',start=2,count=1),
 Case('plan-empty-file','plan',b'','MISSING_START_LINE',count=1),
 Case('plan-zero-count','plan',b'1000000000\n','INVALID_COUNT',count=0),
 Case('plan-too-many','plan',b'1000000000\n','INVALID_COUNT',count=1025),
]
prng=random.Random(0xD10F3)
for i in range(60):
    n=prng.randrange(10**10)
    token=('+' if i%2==0 else '-')+f'{n:010d}'
    word,truncated=oracle(token)
    CASES.append(Case(f'pseudorandom-{i:02d}','token',token.encode(),
                      'TRUNCATED' if truncated else 'EXACT',(token,)))

def run(exe,case,timeout):
    args=[str(exe),case.mode]
    if case.mode=='plan':
        args += [str(case.start),str(case.offset),str(case.count)]
    try:
        proc=subprocess.run(args,input=case.data,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'D10F3-PIPELINE-CASE {case.label}: FAIL TIMEOUT')
        return False
    raw=proc.stdout.decode('utf-8','replace')
    lines=[x for x in raw.splitlines() if x.startswith('D10F3-OBS ')]
    obs={}
    if len(lines)==1:
        try:obs=dict(x.split('=',1) for x in lines[0].split()[1:])
        except ValueError:pass
    expected='/'.join(oracle(tok)[0] for tok in case.values) if case.values else 'NONE'
    success=(proc.returncode==0 and len(lines)==1 and
             obs.get('mode')==case.mode and obs.get('status')==case.status and
             obs.get('count')==str(len(case.values)) and obs.get('words')==expected and
             obs.get('CPU_MUTATION')=='0' and obs.get('TRUNCATION_PROVISIONAL')=='1')
    print(f'D10F3-PIPELINE-CASE {case.label}: {"PASS" if success else "FAIL"} '
          f'expected={case.status} observed={obs.get("status","NONE")} count={obs.get("count","NA")}')
    if not success:
        print('  expected_words=',expected,'observed=',obs)
        print('  stderr=',proc.stderr.decode('utf-8','replace')[-400:])
    return success

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5)
    a=ap.parse_args()
    exe=Path(a.exe).resolve()
    if not exe.is_file():ap.error('exe missing')
    if not .2<=a.timeout<=60:ap.error('timeout outside 0.2..60')
    ok=sum(run(exe,c,a.timeout) for c in CASES)
    print(f'ISA-07 D10-F3 PIPELINE PASS={ok}/{len(CASES)} '
          'HOST_POLICY=1 TRUNCATION=PROVISIONAL SOURCE_EXACT=1 HARDWARE_ORACLE=0 CPU_MUTATION=0')
    return 0 if ok==len(CASES) else 1
if __name__=='__main__':sys.exit(main())
