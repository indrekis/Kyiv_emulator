#!/usr/bin/env python3
"""ISA-07 D5: exact two-loop EOF guard qualification, no hardware oracle.

Pin pre-fix CPU by reversing exactly the two changed loop headers, then
hashing the reconstructed Git blob. This works both before and after the
D5 commit and does not require historical commit objects to be present.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'a985352'
CPU_BLOB = '9193214d93eb30a961c90800c5773f0dc144b6e0'
UNCHANGED = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d2_io_characterization_probe.cpp': '95b71b0f01d4befacc886afdef11c506327dfea8',
    'tools/isa07_d4_io_sandbox.py': 'a016b1ffa2211b0a3b8452c3781add21cdf201ba',
    'tools/isa07_d3_io22_sandbox.py': 'e337a5a212f29e991d4aab3f074c8aa8ae5f2ac1',
}
# Context-qualified substitutions; *not* generic `while(stream)` replacements.
ORIGINAL_20 = b'                while (punch_cards) {\n                    std::getline(punch_cards, line);\n                    if (counter == perfo_num) {'
CHANGED_20 = b'                while (std::getline(punch_cards, line)) {\n                    if (counter == perfo_num) {'
ORIGINAL_24 = b'            while (magnetic_drum) {\n                std::getline(magnetic_drum, line);\n                if(counter == drum_num_read){'
CHANGED_24 = b'            while (std::getline(magnetic_drum, line)) {\n                if(counter == drum_num_read){'

def normalize(path):
    return (ROOT / path).read_bytes().replace(b'\r\n', b'\n')

def oid(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def verify():
    cpu = normalize('src/main.cpp')
    assert cpu.count(CHANGED_20) == 1, '20: expected exactly one guarded getline header'
    assert cpu.count(CHANGED_24) == 1, '24: expected exactly one guarded getline header'
    assert ORIGINAL_20 not in cpu and ORIGINAL_24 not in cpu, 'old loop still present'
    previous = cpu.replace(CHANGED_20, ORIGINAL_20, 1).replace(CHANGED_24, ORIGINAL_24, 1)
    assert oid(previous) == CPU_BLOB, 'CPU drift: reversing exact D5 edits does not match committed D4 Git blob'
    for path, expected in UNCHANGED.items():
        assert oid(normalize(path)) == expected, 'source drift: ' + path
    path = ROOT / 'docs/ISA_07_D5_GATES.tsv'
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == 8 and {r['gate'] for r in rows} == {
        'D5_CPU_EXACT', 'D5_INPUT_FULL', 'D5_INPUT_SHORT', 'D5_EMPTY_MISSING',
        'D5_PC', 'D5_D3', 'D5_OLD_AUDITS', 'D5_OPEN',
    }, 'gate ledger mismatch'
    assert (ROOT / 'docs/ISA_07_D5_EOF_READ_FIX.md').is_file(), 'D5 documentation missing'
    assert (ROOT / 'docs/ISA_07_D5_SOURCE_MANIFEST.tsv').is_file(), 'D5 manifest missing'
    print('ISA-07 D5: EOF-GUARDED INPUT LOOPS FOR IO20/24; HOST CODE FIX ONLY')
    print('IO-EOF-CHECK PASS base=' + BASE + ' exact_cpu_delta=TWO_GETLINE_GUARDS '
          '20=FIXED 24=FIXED D4_FLAGS=PRESERVED D3_BREAK=PRESERVED '
          'unchanged_files=4 source_blobs=PINNED historical_io_oracles=0 PC_20_24=UNCHANGED')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        parser.error('specify --check')
    try:
        verify()
    except Exception as exc:
        print('IO-EOF-CHECK FAIL:', exc, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
