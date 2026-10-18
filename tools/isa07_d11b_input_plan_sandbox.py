#!/usr/bin/env python3
"""Independent octal parser/planner oracle; no C++ parser reuse."""
from pathlib import Path
import argparse
import random
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MASK=(1<<41)-1

def expected(lines,start,count):
    if count==0 or count>1024:return 'INVALID_COUNT',()
    if start>(1<<64)-1-count:return 'INVALID_SELECTION',()
    if start>=len(lines):return 'MISSING_START_LINE',()
    ret=[]
    for i in range(count):
        index=start+i
        if index>=len(lines):return 'SHORT_INPUT',()
        s=lines[index]
        if s.endswith(b'\r'):s=s[:-1]
        s=s.strip(b' \t')
        if not s:return 'EMPTY_RECORD',()
        if len(s)>14 or re.fullmatch(rb'[0-7]+',s) is None:return 'INVALID_TOKEN',()
        num=int(s,8)
        if num>MASK:return 'INVALID_TOKEN',()
        ret.append(num)
    return 'EXACT',tuple(ret)

def run(exe,name,lines,start,count):
    content=b'\n'.join(lines)+b'\n' if lines else b''
    p=subprocess.run([str(exe),name,str(start),str(count)],input=content,
                     capture_output=True,timeout=5)
    marker=[x for x in p.stdout.decode('utf-8','replace').splitlines() if x.startswith('D11B-PLAN ')]
    exp,words=expected(lines,start,count)
    if p.returncode or len(marker)!=1:
        print('D11B-PLAN FAIL',name,'process',p.returncode,repr(p.stderr[-300:]));return False
    m=re.fullmatch(r'D11B-PLAN tag=(\S+) status=(\S+) count=(\d+) values=(.*)',marker[0])
    try:
        assert m and m[1]==name and m[2]==exp and int(m[3])==len(words)
        got=tuple(int(v,8) for v in m[4].split(',') if v)
        assert got==words,(got,words)
        ok=True
    except (AssertionError,ValueError) as e:
        print('D11B-PLAN-DETAIL',name,'expected',exp,words,'actual',marker,'err',e);ok=False
    print(f'D11B-PLAN-CASE {name}: {"PASS" if ok else "FAIL"} expected={exp} values={len(words)}')
    return ok

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--cases',type=int,default=200)
    a=ap.parse_args()
    exe=Path(a.exe).resolve()
    if not exe.is_file() or not 1<=a.cases<=2000:ap.error('invalid executable/count')
    examples=[
      ('simple',[b'11',b'22',b'33'],0,3),('one',[b'7'],0,1),
      ('h1',[b'11',b'22',b'33',b'44'],1,2),
      ('zero',[b'0'],0,1),('negative-zero',[b'20000000000000'],0,1),
      ('maximum',[b'37777777777777'],0,1),('above-max',[b'40000000000000'],0,1),
      ('leadingzeros',[b'00000000000007'],0,1),('whitespace',[b' \t17 \t'],0,1),
      ('crlf',[b'11\r',b'22\r'],0,2),('blank',[b'11',b'  '],0,2),
      ('short',[b'11',b'22'],0,3),('missing-start',[b'11'],2,1),
      ('empty',[],0,1),('bad-octal',[b'18'],0,1),('suffix',[b'11xyz'],0,1),
      ('plus',[b'+11'],0,1),('minus',[b'-1'],0,1),
      ('binary-nul',[b'1\0'],0,1),('bare-cr',[b'1\r2'],0,1),
      ('too-many-digits',[b'000000000000001'],0,1),
      ('bad-surplus',[b'11',b'broken'],0,1),
      ('zero-count',[b'11'],0,0),('overcount',[b'11'],0,1025),
      ('selection-overflow',[b'11'],(1<<64)-1,2),
    ]
    rng=random.Random(0xD11B)
    for i in range(a.cases):
        values=[rng.randrange(1<<41) for _ in range(rng.randrange(1,7))]
        lines=[f'{v:o}'.encode() for v in values]
        if i%5==0:lines.insert(1,b'8oops')
        if i%7==0:lines.append(b'xyz')
        start=rng.randrange(0,len(lines)+2)
        count=rng.randrange(1,6)
        examples.append((f'random{i:04d}',lines,start,count))
    ok=sum(run(exe,*case) for case in examples)
    print(f'ISA-07 D11-B PLAN PASS={ok}/{len(examples)} INDEPENDENT_OCTAL=1 HOST_POLICY=1 HARDWARE_ORACLE=0')
    return 0 if ok==len(examples) else 1
if __name__=='__main__':sys.exit(main())
