#!/usr/bin/env python3
"""ISA-07 D3: one-step tests proving the *absence* of IO22->IO23 fallthrough.

Use the unchanged ISA-07 D2 C++ one-step probe. Both output paths are relative
inside a disposable sandbox; each case has independent files and timeout.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODES = ('22', '23')


def run_case(exe, mode, parent, timeout):
    with tempfile.TemporaryDirectory(prefix='isa07_d3_', dir=parent) as tmp:
        root = Path(tmp)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        cwd = root/'a'/'b'
        try:
            p = subprocess.run([str(exe), mode], cwd=cwd, capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f'CODE-FIX-FAIL mode={mode} process=TIMEOUT')
            return False
        out = p.stdout + '\n' + p.stderr
        matches = re.findall(r'IO-OBS mode=(\S+) op=(\S+) start_pc=(\S+) next_pc=(\S+)', out)
        perfo = root/'a'/'punc_cards_out.txt'
        drum = root/'a'/'magnetic_drum.txt'
        expected_perfo, expected_drum = (mode == '22'), (mode == '23')
        shape_ok = perfo.exists() == expected_perfo and drum.exists() == expected_drum
        output = perfo if expected_perfo else drum
        content_ok = False
        if output.is_file():
            try:
                # D2 probe initializes memory 1,2,3 with octal 5,7,11,
                # hence signed decimal output (5,7,9).
                content_ok = output.read_text(encoding='ascii').split() == ['5','7','9']
            except (OSError, UnicodeError):
                content_ok = False
        one_step = (len(matches) == 1 and matches[0] ==
                    (mode, mode, '100', '120'))
        # A successful one-step probe returns normally; no STOP is expected.
        status_ok = p.returncode == 0 and 'running=1' in out
        ok = shape_ok and content_ok and one_step and status_ok
        print(f"{'CODE-FIX-PASS' if ok else 'CODE-FIX-FAIL'} mode={mode} "
              f'process=EXIT_{p.returncode} perfo_out={int(perfo.is_file())} '
              f'drum_out={int(drum.is_file())} C=0120 '
              f'target_outputs_exact={int(content_ok)} target_file_only={int(shape_ok)} '
              f'one_step={int(one_step)}')
        if not ok:
            print('  OUTPUT_TAIL=' + repr(out.splitlines()[-12:]))
        return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5)
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        ap.error('compiled existing D2 one-step executable or tempkyiv missing')
    if not 0.2 <= args.timeout <= 60:
        ap.error('Timeout must be between 0.2 and 60 seconds')
    passed = sum(run_case(exe, mode, parent, args.timeout) for mode in MODES)
    print(f'ISA-07 D3 IO22 FIX={passed}/{len(MODES)} '
          'HISTORICAL_DEVICE_ORACLES=0 SOURCE_BASELINE_PINNED=1')
    return 0 if passed == len(MODES) else 1


if __name__ == '__main__':
    sys.exit(main())
