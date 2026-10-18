#!/usr/bin/env python3
"""D10-B documentary-only stage. Pin current D10-A CPU verbatim; no modifications."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'a152049'
CPU_BLOB = 'bc9331b178333d2e3ef32789972bc16bc70c39ea'
PDF_SHA = {
    'GY62_1962_PDF': 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea',
    'DPS64_1964_SCAN_PDF': 'ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5',
}
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tools/isa07_d10a_io20_21_sequential_audit.py': '34c91b2c8480676c73475ce841509cdabeab2051',
    'tests/isa/isa07_d10a_io20_21_sequential_probe.cpp': '5ee9ff5f2b77ef4b3f7fb7764a91ab782bf407e5',
    'docs/ISA_07_D10A_IO20_21_SEQUENTIAL_CONTROL.md': '80ec210bada74bfd6ac2400f0281295bf67ed721',
    'docs/ISA_07_D10A_SOURCE_MANIFEST.tsv': '59ddfd8a120e2d5fa75d49e8aa7d7b59530aefc0',
}
GATES = {'D10B_CPU_IMMUTABLE', 'D10B_SOURCE_GY62', 'D10B_SOURCE_DPS64',
         'D10B_BCD_PAYLOAD', 'D10B_BINARY_WORD', 'D10B_SIGNED_ZERO',
         'D10B_HOST_OBS', 'D10B_IO21_CONTROL', 'D10B_PRIOR_PINS', 'D10B_OPEN'}
CASES = ('20-text10', '20-bcd625', '20-dot625', '20-negzero',
         '20-neg10', '20-text7', '21-raw11')


def git(*arguments):
    return subprocess.check_output(('git',) + arguments, cwd=ROOT,
                                   stderr=subprocess.PIPE).strip()


def blob(content):
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest().encode()


def check(condition, description):
    if not condition:
        raise RuntimeError(description)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.parse_args()
    check(git('cat-file', '-t', BASE) == b'commit', 'D10-A baseline not found')
    check(subprocess.run(('git', 'merge-base', '--is-ancestor', BASE, 'HEAD'),
                         cwd=ROOT).returncode == 0, 'D10-A baseline is not ancestor')
    cpu_base = subprocess.check_output(('git', 'show', BASE + ':src/main.cpp'), cwd=ROOT)
    check(git('rev-parse', BASE + ':src/main.cpp') == CPU_BLOB.encode(), 'D10-A CPU Git blob pin drift')
    check(blob(cpu_base) == CPU_BLOB.encode(), 'D10-A CPU bytes mismatch')
    check(git('rev-parse', 'HEAD:src/main.cpp') == CPU_BLOB.encode(),
          'D10-B modifies committed CPU: prohibited')
    cpu_work = (ROOT / 'src/main.cpp').read_bytes().replace(b'\r\n', b'\n')
    check(cpu_work == cpu_base, 'D10-B may NOT change any CPU code')
    for relative, pin in PINS.items():
        check(git('rev-parse', BASE + ':' + relative) == pin.encode(),
              'base Git pin drift: ' + relative)
        check(git('rev-parse', 'HEAD:' + relative) == pin.encode(),
              'HEAD Git pin drift: ' + relative)
        content = (ROOT / relative).read_bytes().replace(b'\r\n', b'\n')
        check(blob(content) == pin.encode(), 'working source drift: ' + relative)
    manifest = (ROOT / 'docs/ISA_07_D10B_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    check('src/main.cpp\tGIT_BLOB_AT_a152049\t' + CPU_BLOB + '\t' in manifest,
          'source manifest CPU incorrect')
    for relative, pin in PINS.items():
        check(relative + '\tGIT_BLOB_AT_a152049\t' + pin + '\t' in manifest,
              'source manifest entry absent: ' + relative)
    for name, digest in PDF_SHA.items():
        check(name + '\tSHA256\t' + digest + '\t' in manifest,
              'document SHA missing: ' + name)
    gates = (ROOT / 'docs/ISA_07_D10B_GATES.tsv').read_text(encoding='utf-8').splitlines()
    labels = {row.split('\t')[0] for row in gates[1:] if row.strip()}
    check(len(gates) == 11 and labels == GATES, 'expected exact 10 D10-B gates')
    report = (ROOT / 'docs/ISA_07_D10B_DECIMAL_INPUT_SOURCE_QUALIFICATION.md').read_text(encoding='utf-8')
    for source in ('GY62', 'DPS64', '1962', '1964', 'p. 58', 'p. 17',
                   '0.625', '32000000000000', 'BCD', 'OPEN', 'HOST_OBS',
                   'READ-ONLY', 'std::stoi', '0.1'):
        if source == '0.1':  # nonexact example is pinned in numeric oracle, not necessarily report
            continue
        check(source in report, 'missing documentary qualifier: ' + source)
    vectors = (ROOT / 'tools/isa07_d10b_numeric_vectors.py').read_text(encoding='utf-8')
    runner = (ROOT / 'tools/isa07_d10b_decimal_input_sandbox.py').read_text(encoding='utf-8')
    cpp = (ROOT / 'tests/isa/isa07_d10b_decimal_input_obs_probe.cpp').read_text(encoding='utf-8')
    for case in CASES:
        check('"' + case + '"' in cpp and "'" + case + "'" in runner,
              'missing host observation case ' + case)
    check('Fraction' in vectors and "exact_machine_word('+', '1000000000')" in vectors,
          'vectors lack exact rational or nonexact rejection')
    check('ONE_STEP_ONLY' in cpp and 'TemporaryDirectory' in runner and
          'NOT_A_HISTORICAL_DEVICE_ORACLE' in runner,
          'host tests lack isolation and historical caveat')
    print('ISA-07 D10-B: GY62/DPS64 DECIMAL INPUT SOURCE QUALIFICATION; CPU READ-ONLY')
    print('IO20-DECIMAL-DOCUMENT-CHECK PASS base=a152049 CPU_BLOB=PINNED '
          'CPU_MUTATION=0 unchanged_sources=5 GY62_SHA=PINNED '
          'DPS64_SHA=PINNED SOURCE_WORD_ENCODING=STRICT HOST_ASCII_OBS=7 '
          'DECIMAL_CONVERSION=UNFIXED ROUNDING=OPEN PHYSICAL_DEVICE_ORACLES=0')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as err:
        print('IO20-DECIMAL-DOCUMENT-CHECK FAIL:', err, file=sys.stderr)
        sys.exit(1)
