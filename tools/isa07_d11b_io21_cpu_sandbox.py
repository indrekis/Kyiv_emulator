#!/usr/bin/env python3
"""D11-B actual two-step Kyiv_t tests; all files inside tempkyiv/."""
from dataclasses import dataclass
from pathlib import Path
import argparse
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
SENTINEL=0o1234567012345

@dataclass(frozen=True)
class Case:
    name:str
    tape:bytes|None
    start:int=0o200
    end:int=0o202
    h:int=0
    error:str=''
    expected:tuple[int,...]=()
    shift:int=0

CASES=(
    Case('valid',b'11\n22\n33\n44\n',expected=(0o11,0o22,0o33)),
    Case('selected',b'11\n22\n33\n44\n',h=1,expected=(0o22,0o33,0o44)),
    Case('single',b'7\n8\n',end=0o200,expected=(0o7,)),
    Case('sign-bit',b'20000000000000\n22\n33\n',expected=(1<<40,0o22,0o33)),
    Case('max41',b'37777777777777\n22\n33\n',expected=((1<<41)-1,0o22,0o33)),
    Case('zeros',b'00000000000000\n0\n7\n',expected=(0,0,7)),
    Case('crlf',b'11\r\n22\r\n33\r\n',expected=(0o11,0o22,0o33)),
    Case('whitespace',b'  11 \t\n\t22\n33\t\n',expected=(0o11,0o22,0o33)),
    Case('extra-bad-ignored',b'11\n22\n33\nxyz\n',expected=(0o11,0o22,0o33)),
    Case('zero-discard',b'1\n22\n33\n',start=0,end=2,expected=(0,0o22,0o33)),
    Case('last-ram',b'11\n22\n33\n',start=0o1775,end=0o1777,expected=(0o11,0o22,0o33)),
    Case('offset',b'11\n22\n33\n',start=0o200,end=0o202,shift=0o1,expected=(0o11,0o22,0o33)),
    Case('missing',None,error='UNAVAILABLE_STREAM'),
    Case('empty',b'',error='MISSING_START_LINE'),
    Case('short',b'11\n22\n',error='SHORT_INPUT'),
    Case('bad-second',b'11\nBAD\n33\n',error='INVALID_TOKEN'),
    Case('bad-third',b'11\n22\n18\n',error='INVALID_TOKEN'),
    Case('suffix',b'11xyz\n22\n33\n',error='INVALID_TOKEN'),
    Case('negative',b'-1\n22\n33\n',error='INVALID_TOKEN'),
    Case('plus',b'+1\n22\n33\n',error='INVALID_TOKEN'),
    Case('overwide',b'40000000000000\n22\n33\n',error='INVALID_TOKEN'),
    Case('longdigits',b'000000000000001\n22\n33\n',error='INVALID_TOKEN'),
    Case('empty-record',b'11\n \n33\n',error='EMPTY_RECORD'),
    Case('missing-selected',b'11\n22\n',h=5,error='MISSING_START_LINE'),
    Case('short-selected',b'11\n22\n33\n',h=1,error='SHORT_INPUT'),
    Case('reversed',b'11\n22\n33\n',start=0o202,end=0o200,error='INVALID_INTERVAL'),
    Case('ram-over',b'11\n22\n33\n',start=0o1777,end=0o2001,error='INVALID_RAM_ADDRESS'),
    Case('ram-start',b'11\n22\n33\n',start=0o2000,end=0o2002,error='INVALID_RAM_ADDRESS'),
)

def one(exe,case,timeout,parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d11b_',dir=parent) as folder:
        root=Path(folder)
        (root/'a'/'b').mkdir(parents=True)
        if case.tape is not None:
            (root/'a'/'punched_tape.txt').write_bytes(case.tape)
        try:
            p=subprocess.run([str(exe),case.name,format(case.start,'o'),format(case.end,'o'),
                              str(case.h),format(case.shift,'o')],cwd=root/'a'/'b',
                             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f'D11B-CPU-CASE {case.name}: FAIL TIMEOUT');return False
        obs=[line for line in p.stdout.splitlines() if line.startswith('D11B-CPU ')]
        if p.returncode!=0 or len(obs)!=1:
            print('D11B-CPU-CASE',case.name,'FAIL process',p.returncode,'out',p.stdout[-600:],'err',p.stderr[-250:]);return False
        fields=dict(kv.split('=',1) for kv in obs[0].split()[1:])
        error=bool(case.error)
        expect_words=case.expected
        if case.start==0: # cell 0000 is hardwired to zero
            expect_words=(0,)+case.expected[1:]
        wanted='/'.join(format(v,'o') for v in expect_words) if not error and case.end-case.start<5 else None
        try:
            assert fields['tag']==case.name
            assert fields['status']==('ERROR' if error else 'OK')
            assert fields['reason']==(case.error or 'NONE')
            assert fields['pc1']==('100' if error else '101')
            assert fields['pc2']==('100' if error else '102')
            assert fields['k1']=='1' and fields['guard']=='1' and fields['stable']=='1'
            assert fields['h0']==str(case.h)
            assert fields['h1']==str(case.h+(0 if error else len(case.expected)))
            assert fields['HARDWARE_ORACLE']=='0'
            if error:
                assert fields['unchanged']=='1' and fields['k2']=='0' and fields['second']=='0'
                assert fields['xor']==str(SENTINEL)
            else:
                assert fields['second']=='1' and fields['k2']=='1' and fields['xor']=='6'
                if wanted is not None:assert fields['words']==wanted,(fields['words'],wanted)
            ok=True
        except (AssertionError,ValueError,KeyError) as e:
            ok=False;print('  D11B-CPU-DETAIL',case.name,fields,'expected',case,'err',str(e))
        print(f'D11B-CPU-CASE {case.name}: {"PASS" if ok else "FAIL"} '
              f'expected={case.error or "ACCEPTED"} observed={fields.get("status")} atomic={int(error)}')
        return ok

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5)
    a=ap.parse_args()
    exe=Path(a.exe).resolve()
    parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir() or not .2<=a.timeout<=60:
        ap.error('bad executable/tempkyiv/timeout')
    passcount=sum(one(exe,c,a.timeout,parent) for c in CASES)
    accepted=sum(not c.error for c in CASES)
    print(f'ISA-07 D11-B CPU PASS={passcount}/{len(CASES)} '
          f'TWO_STEP_SUCCESS={accepted} ATOMIC_REJECTION={len(CASES)-accepted} '
          'GENUINE_KYIV_T=1 HOST_POLICY=1 HARDWARE_ORACLE=0')
    return 0 if passcount==len(CASES) else 1
if __name__=='__main__':sys.exit(main())
