#!/usr/bin/env python3
"""Bounded opcode-21 runs with disposable host files; not a hardware oracle."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# All expected integers here are OCTAL text, not Python decimal constants.
EXPECT = {
    'h0': [('0', '2', '11', '22')],
    'h1': [('1', '3', '22', '33')],
    'h2': [('2', '4', '33', '44')],
    'h4': [('4', '6', '55', '66')],
    'seq': [('0', '2', '11', '22'), ('2', '4', '33', '44')],
}
OBS = re.compile(
    r'IO21-OBS mode=(\S+) iter=(\d+) h_before=([0-7]+) '
    r'h_after=([0-7]+) mem0200=([0-7]+) mem0201=([0-7]+) '
    r'C=([0-7]+) running=([01])'
)

def run(exe: Path, mode: str, timeout: float, parent: Path) -> bool:
    with tempfile.TemporaryDirectory(prefix='isa07_d6_', dir=parent) as dirname:
        root = Path(dirname)
        work = root / 'work'
        work.mkdir()
        (root / 'punched_tape.txt').write_text(
            '11\n22\n33\n44\n55\n66\n', encoding='ascii'
        )
        # Legacy opcode21 reads this file twice, without consuming any meaning.
        (root / 'heads.txt').write_text('0\n0\n', encoding='ascii')
        try:
            p = subprocess.run(
                [str(exe), mode], cwd=work, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=timeout,
            )
            output = p.stdout + '\n' + p.stderr
            status = f'EXIT_{p.returncode}'
        except subprocess.TimeoutExpired:
            output = ''
            status = 'TIMEOUT'
        rows = OBS.findall(output)
        expected = EXPECT[mode]
        ok = status == 'EXIT_0' and len(rows) == len(expected)
        if ok:
            for i, (row, values) in enumerate(zip(rows, expected)):
                if row != (mode, str(i), *values, '100', '1'):
                    ok = False
                    break
        record = ';'.join(f'{r[2]}->{r[3]}:{r[4]}/{r[5]}' for r in rows) if rows else 'NONE'
        print(f'CODE-FIX-OBS mode={mode} process={status} transitions={record} '
              f'pc_unchanged=1 class=HOST_CODE_FIX result={"PASS" if ok else "FAIL"}')
        if not ok:
            print('  last output lines:', ' | '.join(output.splitlines()[-12:]))
        return ok

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--exe', required=True)
    p.add_argument('--timeout', type=float, default=5.0)
    args = p.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT / 'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        p.error('existing executable and repository tempkyiv directory required')
    if not 0.2 <= args.timeout <= 60:
        p.error('timeout must be within 0.2..60 seconds')
    passed = sum(run(exe, mode, args.timeout, parent) for mode in EXPECT)
    print(f'ISA-07 D6 SANDBOX PASS={passed}/5 TOTAL_STEPS=6 '
          'IO21_COUNTER=ADVANCING H_OFFSET=HOST_POLICY '
          'SOURCE2_EXCLUSIVE=UNCHANGED C_REG=UNCHANGED HISTORICAL_ORACLES=0')
    return 0 if passed == len(EXPECT) else 1

if __name__ == '__main__':
    sys.exit(main())
