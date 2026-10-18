#!/usr/bin/env python3
"""Independent integer oracle for provisional truncation (never hardware oracle)."""
import argparse
from pathlib import Path
import random
import re
import subprocess
import sys

PAT = re.compile(r'^D10F2-CONVERT status=(EXACT|TRUNCATED|INVALID_BCD) '
                 r'word=([0-7]{14}) remainder=(\d+) STAGED_ONLY=1 CPU_MUTATION=0$')
SOURCE = {
    (6250000000, 0): '12000000000000',
    (6250000000, 1): '32000000000000',
    (5000000000, 0): '10000000000000',
    (5000000000, 1): '30000000000000',
    (2500000000, 0): '04000000000000',
    (0, 0): '00000000000000',
    (0, 1): '20000000000000',
}
DIVISOR = 9765625
SCALE = 1 << 30
SIGN = 1 << 40


def oracle(n, negative):
    q, r = divmod(n * SCALE, DIVISOR)
    word = f'{q | (SIGN if negative else 0):014o}'
    assert SOURCE.get((n, negative), word) == word
    return ('EXACT' if r == 0 else 'TRUNCATED', word, str(r))


def check(exe, packed, negative, expected, timeout, label):
    try:
        p = subprocess.run([str(exe), packed, str(negative)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout)
        match = PAT.fullmatch(p.stdout.strip())
        observed = match.groups() if match else None
        ok = p.returncode == 0 and observed == expected
    except subprocess.TimeoutExpired:
        observed = None
        ok = False
    print(f'D10F2-CASE {label}: {"PASS" if ok else "FAIL"}'
          f' expected={expected[0]} observed={observed[0] if observed else "NONE"}')
    if not ok:
        print('  expected:', expected, 'observed:', observed)
        if 'p' in locals():
            print('  stdout:',repr(p.stdout), 'stderr:',repr(p.stderr), 'rc:',p.returncode)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5)
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    if not exe.is_file(): ap.error('missing executable')
    if not 0.2 <= args.timeout <= 60: ap.error('timeout must be 0.2..60')

    # Distinguishing rounding witnesses, exact values, both signed zeros,
    # smallest/largest representable input, each digit in each BCD position.
    values = [0, 1, 2, 10, 100, 9999999999, 9999999998,
              1000000000, 3000000000, 6250000000, 5000000000,
              2500000000, 9765625, 2*9765625, 1023*9765625,
              1234567890, 9876543210, 1_000_000_001]
    values.extend(10**pos for pos in range(10))
    values.extend(9*10**pos for pos in range(10))
    # Reproducible supplemental fraction cases, no floating point.
    rng = random.Random(0xD10F2)
    values.extend(rng.randrange(0, 10**10) for _ in range(40))
    seen = set()
    cases = []
    for n in values:
        if n in seen: continue
        seen.add(n)
        for negative in (0, 1):
            cases.append((f'{n:010d}', negative, oracle(n,negative),
                          f'{"neg" if negative else "pos"}-{n:010d}'))
    for idx, payload in enumerate(('a000000000', '000000000f', '10000000000',
                                   'ffffffffffff', '0a00000000')):
        cases.append((payload,idx%2,('INVALID_BCD','00000000000000','0'),
                      f'invalid-bcd-{idx}'))

    passed = 0
    for packed,negative,expected,label in cases:
        passed += bool(check(exe,packed,negative,expected,args.timeout,label))
    print(f'ISA-07 D10-F2 STAGED PASS={passed}/{len(cases)} '
          'TRUNCATION=PROVISIONAL SOURCE_STRICT_EXACT=1 '
          'HOST_ROUNDING_ORACLE=1 NO_FLOATING_POINT=1 '
          'CPU_MUTATION=0 HARDWARE_ORACLE=0')
    return 0 if passed==len(cases) else 1

if __name__ == '__main__': sys.exit(main())
