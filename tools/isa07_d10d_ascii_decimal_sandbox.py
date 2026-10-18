#!/usr/bin/env python3
"""ISA-07 D10-D: standalone HOST_POLICY ASCII grammar qualification.

Independent Python Fraction arithmetic, literal documentary vectors,
subprocess isolation/timeouts, record-level rejection and C++ 4096 sweep.
"""
import argparse
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import sys

TOKEN_LINE = re.compile(
    r'^D10D-TOKEN status=(EXACT|NONEXACT|INVALID_TOKEN) '
    r'bcd=([0-9a-f]{10}) negative=([01]) oct41=([0-7]{14}) HOST_POLICY=1$',re.M)
RECORD_LINE = re.compile(
    r'^D10D-RECORD status=(EXACT|EMPTY|NONEXACT|INVALID_TOKEN) '
    r'count=([0-9]+) words=(NONE|[0-7]{14}(?:/[0-7]{14})*) '
    r'ATOMIC=1 HOST_POLICY=1$',re.M)
GRAMMAR = re.compile(r'[+-]?(?:[0-9]{10}|0\.[0-9]{10})\Z', re.ASCII)
SOURCE = (
    ('source-pos0625','+0.6250000000','12000000000000'),
    ('source-neg0625','-0.6250000000','32000000000000'),
    ('source-pos05','+0.5000000000','10000000000000'),
    ('source-neg05','-0.5000000000','30000000000000'),
    ('source-pos025','+0.2500000000','04000000000000'),
    ('source-poszero','+0.0000000000','00000000000000'),
    ('source-negzero','-0.0000000000','20000000000000'),
)
VALID_EXACT = (
    ('compact-pos0625','6250000000'),
    ('compact-neg0625','-6250000000'),
    ('compact-poszero','0000000000'),
    ('compact-negzero','-0000000000'),
    ('unsigned-dot','0.6250000000'),
    ('upper-bound','+0.9990234375'),
    ('min-exact','+0.0009765625'),
    ('exact-three-quarter','-0.7500000000'),
    ('exact-one-eighth','0.1250000000'),
)
VALID_NONEXACT = (
    ('tenth','0.1000000000'),
    ('fifth','-2000000000'),
    ('one-last-digit','+0.0000000001'),
    ('near-one','0.9999999999'),
    ('exact-plus-last-digit','0.6250000001'),
)
INVALID = (
    ('blank',''), ('sign-only','-'), ('short-decimal','0.625'),
    ('long-compact','62500000000'), ('integer-ten','10'),
    ('short-compact','625000000'), ('leading-dot','.6250000000'),
    ('integer-one','1.0000000000'), ('extra-zero','00.6250000000'),
    ('scientific','0.625e0'), ('comma','0,6250000000'),
    ('leading-space',' 6250000000'), ('trailing-space','6250000000 '),
    ('embedded-space','62500 00000'), ('embedded-tab','62500\t00000'),
    ('not-ascii','０.6250000000'), ('abc','0.abc0000000'),
    ('junk-suffix','0.6250000000x'), ('double-sign','--0.6250000000'),
)
RECORDS = (
    ('two-spaced', '6250000000 2500000000','EXACT',
     ('12000000000000','04000000000000')),
    ('tab-and-spaces', '  +0.6250000000\t-0.5000000000  ','EXACT',
     ('12000000000000','30000000000000')),
    ('negative-zero', '0.6250000000\t-0000000000','EXACT',
     ('12000000000000','20000000000000')),
    ('one', '  0.6250000000  ','EXACT', ('12000000000000',)),
    ('empty','', 'EMPTY',()),
    ('only-whitespace',' \t \t  ', 'EMPTY',()),
    ('atomic-bad-tail','6250000000 0.625', 'INVALID_TOKEN',()),
    ('atomic-nonexact-tail','6250000000 1000000000', 'NONEXACT',()),
    ('atomic-bad-first','0.625 6250000000','INVALID_TOKEN',()),
    ('atomic-nonexact-first','0.1000000000 6250000000','NONEXACT',()),
    ('bad-middle','6250000000 garbage 2500000000','INVALID_TOKEN',()),
    ('three-values','0000000000\t+0.2500000000  -0.6250000000', 'EXACT',
     ('00000000000000','04000000000000','32000000000000')),
)


