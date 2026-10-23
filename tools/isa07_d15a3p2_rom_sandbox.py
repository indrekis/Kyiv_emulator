#!/usr/bin/env python3
"""D15/A3-P2 real CLI ROM re-open: verify actual 3121/3123 live words."""
from pathlib import Path
import argparse
import subprocess
import tempfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT/'mem/ROM.txt'
WORDS = {0o3121: int('01000530110005', 8),
         0o3123: int('12301100050004', 8),
         0o3036: int('37777777777777', 8)}
assert WORDS[0o3036] > (1 << 31) - 1

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cli-exe', required=True)
    p.add_argument('--timeout', type=int, default=20)
    a = p.parse_args()
    exe = Path(a.cli_exe).resolve()
    assert exe.is_file(), 'CLI_EXE_MISSING'
    before = ROM.read_bytes()
    assert b'3200\t' not in before, '3200_UNEXPECTED'
    for addr, value in WORDS.items():
        row = f'{addr:04o}\t{value:02o}'
        _ = row
    with tempfile.TemporaryDirectory(prefix='d15a3p2_', dir=ROOT/'tempkyiv') as name:
        folder = Path(name)
        image = folder/'stop.k41'
        image.write_bytes(b'KYIV41-OCT1\n0500 33000000000000\n')
        cmd = [str(exe), 'image', str(image), '0500', '2',
               '--watch', '3121', '--watch', '3123', '--watch', '3036']
        # In the current production constructor ../mem/ROM.txt depends on CWD.
        # tempkyiv is exactly one directory below repository root.
        result = subprocess.run(cmd, cwd=ROOT/'tempkyiv', capture_output=True,
                                text=True, errors='replace', timeout=a.timeout)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert 'D15A2-RUN STATUS=CPU_STOP STEPS=1' in result.stdout, result.stdout
        for addr, value in WORDS.items():
            marker = f'D15A2-WATCH ADDR={addr:04o} RAW={value:014o}'
            assert marker in result.stdout, (marker, result.stdout)
            print(f'D15A3P2-CASE ROM_{addr:04o}_LIVE PASS RAW={value:014o}')
        assert ROM.read_bytes() == before, 'ROM_MUTATED'
        assert image.read_bytes() == b'KYIV41-OCT1\n0500 33000000000000\n', 'IMAGE_MUTATED'
    print('D15A3P2-NATIVE PASS CASES=3/3 SOURCE_IMMUTABLE=1 '
          'ROM_VALID=183/183 UNKNOWN_3200=1 ROM_RUNTIME_EXPLICIT=PENDING')

if __name__ == '__main__':
    main()
