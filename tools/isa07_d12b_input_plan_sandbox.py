#!/usr/bin/env python3
"""Independent Python oracle for D12-B HOST_POLICY decimal drum text adapter."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse
import random
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
MAX=(1<<40)-1
SIGN=(1<<40)

@dataclass(frozen=True)
class Case:
    name:str
    data:bytes|None
    track:int=0
    zone:int=0
    count:int=3

def oracle_token(value:bytes):
    if not value: return None
    negative=value.startswith(b'-')
    digits=value[1:] if value[:1] in (b'-',b'+') else value
    if not digits or any(c<ord('0') or c>ord('9') for c in digits):return None
    magnitude=int(digits)
    if magnitude>MAX:return None
    return magnitude | (SIGN if negative else 0)

def oracle(c):
    if c.count==0 or c.count>1024:return 'INVALID_COUNT',()
    if c.data is None:return 'UNAVAILABLE_STREAM',()
    lines=c.data.split(b'\n')
    if lines and lines[-1]==b'':lines.pop()
    if c.track>=len(lines):return 'MISSING_TRACK',()
    first=lines[c.track].removesuffix(b'\r')
    if c.zone>len(first):return 'INVALID_ZONE',()
    selected=[first[c.zone:]]+[v.removesuffix(b'\r') for v in lines[c.track+1:]]
    words=[]
    for line in selected:
        if not line.strip(b' \t'):return 'EMPTY_RECORD',()
        for tok in re.split(rb'[ \t]+',line.strip(b' \t')):
            v=oracle_token(tok)
            if v is None:return 'INVALID_TOKEN',()
            words.append(v)
            if len(words)==c.count:return 'EXACT',tuple(words)
    return 'SHORT_INPUT',()

STATIC=(
    Case('simple',b'5 7 9\n'),
    Case('one',b'-0\n',count=1),
    Case('selected',b'10 20 30\n5 7 9\n',track=1),
    Case('zone',b'xx5 7 9\n',zone=2),
    Case('multiline',b'5 7\n9\n'),
    Case('tabs',b'5\t7  9\n'),
    Case('crlf',b'5 7 9\r\n'),
    Case('positive-sign',b'+5 7 9\n'),
    Case('negative-zero',b'-0 7 9\n'),
    Case('negative',b'-1099511627775 7 9\n'),
    Case('max',b'1099511627775 7 9\n'),
    Case('overflow',b'1099511627776 7 9\n'),
    Case('underflow',b'-1099511627776 7 9\n'),
    Case('empty',b''),
    Case('missing',None),
    Case('missing-track',b'5 7 9\n',track=2),
    Case('zone-over',b'5 7 9\n',zone=80),
    Case('zero-count',b'5 7 9\n',count=0),
    Case('short',b'5 7\n'),
    Case('extra-ignored',b'5 7 9 BAD\n'),
    Case('bad-mid',b'5 abc 9\n'),
    Case('double-space',b'5  7 9\n'),
    Case('bad-cr',b'5\r 7 9\n'),
    Case('bare-sign',b'5 + 9\n'),
    Case('nul',b'5 7\x009\n'),
)

def random_cases(n):
    rng=random.Random(0x12B2026)
    for i in range(n):
        track=rng.randint(0,2);zone=rng.randint(0,4)
        lines=[]
        for _ in range(rng.randint(0,4)):
            tokens=[]
            for _ in range(rng.randint(0,5)):
                t=rng.choice(['good','bad','negative-zero','over','empty','plus'])
                if t=='good':s=str(rng.randrange(MAX+1)).encode()
                elif t=='negative-zero':s=b'-0'
                elif t=='over':s=str(MAX+rng.randrange(1,100)).encode()
                elif t=='bad':s=rng.choice([b'-',b'junk',b'8x',b'5\r',b'1\x00'])
                elif t=='plus':s=b'+'+str(rng.randrange(2000)).encode()
                else:s=b''
                tokens.append(s)
            line=rng.choice([b' ',b'  ',b'\t']).join(tokens)
            if rng.random()<0.2:line+=b'\r'
            lines.append(line)
        data=b'\n'.join(lines)+(b'\n' if lines else b'')
        yield Case(f'random{i:04}',data,track,zone,rng.choice([1,3]))

def one(exe,c,timeout):
    tag='ZERO_COUNT' if c.count==0 else 'ONE' if c.count==1 else c.name
    desired,values=oracle(c)
    try:
        proc=subprocess.run([str(exe),tag,str(c.track),str(c.zone)],input=c.data or b'',
                            capture_output=True,timeout=timeout)
        stdout=proc.stdout.decode('utf-8',errors='replace').strip()
        fields={x.split('=',1)[0]:x.split('=',1)[1] for x in stdout.split()[1:]}
        actual=tuple(int(v,8) for v in fields.get('values','').split(',') if v)
        ok=(proc.returncode==0 and stdout.startswith('D12B-PLAN ') and
            fields['status']==desired and fields['tag']==tag and
            int(fields['count'])==len(values) and actual==values)
    except (ValueError,KeyError,subprocess.TimeoutExpired,OSError) as exc:
        ok=False;stdout='ERROR '+repr(exc)
    if not ok:print('  D12B-PLAN-FAIL',c.name,'expected=',desired,values,'observed=',stdout)
    else:print(f'D12B-PLAN-CASE {c.name}: PASS expected={desired} count={len(values)}')
    return ok

def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',required=True)
    p.add_argument('--cases',type=int,default=200)
    p.add_argument('--timeout',type=float,default=5)
    a=p.parse_args()
    exe=Path(a.exe).resolve()
    if not exe.is_file():p.error('missing plan executable')
    if not 0<=a.cases<=10000 or not .2<=a.timeout<=60:p.error('invalid arguments')
    cases=STATIC+tuple(random_cases(a.cases))
    passed=sum(one(exe,c,a.timeout) for c in cases)
    print(f'ISA-07 D12-B PLAN PASS={passed}/{len(cases)} '
          'INDEPENDENT_DECIMAL=1 SIGNED_ZERO=1 HOST_POLICY=1 HARDWARE_ORACLE=0')
    return 0 if passed==len(cases) else 1
if __name__=='__main__':raise SystemExit(main())
