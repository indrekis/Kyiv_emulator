#!/usr/bin/env python3
"""D15/B1-H5: production CLI, two historical addition pairs, two CWDs."""
from __future__ import annotations
import argparse, pathlib, tempfile, subprocess, re, hashlib, os, sys

IMG='examples/historical/gy1962/au1_addition_0110_0115.k41'
IMG_SHA='661c2cf6fcd948c2bb6fca22d7a49c02364b7616bb305f39fe6df480506ff585'
DATA={'0002':'12525252525252','0003':'25252525252525','0004':'05252525252525'}
# All address literals here are OCTAL strings.
GROUPS=[('0110','0111','0113','12525252525252'),('0113','0114','0116','05252525252525')]
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')

def selftest():
    assert len(DATA)==3 and len(GROUPS)==2
    assert [g[0] for g in GROUPS]==['0110','0113']
    assert RUN.search('D15A2-RUN STATUS=LIMIT STEPS=2 C=0113')
    assert all(len(w)==14 and all(c in '01234567' for c in w) for w in DATA.values())
    print('D15B1H5-RUNNER-SELFTEST PASS GROUPS=2/2 INPUTS=3/3 BOUNDED=1')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cli-exe')
    ap.add_argument('--timeout',type=float,default=20.)
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    selftest()
    if args.self_test:return
    assert args.cli_exe, 'MISSING_CLI_EXE'
    root=pathlib.Path(__file__).resolve().parent.parent
    image=root/IMG
    assert hashlib.sha256(image.read_bytes()).hexdigest()==IMG_SHA,'HISTORICAL_IMAGE_MUTATED'
    executable=pathlib.Path(args.cli_exe).resolve()
    assert executable.is_file(), ('MISSING_EXE',executable)
    all_cases=0
    with tempfile.TemporaryDirectory(prefix='d15b1h5_cwd_') as temp:
        for start,branch,dest,expected in GROUPS:
            for n,expected_c in [(1,branch),(2,dest)]:
                for wd,cwd in [('EXTERNAL',pathlib.Path(temp)),('TEMPKYIV',root/'tempkyiv')]:
                    assert cwd.is_dir(),('CWD_MISSING',cwd)
                    argsv=[str(executable),'image',str(image),start,str(n),'--watch','0347']
                    for addr in DATA: argsv.extend(['--watch',addr])
                    r=subprocess.run(argsv,cwd=cwd,capture_output=True,text=True,
                                     timeout=args.timeout,encoding='utf-8',errors='replace')
                    m=RUN.search(r.stdout)
                    w=dict(WATCH.findall(r.stdout))
                    good=r.returncode==0 and m is not None and m.groups()==('LIMIT',str(n),expected_c) and w.get('0347')==expected and all(w.get(a)==v for a,v in DATA.items())
                    all_cases+=1
                    print(f'D15B1H5-CASE {all_cases:02d} START={start} STEPS={n} CWD={wd} RC={r.returncode} RUN={m.groups() if m else None} RESULT={w.get("0347")} ORACLE={expected} '+('PASS' if good else 'MISMATCH'),flush=True)
                    if not good:
                        print('D15B1H5-OBSERVED STDOUT TAIL:\n'+'\n'.join(r.stdout.splitlines()[-34:]),flush=True)
                        print('D15B1H5-OBSERVED STDERR:\n'+r.stderr,flush=True)
                        raise AssertionError('HISTORICAL_ADDITION_MISMATCH')
    assert all_cases==8
    print('D15B1H5-NATIVE PASS CASES=8/8 PAIRS=2/2 CWD_PARITY=4/4 HISTORICAL_EXPECTATION_MATCH=1 ROM_DEFAULT_PIN=1 CPU_MUTATION=0 HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')

if __name__=='__main__':
    try:main()
    except BaseException as e:raise SystemExit('D15B1H5-NATIVE FAIL '+repr(e))
