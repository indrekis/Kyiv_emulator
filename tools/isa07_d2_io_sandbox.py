#!/usr/bin/env python3
"""Run ISA-07 D2's one-step executable in an ephemeral, isolated file tree.

Only paths under tempkyiv are used. Observed C++ defects are NOT hardware oracles.
Cases 20/24 use complete inputs that initialize their local flag before reading it.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = ('20', '21-h1', '21-h0', '22', '23', '24', '25-read', '25-write')


def do_case(exe, mode, parent, timeout):
    with tempfile.TemporaryDirectory(prefix='isa07_d2_', dir=parent) as d:
        root = Path(d)
        (root / 'mem').mkdir()
        (root / 'a' / 'b').mkdir(parents=True)
        # C++ sources use ../ and ../../mem relative to the child's cwd.
        (root / 'a' / 'punched_tape.txt').write_text('0123\n0456\n', encoding='ascii')
        (root / 'a' / 'heads.txt').write_text('header\nheader\n', encoding='ascii')
        (root / 'mem' / 'punch_cards_in.txt').write_text('01 02 03\n', encoding='ascii')
        (root / 'mem' / 'drum_in.txt').write_text('1 2 3\n', encoding='ascii')
        # The historical ROM file is not needed by these cases. Kyiv_t's
        # constructor can use a fixture under root/a/ only if required.
        try:
            p = subprocess.run([str(exe), mode], cwd=root / 'a' / 'b',
                               capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=timeout)
            status = f'EXIT_{p.returncode}'
            out = p.stdout + '\n' + p.stderr
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
            out = ''
        entries = {
            name: root / 'a' / name
            for name in ('punc_cards_out.txt', 'magnetic_drum.txt')
        }
        files = {name: path.is_file() for name, path in entries.items()}
        obs = re.findall(r'IO-OBS mode=([^ ]+) op=([^ ]+) start_pc=([^ ]+) next_pc=([^ ]+)', out)
        # Stable implementation observations, not assertions of historical ISA.
        if mode == '22':
            ok = status == 'EXIT_0' and all(files.values()) and bool(obs)
        elif mode == '23':
            ok = status == 'EXIT_0' and files['magnetic_drum.txt'] and not files['punc_cards_out.txt'] and bool(obs)
        elif mode.startswith('25-') or mode.startswith('21-') or mode in ('20', '24'):
            ok = status == 'EXIT_0' and bool(obs)
        else:
            # A new case is not automatically a historical oracle.
            ok = True
        print(f"CODE-OBS mode={mode} process={status} "
              f"perfo_out={int(files['punc_cards_out.txt'])} "
              f"drum_out={int(files['magnetic_drum.txt'])} "
              f"step={'yes' if obs else 'no'} "
              f"classification={'BOUNDED_INPUT_PATH' if mode in ('20','24') else 'REPRODUCIBLE_CODE_PATH'} "
              f"result={'OBSERVED' if ok else 'REPRO_MISMATCH'}")
        if obs:
            _, op, start, nxt = obs[-1]
            print(f'  op={op} start_pc={start} next_pc={nxt} [octal]')
        if not ok:
            print('  captured last lines:', '\n  '.join(out.splitlines()[-8:]))
        return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--timeout', type=float, default=5)
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT / 'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        ap.error('compiled executable or tempkyiv directory missing')
    if not 0.2 <= args.timeout <= 60:
        ap.error('--timeout must be between 0.2 and 60 seconds')
    cases = CASES
    passed = sum(do_case(exe, mode, parent, args.timeout) for mode in cases)
    print(f'ISA-07 D2 SANDBOX OBSERVATIONS={passed}/{len(cases)} '
          'HISTORICAL_ORACLES=0 UB_PATHS_NOT_ASSERTED=1')
    return 0 if passed == len(cases) else 1


if __name__ == '__main__':
    sys.exit(main())
