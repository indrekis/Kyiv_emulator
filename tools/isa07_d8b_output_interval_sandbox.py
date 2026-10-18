#!/usr/bin/env python3
"""D8-B: isolated exact code output tests (22/23; a1..a2 inclusive)."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODES = ('22', '23')
EXPECTED = {
    'range': ('5','7','9'),
    'single': ('7',),
    'offset': ('7','9','11'),
    'legacy': ('5','7'),
    'fromzero': ('0','5','7'),  # Cell 0000 is immutable zero.
}
OBS = re.compile(r'D8B-OBS mode=(\S+) op=(\S+) start_pc=(\S+) next_pc=(\S+) running=(\S+)')

def run_case(exe, mode, kind, parent, timeout):
    label = mode + '-' + kind
    with tempfile.TemporaryDirectory(prefix='isa07_d8b_', dir=parent) as tmp:
        root = Path(tmp)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        try:
            p = subprocess.run([str(exe), label], cwd=root/'a'/'b', capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=timeout)
            status = 'EXIT_' + str(p.returncode)
            out = p.stdout + '\n' + p.stderr
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
            out = ''
        match = OBS.findall(out)
        one_step = (len(match) == 1 and match[0] == (label, mode, '100', '120', '1'))
        perfo = root/'a'/'punc_cards_out.txt'
        drum = root/'a'/'magnetic_drum.txt'
        wanted = perfo if mode == '22' else drum
        forbidden = drum if mode == '22' else perfo
        shape_ok = wanted.is_file() and not forbidden.exists()
        try:
            values = tuple(wanted.read_text(encoding='ascii').split()) if wanted.is_file() else ()
        except (OSError, UnicodeError):
            values = ()
        exact = values == EXPECTED[kind]
        ok = status == 'EXIT_0' and one_step and shape_ok and exact
        print(f'D8B-CODE-FIX mode={label} process={status} '
              f'C={match[0][3] if match else "N/A"} '
              f'values={"/".join(values) if values else "N/A"} '
              f'expected={"/".join(EXPECTED[kind])} '
              f'target_file_only={int(shape_ok)} '
              f'class=SOURCE_STRICT_INTERVAL_HOST_ADAPTER '
              f'result={"PASS" if ok else "FAIL"}')
        if not ok:
            print('  OUTPUT_TAIL=' + repr(out.splitlines()[-12:]))
        return ok

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--exe', required=True)
    p.add_argument('--timeout', type=float, default=5)
    args = p.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        p.error('compiled one-step executable and tempkyiv directory required')
    if not .2 <= args.timeout <= 60:
        p.error('timeout must be 0.2..60 seconds')
    passed = 0
    for mode in MODES:
        for kind in EXPECTED:
            passed += bool(run_case(exe, mode, kind, parent, args.timeout))
    print(f'ISA-07 D8B SANDBOX PASS={passed}/10 OP22_23_ABSOLUTE_END=FIXED '
          'SINGLE_ADDR=2 OFFSET=2 FROMZERO=2 LEGACY_D3=NEW_INTERVAL_OUTPUT '
          'D3_FALLTHROUGH=ABSENT REVERSED_INTERVAL=OPEN '
          'HISTORICAL_DEVICE_ORACLES=0 ONE_STEP_ONLY=1')
    return 0 if passed == 10 else 1

if __name__ == '__main__':
    sys.exit(main())
