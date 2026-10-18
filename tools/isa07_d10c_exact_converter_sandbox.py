#!/usr/bin/env python3
"""Standalone converter qualification; 22 independent cases plus 2048 sweep.

Ground truth for exact numbers: Fraction(decimal_digits, 10**10) * 2**40.
Source-pinned examples from D10-B remain literal, independent of C++.
"""
import argparse
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import sys

# name, BCD magnitude as 10 hexadecimal nibbles, sign, expected status,
# expected 14-octal-digit machine word for source-pinned cases.
SOURCE = (
    ('source-pos0625', '6250000000', '+', '12000000000000'),
    ('source-neg0625', '6250000000', '-', '32000000000000'),
    ('source-pos05',   '5000000000', '+', '10000000000000'),
    ('source-neg05',   '5000000000', '-', '30000000000000'),
    ('source-pos025',  '2500000000', '+', '04000000000000'),
    ('source-poszero', '0000000000', '+', '00000000000000'),
    ('source-negzero', '0000000000', '-', '20000000000000'),
)
EXACT_EXTRA = (
    ('exact-pos075',    '7500000000', '+'),
    ('exact-neg075',    '7500000000', '-'),
    ('exact-pos0125',   '1250000000', '+'),
    ('exact-one1024',   '0009765625', '+'),
    ('exact-max1024',   '9990234375', '+'),
    ('exact-pos0375',   '3750000000', '+'),
)
NONEXACT = (
    ('nonexact-tenth',  '1000000000', '+'),
    ('nonexact-fifth',  '2000000000', '-'),
    ('nonexact-plus1',  '6250000001', '+'),
    ('nonexact-under',  '0000000001', '-'),
    ('nonexact-max10',  '9999999999', '+'),
)
INVALID = (
    ('invalid-leading',  'a250000000', '+'),
    ('invalid-trailing', '625000000a', '-'),
    ('invalid-over40',  '10000000000', '+'),
    ('invalid-allf',    'ffffffffff', '-'),
)
LINE = re.compile(r'^D10C-CONVERT bcd=([0-9a-f]+) sign=([+-]) '
                  r'status=(EXACT|NONEXACT|INVALID_BCD) '
                  r'oct41=([0-7]{14}) host_code_only=1$', re.M)


def independent_oracle(digits, sign):
    assert len(digits) == 10 and all('0' <= c <= '9' for c in digits)
    fractional = Fraction(int(digits), 10**10)
    machine_magnitude = fractional * (1 << 40)
    if machine_magnitude.denominator != 1:
        return 'NONEXACT', '00000000000000'
    value = int(machine_magnitude) | ((1 << 40) if sign == '-' else 0)
    return 'EXACT', f'{value:014o}'


def one(exe, label, packed, sign, expected_status, expected_word, timeout):
    try:
        p = subprocess.run([str(exe), packed, sign], capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'D10C-CASE mode={label} process=TIMEOUT result=FAIL')
        return False
    matches = LINE.findall(p.stdout)
    matched = matches[0] if len(matches) == 1 else None
    ok = (p.returncode == 0 and matched ==
          (packed, sign, expected_status, expected_word))
    print(f'D10C-CASE mode={label} status={matched[2] if matched else "N/A"} '
          f'oct41={matched[3] if matched else "N/A"} '
          f'expected_status={expected_status} expected_oct41={expected_word} '
          f'class={"SOURCE_WORD" if label.startswith("source-") else "EXACT_MATH_OR_REJECT"} '
          f'result={"PASS" if ok else "FAIL"}')
    if not ok:
        print('  subprocess_tail=' + repr((p.stdout+'\n'+p.stderr).splitlines()[-8:]))
    return ok


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5.0)
    args=ap.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not 0.2 <= args.timeout <= 60:
        ap.error('valid executable and 0.2..60 second timeout required')
    cases=[]
    for label,packed,sign,want in SOURCE:
        assert independent_oracle(packed, sign) == ('EXACT',want)
        cases.append((label,packed,sign,'EXACT',want))
    for label,packed,sign in EXACT_EXTRA:
        status,octword = independent_oracle(packed,sign)
        assert status == 'EXACT'
        cases.append((label,packed,sign,status,octword))
    for label,packed,sign in NONEXACT:
        status,octword = independent_oracle(packed,sign)
        assert status == 'NONEXACT'
        cases.append((label,packed,sign,status,octword))
    for label,packed,sign in INVALID:
        cases.append((label,packed,sign,'INVALID_BCD','00000000000000'))
    assert len(cases) == 22
    passed=sum(bool(one(exe,*case,args.timeout)) for case in cases)
    try:
        sweep=subprocess.run([str(exe),'--sweep'], capture_output=True,
            text=True,encoding='utf-8',errors='replace',timeout=args.timeout)
        sweep_ok=(sweep.returncode == 0 and
            sweep.stdout.strip() == 'D10C-SWEEP PASS=2048/2048 '
            'MAGNITUDES=1024 SIGNS=2 ZERO_SIGN_PRESERVED=1 NO_FLOATING_POINT=1')
    except subprocess.TimeoutExpired:
        sweep_ok=False
    print(f'ISA-07 D10C SANDBOX PASS={passed}/{len(cases)} '
          f'SWEEP={"2048/2048" if sweep_ok else "FAIL"} '
          'GY62_DPS64_EXACT_WORDS=7 HOST_GRAMMAR=NOT_CHOSEN '
          'CPU_MUTATION=0 NONEXACT=REJECT INVALID_BCD=REJECT '
          'SIGNED_ZERO=ENCODING_ONLY ROUNDING=OPEN DEVICE_ORACLES=0')
    return 0 if passed == len(cases) and sweep_ok else 1

if __name__ == '__main__':
    sys.exit(main())
