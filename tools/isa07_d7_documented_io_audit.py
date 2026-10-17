#!/usr/bin/env python3
"""D7 read-only source qualification; pin GY62 provenance and Git CPU OIDs.

Historic documentary truths are separate from C++ one-step observations.
"""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'f30644f'
PINS = {
    'src/main.cpp': 'eef2d92ce5c39205960aa64bc8839d924730d882',
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d2_io_characterization_probe.cpp': '95b71b0f01d4befacc886afdef11c506327dfea8',
    'docs/ISA_07_D1_OPEN_ISSUES.tsv': '013549da8348b0575f960387715fb1cc5ec95121',
    'docs/ISA_07_D6_GATES.tsv': 'f08b70a074b40cc19974f39eb604f8754ec0a35d',
}
GY62 = ('Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf',
        'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea')
CASES = ('D7_RANGE20', 'D7_DECIMAL20', 'D7_RANGE21', 'D7_RANGE22',
         'D7_RANGE23', 'D7_RANGE24_PC', 'D7_PC25')


def git(*args):
    return subprocess.check_output(('git',) + args, cwd=ROOT, text=True,
                                   stderr=subprocess.PIPE).strip()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify the pinned documentary gate")
    parser.parse_args()
    need(git('rev-parse', '--is-inside-work-tree') == 'true', 'Not a Git working tree')
    need(git('cat-file', '-t', BASE) == 'commit', 'D6 baseline commit missing')
    need(subprocess.run(('git', 'merge-base', '--is-ancestor', BASE, 'HEAD'),
                        cwd=ROOT, check=False).returncode == 0,
         'D6 baseline not ancestor of HEAD')
    for path, expected in PINS.items():
        need(git('rev-parse', f'{BASE}:{path}') == expected,
             f'D6 baseline Git blob mismatch: {path}')
        need(git('rev-parse', f'HEAD:{path}') == expected,
             f'Current HEAD Git blob mismatch: {path}')
        actual = (ROOT/path).read_bytes().replace(b'\r\n', b'\n')
        need(git_blob(actual) == expected,
             f'Working source changed (normalized CRLF): {path}')

    manifest = (ROOT/'docs/ISA_07_D7_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    for path, expected in PINS.items():
        need(f'{path}\tGIT_BLOB_AT_f30644f\t{expected}\t' in manifest,
             f'Manifest source mismatch: {path}')
    need(f'{GY62[0]}\tSHA256_EXTERNAL_SOURCE\t{GY62[1]}\t' in manifest,
         'Historical source PDF identity missing')
    rows = (ROOT/'docs/ISA_07_D7_GATES.tsv').read_text(encoding='utf-8').splitlines()
    observed = {line.split('\t')[0]:line.split('\t') for line in rows[1:] if line.strip()}
    need(len(rows) == 11 and len(observed) == 10, 'Expected ten distinct documented gates')
    for label in CASES:
        need(label in observed and observed[label][1] == 'DOC_MISMATCH' and
             observed[label][4] == 'CHARACTERIZED_NO_FIX', f'D7 gate mismatch: {label}')
    for label in ('D7_PC20_21', 'D7_MOD_REGISTER', 'D7_HOST_IO_FORMAT'):
        need(label in observed and observed[label][4].startswith('OPEN_'),
             f'Unresolved documentary scope missing: {label}')
    doc = (ROOT/'docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md').read_text(encoding='utf-8')
    need('printed pp. 15–16' in doc and 'NO CPU FIX' in doc and
         'a1 through a2 inclusive' in doc,
         'Provenance/interval/no-fix statement missing in D7 report')
    cpp = (ROOT/'tests/isa/isa07_d7_io_documented_boundaries_probe.cpp').read_text(encoding='utf-8')
    runner = (ROOT/'tools/isa07_d7_io_documented_sandbox.py').read_text(encoding='utf-8')
    for mode in ('20-range','20-decimal','21-range','22-range','23-range','24-range','25-next'):
        need(mode in cpp and mode in runner, f'Missing probe/sandbox mode: {mode}')
    need('EXACTLY ONE CPU STEP' in cpp and 'TemporaryDirectory' in runner,
         'Process isolation and bounded step gates missing')
    print('ISA-07 D7: GY62 DOCUMENTED I/O SEMANTICS; CPU READ-ONLY')
    print('IO-DOCUMENT-CHECK PASS base=f30644f CPU_BLOB=PINNED '+
          'unchanged_sources=5 GY62_PDF_SHA=PINNED_DOCUMENTARY '+
          'documented_discrepancies=7 unresolved_scopes=3 '+
          'CPU_MUTATION=0 HISTORICAL_DEVICE_ORACLES=0')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print('IO-DOCUMENT-CHECK FAIL:', exc, file=sys.stderr)
        sys.exit(1)
