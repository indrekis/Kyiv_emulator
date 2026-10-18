#!/usr/bin/env python3
"""D10-F3 real Kyiv_t CPU oracle, reuses D10-E3 executable and baseline fixtures.

This runner intentionally supersedes D10-E3's three NONEXACT-rejection
expectations. Keep original D10-E3 tests and logs unchanged as history.
"""
import argparse
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import isa07_d10e3_io20_cpu_sandbox as old

Case=old.Case
SOURCE=old.SOURCE

def word(token):
    negative=token.startswith('-')
    digits=token.lstrip('+-')
    if digits.startswith('0.'): digits=digits[2:]
    assert len(digits)==10 and digits.isascii() and digits.isdigit(),token
    quotient,remainder=divmod(int(digits)*(1<<40),10**10)
    octal=f'{quotient | ((1<<40) if negative else 0):014o}'
    if token in SOURCE: assert octal==SOURCE[token],(token,octal,SOURCE[token])
    return octal, bool(remainder)

OVERRIDES={
    'nonexact-first': ('+0.1000000000','+0.6250000000'),
    'nonexact-second': ('+0.6250000000','+0.1000000000'),
    # Extra VALID token must be checked, but is not written and does not
    # change status of the actually committed word.
    'nonexact-extra': ('+0.6250000000',),
}
CASES=[]
for c in old.CASES:
    if c.name in OVERRIDES:
        assert c.error=='NONEXACT',c.name
        c=replace(c,error='',values=OVERRIDES[c.name])
    CASES.append(c)
CASES += [
    Case('trunc-positive',0o200,0o200,0,0,0,b'+0.1000000000\n',('+0.1000000000',)),
    Case('trunc-negative',0o200,0o200,0,0,0,b'-0.1000000000\n',('-0.1000000000',)),
    Case('trunc-300',0o200,0o200,0,0,0,b'3000000000\n',('+0.3000000000',)),
    Case('trunc-tiny',0o200,0o200,0,0,0,b'0000000001\n',('+0.0000000001',)),
    Case('trunc-tiny-negative',0o200,0o200,0,0,0,b'-0000000001\n',('-0.0000000001',)),
    Case('trunc-max',0o200,0o200,0,0,0,b'9999999999\n',('+0.9999999999',)),
    Case('trunc-max-negative',0o200,0o200,0,0,0,b'-9999999999\n',('-0.9999999999',)),
    Case('trunc-mixed-record',0o200,0o202,0,0,0,
         b'6250000000 -1000000000 3000000000\n',
         ('+0.6250000000','-0.1000000000','+0.3000000000')),
    Case('trunc-multiline',0o200,0o201,0,0,0,
         b'1000000000\n-5000000000\n',('+0.1000000000','-0.5000000000')),
    Case('trunc-offset',0o200,0o201,3,0,0,
         b'xxx-1000000000 6250000000\n',('-0.1000000000','+0.6250000000')),
    Case('trunc-selected-line',0o200,0o200,3,1,0,
         b'BAD NOT PROCESSED\nxxx1000000000\n',('+0.1000000000',)),
    Case('trunc-crlf',0o200,0o201,0,0,0,
         b'1000000000\r\n-6250000000\r\n',('+0.1000000000','-0.6250000000')),
    Case('trunc-surplus-valid',0o200,0o200,0,0,0,
         b'6250000000 1000000000\n',('+0.6250000000',)),
    Case('trunc-surplus-invalid',0o200,0o200,0,0,0,
         b'1000000000 INVALID\n',error='INVALID_TOKEN'),
    Case('trunc-then-invalid',0o200,0o201,0,0,0,
         b'1000000000\nINVALID\n',error='INVALID_TOKEN'),
    Case('trunc-then-empty',0o200,0o201,0,0,0,
         b'1000000000\n\n',error='EMPTY_RECORD'),
    Case('trunc-then-short',0o200,0o201,0,0,0,
         b'1000000000\n',error='SHORT_INPUT'),
    Case('trunc-ram-end',0o1777,0o1777,0,0,0,
         b'1000000000\n',('+0.1000000000',)),
    Case('trunc-zero-discard',0o0,0o1,0,0,0,
         b'1000000000 -3000000000\n',('+0.1000000000','-0.3000000000')),
]
assert len(set(c.name for c in CASES))==len(CASES)

def run_case(exe, case, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d10f3_',dir=parent) as d:
        root=Path(d)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        if case.data is not None:
            (root/'mem'/'punch_cards_in.txt').write_bytes(case.data)
        argv=[str(exe),case.name,old.oct_arg(case.a1),old.oct_arg(case.a2),
              old.oct_arg(case.a3),str(case.line),old.oct_arg(case.a_reg)]
        try:
            p=subprocess.run(argv,cwd=root/'a'/'b',capture_output=True,
                             text=True,encoding='utf-8',errors='replace',timeout=timeout)
            obs=old.parse_summary(p.stdout,case.name)
            process='EXIT_'+str(p.returncode)
        except subprocess.TimeoutExpired:
            obs=None;p=None;process='TIMEOUT'
        if case.error:
            ok=(p is not None and p.returncode==0 and obs is not None and
                obs.get('status')=='ERROR' and obs.get('reason')==case.error and
                obs.get('pc')=='100' and obs.get('k')=='1' and
                obs.get('unchanged')=='1' and obs.get('regs')=='1' and
                obs.get('steps')=='1')
            expect_words='NONE'
        else:
            expected=tuple(word(v)[0] for v in case.values)
            if case.a1==0:
                expected=('00000000000000',)+expected[1:]
            expect_words='/'.join(expected)
            ok=(p is not None and p.returncode==0 and obs is not None and
                obs.get('status')=='OK' and obs.get('pc1')=='101' and
                obs.get('pc2')=='102' and obs.get('k1')=='1' and
                obs.get('k2')=='1' and obs.get('guard')=='1' and
                obs.get('regs')=='1' and obs.get('xor')=='6' and
                obs.get('run')=='1/1' and obs.get('steps')=='2' and
                obs.get('words')==expect_words)
        print(f'D10F3-CPU-CASE {case.name}: {"PASS" if ok else "FAIL"} '
              f'expected={case.error or "ACCEPTED"} '
              f'observed={obs.get("status") if obs else "NONE"} process={process}')
        if not ok:
            print(' expected_words=',expect_words,'observed=',obs)
            if p is not None:
                print(' stdout_tail=',repr(p.stdout.splitlines()[-8:]))
                print(' stderr_tail=',repr(p.stderr.splitlines()[-8:]))
        return ok

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5);a=ap.parse_args()
    exe=Path(a.exe).resolve()
    if not exe.is_file(): ap.error('genuine CPU probe executable required')
    if not .2<=a.timeout<=60: ap.error('timeout outside 0.2..60')
    parent=ROOT/'tempkyiv'
    if not parent.is_dir(): ap.error('repo tempkyiv directory required')
    passed=sum(run_case(exe,c,a.timeout,parent) for c in CASES)
    print(f'ISA-07 D10-F3 CPU PASS={passed}/{len(CASES)} '
          f'TWO_STEP_SUCCESS={sum(not c.error for c in CASES)} '
          f'ATOMIC_REJECTION={sum(bool(c.error) for c in CASES)} '
          'GENUINE_KYIV_T=1 TRUNCATION=PROVISIONAL HARDWARE_ORACLE=0')
    return 0 if passed==len(CASES) else 1
if __name__=='__main__':sys.exit(main())
