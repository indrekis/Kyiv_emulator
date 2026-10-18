#!/usr/bin/env python3
"""ISA-07 D9-A: process-isolated, actual 2-step CPU control transfer tests.

Book GY62 printed p15 documents IO24 branch to a3. The host file content,
empty/missing cases and K prefetch are emulator adapter/convention checks, not
independent historical hardware witnesses.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = {
    'full': ('5 7 9\n', '5/7/9', '120'),
    'short': ('5\n', '5/0/0', '120'),
    'empty': ('', '0/0/0', '120'),
    'missing': (None, '0/0/0', '120'),
    'track1': ('99 88 77\n5 7 9\n', '5/7/9', '120'),
    'single': ('5 7 9\n', '0/5/0', '120'),
    'altjump': ('5 7 9\n', '5/7/9', '130'),
}
PATTERN = re.compile(
    r'^D9A-OBS mode=(\S+) pc0=(\S+) target=(\S+) pc1=(\S+) pc2=(\S+) '
    r'k1_match=(\d) k2_match=(\d) mem=(\S+) xor=(\d+) '
    r'drum_unchanged=(\d) running=(\d)/(\d) steps=(\d+)$', re.M)

def case(exe, mode, parent, timeout):
    source, expected_memory, target = FIXTURES[mode]
    with tempfile.TemporaryDirectory(prefix='isa07_d9a_', dir=parent) as folder:
        root = Path(folder)
        (root / 'a' / 'b').mkdir(parents=True)
        (root / 'mem').mkdir()
        if source is not None:
            (root / 'mem' / 'drum_in.txt').write_text(source, encoding='ascii')
        try:
            child = subprocess.run([str(exe), mode], cwd=root / 'a' / 'b',
                                   text=True, encoding='utf-8', errors='replace',
                                   capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f'D9A-CODE-FAIL mode={mode} process=TIMEOUT result=FAIL')
            return False
        output = child.stdout + '\n' + child.stderr
        found = PATTERN.findall(output)
        good = (child.returncode == 0 and len(found) == 1 and
                found[0] == (mode, '100', target, target,
                             '131' if target == '130' else '121',
                             '1', '1', expected_memory, '6', '1', '1', '1', '2'))
        # A host file may not be written by IO24 or target XOR.
        extra = [p for p in root.rglob('*') if p.is_file() and p.name != 'drum_in.txt']
        good = good and not extra
        print(f'D9A-CODE-{"PASS" if good else "FAIL"} mode={mode} '
              f'process=EXIT_{child.returncode} target={target} '
              f'memory={found[0][7] if found else "N/A"} '
              f'pc1={found[0][3] if found else "N/A"} '
              f'pc2={found[0][4] if found else "N/A"} '
              f'K_PREFETCH={int(bool(found) and found[0][5:7] == ("1", "1"))} '
              f'drum_state={int(bool(found) and found[0][9] == "1")} '
              f'host_class={"HOST_POLICY" if mode in ("empty", "missing") else "SOURCE_STRICT_BRANCH_HOST_ADAPTER"} '
              f'result={"PASS" if good else "FAIL"}')
        if not good:
            print('  OUTPUT_TAIL=' + repr(output.splitlines()[-12:]))
            if extra: print('  UNEXPECTED_FILES=' + repr([str(p.relative_to(root)) for p in extra]))
        return good

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True)
    parser.add_argument('--timeout', type=float, default=5)
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    parent = ROOT / 'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        parser.error('compiled executable and tempkyiv required')
    if not 0.2 <= args.timeout <= 60:
        parser.error('timeout must be 0.2..60 seconds')
    passed = sum(case(exe, mode, parent, args.timeout) for mode in FIXTURES)
    print(f'ISA-07 D9A SANDBOX PASS={passed}/7 TWO_STEPS=7 '
          'IO24_PC_TO_A3=DOCUMENTED K_REG_PREFETCH=EMULATOR_CONVENTION '
          'DRUM_PARAMS=PRESERVED HOST_MISSING_EMPTY=POLICY '
          'IO25=UNCHANGED IO20_21_PC=OPEN DEVICE_ORACLES=0')
    return 0 if passed == 7 else 1

if __name__ == '__main__':
    sys.exit(main())
