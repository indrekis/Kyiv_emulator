#!/usr/bin/env python3
"""D12-B real Kyiv_t IO24 tests; no peripheral hardware oracle."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
SIGN=1<<40
@dataclass(frozen=True)
class Case:
    name:str
    data:bytes|None
    status:str='OK'
    ram:tuple[int,int,int]=(5,7,9)
    last:int=0
    changed:int=3
    target:str='120'

CASES=(
    Case('valid',b'5 7 9\n'),
    Case('single',b'7\n',ram=(0,7,0),changed=1),
    Case('track1',b'99 88 77\n5 7 9\n'),
    Case('zone2',b'xx5 7 9\n'),
    Case('multiline',b'5 7\n9\n'),
    Case('whitespace',b' 5  \t  7   9 \n'),
    Case('negative',b'-1 7 9\n',ram=(SIGN|1,7,9)),
    Case('negative-zero',b'-0 7 9\n',ram=(SIGN,7,9)),
    Case('plus',b'+5 7 9\n'),
    Case('maximum',b'1099511627775 7 9\n',ram=(SIGN-1,7,9)),
    Case('zero-discard',b'5\n',ram=(0,0,0),changed=0),
    Case('last-ram',b'5\n',ram=(0,0,0),last=5,changed=1),
    Case('extra-bad-ignored',b'5 7 9 BAD\n'),
    Case('crlf',b'5 7 9\r\n'),
    Case('altjump',b'5 7 9\n',target='130'),
    Case('double-space',b'5  7 9\n'),
    Case('missing',None,'UNAVAILABLE_STREAM',(0,0,0),0,0),
    Case('empty',b'','MISSING_TRACK',(0,0,0),0,0),
    Case('short',b'5 7\n','SHORT_INPUT',(0,0,0),0,0),
    Case('bad-second',b'5 BAD 9\n','INVALID_TOKEN',(0,0,0),0,0),
    Case('bad-third',b'5 7 X\n','INVALID_TOKEN',(0,0,0),0,0),
    Case('suffix',b'5xyz 7 9\n','INVALID_TOKEN',(0,0,0),0,0),
    Case('overwide',b'1099511627776 7 9\n','INVALID_TOKEN',(0,0,0),0,0),
    Case('bad-cr',b'5\r7 9\n','INVALID_TOKEN',(0,0,0),0,0),
    Case('track-missing',b'5 7 9\n','MISSING_TRACK',(0,0,0),0,0),
    Case('zone-over',b'5 7 9\n','INVALID_ZONE',(0,0,0),0,0),
    Case('negative-track',b'5 7 9\n','INVALID_TRACK',(0,0,0),0,0),
    Case('negative-zone',b'5 7 9\n','INVALID_ZONE',(0,0,0),0,0),
    Case('reversed',b'5 7 9\n','INVALID_INTERVAL',(0,0,0),0,0),
    Case('ram-over',b'5 7 9\n','INVALID_RAM_ADDRESS',(0,0,0),0,0),
)

def parse(out):
    lines=[x for x in out.splitlines() if x.startswith('D12B-CPU ')]
    if len(lines)!=1:raise ValueError('missing/duplicate CPU summary: '+repr(out[-500:]))
    f={}
    for pair in lines[0].split()[1:]:
        key, val=pair.split('=',1)
        if key in f:raise ValueError('duplicate output field '+key)
        f[key]=val
    return f

def one(exe,c,timeout,parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d12b_',dir=parent) as d:
        root=Path(d)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        if c.data is not None:(root/'mem'/'drum_in.txt').write_bytes(c.data)
        try:
            p=subprocess.run([str(exe),c.name],cwd=root/'a'/'b',timeout=timeout,
                capture_output=True,text=True,encoding='utf-8',errors='replace')
            f=parse(p.stdout)
            accepted=c.status=='OK'
            pc1=c.target if accepted else '100'
            pc2=(oct(int(c.target,8)+1)[2:] if accepted else '100')
            expected={
                'mode':c.name,'status':'OK' if accepted else 'ERROR',
                'reason':'NONE' if accepted else c.status,
                'pc1':pc1,'pc2':pc2,'k1':'1','k2':'1',
                'stable':'1','outside':'0','changed':str(c.changed),
                'ram':'/'.join(format(x,'o') for x in c.ram),
                'last':format(c.last,'o'),'zero':'0','unmapped':'0',
                'xor':'6' if accepted else '0','steps':'2' if accepted else '1',
                'run':'1/1' if accepted else '0/0',
                'HOST_POLICY':'1','HARDWARE_ORACLE':'0'}
            allowed={'mem/drum_in.txt'} if c.data is not None else set()
            files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            good=p.returncode==0 and expected==f and files==allowed
            if not good:
                print('  EXPECTED',repr(expected))
                print('  OBSERVED',repr(f))
                print('  FILES',repr(files))
                print('  TAIL',repr((p.stdout+'\n'+p.stderr)[-600:]))
        except (OSError,ValueError,subprocess.TimeoutExpired) as e:
            print('  ERROR',repr(e));good=False
        print(f'D12B-CPU-CASE {c.name}: {"PASS" if good else "FAIL"} '
              f'expected={"ACCEPTED" if c.status=="OK" else c.status} '
              f'atomic={int(c.status!="OK")} REAL_CPU=1')
        return good

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exe',required=True)
    p.add_argument('--timeout',type=float,default=5)
    args=p.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():p.error('exe and tempkyiv required')
    if not .2<=args.timeout<=60:p.error('timeout out of bounds')
    passed=sum(one(exe,c,args.timeout,ROOT/'tempkyiv') for c in CASES)
    accepted=sum(c.status=='OK' for c in CASES)
    rejected=len(CASES)-accepted
    print(f'ISA-07 D12-B CPU PASS={passed}/{len(CASES)} '
          f'TWO_STEP_SUCCESS={accepted} ATOMIC_REJECTION={rejected} '
          'GENUINE_KYIV_T=1 HOST_POLICY=1 HARDWARE_ORACLE=0')
    return 0 if passed==len(CASES) else 1
if __name__=='__main__':raise SystemExit(main())
