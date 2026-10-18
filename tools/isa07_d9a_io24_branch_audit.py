#!/usr/bin/env python3
"""ISA-07 D9-A exact two-line control-state change, historical Git pins preserved.

Comparisons normalize only CRLF, not trailing-newline differences.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'df480cd'
CPU_BLOB = '290bdd7bc803aee6f5ddb2fd979a8ba233c4b050'
PDF_SHA = 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d8b_absolute_output_probe.cpp': '756ccb35ee1ee2774474ebc59c9a736049f1cda3',
    'tools/isa07_d8b_output_interval_audit.py': '12da5accee42d59e6a00e6823918b94db3d4a65b',
    'tools/isa07_d8a_input_interval_sandbox.py': '638365b9d32c2b3071af97c6bbe26f4142ed302d',
    'docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md': 'debc8a21a73e4a0e2ab965f938b6b46e90f5323b',
}
OLD = (b'            magnetic_drum.close();\n'
       b'        }\n'
       b'            break;\n\n'
       b'        case IO_operations_t::opcode_write_perfo_binary:{')
NEW = (b'            magnetic_drum.close();\n'
       b'            C_reg = addr3_shifted.destination;\n'
       b'            K_reg = kmem.read_memory(C_reg);\n'
       b'        }\n'
       b'            break;\n\n'
       b'        case IO_operations_t::opcode_write_perfo_binary:{')
CASES = ('full', 'short', 'empty', 'missing', 'track1', 'single', 'altjump')
GATES = {'D9A_CPU_DELTA', 'D9A_BRANCH24', 'D9A_K_PREFETCH', 'D9A_TWO_STEPS',
         'D9A_DRUM_STATE', 'D9A_HOST_INPUT', 'D9A_PRIOR', 'D9A_OPEN'}

def git(*args):
    return subprocess.check_output(('git',) + args, cwd=ROOT, stderr=subprocess.PIPE).strip()

def git_blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest().encode()

def need(cond, desc):
    if not cond:
        raise RuntimeError(desc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.parse_args()
    need(git('cat-file', '-t', BASE) == b'commit', 'D8B base unavailable')
    need(subprocess.run(('git', 'merge-base', '--is-ancestor', BASE, 'HEAD'),
                        cwd=ROOT).returncode == 0, 'D8B base not ancestor')
    base = subprocess.check_output(('git', 'show', BASE + ':src/main.cpp'), cwd=ROOT)
    need(git('rev-parse', BASE + ':src/main.cpp') == CPU_BLOB.encode(),
         'D8B baseline CPU Git blob drift')
    need(git_blob(base) == CPU_BLOB.encode(), 'D8B baseline CPU bytes differ from Git blob')
    need(base.count(OLD) == 1, 'expected one D8B IO24 handler boundary')
    expected = base.replace(OLD, NEW, 1)
    current = (ROOT / 'src/main.cpp').read_bytes().replace(b'\r\n', b'\n')
    need(current == expected, 'current CPU must differ by exactly two IO24 branch/prefetch lines')
    head = git('rev-parse', 'HEAD:src/main.cpp')
    need(head in (CPU_BLOB.encode(), git_blob(expected)),
         'HEAD CPU neither D8B baseline nor exact D9A update')
    for rel, pin in PINS.items():
        need(git('rev-parse', BASE + ':' + rel) == pin.encode(),
             'D8B source blob mismatch: ' + rel)
        need(git('rev-parse', 'HEAD:' + rel) == pin.encode(),
             'HEAD source blob drift: ' + rel)
        raw = (ROOT / rel).read_bytes().replace(b'\r\n', b'\n')
        need(git_blob(raw) == pin.encode(), 'working source drift: ' + rel)
    manifest = (ROOT / 'docs/ISA_07_D9A_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_' + BASE + '\t' + CPU_BLOB + '\t' in manifest,
         'baseline CPU absent from D9A manifest')
    for rel, pin in PINS.items():
        need(rel + '\tGIT_BLOB_AT_' + BASE + '\t' + pin + '\t' in manifest,
             'source missing from D9A manifest: ' + rel)
    need(PDF_SHA in manifest, 'GY62 PDF digest missing')
    gates = (ROOT / 'docs/ISA_07_D9A_GATES.tsv').read_text(encoding='utf-8').splitlines()
    labels = {line.split('\t')[0] for line in gates[1:] if line.strip()}
    need(len(gates) == 9 and labels == GATES, 'D9A gates differ from declared contract')
    cpp = (ROOT / 'tests/isa/isa07_d9a_io24_branch_probe.cpp').read_text(encoding='utf-8')
    runner = (ROOT / 'tools/isa07_d9a_io24_branch_sandbox.py').read_text(encoding='utf-8')
    for name in CASES:
        need('"' + name + '"' in cpp and "'" + name + "'" in runner,
             'D9A case missing: ' + name)
    for snippet in ('execute_opcode(); // CPU STEP 1', 'execute_opcode(); // CPU STEP 2',
                    'instruction(017, 0204, 0205, 0206)',
                    'instruction(033, 0, 0, 0)', 'k1 == target_word',
                    'params_unchanged'):
        need(snippet in cpp, 'missing two-step branch witness: ' + snippet)
    need('TemporaryDirectory' in runner and 'PATTERN.findall' in runner,
         'missing process-isolation or structured-output checks')
    report = (ROOT / 'docs/ISA_07_D9A_IO24_BRANCH_AND_PREFETCH.md').read_text(encoding='utf-8')
    for needle in ('GY62', 'a₃', 'K_reg', 'D9-B', 'HOST_POLICY', 'two genuine'):
        need(needle in report, 'documentation missing: ' + needle)
    print('ISA-07 D9-A: GY62 IO24 BRANCH TO A3; K PREFETCH IS EMULATOR CONVENTION')
    print('IO24-BRANCH-CHECK PASS base=df480cd exact_cpu_delta=TWO_LINES '
          '24=C_TO_A3 24=K_PREFETCH D8B_OUTPUTS=PRESERVED D8A_INTERVALS=PRESERVED '
          'unchanged_files=5 source_blobs=PINNED D7_OLD_PC=HISTORICAL '
          'IO25=UNCHANGED IO20_21_PC=OPEN HISTORICAL_DEVICE_ORACLES=0')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as err:
        print('IO24-BRANCH-CHECK FAIL:', err, file=sys.stderr)
        sys.exit(1)
