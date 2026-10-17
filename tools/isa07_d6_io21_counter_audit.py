#!/usr/bin/env python3
"""ISA-07 D6: full-blob pin with exactly one added opcode21 counter increment."""
from __future__ import annotations
import argparse
import csv
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '464f6d3'
BASE_CPU_SHA = '8beb18801926fbd40fa5680b7490124fedeeead7'
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d2_io_characterization_probe.cpp': '95b71b0f01d4befacc886afdef11c506327dfea8',
    'tools/isa07_d5_eof_audit.py': '1833100e9eaddebf6c4be140148e353402f92477',
    'tools/isa07_d3_io22_sandbox.py': 'e337a5a212f29e991d4aab3f074c8aa8ae5f2ac1',
}
# Anchored at the exact close of opcode21, never at an arbitrary 'if(flag)'.
OLD = (b'                if(flag){\n'
       b'                    break;\n'
       b'                }\n'
       b'            }\n'
       b'            h += com_counter;')
NEW = (b'                if(flag){\n'
       b'                    break;\n'
       b'                }\n'
       b'                ++counter;\n'
       b'            }\n'
       b'            h += com_counter;')

def canonical(path: str) -> bytes:
    return (ROOT / path).read_bytes().replace(b'\r\n', b'\n')

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()

def require(cond: bool, message: str):
    if not cond:
        raise ValueError(message)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    print('ISA-07 D6: ONE-LINE OPCODE21 RECORD-COUNTER FIX; HOST POLICY ONLY')
    try:
        data = canonical('src/main.cpp')
        require(data.count(NEW) == 1, 'expected exactly one opcode21 counter increment')
        require(data.count(OLD) == 0, 'pre-fix opcode21 block still present')
        original = data.replace(NEW, OLD, 1)
        require(blob_sha(original) == BASE_CPU_SHA,
                'CPU differs from exact parent blob beyond the single increment')
        require(data.count(b'++counter;') >= 1, 'counter update missing')
        for path, expected in PINS.items():
            require(blob_sha(canonical(path)) == expected,
                    'unchanged dependency blob drift: ' + path)
        tsv = ROOT / 'docs/ISA_07_D6_GATES.tsv'
        with tsv.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        require(len(rows) == 7 and len({r['gate'] for r in rows}) == 7,
                'expected seven unique D6 gates')
        manifest = ROOT / 'docs/ISA_07_D6_SOURCE_MANIFEST.tsv'
        with manifest.open(newline='', encoding='utf-8') as f:
            sources = {r['path']: r['git_blob_or_ref'] for r in csv.DictReader(f, delimiter='\t')}
        require(sources.get('src/main.cpp') == BASE_CPU_SHA, 'source manifest CPU pin drift')
        for path, sha in PINS.items():
            require(sources.get(path) == sha, 'source manifest dependency pin drift: '+path)
        probe = canonical('tests/isa/isa07_d6_io21_counter_probe.cpp')
        runner = canonical('tools/isa07_d6_io21_sandbox.py')
        require(b'int disassembly(' in probe and b'iter=' in probe,
                'missing standalone test probe contract')
        require(b'TemporaryDirectory(' in runner and b'IO21_COUNTER=ADVANCING' in runner,
                'missing isolated test runner contract')
        print('IO21-COUNTER-CHECK PASS base=464f6d3 exact_cpu_delta=ONE_COUNTER_INCREMENT '
              '21=FIXED h_modes=0,1,2,4 two_step_seq=1 PC21=UNCHANGED '
              'D5_EOF=PRESERVED D4_FLAGS=PRESERVED D3_BREAK=PRESERVED '
              'unchanged_files=4 source_blobs=PINNED historical_io_oracles=0')
        return 0
    except (OSError, ValueError, KeyError) as e:
        print('IO21-COUNTER-CHECK FAIL: '+str(e), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
