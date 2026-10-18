#!/usr/bin/env python3
"""D12-A: current-code IO24 host observations on genuine Kyiv_t, NOT hardware.

Execute each source mode with separate cwd/temporary mock drum file. Historical
success transfer is GY62 p.15; host failures are OBS and remain deliberately
UNQUALIFIED as source oracles. Never execute reversed interval on current CPU.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SIGN = (1 << 40)

@dataclass(frozen=True)
class Case:
    mode: str
    tape: bytes | None
    status: str
    ram: tuple[int, int, int]
    changed: int
    unmapped: int = 0
    target: str = '120'

CASES = (
    Case('full',b'5 7 9\n','OK',(5,7,9),3),
    Case('single',b'5 7 9\n','OK',(0,5,0),1),
    Case('track1',b'99 88 77\n5 7 9\n','OK',(5,7,9),3),
    Case('zone2',b'xx5 7 9\n','OK',(5,7,9),3),
    Case('multiline',b'5 7\n9\n','OK',(5,7,9),3),
    Case('missing',None,'OK',(0,0,0),0),
    Case('empty',b'','OK',(0,0,0),0),
    Case('short',b'5 7\n','OK',(5,7,0),2),
    Case('malformed',b'5 BAD 9\n','THROW',(5,0,0),1),
    Case('bad-first',b'BAD 7 9\n','THROW',(0,0,0),0),
    Case('suffix',b'5xyz 7 9\n','OK',(5,7,9),3),
    Case('negative',b'-1 7 9\n','OK',(SIGN|1,7,9),3),
    Case('negative-zero',b'-0 7 9\n','OK',(0,7,9),2),
    Case('over32',b'2147483648 7 9\n','THROW',(0,0,0),0),
    Case('word41',b'1099511627776 7 9\n','THROW',(0,0,0),0),
    Case('double-space',b'5  7 9\n','THROW',(5,0,0),1),
    Case('outside-physical',b'5\n','OK',(0,0,0),1,5),
    Case('alternate',b'5 7 9\n','OK',(5,7,9),3,0,'130'),
    Case('crlf',b'5 7 9\r\n','OK',(5,7,9),3),
    Case('track-missing',b'5 7 9\n','OK',(0,0,0),0),
)

def decode(output):
    obs = [line for line in output.splitlines() if line.startswith('D12A-OBS ')]
    if len(obs) != 1:
        raise ValueError('expected exactly one D12A-OBS line')
    items=obs[0].split()[1:]
    result={}
    for part in items:
        if '=' not in part:raise ValueError('malformed output field: '+part)
        k,v=part.split('=',1)
        if k in result:raise ValueError('duplicate field: '+k)
        result[k]=v
    return result

def one(exe, case, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d12a_',dir=parent) as folder:
        root=Path(folder)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        if case.tape is not None:
            (root/'mem'/'drum_in.txt').write_bytes(case.tape)
        try:
            p=subprocess.run([str(exe),case.mode],cwd=root/'a'/'b',
                             capture_output=True,text=True,encoding='utf-8',
                             errors='replace',timeout=timeout)
            out=p.stdout+'\n'+p.stderr
            f=decode(out)
            final_pc=oct(int(case.target,8)+1)[2:]
            expect={
                'mode':case.mode, 'status':case.status,
                'pc1':case.target if case.status=='OK' else '100',
                'pc2':final_pc if case.status=='OK' else '100',
                'k1':'1','k2':'1','changed':str(case.changed),
                'outside':'0','stable':'1',
                'ram':'/'.join(map(str,case.ram)),
                'unmapped':str(case.unmapped),
                'xor':'6' if case.status=='OK' else '0',
                'run':'1/1' if case.status=='OK' else '0/0',
                'error':'NONE' if case.status=='OK' else 'STD_EXCEPTION',
                'steps':'2' if case.status=='OK' else '1',
                'HOST_OBSERVATION':'1','HARDWARE_ORACLE':'0',
            }
            ok=(p.returncode==0 and f==expect)
            allowed = {'mem/drum_in.txt'} if case.tape is not None else set()
            observed={x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file()}
            ok=ok and observed==allowed
            if not ok:
                print('  D12A-DIAGNOSTIC mode='+case.mode+' code='+str(p.returncode))
                print('  observed='+repr(f))
                print('  expected='+repr(expect))
                print('  files='+repr(sorted(observed)))
                print('  output_tail='+repr(out.splitlines()[-12:]))
        except (subprocess.TimeoutExpired, OSError, ValueError) as e:
            ok=False
            print('  D12A-DIAGNOSTIC mode='+case.mode+' error='+repr(e))
        print(f'D12A-CASE {case.mode}: {"PASS" if ok else "FAIL"} '
              f'CURRENT_CODE={case.status} PARTIAL_WRITES={case.changed if case.status=="THROW" else 0} '
              f'HOST_OBSERVATION=1')
        return ok

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--exe',required=True)
    cli.add_argument('--timeout',type=float,default=5)
    args=cli.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():
        cli.error('compiled real-CPU executable and tempkyiv/ are required')
    if not 0.2<=args.timeout<=60:cli.error('timeout outside 0.2..60 s')
    passed=sum(one(exe,c,args.timeout,ROOT/'tempkyiv') for c in CASES)
    print(f'ISA-07 D12-A IO24 HOST OBS PASS={passed}/{len(CASES)} '
          'REAL_CPU=1 GY62_BRANCH=QUALIFIED HOST_FAILURES=OBS_ONLY '
          'IO25_STATE=PRESERVED REVERSED_INTERVAL=STATIC_ONLY '
          'CPU_MUTATION=0 HARDWARE_ORACLE=0')
    return 0 if passed==len(CASES) else 1

if __name__=='__main__':raise SystemExit(main())
