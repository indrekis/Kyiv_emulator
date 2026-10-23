#!/usr/bin/env python3
"""D15/B1-H1 observed real-CPU reproduction, NOT historical-success qualification."""
import argparse,hashlib,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE=ROOT/'examples/historical/gy1962/au1_logic.k41'
IMAGE_SHA='56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c'
ROM=ROOT/'mem/ROM.txt'
ROM_SHA='a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
ALL_ONES='37777777777777'
ZERO='00000000000000'
# Historical 0043 start and three isolated HOST diagnostics.  Never modify the source image.
PROFILES=[('HISTORICAL_ENTRY','0043','22','CPU_STOP','19','0076',ALL_ONES),
          ('XOR_COMPLEMENTS','0073','2','LIMIT','2','0075',ALL_ONES),
          ('XOR_IDENTICAL_2','0101','2','LIMIT','2','0103',ZERO),
          ('XOR_IDENTICAL_3','0104','2','LIMIT','2','0106',ZERO)]
WATCH={'0002':'12525252525252','0003':'25252525252525','3036':ALL_ONES}

def need(ok,why,result=None):
    if ok:return
    if result is not None:
        print('D15B1H1-OBSERVATION STDOUT LAST LINES:',file=sys.stderr)
        print('\n'.join(result.stdout.splitlines()[-35:]),file=sys.stderr)
        print('D15B1H1-OBSERVATION STDERR:',result.stderr[-2500:],file=sys.stderr)
    raise RuntimeError(why)

def parse_summary(out):
    m=re.search(r'D15A2-RUN STATUS=(CPU_STOP|LIMIT) STEPS=(\d+) C=([0-7]{4})',out)
    if not m:raise RuntimeError('MISSING_RUN_REPORT')
    return m.groups()

def selftest():
    good='D15A2-RUN STATUS=CPU_STOP STEPS=19 C=0076 K=33000000000000'
    assert parse_summary(good)==('CPU_STOP','19','0076')
    assert len(PROFILES)==4 and all(len(p)==7 for p in PROFILES)
    assert PROFILES[0][3:6]==('CPU_STOP','19','0076')
    print('D15B1H1-NATIVE-SELFTEST PASS OBSERVED_STOP=1 PROFILES=4/4')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cli-exe')
    p.add_argument('--timeout',type=int,default=20)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    if args.self_test:selftest();return
    need(bool(args.cli_exe),'EXE_REQUIRED')
    exe=Path(args.cli_exe).resolve()
    need(exe.is_file(),'EXE_NOT_FOUND')
    before=IMAGE.read_bytes()
    need(hashlib.sha256(before).hexdigest()==IMAGE_SHA,'IMAGE_SHA')
    rom_before=ROM.read_bytes()
    need(hashlib.sha256(rom_before).hexdigest()==ROM_SHA,'ROM_SHA')
    with tempfile.TemporaryDirectory(prefix='gy62_b1h1_') as td:
        count=0
        for name,start,bound,status,steps,c_expected,scratch in PROFILES:
            reports=[]
            for cwd in (Path(td), ROOT/'tempkyiv'):
                count+=1
                need(cwd.is_dir(),'CWD_MISSING')
                cmd=[str(exe),'image',str(IMAGE),start,bound]
                for address in [*WATCH,'0347']:cmd+=['--watch',address]
                r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,
                                 errors='replace',timeout=args.timeout)
                actual=parse_summary(r.stdout)
                print(f'D15B1H1-CASE {count:02d} PROFILE={name} CWD={"EXTERNAL" if count%2 else "TEMPKYIV"} RC={r.returncode} RUN={actual} EXPECTED_OBSERVATION={(status,steps,c_expected)}')
                need(r.returncode==0,'RUN_FAILED',r)
                need(actual==(status,steps,c_expected),'OBSERVATION_MISMATCH',r)
                need('D15A3P3-ROM PASS SOURCE=DEFAULT WORDS=183 UNKNOWN_3200=1' in r.stdout
                     and 'SHA_PINNED=1' in r.stdout and f'SHA256={ROM_SHA}' in r.stdout,'ROM_REPORT',r)
                need('D15A2-LOAD PASS WORDS=39 ROM_OPT_IN=0' in r.stdout,'IMAGE_LOAD',r)
                for address,raw in {**WATCH,'0347':scratch}.items():
                    need(f'D15A2-WATCH ADDR={address} RAW={raw}' in r.stdout,
                         'WATCH_'+address,r)
                reports.append('\n'.join(l for l in r.stdout.splitlines()
                    if l.startswith(('D15A2-RUN','D15A2-WATCH','D15A2-LOAD','D15A3P3-ROM'))))
            need(reports[0]==reports[1],'CWD_PARITY_'+name)
    need(IMAGE.read_bytes()==before and ROM.read_bytes()==rom_before,'SOURCE_MUTATION')
    print(f'D15B1H1-OBSERVATION PASS CASES={count}/{count} CWD_PARITY=4/4 SOURCE_IMMUTABLE=1 '
          'SOURCE_WORDS=39/39 CPU_MUTATION=0 HISTORICAL_EXPECTATION_MATCH=0 '
          'ISA_ADJUDICATION=OPEN INDEPENDENT_SECOND_PASS=PENDING HARDWARE_ORACLE=0')
    print('D15B1H1-NATIVE PASS OBSERVATION_ONLY=1 HISTORICAL_DIAGNOSTIC_PASS=0')
if __name__=='__main__':
    try:main()
    except Exception as exc:print('D15B1H1-NATIVE FAIL',str(exc),file=sys.stderr);sys.exit(1)
