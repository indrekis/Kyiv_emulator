#!/usr/bin/env python3
"""ISA-07 D2: version-pinned IO characterization, no CPU fixes.

Pin Git blob OIDs (rather than local raw file SHA) to avoid CRLF failures.
The historical commit need not be available in a shallow checkout.
"""
import argparse
import csv
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/main.cpp'
HEADER = ROOT / 'inc/kyiv.h'
D1_ISSUES = ROOT / 'docs/ISA_07_D1_OPEN_ISSUES.tsv'
LEDGER = ROOT / 'docs/ISA_07_D2_IO_CHARACTERIZATION.tsv'
PIN = {
    'src/main.cpp': 'f84acfb22fa3e00f598f3cdb05d4ed2a6618f893',
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'docs/ISA_07_D1_OPEN_ISSUES.tsv': '013549da8348b0575f960387715fb1cc5ec95121',
}
MODES = {'20', '21', '22', '23', '24', '25'}


def require(value, msg):
    if not value:
        raise AssertionError(msg)


def handler(code):
    symbol = {
        '20': 'opcode_read_perfo_data',
        '21': 'opcode_read_perfo_binary',
        '22': 'opcode_write_perfo_binary',
        '23': 'opcode_write_magnetic_drum',
        '24': 'opcode_read_magnetic_drum',
        '25': 'opcode_init_magnetic_drum',
    }[code]
    return symbol


def extract(source, symbol):
    match = re.search(r'case\s+IO_operations_t::' + re.escape(symbol) +
                      r'\s*:\s*\{(?P<body>.*?)(?=\n\s*case\s+IO_operations_t::|\n\s*default\s*:)',
                      source, flags=re.DOTALL)
    require(match is not None, 'Cannot delimit C++ handler ' + symbol)
    return match.group('body')


def load_tsv(path):
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        require(reader.fieldnames is not None, 'TSV has no header: ' + path.name)
        rows = list(reader)
    require(all(all(v is not None and v.strip() for v in row.values()) for row in rows),
            'Empty cell or malformed TSV row: ' + path.name)
    return rows


def git_blob(path):
    r = subprocess.run(['git', 'rev-parse', 'HEAD:' + path], cwd=ROOT,
                       text=True, capture_output=True, check=True)
    return r.stdout.strip()


def structural_checks(source, ledger):
    lines = {row['issue_id']: row for row in ledger}
    require(len(lines) == len(ledger), 'Duplicate issue_id')
    expected = ('IO_FALLTHROUGH', 'IO_UNINIT', 'IO_COUNTER', 'IO_PC', 'IO_RANGE', 'IO_PATHS')
    require(set(lines) == set(expected), f'Unexpected ledger rows: {set(lines)}')
    require(set.union(*(set(row['opcodes_octal'].split(',')) for row in ledger)) == MODES,
            'Ledger must explicitly cover 20–25')
    bodies = {k: extract(source, handler(k)) for k in MODES}
    require(re.search(r'\bC_reg\s*=\s*addr3_shifted\.destination\s*;', bodies['22']) is not None,
            '22 no longer sets C=III')
    require('break;' not in bodies['22'], '22 no longer falls through: update issue classification')
    require('std::ofstream' in bodies['22'] and 'std::ofstream' in bodies['23'],
            'Output handlers changed')
    for code in ('20', '24'):
        require(re.search(r'\bbool\s+flag\s*;', bodies[code]),
                'Uninitialized flag changed in ' + code)
    body = bodies['21']
    require(re.search(r'\bint\s+counter\s*=\s*0\s*;', body) and
            not re.search(r'\b(?:counter\s*\+\+|\+\+\s*counter|counter\s*\+=)', body),
            '21 counter no longer remains unchanged')
    for code in ('20', '21', '24', '25'):
        require(not re.search(r'\b(?:C_reg\s*(?:=|\+\+|\+=|-=)|\+\+\s*C_reg)', bodies[code]),
                'C behavior changed in ' + code)
    require('punc_cards_out.txt' in bodies['22'] and 'magnetic_drum.txt' in bodies['23'],
            'Expected fixture output paths changed')
    require('punch_cards_in.txt' in bodies['20'] and 'drum_in.txt' in bodies['24'] and
            'punched_tape.txt' in bodies['21'], 'Expected fixture input paths changed')
    # Distinguish the loop's source_2-as-count from address-range semantics.
    for code in ('22', '23'):
        require(re.search(r'for\s*\(\s*uint64_t\s+i\s*=\s*0\s*;\s*i\s*<=\s*addr3_shifted\.source_2', bodies[code]),
                code + ' loop bounds changed')
    return bodies


def check():
    ledger = load_tsv(LEDGER)
    d1 = load_tsv(D1_ISSUES)
    ids = {row['issue_id'] for row in d1}
    require({'IO_FALLTHROUGH', 'IO_UNINIT', 'IO_COUNTER', 'IO_PC', 'IO_RANGE'}.issubset(ids),
            'D1 issue ledger drift')
    source = SOURCE.read_text(encoding='utf-8')
    bodies = structural_checks(source, ledger)
    for path, expected in PIN.items():
        actual = git_blob(path)
        require(actual == expected, f'Pinned base Git blob drift: {path} expected={expected}, got={actual}')
    print('ISA-07 D2: SOURCE CHARACTERIZATION OF IO20..25; NO HISTORICAL I/O ORACLE')
    print('IO-CHECK PASS codes=6 ledger=6 fallthrough_22_23=CONFIRMED '
          'uninit_flags_20_24=CONFIRMED nonadvancing_21_counter=CONFIRMED '
          'unchanged_pc=20,21,24,25 output_loops=SOURCE2_AS_COUNT '
          'source_pins=PINNED cpu=UNCHANGED')
    for row in ledger:
        print(f"CODE-OBS id={row['issue_id']} codes={row['opcodes_octal']} "
              f"class={row['classification']} status={row['test_boundary']}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    try:
        check()
    except (OSError, AssertionError, subprocess.CalledProcessError, ValueError) as exc:
        print('IO-CHECK FAIL: ' + str(exc), file=sys.stderr)
        sys.exit(1)
