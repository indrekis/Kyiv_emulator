#!/usr/bin/env python3
"""Independent Python oracle for D14-B1 standalone C++ raw-word logical media.

This tests a HOST_PROFILE, never an authenticated Kyiv drum geometry or image.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAX41 = (1 << 41) - 1
SIGN = 1 << 40


def protocol(profile, dims, commands, exe, timeout):
    with tempfile.TemporaryDirectory(prefix='isa07_d14b1_', dir=ROOT / 'tempkyiv') as folder:
        # On Windows/MinGW, wchar-to-char argv conversion may silently strip
        # unsupported Unicode characters. Send a probe-only UTF-8 hex token
        # to test logical_media's byte validator, not the host ANSI code page.
        profile_args = ([profile] if profile.isascii() else
                        ['--profile-hex', profile.encode('utf-8').hex()])
        proc = subprocess.run([str(exe), *profile_args, *(str(d) for d in dims)],
            input='\n'.join(commands) + ('\n' if commands else ''), cwd=folder,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        files = [p for p in Path(folder).rglob('*') if p.is_file()]
        return proc.returncode, proc.stdout.splitlines(), proc.stderr, files


def independent_oracle(operations, dims):
    state = {}
    snap = None
    observed = []
    for op, point, value in operations:
        if op == 'COUNT':
            result = f'COUNT {len(state)}'
        elif op == 'CAP':
            result = f'CAP {dims[0] * dims[1] * dims[2]}'
        elif op == 'SNAP':
            snap = dict(state)
            result = f'SNAP {len(snap)}'
        elif op == 'COUNTSNAP':
            result = f'COUNTSNAP {len(snap)}' if snap is not None else 'ERROR NO_SNAPSHOT'
        else:
            destination = snap if op.endswith('SNAP') else state
            if destination is None:
                result = 'ERROR NO_SNAPSHOT'
            elif point[0] >= dims[0]:
                result = 'ERROR INVALID_DRUM'
            elif point[1] >= dims[1]:
                result = 'ERROR INVALID_TRACK'
            elif point[2] >= dims[2]:
                result = 'ERROR INVALID_SLOT'
            elif op.startswith('PUT'):
                if value > MAX41:
                    result = 'ERROR INVALID_WORD'
                else:
                    destination[point] = value
                    result = 'PUT OK'
            elif op.startswith('ERASE'):
                destination.pop(point, None)
                result = 'ERASE OK'
            elif op.startswith('GET'):
                result = ('CELL WRITTEN ' + str(destination[point]) if point in destination
                          else 'CELL UNWRITTEN')
            else:
                raise AssertionError(op)
        observed.append(result)
    return observed


def encode(operations):
    result = []
    for op, p, value in operations:
        if p is None:
            result.append(op)
        elif value is None:
            result.append(f'{op} {p[0]} {p[1]} {p[2]}')
        else:
            result.append(f'{op} {p[0]} {p[1]} {p[2]} {value}')
    return result


def scenario(name, profile, dims, operations, exe, timeout):
    actual = protocol(profile, dims, encode(operations), exe, timeout)
    expected = [f'D14B1-INIT OK {dims[0] * dims[1] * dims[2]}']
    expected.extend(f'D14B1-RESULT {i} {x}' for i, x in
                    enumerate(independent_oracle(operations, dims)))
    ok = actual[0] == 0 and actual[1] == expected and not actual[3]
    print(f'D14B1-CASE {name}: {"PASS" if ok else "FAIL"} '
          f'OPERATIONS={len(operations)} HOST_PROFILE={profile}')
    if not ok:
        print('  EXPECTED_TAIL=', expected[-8:])
        print('  ACTUAL_TAIL=', actual[1][-8:])
        print('  STDERR=', repr(actual[2][-600:]))
        print('  FILES=', [str(x) for x in actual[3]])
    return ok, len(operations)


def case_invalid(name, profile, dims, error, exe, timeout):
    try:
        code, lines, stderr, files = protocol(profile, dims, [], exe, timeout)
        ok = code == 0 and lines == [f'D14B1-INIT ERROR {error}'] and not files
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        ok = False
        stderr = repr(exc)
        lines = []
    print(f'D14B1-INVALID {name}: {"PASS" if ok else "FAIL"} '
          f'EXPECTED={error}')
    if not ok: print('  OUTPUT=', lines, 'STDERR=', repr(stderr[-400:]))
    return ok


def items(*ops):
    return list(ops)


def run(exe, timeout, random_steps):
    out = []
    def add(op, point=None, value=None): out.append((op, point, value))

    # Hand-computed regression examples prevent the randomized oracle from
    # masking an off-by-one or sign-bit mistake.
    add('COUNT'); add('CAP')
    add('GET', (0, 0, 0))
    add('PUT', (0, 0, 0), 0)              # written +0 != unwritten
    add('GET', (0, 0, 0))
    add('PUT', (0, 0, 1), SIGN)           # written -0
    add('GET', (0, 0, 1))
    add('PUT', (1, 2, 3), MAX41)          # all 41 bits
    add('GET', (1, 2, 3))
    add('GET', (0, 2, 3))                 # different drum
    add('GET', (1, 1, 3))                 # different track
    add('PUT', (1, 2, 3), 17)
    add('COUNT'); add('GET', (1, 2, 3))
    add('PUT', (1, 2, 2), MAX41 + 1)      # invalid high bit, no commit
    add('GET', (1, 2, 2)); add('COUNT')
    add('SNAP'); add('COUNTSNAP')
    add('PUT', (1, 2, 3), SIGN + 1)
    add('GETSNAP', (1, 2, 3))
    add('PUTSNAP', (0, 0, 0), 11)
    add('GET', (0, 0, 0)); add('GETSNAP', (0, 0, 0))
    add('ERASE', (1, 2, 3)); add('ERASE', (1, 2, 3))
    add('GETSNAP', (1, 2, 3)); add('GET', (1, 2, 3)); add('COUNT')
    add('GET', (2, 0, 0)); add('GET', (0, 3, 0)); add('GET', (0, 0, 4))
    add('PUT', (0, 0, 4), 11); add('COUNT')
    add('ERASESNAP', (2, 0, 0)); add('COUNTSNAP')
    a, n = scenario('mini-fixed', 'test-mini-2x3x4', (2, 3, 4), out, exe, timeout)
    # Explicitly pin several expected lines independently of the dynamic oracle.
    fixed = independent_oracle(out, (2, 3, 4))
    assert fixed[3] == 'PUT OK' and fixed[4] == 'CELL WRITTEN 0'
    assert fixed[6] == f'CELL WRITTEN {SIGN}'
    assert fixed[8] == f'CELL WRITTEN {MAX41}'
    assert fixed[14] == 'ERROR INVALID_WORD'
    passed = int(a); total = 1; operations = n

    rnd = random.Random(0xD14B1)
    for profile, dims in (
        ('test-one-1x1x1', (1, 1, 1)),
        ('test-asymmetric-3x4x5', (3, 4, 5)),
        ('experiment-137', (3, 24, 137)),
        ('experiment-511', (3, 24, 511)),
    ):
        opers = [('COUNT', None, None), ('CAP', None, None), ('COUNTSNAP', None, None)]
        # Ensure the first and final index are exercised, including both
        # sides of a track boundary. AUTO advancement is NOT tested in B1.
        points = [(0, 0, 0), (dims[0]-1, dims[1]-1, dims[2]-1),
                  (0, dims[1]-1, dims[2]-1), (0, dims[1]-1, 0)]
        for idx, point in enumerate(points):
            opers.extend([('PUT', point, [0, SIGN, MAX41, 37][idx]),
                          ('GET', point, None)])
        opers += [('SNAP', None, None)]
        for _ in range(random_steps):
            p = (rnd.randrange(dims[0]+2), rnd.randrange(dims[1]+2),
                 rnd.randrange(dims[2]+2))
            cmd = rnd.choice(['PUT','GET','ERASE','PUT','GETSNAP','PUTSNAP','ERASESNAP'])
            val = rnd.choice([0, 1, SIGN, SIGN+1, MAX41, MAX41+1, (1<<63), rnd.randrange(MAX41+1)]) if cmd.startswith('PUT') else None
            opers.append((cmd, p, val))
            if rnd.randrange(11) == 0: opers.append(('COUNT', None, None))
            if rnd.randrange(20) == 0: opers.append(('COUNTSNAP', None, None))
        for point in points:
            opers.append(('GET', point, None))
            opers.append(('GETSNAP', point, None))
        opers.extend([('COUNT', None, None), ('COUNTSNAP', None, None)])
        a, n = scenario(profile, profile, dims, opers, exe, timeout)
        passed += bool(a); total += 1; operations += n

    # Dimension/profile validation before any memory allocation.
    invalid = [
        ('zero-drums','test-zero',(0,3,4),'INVALID_GEOMETRY'),
        ('zero-tracks','test-zero',(2,0,4),'INVALID_GEOMETRY'),
        ('zero-slots','test-zero',(2,3,0),'INVALID_GEOMETRY'),
        ('empty-profile','',(2,3,4),'INVALID_PROFILE'),
        ('space-profile','invalid profile',(2,3,4),'INVALID_PROFILE'),
        ('unicode-profile','invalid-ą',(2,3,4),'INVALID_PROFILE'),
        ('long-profile','p'*65,(2,3,4),'INVALID_PROFILE'),
        ('host-limit','test-large',(3,24,20000),'HOST_CAPACITY_LIMIT'),
        ('multiply-overflow','test-overflow',(2**63,4,4),'GEOMETRY_OVERFLOW'),
    ]
    for name,profile,dims,error in invalid:
        passed += bool(case_invalid(name,profile,dims,error,exe,timeout));total+=1
    print(f'ISA-07 D14-B1 MEDIA {"PASS" if passed==total else "FAIL"}={passed}/{total} '
          f'OPERATIONS={operations} HOST_PROFILE=EXPLICIT RAW41=1 SIGNED_ZERO=1 '
          'UNWRITTEN_DISTINCT=1 ZERO_BASED_API=1 CPU_MUTATION=0 '
          'SERIALIZATION=DEFERRED HARDWARE_ORACLE=0')
    return 0 if passed==total else 1


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5)
    ap.add_argument('--random-steps', type=int, default=200)
    args=ap.parse_args()
    if not 1 <= args.timeout <= 60 or not 1 <= args.random_steps <= 1000:
        ap.error('unsupported limit')
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():
        ap.error('built C++ standalone probe and tempkyiv/ required')
    return run(exe,args.timeout,args.random_steps)

if __name__=='__main__': sys.exit(main())
