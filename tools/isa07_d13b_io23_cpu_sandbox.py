#!/usr/bin/env python3
"""D13-B: process-isolated genuine Kyiv_t IO23 and IO25->IO23 observations."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SIGN=1<<40

@dataclass(frozen=True)
class Case:
    name: str
    expected: bytes | None
    reason: str = 'NONE'
    existing: bytes | str | None = None

CASES=(
    Case('range',b'5 7 9 '),
    Case('single',b'7 '),
    Case('offset',b'7 9 11 '),
    Case('fromzero',b'0 5 7 '),
    Case('negative',b'-5 7 9 '),
    Case('negative-zero',b'-0 '),
    Case('sign-only',b'-0 '),
    Case('max-positive',str(SIGN-1).encode()+b' '),
    Case('max-negative',b'-'+str(SIGN-1).encode()+b' '),
    Case('overwrite',b'5 7 9 ',existing=b'OLD DATA\n'),
    Case('altjump',b'5 7 9 '),
    Case('modified',b'5 7 9 '),
    Case('io25-setup',b'5 7 9 '),
    Case('last-ram',b'15 '),
    Case('zero-source',b'0 '),
    Case('mixed',b'-5 -0 '+str(SIGN-1).encode()+b' '),
    Case('reversed',None,'INVALID_INTERVAL',existing=b'KEEP\n'),
    Case('beyond-physical',None,'INVALID_RAM_ADDRESS',existing=b'KEEP\n'),
    Case('rom-source',None,'INVALID_RAM_ADDRESS',existing=b'KEEP\n'),
    Case('cross-physical',None,'INVALID_RAM_ADDRESS',existing=b'KEEP\n'),
    Case('invalid-start',None,'INVALID_RAM_ADDRESS',existing=b'KEEP\n'),
    Case('invalid-end',None,'INVALID_RAM_ADDRESS',existing=b'KEEP\n'),
    Case('invalid-first',None,'INVALID_WORD',existing=b'KEEP\n'),
    Case('invalid-second',None,'INVALID_WORD',existing=b'KEEP\n'),
    Case('invalid-third',None,'INVALID_WORD',existing=b'KEEP\n'),
    Case('invalid-negative',None,'INVALID_WORD',existing=b'KEEP\n'),
    Case('invalid-last',None,'INVALID_WORD',existing=b'KEEP\n'),
    Case('output-is-dir',None,'REPLACE_FAILED',existing='DIR'),
    Case('empty-out-is-dir',None,'REPLACE_FAILED',existing='DIR'),
    Case('invalid-before-overwrite',None,'INVALID_WORD',existing=b'OLD DATA\n'),
)
assert len(CASES)==30 and len(set(c.name for c in CASES))==30

def parse(output):
    lines=[line.strip() for line in output.splitlines() if line.startswith('D13B-OBS ')]
    if len(lines)!=1:raise ValueError('expected one D13B-OBS line')
    record={}
    for part in lines[0].split()[1:]:
        k,sep,v=part.partition('=')
        if not sep or k in record:raise ValueError('bad field '+part)
        record[k]=v
    return record

def one(exe,c,parent,timeout):
    with tempfile.TemporaryDirectory(prefix='d13b_cpu_',dir=parent) as tmp:
        root=Path(tmp)
        (root/'a'/'b').mkdir(parents=True)
        target=root/'a'/'magnetic_drum.txt'
        if c.existing=='DIR':target.mkdir()
        elif isinstance(c.existing,bytes):target.write_bytes(c.existing)
        try:
            p=subprocess.run([str(exe),c.name],cwd=root/'a'/'b',capture_output=True,
                             text=True,encoding='utf-8',errors='replace',timeout=timeout)
            observed=parse(p.stdout)
            pc0='101' if c.name=='io25-setup' else '100'
            pc1=('130' if c.name=='altjump' else '120') if c.expected is not None else pc0
            pc2=(('131' if c.name=='altjump' else '121') if c.expected is not None else pc0)
            wanted={
                'mode':c.name,
                'status':'OK' if c.expected is not None else 'ERROR',
                'pc0':pc0,'pc1':pc1,'pc2':pc2,
                'k1':'1','k2':'1','setup':'1','memory':'1','stable':'1',
                'xor':'6' if c.expected is not None else '0',
                'run2':'1' if c.expected is not None else '0',
                'steps':'3' if c.name=='io25-setup' else ('2' if c.expected is not None else '1'),
                'reason':c.reason,
                'HARDWARE_ORACLE':'0',
            }
            allowed_files={'a/magnetic_drum.txt'} if (c.expected is not None or isinstance(c.existing,bytes)) else set()
            files={x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file()}
            if c.expected is not None:output_ok=target.is_file() and target.read_bytes()==c.expected
            elif c.existing=='DIR':output_ok=target.is_dir() and list(target.iterdir())==[]
            elif isinstance(c.existing,bytes):output_ok=target.is_file() and target.read_bytes()==c.existing
            else:output_ok=not target.exists()
            ok=(p.returncode==0 and observed==wanted and output_ok and files==allowed_files)
            if not ok:
                print('  D13B-EXPECTED',wanted,'D13B-OBSERVED',observed)
                print('  output_ok',output_ok,'files',sorted(files),'exit',p.returncode)
                print('  stdout_tail',repr(p.stdout.splitlines()[-9:]))
                print('  stderr_tail',repr(p.stderr.splitlines()[-9:]))
        except (subprocess.TimeoutExpired, OSError, ValueError) as e:
            ok=False;print('  D13B-EXCEPTION',repr(e))
        print(f'D13B-CPU-CASE {c.name}: {"PASS" if ok else "FAIL"} '
              f'expected={c.reason if c.expected is None else "ACCEPTED"} '
              f'atomic={int(c.expected is None)} REAL_CPU=1',flush=True)
        return ok

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5);a=ap.parse_args()
    exe=Path(a.exe).resolve()
    parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():ap.error('exe and tempkyiv required')
    if not .2<=a.timeout<=60:ap.error('timeout out of range')
    passed=sum(one(exe,c,parent,a.timeout) for c in CASES)
    successes=sum(c.expected is not None for c in CASES)
    fails=len(CASES)-successes
    print(f'ISA-07 D13-B CPU PASS={passed}/30 TWO_STEP_SUCCESS={successes} '
          f'ATOMIC_REJECTION={fails} GENUINE_KYIV_T=1 '
          'HOST_POLICY=1 HARDWARE_ORACLE=0',flush=True)
    return 0 if passed==len(CASES) else 1
if __name__=='__main__':raise SystemExit(main())
