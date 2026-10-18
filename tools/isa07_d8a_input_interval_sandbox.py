#!/usr/bin/env python3
"""D8-A single-step IO20/21/24 inclusive a1..a2 tests on temp files only.

Only nondecreasing address intervals are qualified. No model of historical
physical devices, control transfer, malformed input, or register-M effects.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    '20-range': ((1, 2, 3, 0), 0),
    '20-single': ((0, 7, 0, 0), 0),
    '20-offset': ((0, 1, 2, 3), 0),
    '20-short': ((1, 2, 0, 0), 0),
    '21-range': ((1, 2, 3, 0), 3),
    '21-single': ((0, 7, 0, 0), 1),
    '21-offset': ((0, 1, 2, 3), 3),
    '21-h1': ((18, 27, 36, 0), 4),
    '24-range': ((1, 2, 3, 0), 0),
    '24-single': ((0, 7, 0, 0), 0),
    '24-offset': ((0, 1, 2, 3), 0),
    '24-short': ((1, 2, 0, 0), 0),
}
LINE = re.compile(
    r'D8A-OBS mode=(\S+) op=(\S+) start_pc=(\S+) next_pc=(\S+) '
    r'mem0=(\d+) mem1=(\d+) mem2=(\d+) mem3=(\d+) h=(\d+) running=(\d+)'
)

def one(exe, mode, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d8a_', dir=parent) as folder:
        root = Path(folder)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        kind, shape = mode.split('-')
        if kind == '21':
            data = ('7\n8\n' if shape == 'single' else
                    '11\n22\n33\n44\n55\n' if shape == 'h1' else
                    '1\n2\n3\n4\n')
            (root/'a'/'punched_tape.txt').write_text(data,encoding='ascii')
            (root/'a'/'heads.txt').write_text('0\n0\n',encoding='ascii')
        else:
            data = ('7 8\n' if shape == 'single' else
                    '1 2\n' if shape == 'short' else '1 2 3 4\n')
            filename = 'punch_cards_in.txt' if kind == '20' else 'drum_in.txt'
            (root/'mem'/filename).write_text(data,encoding='ascii')
        try:
            result = subprocess.run([str(exe), mode],cwd=root/'a'/'b',
                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
            state = f'EXIT_{result.returncode}'
            output = result.stdout+'\n'+result.stderr
        except subprocess.TimeoutExpired:
            state = 'TIMEOUT'; output = ''
        matches = LINE.findall(output)
        m = matches[0] if len(matches) == 1 else None
        words = tuple(map(int,m[4:8])) if m else None
        h = int(m[8]) if m else None
        expected_words,expected_h = CASES[mode]
        ok = (state == 'EXIT_0' and m is not None and m[0] == mode and
              m[1] == kind and m[2] == '100' and m[3] == '100' and
              words == expected_words and h == expected_h and m[9] == '1')
        print(f'D8A-CODE-FIX mode={mode} process={state} memory={words} '
              f'h={h} C={m[3] if m else "N/A"} '
              f'class=SOURCE_STRICT_INTERVAL_HOST_ADAPTER '
              f'result={"PASS" if ok else "FAIL"}')
        if not ok:
            print(f'  expected memory={expected_words}, h={expected_h}, C=100')
            print('  last output lines:', ' | '.join(output.splitlines()[-8:]))
        return ok

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',required=True)
    parser.add_argument('--timeout',type=float,default=5)
    args=parser.parse_args()
    exe=Path(args.exe).resolve()
    parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        parser.error('existing executable and tempkyiv directory required')
    if not 0.2<=args.timeout<=60:
        parser.error('timeout must be 0.2..60 seconds')
    passed=sum(bool(one(exe,mode,args.timeout,parent)) for mode in CASES)
    print(f'ISA-07 D8A SANDBOX PASS={passed}/{len(CASES)} '
          'IO20_21_24_INCLUSIVE=FIXED SINGLE_ADDR=3 OFFSET=3 SHORT_INPUT=2 '
          'H1=CHECKED REVERSED_INTERVAL=OPEN C_REG=UNCHANGED '
          'HISTORICAL_DEVICE_ORACLES=0 ONE_STEP_ONLY=1')
    return 0 if passed == len(CASES) else 1

if __name__=='__main__':
    sys.exit(main())
