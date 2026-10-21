#!/usr/bin/env python3
"""Independent HOST CLI parser oracle; NOT a historical hardware oracle."""
import argparse
import random
import subprocess
import sys
from pathlib import Path

MARK = '--experimental-drum'
OVERFLOW = '--block-overflow-stop'
ALLOWED = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-')
MAX_SIZE = (1 << 64) - 1

class ExpectedError(Exception):
    pass

def fail(code):
    raise ExpectedError(code)

def number(s):
    if not s or any(c not in '0123456789' for c in s):
        fail('CLI_INVALID_DECIMAL')
    n = int(s)
    if n > MAX_SIZE: fail('CLI_INVALID_DECIMAL')
    if not n: fail('CLI_ZERO_VALUE')
    return n

def expected(args):
    items = list(args)
    block = bool(items and items[-1] == OVERFLOW)
    if block: items.pop()
    drum = None
    if len(items) >= 6 and items[-6] == MARK:
        img, profile, tracks_s, slots_s, pin_s = items[-5:]
        if img in ('', MARK, OVERFLOW): fail('CLI_INVALID_IMAGE_PATH')
        tracks = number(tracks_s)
        slots = number(slots_s)
        pin = number(pin_s)
        if pin > 3: fail('CLI_INVALID_DRUM_LOCK')
        if not profile or len(profile) > 64 or any(c not in ALLOWED for c in profile):
            fail('INVALID_PROFILE')
        if tracks > MAX_SIZE // 3 or slots > MAX_SIZE // (3 * tracks):
            fail('GEOMETRY_OVERFLOW')
        if 3 * tracks * slots > 1000000:
            fail('HOST_CAPACITY_LIMIT')
        drum = (profile, tracks, slots, pin, img)
        items = items[:-6]
    if MARK in items: fail('CLI_INCOMPLETE_EXPERIMENTAL_DRUM')
    if OVERFLOW in items: fail('CLI_MISPLACED_OVERFLOW_FLAG')
    prefix = f'OK|{len(items)+1}|{int(block)}|{int(drum is not None)}'
    return prefix + (('|' + '|'.join(map(str, drum))) if drum else '')

def oracle(args):
    try: return expected(args)
    except ExpectedError as e: return 'ERR|' + str(e)

def cases(seed, n, img):
    fixed = [
        [], ['command', '1', '2', '01'], ['expression', '(1,2)', '0004'],
        ['command', '1', '2', '01', OVERFLOW],
        ['expression', '(1,2)', '0004', MARK, img, 'experiment-137', '24', '137', '1'],
        ['removable_memory', 'lib', '(1,2)', '0004', MARK, 'C:\\my data\\disk.kdr', 'exp_511', '24', '511', '3', OVERFLOW],
        ['expression', '0004', MARK],
        ['expression', '0004', MARK, img, 'p', '1', '1'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '0'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '4'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '1', OVERFLOW],
        ['expression', '0004', MARK, img, 'p', '1', '1', '+1'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '-1'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '2.0'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '999999999999999999999'],
        ['expression', '0004', MARK, img, 'p', '24', '0', '1'],
        ['expression', '0004', MARK, img, 'p', '1', '333333', '1'],
        ['expression', '0004', MARK, img, 'p', '24', '511', '3'],
        ['expression', '0004', MARK, img, 'bad profile', '1', '1', '1'],
        ['expression', '0004', MARK, img, '', '1', '1', '1'],
        ['expression', '0004', MARK, '', 'p', '1', '1', '1'],
        ['expression', '0004', MARK, img, 'p', '1', '1', '1', OVERFLOW, OVERFLOW],
        ['expression', '0004', OVERFLOW, MARK, img, 'p', '1', '1', '1'],
    ]
    rng = random.Random(seed)
    output = list(fixed)
    for k in range(n):
        path = [img, 'D:\\emulators\\kyiv drum.kdr', 'with spaces.kdr'][rng.randrange(3)]
        profile = rng.choice(['p', 'experiment.137', 'bad profile', '', 'x'*65])
        tracks = str(rng.choice([1, 3, 24, 256, 999999, 0]))
        slots = str(rng.choice([1, 2, 137, 511, 2048, 0]))
        pin = rng.choice(['1','2','3','4','0','+1','x'])
        arg = ['expression', '(1,2)', '0004', MARK, path, profile, tracks, slots, pin]
        if rng.randrange(4) == 0: arg.append(OVERFLOW)
        if rng.randrange(12) == 0: arg.insert(1, MARK)
        output.append(arg)
    return output

def selftest():
    assert oracle(['expression', MARK]) == 'ERR|CLI_INCOMPLETE_EXPERIMENTAL_DRUM'
    assert oracle(['expression', '0004', MARK, 'x', 'p', '1', '1', '1']) == 'OK|3|0|1|p|1|1|1|x'
    assert oracle(['expression', '0004', MARK, 'x', 'p', '1', '1', '+1']) == 'ERR|CLI_INVALID_DECIMAL'
    assert oracle(['expression', '0004', MARK, 'x', 'p', '1', '1', '4']) == 'ERR|CLI_INVALID_DRUM_LOCK'
    assert oracle(['expression', '0004', MARK, 'x', 'p', '1', '1', '1', OVERFLOW]) == 'OK|3|1|1|p|1|1|1|x'
    # If a mutant model incorrectly accepts +1 as an integer, fixed vectors kill it.
    print('D14C2H3A1-SELFTEST PASS INDEPENDENT_MODEL=1 INVALID_DECIMAL_MUTANT_REJECTED=1')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--exe')
    p.add_argument('--random-cases', type=int, default=200)
    p.add_argument('--timeout', type=float, default=5)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        selftest()
        if not a.exe: return
    if not a.exe or not (0 <= a.random_cases <= 5000): p.error('exe or count')
    exe = Path(a.exe).resolve()
    nonexistent = str(Path.cwd() / 'tempkyiv' / 'D14C2H3A1_NEVER_CREATE.kdr')
    if Path(nonexistent).exists(): raise AssertionError('PROVISION_COLLISION')
    vectors = cases(0xD14C23A1, a.random_cases, nonexistent)
    for k, argv in enumerate(vectors):
        proc = subprocess.run([str(exe), *argv], capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=a.timeout)
        got = proc.stdout.strip()
        want = oracle(argv)
        if proc.returncode or got != want or proc.stderr.strip():
            raise AssertionError(f'case={k} argv={argv!r} want={want!r} got={got!r} '
                                 f'rc={proc.returncode} stderr={proc.stderr[-700:]!r}')
    if Path(nonexistent).exists(): raise AssertionError('UNEXPECTED_FILE_CREATION')
    print(f'D14C2H3A1-CLI PASS={len(vectors)}/{len(vectors)} '
          'INDEPENDENT_PYTHON=1 LEGACY_POSITIONALS=1 BLOCK_OVERFLOW_SUFFIX=1 '
          'WINDOWS_PATH=1 GEOMETRY_EXPLICIT=1 FILE_CREATION=0 CPU_MUTATION=0 '
          'HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')

if __name__ == '__main__':
    try: main()
    except Exception as e:
        print('D14C2H3A1-CLI FAIL', type(e).__name__, str(e), file=sys.stderr)
        raise SystemExit(1)
