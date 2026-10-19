#!/usr/bin/env python3
"""D13-A: 20 isolated, genuine-CPU observations of CURRENT IO23 host output.

No physical drum encoding or physical failure semantics are inferred.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAX40 = (1 << 40) - 1

@dataclass(frozen=True)
class Case:
    mode: str
    expected: bytes | None
    initial: bytes | str | None = None
    target: int = 0o120
    steps: int = 2
    note: str = 'HOST_POLICY'

CASES = (
    Case('range', b'5 7 9 '),
    Case('single', b'7 '),
    Case('offset', b'7 9 11 '),
    Case('legacy', b'5 7 '),
    Case('fromzero', b'0 5 7 '),
    Case('overwrite', b'5 7 9 ', b'STALE DATA\n'),
    Case('open-error', None, 'DIRECTORY', note='CODE_OBS_ERROR_CONTINUATION'),
    Case('negative', b'-5 7 9 '),
    Case('negative-zero', b'0 7 9 ', note='CODE_OBS_SIGN_LOSS'),
    Case('max-positive', str(MAX40).encode() + b' '),
    Case('max-negative', b'-' + str(MAX40).encode() + b' '),
    Case('sign-only', b'0 ', note='CODE_OBS_SIGN_LOSS'),
    Case('reversed', b'', note='CODE_OBS_EMPTY_REVERSED'),
    Case('beyond-physical', b'13 ', note='CODE_OBS_OUTSIDE_PHYSICAL_RAM'),
    Case('rom-source', b'17 ', note='CODE_OBS_ROM_READ'),
    Case('drum-params', b'5 7 9 ', note='CODE_OBS_IGNORES_DRUM_PARAMETERS'),
    Case('modified-addresses', b'5 7 9 '),
    Case('alternate-branch', b'5 7 9 ', target=0o130),
    Case('io25-setup', b'5 7 9 ', steps=3, note='IO25_TO_IO23_HOST_ADAPTER'),
    Case('highbits-masked', b'5 ', note='CODE_OBS_HOST_OVERWIDE_MASK'),
)

def parse(output: str):
    # IO23's 'Unable to open file' has no newline: the probe header follows it.
    lines = [line[line.index('D13A-OBS '):] for line in output.splitlines()
             if 'D13A-OBS ' in line]
    if len(lines) != 1:
        raise ValueError('expected one D13A-OBS line')
    result = {}
    for token in lines[0].split()[1:]:
        key, separator, value = token.partition('=')
        if not separator or key in result:
            raise ValueError('malformed or repeated field ' + token)
        result[key] = value
    return result

def one(exe: Path, case: Case, timeout: float, parent: Path):
    with tempfile.TemporaryDirectory(prefix='isa07_d13a_', dir=parent) as folder:
        root = Path(folder)
        (root/'a'/'b').mkdir(parents=True)
        out = root/'a'/'magnetic_drum.txt'
        if case.initial == 'DIRECTORY':
            out.mkdir()
        elif isinstance(case.initial, bytes):
            out.write_bytes(case.initial)
        try:
            proc = subprocess.run([str(exe), case.mode], cwd=root/'a'/'b',
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            fields = parse(proc.stdout)
            target = oct(case.target)[2:]
            second = oct(case.target + 1)[2:]
            expected = {'mode': case.mode, 'pc1': target, 'pc2': second,
                'k1': '1', 'k2': '1', 'setup': '1', 'memory': '1',
                'stable': '1', 'xor': '6', 'running': '1',
                'steps': str(case.steps),
                'HOST_OBSERVATION': '1', 'HARDWARE_ORACLE': '0'}
            expected_files = {'a/magnetic_drum.txt'}
            actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            if case.expected is None:
                file_ok = out.is_dir()
                error_ok = proc.stdout.count('Unable to open file') == 1
                expected_files = set()
            else:
                file_ok = out.is_file() and out.read_bytes() == case.expected
                error_ok = 'Unable to open file' not in proc.stdout
            ok = (proc.returncode == 0 and fields == expected and
                  file_ok and error_ok and actual_files == expected_files)
            if not ok:
                print('  DIAG mode=', case.mode, 'exit=', proc.returncode)
                print('  observed=', fields, 'expected=', expected)
                print('  file=', repr(out.read_bytes()) if out.is_file() else 'NOT_FILE')
                print('  output_tail=', repr(proc.stdout.splitlines()[-8:]))
                print('  stderr_tail=', repr(proc.stderr.splitlines()[-8:]))
                print('  files=', sorted(actual_files))
        except (ValueError, OSError, subprocess.TimeoutExpired) as err:
            ok = False
            print('  DIAG mode=', case.mode, 'error=', repr(err))
        print(f'D13A-CASE {case.mode}: {"PASS" if ok else "FAIL"} '
              f'PC_TO_A3=1 FILE_POLICY={int(ok)} {case.note}=1 HOST_OBSERVATION=1')
        return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5)
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():
        ap.error('real CPU executable and repo tempkyiv/ are required')
    if not .2 <= args.timeout <= 60:
        ap.error('timeout must be 0.2..60s')
    passed = sum(one(exe, case, args.timeout, ROOT/'tempkyiv') for case in CASES)
    print(f'ISA-07 D13-A IO23 HOST OBS PASS={passed}/{len(CASES)} '
          'REAL_CPU=1 WRITE_READ_SEPARATE_HOST_FILES=1 IO25_TO_IO23=1 '
          'CPU_MUTATION=0 HOST_FAILURES=OBS_ONLY HARDWARE_ORACLE=0')
    return 0 if passed == len(CASES) else 1

if __name__ == '__main__':
    sys.exit(main())
