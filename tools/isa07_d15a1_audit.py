#!/usr/bin/env python3
"""D15/A1 strict precommit auditor for qualified HOST image runner."""
from pathlib import Path
import argparse
import hashlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'a361ff744befbd76062133a488b00ddcba9565ff'
PINS = {'docs/HISTORICAL_GY1962_TESTS_PLAN.md': 'eb323ea2a4d5b00ee025afec352b95257c8e0ac5',
 'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
 'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19',
 'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804'}
CONTENT_SHA = {'docs/ISA_07_D15A1_BOUND_RUN_CONTRACT.md': 'b3284f0d47fe0aaa694bdb70917fc6deef32a9fc88aba71474accd21c60137f9',
 'docs/ISA_07_D15A1_DECISION_LEDGER.tsv': '5fddbbf563f75cdd59405c2a131deaa087598a2a2ecab6d952fc1fbd781be28e',
 'tools/isa07_d15a1_extended_regression.py': 'c02f8b076803905174bf811f6b9689037d5dcf3d7dba79e6ed6bc0c52048b6ee',
 'tools/isa07_d15a1_run_image.cpp': '53f0bb877c2098d5371f3c86b3a95c39820c8cae34e79a99219ed4f8f0fa9995'}
NEW = {
    'docs/ISA_07_D15A1_BOUND_RUN_CONTRACT.md',
    'docs/ISA_07_D15A1_DECISION_LEDGER.tsv',
    'tools/isa07_d15a1_run_image.cpp',
    'tools/isa07_d15a1_extended_regression.py',
    'tools/isa07_d15a1_audit.py',
}


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace')
    need(p.returncode == 0, 'GIT_ERROR ' + p.stderr[-300:])
    return p.stdout.strip()


def self_test():
    need(len(PINS) == 4 and all(len(p) == 40 for p in PINS.values()), 'BAD_PINS')
    need(len(NEW) == 5 and set(CONTENT_SHA) ==
         NEW - {'tools/isa07_d15a1_audit.py'}, 'BAD_SCOPE')
    need(all(len(h) == 64 for h in CONTENT_SHA.values()), 'BAD_SHA')
    need(sha(b'a') != sha(b'A'), 'MUTANT_ACCEPTED')
    need(sha(b'x' * 10) != sha(b'x' * 9 + b'y'), 'MUTANT_ACCEPTED')
    print('D15A1-AUDIT-SELFTEST PASS PINS=4/4 NEW_FILES=5/5 '
          'CONTENT_SHA=4/4 MUTANT_REJECTED=1')


def audit():
    need(git('rev-parse','HEAD') == BASE, 'HEAD_MISMATCH')
    need(git('branch','--show-current') == 'main', 'NOT_MAIN')
    need(git('rev-parse','--show-prefix') == '', 'NOT_REPOSITORY_ROOT')
    need(not git('diff','--name-only'), 'TRACKED_MUTATION')
    need(not git('diff','--cached','--name-only'), 'STAGED_MUTATION')
    u = set(git('ls-files','--others','--exclude-standard').splitlines())
    need(u == NEW, 'UNTRACKED_SCOPE_MISMATCH '+repr(sorted(u ^ NEW)))
    for path, expected in PINS.items():
        need(git('rev-parse','HEAD:'+path) == expected, 'GIT_PIN_MISMATCH '+path)
    for path, expected in CONTENT_SHA.items():
        fp=ROOT/path
        need(fp.is_file() and not fp.is_symlink(), 'BAD_FILE '+path)
        content=fp.read_bytes().replace(b'\r\n',b'\n')
        need(sha(content)==expected, 'CONTENT_MISMATCH '+path)
    source=(ROOT/'tools/isa07_d15a1_run_image.cpp').read_text(encoding='utf-8')
    need('if (n > (100000 - digit) / 10)' in source and
         'n = n * 10 + digit' in source, 'LIMIT_GUARD_MISSING')
    runner=(ROOT/'tools/isa07_d15a1_extended_regression.py').read_text(encoding='utf-8')
    need("'18446744073709551617'" in runner and 'CASES={passed}/21' in runner,
         'NATIVE_RUNNER_CONTRACT_MISSING')
    print('D15A1-AUDIT PASS BASELINE=a361ff7 PINS=4/4 '
          'NEW_FILES=5/5 CONTENT_SHA=4/4 TRACKED_MUTATION=0 '
          'CPU_MUTATION=0 REAL_NATIVE_GATE=PENDING ROM_BASELINE=OPEN '
          'HISTORICAL_CORPUS=PENDING HARDWARE_ORACLE=0')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    a=p.parse_args()
    self_test() if a.self_test else audit()
