#!/usr/bin/env python3
"""ISA-07 D10-C independent BCD converter: no modification to CPU.

Strictly preserve prior committed Git blobs; do not rewrite old evidence pins.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '9fd7c4c'
CPU_BLOB = 'bc9331b178333d2e3ef32789972bc16bc70c39ea'
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'docs/ISA_07_D10B_DECIMAL_INPUT_SOURCE_QUALIFICATION.md': '6e114872533f3e4903fd4242ce09f06d25334c4a',
    'docs/ISA_07_D10B_SOURCE_MANIFEST.tsv': 'c9839bd2d38d1267d53ee139a86f1db1b3fc88fc',
    'tools/isa07_d10b_numeric_vectors.py': 'fdf2a51557805e601cbfe75454e0e7c81b75ae03',
    'tools/isa07_d10b_decimal_input_audit.py': '09ec0829e6f448ff3851061734fb86eb2604ccad',
    'tests/isa/isa07_d10b_decimal_input_obs_probe.cpp': '2fd4a03e44c53cdb1d6574cc57d4e84c80aed9a2',
}
PDF_SHA = {
    'GY62_1962_PDF': 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea',
    'DPS64_1964_SCAN_PDF': 'ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5',
}
GATES = {'D10C_CPU_IMMUTABLE', 'D10C_PRIOR_SOURCES', 'D10C_GY62_DPS64',
         'D10C_BCD_VALIDATION', 'D10C_EXACT_ARITHMETIC', 'D10C_SOURCE_VECTORS',
         'D10C_EXTRA_EXACT', 'D10C_REJECT', 'D10C_FULL_GRID', 'D10C_OPEN'}


def git(*args):
    return subprocess.check_output(('git',) + args, cwd=ROOT, stderr=subprocess.PIPE).strip()


def blob(s):
    return hashlib.sha1(b'blob ' + str(len(s)).encode() + b'\0' + s).hexdigest().encode()


def need(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.parse_args()
    need(git('cat-file', '-t', BASE) == b'commit', 'D10-B commit not found')
    need(subprocess.run(('git', 'merge-base', '--is-ancestor', BASE, 'HEAD'),
                        cwd=ROOT).returncode == 0, 'D10-B not ancestor')
    cpu = subprocess.check_output(('git', 'show', BASE + ':src/main.cpp'), cwd=ROOT)
    need(blob(cpu) == CPU_BLOB.encode(), 'BASE CPU Git content/blob mismatch')
    need(git('rev-parse', BASE + ':src/main.cpp') == CPU_BLOB.encode(), 'BASE CPU pin drift')
    need(git('rev-parse', 'HEAD:src/main.cpp') == CPU_BLOB.encode(), 'HEAD CPU drift')
    need((ROOT/'src/main.cpp').read_bytes().replace(b'\r\n', b'\n') == cpu,
         'Working CPU modified; D10-C is standalone')
    manifest = (ROOT/'docs/ISA_07_D10C_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_'+BASE+'\t'+CPU_BLOB+'\t' in manifest,
         'CPU manifest mismatch')
    for rel, pin in PINS.items():
        expected = pin.encode()
        need(git('rev-parse', BASE + ':' + rel) == expected, 'Base pin drift: '+rel)
        need(git('rev-parse', 'HEAD:' + rel) == expected, 'HEAD pin drift: '+rel)
        raw = (ROOT/rel).read_bytes().replace(b'\r\n', b'\n')
        need(blob(raw) == expected, 'Working pinned file drift: '+rel)
        need(rel+'\tGIT_BLOB_AT_'+BASE+'\t'+pin+'\t' in manifest,
             'Manifest omitted pinned file: '+rel)
    for name, digest in PDF_SHA.items():
        need(name+'\tSHA256\t'+digest+'\t' in manifest, 'PDF pin absent: '+name)
    gates = (ROOT/'docs/ISA_07_D10C_GATES.tsv').read_text(encoding='utf-8').splitlines()
    rows={line.split('\t')[0] for line in gates[1:] if line.strip()}
    need(len(gates) == 11 and rows == GATES, 'Expected exactly ten D10-C gates')
    header=(ROOT/'inc/kyiv_decimal_exact.h').read_text(encoding='utf-8')
    probe=(ROOT/'tests/isa/isa07_d10c_exact_converter_probe.cpp').read_text(encoding='utf-8')
    runner=(ROOT/'tools/isa07_d10c_exact_converter_sandbox.py').read_text(encoding='utf-8')
    for token in ('convert_bcd10', '9\'765\'625ULL', 'invalid_bcd', 'nonexact',
                  'packed_bcd & ~bcd_bits_mask', 'negative ? sign_bit : 0'):
        need(token in header, 'Standalone converter gate missing '+token)
    need('#include "kyiv_decimal_exact.h"' in probe and '2048' in probe and
         'NO_FLOATING_POINT=1' in probe, 'C++ 2048 grid witness absent')
    need('Fraction' in runner and 'len(cases) == 22' in runner and
         'NONEXACT' in runner and 'INVALID_BCD' in runner and
         '2048/2048' in runner and 'sweep_ok' in runner,
         'Independent/reject test runner absent')
    report=(ROOT/'docs/ISA_07_D10C_EXACT_BCD_CONVERTER.md').read_text(encoding='utf-8')
    for token in ('GY62', 'DPS64', '9,765,625', 'SOURCE_STRICT', 'HOST_POLICY',
                  '2048/2048', 'OPEN', 'CPU', 'negative zero'):
        need(token in report, 'Missing documentary qualification '+token)
    print('ISA-07 D10-C: EXACT TEN-DIGIT BCD -> SIGNED 41-BIT WORD; STANDALONE ONLY')
    print('IO20-EXACT-CONVERTER-CHECK PASS base=9fd7c4c CPU_BLOB=PINNED '
          'CPU_MUTATION=0 INC_KYIV_H=UNCHANGED unchanged_sources=6 '
          'GY62_SHA=PINNED DPS64_SHA=PINNED BCD_NIBBLES=10 '
          'FRACTION_BITS=40 EXACT_DIVISOR=9765625 GRID=2048 '
          'IO20_INTEGRATION=NOT_DONE HOST_ASCII=OPEN ROUNDING=OPEN DEVICE_ORACLES=0')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
        print('IO20-EXACT-CONVERTER-CHECK FAIL:', e, file=sys.stderr)
        sys.exit(1)
