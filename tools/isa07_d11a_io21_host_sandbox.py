#!/usr/bin/env python3
"""D11-A: inspect real CPU host observations in isolated directories.

Expected outcomes are frozen CURRENT-CODE observations, not device oracles.
Do not use this runner as a gate after D11-B intentionally changes IO21.
"""
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
@dataclass(frozen=True)
class Case:
    mode: str
    tape: bytes | None
    status: str
    changed: int
    h: int
    w0: int | None = None

CASES = (
    Case('valid',b'11\n22\n33\n44\n','OK',3,3,0o11),
    Case('h1',b'11\n22\n33\n44\n55\n','OK',3,4,0o22),
    Case('single',b'11\n22\n','OK',1,1,0o11),
    Case('missing',None,'OK',0,0),
    Case('empty',b'','THROW',0,0),
    Case('short',b'11\n22\n','THROW',2,0,0o11),
    Case('malformed',b'11\nBAD\n33\n44\n','THROW',1,0,0o11),
    Case('suffix',b'11xyz\n22\n33\n44\n','OK',3,3,0o11),
    Case('negative',b'-1\n22\n33\n44\n','OK',3,3,(1<<64)-1),
    Case('word41',b'20000000000000\n22\n33\n44\n','WIDTH',None,None),
    Case('overwide',b'37777777777777\n22\n33\n44\n','WIDTH',None,None),
)

def one(exe,case,timeout,parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d11a_',dir=parent) as p:
        root=Path(p)
        (root/'a'/'b').mkdir(parents=True)
        if case.tape is not None:
            (root/'a'/'punched_tape.txt').write_bytes(case.tape)
            (root/'a'/'heads.txt').write_bytes(b'0\n0\n')
        try:
            proc=subprocess.run([str(exe),case.mode],cwd=root/'a'/'b',
                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f'D11A-CASE {case.mode}: FAIL process=TIMEOUT')
            return False
        obs=[line for line in proc.stdout.splitlines() if line.startswith('D11A-OBS ')]
        if proc.returncode!=0 or len(obs)!=1:
            print(f'D11A-CASE {case.mode}: FAIL exit={proc.returncode} output={proc.stdout[-600:]!r} stderr={proc.stderr[-300:]!r}')
            return False
        try:
            fields=dict(entry.split('=',1) for entry in obs[0].split()[1:])
            long_bits=int(fields['long_bits'])
            expected_state=(('THROW' if long_bits<=32 else 'OK') if case.status=='WIDTH' else case.status)
            count=(0 if expected_state=='THROW' else 3) if case.status=='WIDTH' else case.changed
            h=(0 if expected_state=='THROW' else 3) if case.status=='WIDTH' else case.h
            assert fields['mode']==case.mode
            assert fields['status']==expected_state
            assert int(fields['changed'])==count
            assert int(fields['h1'])==h
            assert fields['pc1']==('101' if expected_state=='OK' else '100')
            assert fields['k1']=='1' and fields['outside']=='0'
            assert fields['next']==('1' if expected_state=='OK' else '0')
            assert fields['k2']==('1' if expected_state=='OK' else '0')
            assert fields['xor']==('6' if expected_state=='OK' else '0')
            assert fields['HOST_OBSERVATION']=='1' and fields['HARDWARE_ORACLE']=='0'
            if case.w0 is not None:
                assert int(fields['w0'],8)==case.w0
            if case.mode=='word41' and expected_state=='OK':
                assert int(fields['w0'],8)==(1<<40)
            if case.mode=='overwide' and expected_state=='OK':
                assert int(fields['w0'],8)==(1<<41)-1
            result=True
        except (AssertionError, ValueError, KeyError) as e:
            result=False
            print(f'  D11A-OBSERVED={fields!r} expected={case!r} issue={e!r}')
        print(f'D11A-CASE {case.mode}: {"PASS" if result else "FAIL"} '
              f'CURRENT_CODE={fields.get("status")} LONG_BITS={fields.get("long_bits")} '
              f'RAM_CHANGED={fields.get("changed")} HOST_OBSERVATION=1')
        return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5)
    args=ap.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():
        ap.error('real CPU executable and tempkyiv/ directory required')
    if not .2 <= args.timeout <= 60:
        ap.error('timeout must be 0.2..60s')
    passed=sum(one(exe,c,args.timeout,ROOT/'tempkyiv') for c in CASES)
    print(f'ISA-07 D11-A IO21 HOST OBS PASS={passed}/{len(CASES)} '
          'SOURCE_PC=GY62_P58 HOST_FAILURES_NOT_HARDWARE=1 CPU_MUTATION=0')
    return 0 if passed==len(CASES) else 1

if __name__=='__main__':sys.exit(main())
