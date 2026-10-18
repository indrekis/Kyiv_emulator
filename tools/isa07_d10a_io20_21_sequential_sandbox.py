#!/usr/bin/env python3
"""D10-A: isolated TWO-STEP IO20/21 sequential control and XOR witnesses.

Text fixtures deliberately retain current host octal parsing for the narrow PC
fix; GY62 numerical/BCD conversion is deferred, NOT asserted by this runner.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    '20-range':   ((1,2,3,0),0,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '20-single':  ((0,7,0,0),0,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '20-offset':  ((0,1,2,3),0,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '20-short':   ((1,2,0,0),0,'HOST_POLICY'),
    '20-missing': ((0,0,0,0),0,'HOST_POLICY'),
    '20-zone1':   ((1,2,3,0),0,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-range':   ((1,2,3,0),3,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-single':  ((0,7,0,0),1,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-offset':  ((0,1,2,3),3,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-h1':     ((18,27,36,0),4,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-a3':     ((1,2,3,0),3,'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER'),
    '21-missing': ((0,0,0,0),0,'HOST_POLICY'),
}
OBS = re.compile(r'D10A-OBS mode=(\S+) pc0=(\S+) pc1=(\S+) pc2=(\S+) '
                 r'k1_match=(\d+) k2_match=(\d+) memory=(\d+)/(\d+)/(\d+)/(\d+) '
                 r'h=(\d+) xor=(\d+) running=(\d+)/(\d+) steps=(\d+)')

def one(exe, mode, parent, timeout):
    with tempfile.TemporaryDirectory(prefix='isa07_d10a_', dir=parent) as folder:
        root=Path(folder)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        kind,shape=mode.split('-',1)
        if kind=='20' and shape!='missing':
            data=('7 8\n' if shape=='single' else
                  '1 2\n' if shape=='short' else
                  ' 1 2 3 4\n' if shape=='zone1' else '1 2 3 4\n')
            (root/'mem'/'punch_cards_in.txt').write_text(data,encoding='ascii')
        if kind=='21' and shape!='missing':
            data=('7\n8\n' if shape=='single' else
                  '11\n22\n33\n44\n55\n' if shape=='h1' else
                  '1\n2\n3\n4\n5\n')
            (root/'a'/'punched_tape.txt').write_text(data,encoding='ascii')
            (root/'a'/'heads.txt').write_text('0\n0\n',encoding='ascii')
        try:
            p=subprocess.run([str(exe),mode],cwd=root/'a'/'b',
                             capture_output=True,text=True,encoding='utf-8',
                             errors='replace',timeout=timeout)
            state=f'EXIT_{p.returncode}'
            out=p.stdout+'\n'+p.stderr
        except subprocess.TimeoutExpired:
            state='TIMEOUT';out=''
        matches=OBS.findall(out)
        m=matches[0] if len(matches)==1 else None
        mem=tuple(map(int,m[6:10])) if m else None
        h=int(m[10]) if m else None
        x=int(m[11]) if m else None
        expected_mem,expected_h,classification=CASES[mode]
        ok=(state=='EXIT_0' and m is not None and m[0]==mode and
            m[1:4]==('100','101','102') and m[4:6]==('1','1') and
            mem==expected_mem and h==expected_h and x==6 and
            m[12:]==('1','1','2'))
        print(f"{'D10A-CODE-PASS' if ok else 'D10A-CODE-FAIL'} mode={mode} "
              f'process={state} pc1={m[2] if m else "NA"} '
              f'pc2={m[3] if m else "NA"} K_PREFETCH={int(bool(m and m[4:6]==("1","1")))} '
              f'memory={"/".join(map(str,mem)) if mem else "NA"} '
              f'h={h} xor={x} class={classification} result={"PASS" if ok else "FAIL"}')
        if not ok:
            print('  expected:',expected_mem,expected_h,'PC=101/102 K=1/1 XOR=6')
            print('  OUTPUT_TAIL=',repr(out.splitlines()[-12:]))
        return ok

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5)
    args=ap.parse_args()
    exe=Path(args.exe).resolve()
    parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        ap.error('compiled two-step executable and tempkyiv required')
    if not 0.2<=args.timeout<=60: ap.error('timeout must be in 0.2..60 seconds')
    results=[one(exe,mode,parent,args.timeout) for mode in CASES]
    passed=sum(results)
    print(f'ISA-07 D10A SANDBOX PASS={passed}/{len(CASES)} TWO_STEPS={passed} '
          'IO20_21_SEQUENTIAL=GY62_P58 K_PREFETCH=GY62_P58_DOCUMENTED '
          'INPUT_INTERVALS=PRESERVED NUMERIC_CONVERSION=OPEN '
          'MISSING_SHORT=HOST_POLICY IO24_25=PRESERVED DEVICE_ORACLES=0')
    return 0 if passed==len(CASES) else 1

if __name__=='__main__': sys.exit(main())
