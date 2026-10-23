#!/usr/bin/env python3
"""D15/B1-H3: actual native tests, unchanged H2 oracle and updated ISA06 probes."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'examples/historical/gy1962/au1_logic.k41'
ROM=ROOT/'mem/ROM.txt'
EXPECTED_HIST='56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c'
EXPECTED_ROM='a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
CASES=(
 ('D1','tests/isa/isa06_d1_logic_probe.cpp','ISA-06 D1 STRICT=38/38 DOC-MISMATCH=0 POLICY=0 OBS=2'),
 ('D2','tests/isa/isa06_d2_logic_sequence_probe.cpp','ISA-06 D2 STRICT=17/17 DOC-MISMATCH=0 POLICY=0 OBS=0'),
)

def need(condition, code):
    if not condition:
        raise RuntimeError(code)

def run(cmd, cwd, timeout, tag):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,errors='replace',timeout=timeout)
    if p.returncode:
        print(f'D15B1H3-{tag} STDERR:\n{p.stderr[-5000:]}',file=sys.stderr)
        print(f'D15B1H3-{tag} STDOUT TAIL:\n'+ '\n'.join(p.stdout.splitlines()[-40:]),file=sys.stderr)
        raise RuntimeError(f'{tag}_RETURNED_{p.returncode}')
    return p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cli-exe', required=False)
    ap.add_argument('--cxx',default='g++')
    ap.add_argument('--timeout',type=int,default=30)
    ap.add_argument('--self-test',action='store_true')
    a=ap.parse_args()
    need(len(CASES)==2 and all('DOC-MISMATCH=0' in t[2] for t in CASES),'BAD_EXPECTATIONS')
    print('D15B1H3-REGRESSION-SELFTEST PASS ISA06_PROBES=2/2 HISTORY_ORACLE_REUSED=1')
    if a.self_test:return
    need(a.timeout>0,'TIMEOUT')
    exe=Path(a.cli_exe).resolve() if a.cli_exe else None
    need(exe is not None and exe.is_file(),'CLI_EXE_REQUIRED')
    tmp=ROOT/'tempkyiv'
    need(tmp.is_dir(),'TEMP_DIRECTORY_MISSING')
    need(hashlib.sha256(HIST.read_bytes()).hexdigest()==EXPECTED_HIST,'HIST_SHA_CHANGED')
    need(hashlib.sha256(ROM.read_bytes()).hexdigest()==EXPECTED_ROM,'ROM_SHA_CHANGED')
    for key,path,marker in CASES:
        target=tmp/('d15b1h3_isa06_'+key.lower()+'.exe')
        cmd=[a.cxx,'-std=c++17','-O0','-Wall','-Wextra','-pedantic','-Iinc',
             'src/main.cpp',path,'-o',str(target)]
        built=run(cmd,ROOT,max(90,a.timeout),key+'_BUILD')
        print(f'D15B1H3-BUILD {key} PASS WARNINGS={built.stderr.count("warning:")}',flush=True)
        output=run([str(target)],tmp,a.timeout,key+'_NATIVE')
        need(marker in output.stdout,key+'_MISSING_STRICT_SIGNATURE')
        print(f'D15B1H3-NATIVE {key} PASS '+marker,flush=True)
    check=run([sys.executable,str(ROOT/'tools/isa07_d15b1_h2_opcode17_probe.py'),
               '--cli-exe',str(exe),'--expect','xnor','--timeout',str(a.timeout)],
              ROOT,max(2*a.timeout,60),'OP17_HISTORICAL')
    need('D15B1H2-NATIVE PASS CASES=18/18' in check.stdout and
         'EXPECTED_ISA=XNOR HISTORICAL_TEST_MATCH=1' in check.stdout,
         'H2_HISTORICAL_ORACLE_MISMATCH')
    print('D15B1H3-NATIVE OP17 PASS CASES=18/18 HISTORICAL_TEST_MATCH=1',flush=True)
    need(hashlib.sha256(HIST.read_bytes()).hexdigest()==EXPECTED_HIST and
         hashlib.sha256(ROM.read_bytes()).hexdigest()==EXPECTED_ROM,
         'SOURCE_CHANGED_DURING_NATIVE_RUN')
    print('D15B1H3-REGRESSION PASS ISA06_D1=38/38 ISA06_D2=17/17 '
          'OP17=18/18 HISTORICAL_TEST_MATCH=1 HISTORY_IMAGE_IMMUTABLE=1 '
          'ROM_IMMUTABLE=1 HARDWARE_ORACLE=0')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('D15B1H3-REGRESSION FAIL',exc,file=sys.stderr)
        sys.exit(1)
