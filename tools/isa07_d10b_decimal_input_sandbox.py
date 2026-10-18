#!/usr/bin/env python3
"""D10-B isolated current-HOST observations, NOT historical-number oracles."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SIGN_BIT = 1 << 40
CASES = {
    # ASCII host tokens, not historical punched-card encoding.
    '20-text10': ('10', 8, 0),
    '20-bcd625': ('6250000000', int('6250000000', 8), 0),
    '20-dot625': ('0.625', 0, 0),  # current stol accepts the octal prefix 0
    '20-negzero': ('-0', 0, 0),
    '20-neg10': ('-10', SIGN_BIT | 8, 0),
    '20-text7': ('7', 7, 0),
    '21-raw11': ('11', int('11', 8), 1),
}
OBS = re.compile(r'D10B-HOST-OBS mode=(\S+) raw=(\d+) oct41=(\d+) '
                 r'pc=(\S+) k_prefetch=(\d+) h=(\d+) running=(\d+) one_step=(\d+)')


def run_case(exe: Path, mode: str, timeout: float, parent: Path) -> bool:
    token, expected_raw, expected_h = CASES[mode]
    with tempfile.TemporaryDirectory(prefix='isa07_d10b_', dir=parent) as temp:
        root = Path(temp)
        (root / 'a' / 'b').mkdir(parents=True)
        (root / 'mem').mkdir()
        if mode.startswith('20-'):
            (root / 'mem' / 'punch_cards_in.txt').write_text(token + '\n', encoding='ascii')
        else:
            (root / 'a' / 'punched_tape.txt').write_text(token + '\n', encoding='ascii')
            (root / 'a' / 'heads.txt').write_text('0\n0\n', encoding='ascii')
        try:
            p = subprocess.run([str(exe), mode], cwd=root / 'a' / 'b',
                               capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=timeout)
            output = p.stdout + '\n' + p.stderr
            status = f'EXIT_{p.returncode}'
        except subprocess.TimeoutExpired:
            output, status = '', 'TIMEOUT'
        found = OBS.findall(output)
        value = found[0] if len(found) == 1 else None
        ok = (status == 'EXIT_0' and value is not None and value[0] == mode and
              int(value[1]) == expected_raw and int(value[2], 8) == expected_raw and
              value[2] == f'{expected_raw:014o}' and value[3] == '101' and
              value[4] == '1' and int(value[5]) == expected_h and
              value[6] == '1' and value[7] == '1')
        print(f'D10B-HOST-OBS mode={mode} token={token} '
              f'raw={value[1] if value else "NONE"} expected={expected_raw} '
              f'pc={value[3] if value else "NONE"} '
              f'class=HOST_OBS_NOT_HISTORICAL result={"PASS" if ok else "FAIL"}')
        if not ok:
            print('  tail=' + repr(output.splitlines()[-12:]))
        return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True)
    parser.add_argument('--timeout', type=float, default=5)
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT / 'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        parser.error('D10B executable or tempkyiv absent')
    if not 0.2 <= args.timeout <= 60:
        parser.error('timeout out of range')
    passed = sum(bool(run_case(exe, mode, args.timeout, parent)) for mode in CASES)
    print(f'ISA-07 D10B HOST OBS PASS={passed}/{len(CASES)} '
          'CPU_MUTATION=0 SOURCE_MACHINE_WORDS=SEPARATE_VECTOR_GATE '
          'NUMERIC_CONVERSION_MISMATCH=DOCUMENTED HOST_ASCII_ONLY=1 '
          'NOT_A_HISTORICAL_DEVICE_ORACLE=1')
    return 0 if passed == len(CASES) else 1


if __name__ == '__main__':
    sys.exit(main())