def independent(token):
    if GRAMMAR.fullmatch(token) is None:
        return 'INVALID_TOKEN', '0000000000', '0', '00000000000000'
    negative = token.startswith('-')
    mag=token.lstrip('+-')
    digits = mag[2:] if mag.startswith('0.') else mag
    assert len(digits) == 10
    fraction = Fraction(int(digits), 10**10)
    scaled=fraction * (1 << 40)
    if scaled.denominator != 1:
        return 'NONEXACT',digits,'1' if negative else '0','00000000000000'
    return 'EXACT',digits,'1' if negative else '0',f'{int(scaled) | ((1<<40) if negative else 0):014o}'


def run(exe,args,timeout):
    try:
        proc=subprocess.run([str(exe),*args],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1,'','TIMEOUT'


def test_token(exe,label,token,timeout,source_word=None):
    expected=independent(token)
    if source_word is not None:
        assert expected[0]=='EXACT' and expected[3]==source_word, f'wrong literal GY62 pin: {label}'
    # Unicode must bypass Windows argv best-fit transcoding (U+FF10 -> '0').
    # --nonascii constructs the exact UTF-8 bytes inside the C++ probe.
    cmd_args = ['--nonascii'] if label == 'not-ascii' else [token]
    rc,out,err=run(exe,cmd_args,timeout)
    matches=TOKEN_LINE.findall(out)
    got=matches[0] if len(matches)==1 else None
    ok=(rc==0 and got==expected)
    print(f'D10D-TOKEN-CASE mode={label} status={got[0] if got else "N/A"} '
          f'oct41={got[3] if got else "N/A"} '
          f'class={"SOURCE_WORD_AND_HOST_GRAMMAR" if source_word else "HOST_POLICY"} '
          f'result={"PASS" if ok else "FAIL"}')
    if not ok: print('  expected=',expected,'got=',got,'tail=',repr((out+'\n'+err).splitlines()[-8:]))
    return ok


def test_record(exe,label,record,expected_status,expected_words,timeout):
    rc,out,err=run(exe,['--record',record],timeout)
    matches=RECORD_LINE.findall(out)
    got=matches[0] if len(matches)==1 else None
    want=(expected_status,str(len(expected_words)),'/'.join(expected_words) if expected_words else 'NONE')
    ok=(rc==0 and got==want)
    print(f'D10D-RECORD-CASE mode={label} status={got[0] if got else "N/A"} '
          f'count={got[1] if got else "N/A"} class=HOST_POLICY_ATOMIC '
          f'result={"PASS" if ok else "FAIL"}')
    if not ok:print('  expected=',want,'got=',got,'tail=',repr((out+'\n'+err).splitlines()[-8:]))
    return ok


def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',required=True)
    p.add_argument('--timeout',type=float,default=5.0);args=p.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not .2<=args.timeout<=60:
        p.error('executable and timeout 0.2..60 required')
    cases=[(label,token,word) for label,token,word in SOURCE]
    cases.extend((label,token,None) for label,token in VALID_EXACT+VALID_NONEXACT+INVALID)
    passed=sum(bool(test_token(exe,label,token,args.timeout,word))
               for label,token,word in cases)
    records_passed=sum(bool(test_record(exe,*rec,args.timeout)) for rec in RECORDS)
    rc_edge,out_edge,err_edge=run(exe,['--edges'],args.timeout)
    edge_ok=(rc_edge==0 and out_edge.strip() ==
        'D10D-EDGES PASS=4/4 CR_LF=REJECTED IN_PROCESS=1')
    rc,out,err=run(exe,['--sweep'],args.timeout)
    sweep_ok=(rc==0 and out.strip() ==
        'D10D-SWEEP PASS=4096/4096 MAGNITUDES=1024 SIGNS=2 FORMATS=2 SIGNED_ZERO=1 CPU_MUTATION=0')
    print(f'ISA-07 D10D SANDBOX TOKENS={passed}/{len(cases)} '
          f'RECORDS={records_passed}/{len(RECORDS)} '
          f'EDGES={"4/4" if edge_ok else "FAIL"} '
          f'SWEEP={"4096/4096" if sweep_ok else "FAIL"} '
          'ASCII_GRAMMAR=HOST_POLICY SOURCE_WORDS=7 '
          'ALL_OR_NOTHING=1 NONEXACT=REJECT CPU_MUTATION=0 '
          'IO20_INTEGRATION=NOT_DONE DEVICE_ORACLES=0')
    if not edge_ok: print('  edge failure=',repr(out_edge),repr(err_edge))
    if not sweep_ok: print('  sweep failure=',repr(out),repr(err))
    return 0 if passed==len(cases) and records_passed==len(RECORDS) and edge_ok and sweep_ok else 1

if __name__=='__main__':
    sys.exit(main())
