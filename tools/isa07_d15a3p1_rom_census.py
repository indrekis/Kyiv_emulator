#!/usr/bin/env python3
"""D15/A3-P1: read-only, byte-exact ROM source inventory and provisional export.

Reads ROM from a pinned Git object, NOT a potentially CRLF-converted worktree.
Never invents/repairs undecodable or missing historical words.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '846c450a9f84334169e8f00a1f1b285fffb6c20c'
ROM_BLOB = 'bb6224e130c59564a8ccc4b224c55e41e50784a3'
WORD_MASK = (1 << 41) - 1
ADDRESS_MIN, ADDRESS_MAX = 0o3010, 0o3277
# No UTF-8 replacement or whitespace cleaning: the original 3-byte U+FFFD
# sequences at 3121/3123 must remain observable and unresolved.
LINE = re.compile(rb'([0-7]{4})[\t ]+([0-7]{2})[\t ]+([0-7]{4})[\t ]+([0-7]{4})[\t ]+([0-7]{4})[\t ]*')


def check(ok, code):
    if not ok:
        raise RuntimeError(code)


def git(*args, binary=False):
    p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=False)
    check(p.returncode == 0, 'GIT_FAIL: ' + p.stderr[-500:].decode('utf8', 'replace'))
    return p.stdout if binary else p.stdout.decode('utf8').strip()


def validate_git():
    check(git('branch', '--show-current') == 'main', 'NOT_MAIN')
    check(git('rev-parse', 'HEAD') == BASE, 'BASELINE_CHANGED')
    check(git('rev-parse', '--show-prefix') == '', 'NOT_REPO_ROOT')
    check(git('rev-parse', f'{BASE}:mem/ROM.txt') == ROM_BLOB, 'ROM_BLOB_CHANGED')
    source = git('show', f'{BASE}:mem/ROM.txt', binary=True)
    return source


def analyze(data):
    parsed, invalid, duplicates = {}, [], []
    for n, raw in enumerate(data.splitlines(), 1):
        match = LINE.fullmatch(raw)
        if not match:
            invalid.append({'line': n, 'raw_hex': raw.hex(),
                            'address_hint': raw[:4].decode('ascii', 'replace')})
            continue
        addr = int(match[1], 8)
        word = int(b''.join(match.groups()[1:]), 8)
        if not ADDRESS_MIN <= addr <= ADDRESS_MAX or word > WORD_MASK:
            invalid.append({'line': n, 'raw_hex': raw.hex(),
                            'address_hint': match[1].decode('ascii')})
            continue
        if addr in parsed:
            duplicates.append({'line': n, 'address': f'{addr:04o}'})
            continue
        parsed[addr] = word
    missing = [f'{a:04o}' for a in range(ADDRESS_MIN, ADDRESS_MAX + 1)
               if a not in parsed]
    return parsed, invalid, duplicates, missing


def self_test():
    good = b'3010\t00 0001 0000 0000\r\n'
    parsed, bad, dup, missing = analyze(good)
    check(parsed[0o3010] == (1 << 24) and not bad and not dup, 'VALID_RECORD')
    corrupt = good + b'3121\t01 0005 \xef\xbf\xbd011 0005\r\n'
    parsed, bad, dup, missing = analyze(corrupt)
    check(len(bad) == 1 and bad[0]['line'] == 2 and
          bad[0]['raw_hex'].count('efbfbd') == 1, 'CORRUPT_BYTE_REJECTED')
    parsed, bad, dup, missing = analyze(good + good)
    check(len(dup) == 1 and dup[0]['address'] == '3010', 'DUPLICATE_REJECTED')
    check('3200' in missing, 'MISSING_DETECTION')
    print('D15A3P1-SELFTEST PASS ASCII_STRICT=1 REPLACEMENT_REJECTED=1 '
          'DUPLICATE_REJECTED=1 HOLE_DETECTED=1')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--strict-complete', action='store_true')
    ap.add_argument('--export-private', type=Path)
    a = ap.parse_args()
    if a.self_test:
        self_test()
        if not (a.strict_complete or a.export_private):
            return
    data = validate_git()
    parsed, invalid, duplicates, missing = analyze(data)
    check(len(data) == 4396 and len(data.splitlines()) == 183, 'ROM_SOURCE_SHAPE_CHANGED')
    check(len(parsed) == 181 and len(invalid) == 2 and len(duplicates) == 0,
          'ROM_CLASSIFICATION_CHANGED')
    check([(x['line'], x['address_hint']) for x in invalid] ==
          [(74, '3121'), (76, '3123')], 'INVALID_LOCATION_CHANGED')
    check(missing == ['3121', '3123', '3200'], 'ROM_HOLES_CHANGED')
    sha = hashlib.sha256(data).hexdigest()
    print(f'D15A3P1-ROM-CENSUS PASS BLOB={ROM_BLOB} BYTES={len(data)} '
          f'LINES=183 VALID=181 INVALID=2 MISSING=1 DUPLICATES=0 '
          f'RAW_SHA256={sha}')
    print('D15A3P1-ROM-UNRESOLVED ADDRS=3121,3123,3200 '
          'SYNTAX_UNCERTAIN=2 ABSENT=1 HISTORICAL_ORACLE=0')
    if a.strict_complete:
        check(not invalid and not duplicates and not missing,
              'STRICT_ROM_INCOMPLETE: 3121,3123,3200')
    if a.export_private is not None:
        output = a.export_private.resolve()
        scratch = (ROOT / 'tempkyiv').resolve()
        check(output != scratch and scratch in output.parents,
              'EXPORT_MUST_BE_PRIVATE_UNDER_TEMPKYIV')
        check(not output.exists(), 'EXPORT_PATH_OCCUPIED')
        # Parent must be existing, trusted and not symlinked (create under tempkyiv).
        check(output.parent.is_dir() and not output.parent.is_symlink(),
              'EXPORT_PARENT_INVALID')
        # Files are explicitly provisional. 3121,3123,3200 remain omitted.
        payload = ('# PROVISIONAL SYNTACTIC ROM EXPORT, NOT HISTORY-VERIFIED\n'
                   'KYIV41-OCT1\n' +
                   ''.join(f'{address:04o} {value:014o}\n'
                           for address, value in sorted(parsed.items()))).encode('ascii')
        manifest = {'classification': 'PROVISIONAL_SYNTAX_ONLY',
                    'source_git_blob_sha1': ROM_BLOB,
                    'source_git_commit': BASE,
                    'source_raw_sha256': sha,
                    'image_sha256': hashlib.sha256(payload).hexdigest(),
                    'valid_records': 181, 'unresolved': missing,
                    'unresolved_line_hex': invalid,
                    'HARDWARE_ORACLE': 0}
        output.mkdir()
        try:
            (output/'ROM-provisional.k41').write_bytes(payload)
            (output/'ROM-provisional-manifest.json').write_text(
                json.dumps(manifest, indent=2, ensure_ascii=True) + '\n', encoding='ascii')
        except Exception:
            # Private output only; do not silently replace user's existing data.
            import shutil
            shutil.rmtree(output)
            raise
        check(len(parsed) == 181, 'EXPORT_RECORD_COUNT')
        print('D15A3P1-EXPORT PASS RECORDS=181 OMITTED=3 '
              'HISTORICAL_ORACLE=0 PRIVATE_ONLY=1')
        print(f'D15A3P1-EXPORT-PATH {output}')


if __name__ == '__main__':
    main()
