#!/usr/bin/env python3
"""D15/B1-H2: executable opcode 17 discriminator; no source or CPU mutation."""
import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / 'examples/historical/gy1962/au1_logic.k41'
ROM = ROOT / 'mem/ROM.txt'
HIST_SHA = '56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c'
ROM_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
MASK = (1 << 41) - 1
ONES = 0o37777777777777
A = 0o12525252525252
B = 0o25252525252525
PROFILES = (
    ('ZERO_ZERO', 0, 0),
    ('ZERO_ONE', 0, 1),
    ('ONE_ZERO', 1, 0),
    ('ONE_ONE', 1, 1),
    ('HISTORICAL_COMPLEMENTS', A, B),
    ('ONES_IDENTICAL', ONES, ONES),
    ('SIGN_VS_ZERO', 1 << 40, 0),
    ('SIGN_IDENTICAL', 1 << 40, 1 << 40),
)


def raw(v):
    if not (0 <= v <= MASK):
        raise ValueError('OUTSIDE_41_BIT_WORD')
    return f'{v:014o}'


def oracle(a, b, kind):
    return ((a ^ b) if kind == 'xor' else (~(a ^ b))) & MASK


def need(ok, code, proc=None):
    if ok:
        return
    if proc is not None:
        print('STDOUT TAIL:\n'+'\n'.join(proc.stdout.splitlines()[-18:]), file=sys.stderr)
        print('STDERR TAIL:\n'+proc.stderr[-1000:],file=sys.stderr)
    raise RuntimeError(code)


def summary(out):
    m = re.search(r'D15A2-RUN STATUS=(CPU_STOP|LIMIT) STEPS=(\d+) C=([0-7]{4})', out)
    if not m:
        raise RuntimeError('MISSING_RUN_SUMMARY')
    return m.groups()


def watch(out, addr):
    m = re.search(r'D15A2-WATCH ADDR='+addr+r' RAW=([0-7]{14})', out)
    if not m:
        raise RuntimeError('MISSING_WATCH_'+addr)
    return m.group(1)


