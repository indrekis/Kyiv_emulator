#!/usr/bin/env python3
"""D5 one-step single-command host-file tests, fully disposable file trees."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODES = ('20', '24')
KINDS = ('full', 'short', 'empty', 'missing', 'full_noeol', 'short_noeol')
PATTERN = re.compile(r'IO-OBS mode=(\S+) op=(\S+) start_pc=(\S+) next_pc=(\S+) mem0200=(\S+) mem0201=(\S+)')
PAYLOADS = {
    'full': '1 2 3\n',
    'short': '1\n',
    'empty': '',
    'full_noeol': '1 2 3',
    'short_noeol': '1',
}


def one(exe, mode, kind, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d5_', dir=parent) as tmp:
        root = Path(tmp)
        (root / 'a' / 'b').mkdir(parents=True)
        (root / 'mem').mkdir()
        source = root / 'mem' / ('punch_cards_in.txt' if mode == '20' else 'drum_in.txt')
        if kind != 'missing':
            source.write_text(PAYLOADS[kind], encoding='ascii', newline='')
        try:
            proc = subprocess.run([str(exe), mode], cwd=root / 'a' / 'b',
                                  capture_output=True, text=True, encoding='utf-8',
                                  errors='replace', timeout=timeout)
            status = f'EXIT_{proc.returncode}'
            output = proc.stdout + '\n' + proc.stderr
        except subprocess.TimeoutExpired:
            status, output = 'TIMEOUT', ''
        observations = PATTERN.findall(output)
        observed = observations[0] if len(observations) == 1 else None
        if kind in ('full', 'full_noeol'):
            values = ('1', '2')
        elif kind in ('short', 'short_noeol'):
            values = ('1', '0')
        else:
            values = ('0', '0')
        good = (status == 'EXIT_0' and observed is not None and observed[:4] ==
                (mode, mode, '100', '100') and observed[4:] == values)
        classification = ('HOST_CODE_FIX' if kind != 'missing' else 'HOST_CODE_OBS')
        print(f'CODE-FIX-OBS mode={mode} input={kind} process={status} '
              f'C={observed[3] if observed else "N/A"} '
              f'values={"/".join(observed[4:]) if observed else "N/A"} '
              f'class={classification} result={"PASS" if good else "FAIL"}')
        if not good:
            print('  last output lines:', ' | '.join(output.splitlines()[-8:]))
        return good


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True)
    parser.add_argument('--timeout', type=float, default=5)
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT / 'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        parser.error('executable and tempkyiv directory required')
    if not 0.2 <= args.timeout <= 60:
        parser.error('timeout must be in [0.2,60] seconds')
    n, ok = 0, 0
    for mode in MODES:
        for kind in KINDS:
            n += 1
            ok += bool(one(exe, mode, kind, args.timeout, parent))
    print(f'ISA-07 D5 SANDBOX PASS={ok}/{n} EOF20_24=FIXED '
          'EMPTY_FILES=HOST_POLICY BLANK_RECORDS=OPEN '
          'HISTORICAL_ORACLES=0 ONE_STEP_ONLY=1')
    return 0 if ok == n else 1

if __name__ == '__main__':
    sys.exit(main())
