#!/usr/bin/env python3
"""D7 read-only qualification: observe documented discrepancies, do NOT repair CPU.

Running only one opcode per disposable directory; no repository peripheral files.
Observed emulation values are regression anchors, NOT historical device oracles.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    '20-range', '20-decimal', '21-range', '22-range',
    '23-range', '24-range', '25-next',
)
LINE = re.compile(
    r'D7-OBS mode=(\S+) op=(\S+) start_pc=(\S+) next_pc=(\S+) '
    r'mem0=(\d+) mem1=(\d+) mem2=(\d+) h=(\d+) running=(\d+)'
)
# All PC/opcodes are octal, memories decimal, respectively.
# Current code observations MUST differ from their explicit GY62 counterparts.
BASE_OBS = {
    '20-range':   dict(op='20', pc='100', memory=(1,2,0), doc='a1..a2 inclusive'),
    '20-decimal': dict(op='20', pc='100', memory=(8,0,0), doc='decimal input 10'),
    '21-range':   dict(op='21', pc='100', memory=(1,2,0), doc='a1..a2 inclusive'),
    '22-range':   dict(op='22', pc='120', count=131, doc='a1..a2 inclusive: 3 words'),
    '23-range':   dict(op='23', pc='120', count=131, doc='a1..a2 inclusive: 3 words'),
    '24-range':   dict(op='24', pc='100', memory=(1,2,0), doc='a1..a2 inclusive; PC=a3=120'),
    '25-next':    dict(op='25', pc='100', doc='following command PC=101'),
}


def one(exe, mode, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d7_', dir=parent) as d:
        root = Path(d)
        (root / 'a' / 'b').mkdir(parents=True)
        (root / 'mem').mkdir()
        if mode == '20-range':
            (root / 'mem' / 'punch_cards_in.txt').write_text('1 2 3\n', encoding='ascii')
        elif mode == '20-decimal':
            (root / 'mem' / 'punch_cards_in.txt').write_text('10 20\n', encoding='ascii')
        elif mode == '21-range':
            (root / 'a' / 'punched_tape.txt').write_text('1\n2\n3\n', encoding='ascii')
            (root / 'a' / 'heads.txt').write_text('0\n0\n', encoding='ascii')
        elif mode == '24-range':
            (root / 'mem' / 'drum_in.txt').write_text('1 2 3\n', encoding='ascii')
        try:
            result = subprocess.run([str(exe), mode], cwd=root/'a'/'b',
                                    text=True, encoding='utf-8', errors='replace',
                                    capture_output=True, timeout=timeout)
            proc = f'EXIT_{result.returncode}'
            out = result.stdout + '\n' + result.stderr
        except subprocess.TimeoutExpired:
            proc = 'TIMEOUT'
            out = ''
        matches = LINE.findall(out)
        match = matches[-1] if len(matches) == 1 else None
        base = BASE_OBS[mode]
        checks = [proc == 'EXIT_0', match is not None]
        fields = None
        if match:
            _, op, start, pc, v0, v1, v2, h, running = match
            fields = (int(v0), int(v1), int(v2))
            checks.extend((match[0] == mode, op == base['op'], start == '100',
                           pc == base['pc'], running == '1'))
            if 'memory' in base:
                checks.append(fields == base['memory'])
        output_count = None
        if 'count' in base:
            out_name = 'punc_cards_out.txt' if mode == '22-range' else 'magnetic_drum.txt'
            path = root / 'a' / out_name
            forbidden = root / 'a' / ('magnetic_drum.txt' if mode == '22-range' else 'punc_cards_out.txt')
            if path.is_file():
                output_count = len(path.read_text(encoding='utf-8', errors='replace').split())
            checks.extend((output_count == base['count'], not forbidden.exists()))
        # This gate checks the CURRENT emulator's documented deviation. If the
        # CPU is fixed later, D7's pre-fix observations must be historical.
        ok = all(checks)
        print(f'D7-CODE-OBS mode={mode} process={proc} pc={match[3] if match else "N/A"} '
              f'memory={fields if fields is not None else "N/A"} '
              f'output_words={output_count if output_count is not None else "N/A"} '
              f'class=DOC_MISMATCH result={"QUALIFIED" if ok else "FAIL"}')
        if not ok:
            print('  historical documented expectation:', base['doc'])
            print('  last process lines:', ' | '.join(out.splitlines()[-8:]))
        return ok


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
        parser.error('timeout must be 0.2..60 seconds')
    passing = sum(bool(one(exe, mode, args.timeout, parent)) for mode in CASES)
    print(f'ISA-07 D7 SANDBOX DOC_MISMATCH_QUALIFIED={passing}/{len(CASES)} '
          'CPU=UNCHANGED DEVICE_ORACLES=0 SINGLE_STEP=1 '
          'GY62=PRINTED_PAGES_15_16')
    return 0 if passing == len(CASES) else 1

if __name__ == '__main__':
    sys.exit(main())