def selftest():
    need(A ^ B == MASK, 'NOT_COMPLEMENTARY_41')
    need(len(PROFILES) == 8, 'PROFILES')
    for a,b in [(0,0),(0,1),(1,0),(1,1),(A,B),(ONES,ONES),(1<<40,0)]:
        need(oracle(a,b,'xor') ^ oracle(a,b,'xnor') == MASK, 'BAD_ORACLE')
    need([oracle(a,b,'xnor') & 1 for a,b in [(0,0),(0,1),(1,0),(1,1)]] == [1,0,0,1], 'XNOR_TRUTH_TABLE')
    need([oracle(a,b,'xor') & 1 for a,b in [(0,0),(0,1),(1,0),(1,1)]] == [0,1,1,0], 'XOR_TRUTH_TABLE')
    need(raw(MASK) == '37777777777777', 'RAW_41_MASK')
    need(oracle(A,B,'xnor') == 0 and oracle(A,A,'xnor') == MASK, 'HISTORICAL_ORACLE')
    print('D15B1H2-PROBE-SELFTEST PASS PROFILES=8/8 TRUTH_TABLES=2/2 SIGN_BIT=1 MASK41=1')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cli-exe',required=False)
    p.add_argument('--expect',choices=('xor','xnor'),default='xor')
    p.add_argument('--timeout',type=int,default=20)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    selftest()
    if args.self_test:
        return
    need(bool(args.cli_exe),'EXE_REQUIRED')
    exe=Path(args.cli_exe).resolve()
    need(exe.is_file(),'EXE_MISSING')
    before=HIST.read_bytes()
    rom_before=ROM.read_bytes()
    need(hashlib.sha256(before).hexdigest()==HIST_SHA,'HISTORICAL_IMAGE_SHA')
    need(hashlib.sha256(rom_before).hexdigest()==ROM_SHA,'BASE_ROM_SHA')
    count=0
    with tempfile.TemporaryDirectory(prefix='gy62_h2_') as td:
        folder=Path(td)
        for name,a,b in PROFILES:
            fixture=folder/(name.lower()+'.k41')
            contents=('KYIV41-OCT1\n'
                + f'0002 {raw(a)}\n0003 {raw(b)}\n'
                + '0200 17000200030347\n')
            fixture.write_bytes(contents.encode('ascii'))
            before_fixture=fixture.read_bytes()
            reports=[]
            for cwd in (folder,ROOT/'tempkyiv'):
                need(cwd.is_dir(),'CWD_MISSING')
                cmd=[str(exe),'image',str(fixture),'0200','1',
                     '--watch','0002','--watch','0003','--watch','0347']
                r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,
                                 errors='replace',timeout=args.timeout)
                count+=1
                actual=summary(r.stdout) if r.returncode==0 else ('FAIL',str(r.returncode),'?')
                observed=watch(r.stdout,'0347') if r.returncode==0 else '?'
                expected=raw(oracle(a,b,args.expect))
                print(f'D15B1H2-CASE {count:02d} PROFILE={name} CWD={"EXTERNAL" if count%2 else "TEMPKYIV"} EXPECT={args.expect.upper()} RC={r.returncode} RESULT={observed} ORACLE={expected} RUN={actual}',flush=True)
                need(r.returncode==0, 'CLI_FAILED',r)
                need(actual==('LIMIT','1','0201'), 'CONTROL_FLOW_MISMATCH',r)
                need(observed==expected, 'OP17_SEMANTICS_MISMATCH',r)
                need(watch(r.stdout,'0002')==raw(a) and watch(r.stdout,'0003')==raw(b), 'INPUT_MUTATION',r)
                need('D15A3P3-ROM PASS SOURCE=DEFAULT WORDS=183 UNKNOWN_3200=1' in r.stdout
                    and f'SHA256={ROM_SHA}' in r.stdout and 'SHA_PINNED=1' in r.stdout, 'ROM_PIN_FAILED',r)
                reports.append(tuple(l for l in r.stdout.splitlines() if l.startswith(('D15A2-RUN','D15A2-WATCH','D15A3P3-ROM'))))
            need(reports[0]==reports[1], 'CWD_PARITY_'+name)
            need(fixture.read_bytes()==before_fixture, 'FIXTURE_MUTATION')
        # Existing H1 historical image: actual outcome distinguishes the two candidate ISA semantics.
        expected_historical=(('CPU_STOP','19','0076') if args.expect=='xor' else ('LIMIT','22','0107'))
        for cwd in (folder,ROOT/'tempkyiv'):
            cmd=[str(exe),'image',str(HIST),'0043','22','--watch','0347']
            r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,errors='replace',timeout=args.timeout)
            count+=1
            actual=summary(r.stdout) if r.returncode==0 else ('FAIL',str(r.returncode),'?')
            print(f'D15B1H2-CASE {count:02d} PROFILE=HISTORICAL_ENTRY CWD={"EXTERNAL" if count%2 else "TEMPKYIV"} EXPECT={args.expect.upper()} RC={r.returncode} RUN={actual} ORACLE={expected_historical}',flush=True)
            need(r.returncode==0 and actual==expected_historical, 'HISTORICAL_ROUTE_MISMATCH',r)
            need(watch(r.stdout,'0347')==raw(MASK), 'HISTORICAL_FINAL_0347',r)
        need(HIST.read_bytes()==before and ROM.read_bytes()==rom_before,'PRIMARY_SOURCE_MUTATION')
    print(f'D15B1H2-NATIVE PASS CASES={count}/{count} PROFILES=8/8 CWD_PARITY=8/8 '
          f'EXPECTED_ISA={args.expect.upper()} HISTORICAL_TEST_MATCH={1 if args.expect=="xnor" else 0} '
          'GY1962_TEXT_CONFLICT=OPEN SOURCE_SHA_PIN=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')

if __name__=='__main__':
    try:
        main()
    except Exception as e:
        print('D15B1H2-NATIVE FAIL',e,file=sys.stderr)
        sys.exit(1)
