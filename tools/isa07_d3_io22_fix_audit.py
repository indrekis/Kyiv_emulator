#!/usr/bin/env python3
"""ISA-07 D3: strict byte-for-byte qualification of the SINGLE op22 break fix.

The D1/D2 scripts intentionally qualify the old CPU source: don't weaken their
pre-fix fingerprints after this change. D3 fetches that unchanged Git blob,
constructs the sole allowed transformation, and compares *all* CPU source bytes.
"""
import argparse
import csv
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'a311c22'
CPU_BLOB = 'f84acfb22fa3e00f598f3cdb05d4ed2a6618f893'
UNCHANGED = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d2_io_characterization_probe.cpp': '95b71b0f01d4befacc886afdef11c506327dfea8',
    'tools/isa07_d2_io_sandbox.py': '06482b6004dd9e1e634fadf2ed5bd0e3ea69a484',
    'tools/isa07_d1_opcode_inventory_audit.py': 'f9d0d6cac2688ef199ec21752f30273579086068',
    'tools/isa07_d2_io_audit.py': 'c94223389b677024c26124bdd8237a47114017ef',
    'docs/ISA_07_D1_OPEN_ISSUES.tsv': '013549da8348b0575f960387715fb1cc5ec95121',
    'docs/ISA_07_D2_IO_CHARACTERIZATION.tsv': 'a519ace7dbbb1516ed0802bd46342d96d3c0b360',
}
OLD = (b'            C_reg = addr3_shifted.destination;\n'
       b'            K_reg = kmem.read_memory(C_reg);\n'
       b'        }\n'
       b'\n'
       b'\n'
       b'        case IO_operations_t::opcode_write_magnetic_drum:{')
NEW = (b'            C_reg = addr3_shifted.destination;\n'
       b'            K_reg = kmem.read_memory(C_reg);\n'
       b'        }\n'
       b'            break;\n'
       b'\n'
       b'\n'
       b'        case IO_operations_t::opcode_write_magnetic_drum:{')


def require(value, explanation):
    if not value:
        raise AssertionError(explanation)


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def check():
    old = git('cat-file', 'blob', CPU_BLOB)
    require(old.count(OLD) == 1, 'Historical pinned CPU does not contain one exact 22/23 boundary')
    require(b'            break;\n\n\n        case IO_operations_t::opcode_write_magnetic_drum' not in old,
            'Historical CPU unexpectedly already fixed')
    expected = old.replace(OLD, NEW, 1)
    current = (ROOT / 'src/main.cpp').read_bytes().replace(b'\r\n', b'\n')
    require(current == expected,
            'Current CPU differs from historical source in more than one inserted break')
    for path, pin in UNCHANGED.items():
        actual = git('rev-parse', 'HEAD:' + path).decode('ascii').strip()
        require(actual == pin, f'Unchanged tracked Git blob drift: {path} got={actual}')
        # Reject uncommitted changes too. Normalization reflects git text EOL settings.
        tracked = git('show', 'HEAD:' + path)
        actual_file = (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
        require(actual_file == tracked, 'Uncommitted source drift: ' + path)

    gates_file = ROOT / 'docs/ISA_07_D3_FIX_GATES.tsv'
    with gates_file.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    require(len(rows) == 6 and {r['gate'] for r in rows} == {
        'D3_EXACT_EDIT', 'D3_22_OUTPUT', 'D3_23_OUTPUT', 'D3_PC_22_23',
        'D3_OLD_PROBES', 'D3_OTHER_IO'}, 'D3 gates incomplete')
    require(all(r['classification'] and r['assertion'] for r in rows), 'Invalid D3 gate row')
    for path in ('docs/ISA_07_D3_IO22_FALLTHROUGH_FIX.md',
                 'docs/ISA_07_D3_SOURCE_MANIFEST.tsv',
                 'tools/isa07_d3_io22_sandbox.py'):
        require((ROOT/path).is_file(), 'Missing D3 artifact ' + path)
    print('ISA-07 D3: MINIMAL IO22 FALLTHROUGH FIX; NO HISTORICAL DEVICE ORACLE')
    print('IO22-FIX-CHECK PASS base=' + BASE + ' exact_cpu_delta=ONE_BREAK '
          'before_22_falls_to_23=YES after_22_falls_to_23=NO '
          'old_cpu_blob=PINNED unchanged_files=7 '
          'D1_D2_BASELINE=HISTORICAL_NOT_CURRENT CPU_ONLY_ONE_LINE_CHANGED=1')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    try:
        check()
    except (AssertionError, FileNotFoundError, ValueError, subprocess.CalledProcessError) as exc:
        print('IO22-FIX-CHECK FAIL: ' + str(exc), file=sys.stderr)
        sys.exit(1)
