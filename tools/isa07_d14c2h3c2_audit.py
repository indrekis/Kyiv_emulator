#!/usr/bin/env python3
"""H3/C2 immutable baseline, exact five new files and isolated instrumentation."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '9ff476b9cf4d5a632f4af2649ff46aca918d4377'
PINS = {
    'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804',
    'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19',
    'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
    'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3',
    'inc/kyiv_drum_transaction_v1.h': '1aab83a4735280df0cf4331191c5521dcc5ddcb4',
    'inc/kyiv_drum_provision_v1.h': '19f3a4e3f6a6f7dad744b83aeedcbf44361ceb12',
    'tools/isa07_d14c2h3b1_create.cpp': 'b9630c2fbebd2f4cb0594c9f4cc36a198553185f',
    'tools/isa07_d14c2h3b2_restart_sandbox.py': '59d92b31af1c02381232554eca21fc26e9eca2e5',
    'tools/isa07_d14c2h3c1_recovery_sandbox.py': '4bb96a176f862dd34d7909d552c4cd6aa445bd1e',
    'tests/isa/isa07_d14c2h3c1_failed_replace_probe.cpp': '8d957078f83812830fe743858b77a4c33dc682a9',
}
NEW = {
    'docs/ISA_07_D14C2H3C2_PROCESS_TERMINATION_CONTRACT.md',
    'docs/ISA_07_D14C2H3C2_DECISION_LEDGER.tsv',
    'tests/isa/isa07_d14c2h3c2_termination_probe.cpp',
    'tools/isa07_d14c2h3c2_termination_sandbox.py',
    'tools/isa07_d14c2h3c2_audit.py',
}
# Resolved during package production; 4 non-auditor source hashes.
CONTENT_SHA = {'docs/ISA_07_D14C2H3C2_DECISION_LEDGER.tsv': '7d91c9c5992c8c45d6c96205ceb914ff8deafd65cb1108b2b9a9e903bfb5a8c2',
 'docs/ISA_07_D14C2H3C2_PROCESS_TERMINATION_CONTRACT.md': '054a10da4eda2a06a908e05629166686f808799c81b33db555a7bd45ab5bba05',
 'tests/isa/isa07_d14c2h3c2_termination_probe.cpp': 'e29941e8454d11fb967cb7a90be2bbae223d89675003e721088651c0a32fd460',
 'tools/isa07_d14c2h3c2_termination_sandbox.py': '15ed5f7f4d1b1020ea5045f772c26d26e1e5d838555cc885ab3b0b024760dd69'}


def need(cond, message):
    if not cond:
        raise RuntimeError(message)


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    need(p.returncode == 0, 'GIT_COMMAND_FAILED: '+p.stderr[-500:])
    return p.stdout.strip()


def self_test():
    need(len(PINS)==10 and all(len(v)==40 for v in PINS.values()), 'BAD_PINS')
    need(len(NEW)==5 and set(CONTENT_SHA) ==
         NEW - {'tools/isa07_d14c2h3c2_audit.py'}, 'BAD_FILES')
    need(all(len(s)==64 for s in CONTENT_SHA.values()), 'BAD_HASHES')
    need(digest(b'A') != digest(b'a'), 'HASH_MUTANT_FAILED')
    need(not NEW.intersection(PINS) and all('..' not in Path(p).parts for p in NEW),
         'UNSAFE_FILE_SCOPE')
    print('D14C2H3C2-AUDIT-SELFTEST PASS PINS=10/10 NEW_FILES=5/5 '
          'CONTENT_SHA=4/4 MUTANT_REJECTED=1')


def audit():
    need(git('rev-parse','HEAD') == BASE, 'BASE_MISMATCH')
    need(git('branch','--show-current') == 'main', 'NOT_MAIN')
    need(not git('rev-parse', '--show-prefix'), 'NOT_REPO_ROOT')
    need(not git('diff','--name-only'), 'TRACKED_MUTATION')
    need(not git('diff','--cached','--name-only'), 'STAGED_MUTATION')
    others = set(git('ls-files','--others','--exclude-standard').splitlines())
    need(others == NEW, 'UNTRACKED_FILE_SET_MISMATCH: '+repr(sorted(others^NEW)))
    for path, sha in PINS.items():
        need(git('rev-parse','HEAD:'+path)==sha, 'SOURCE_PIN_CHANGED: '+path)
    for path, sha in CONTENT_SHA.items():
        need(digest((ROOT/path).read_bytes())==sha, 'NEW_SOURCE_SHA: '+path)
    runner = (ROOT/'tools/isa07_d14c2h3c2_termination_sandbox.py').read_text(
        encoding='utf-8')
    probe = (ROOT/'tests/isa/isa07_d14c2h3c2_termination_probe.cpp').read_text(
        encoding='utf-8')
    need(all(q in runner for q in ('proc.kill()', 'instrument(',
         'PARTIAL_TEMP', 'PRE_RENAME', 'POST_RENAME', 'canonical(')),
         'RUNNER_BEHAVIOR_CHANGED')
    need(all(q in probe for q in ('ISOLATION_MARKER_REQUIRED',
         'KYIVEMU_D14C2H3C2_TEST_COPY', 's.write_words', 'crash.kdr')),
         'PROBE_BEHAVIOR_CHANGED')
    print('D14C2H3C2-AUDIT PASS BASELINE=9ff476b PINS=10/10 '
          'NEW_FILES=5/5 CONTENT_SHA=4/4 TRACKED_MUTATION=0 '
          'CPU_MUTATION=0 B3_P1_H3C1_PRESERVED=1 '
          'PRIVATE_INSTRUMENTATION=1 REAL_NATIVE_GATE=PENDING '
          'CRASH_DURABILITY=OPEN CONCURRENT_WRITERS=OPEN '
          'HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    self_test() if a.self_test else audit()


if __name__=='__main__':
    main()
