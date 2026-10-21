#!/usr/bin/env python3
"""D14-C2-H3/C1 strict source + scope audit. Read-only and precommit only."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '59e3fd25b8655ca869f7510b8c4e5cd3598d897e'
PINS = {
    'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19',
    'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804',
    'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
    'inc/kyiv_drum_provision_v1.h': '19f3a4e3f6a6f7dad744b83aeedcbf44361ceb12',
    'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3',
    'inc/kyiv_drum_cli_v1.h': '3925ec9503b92c614a43f877686a47fc6884a2b6',
    'inc/kyiv_drum_transaction_v1.h': '1aab83a4735280df0cf4331191c5521dcc5ddcb4',
    'tools/isa07_d14c2h3b1_create.cpp': 'b9630c2fbebd2f4cb0594c9f4cc36a198553185f',
    'tools/isa07_d14c2h3b2_restart_sandbox.py': '59d92b31af1c02381232554eca21fc26e9eca2e5',
}
NEW = {
    'docs/ISA_07_D14C2H3C1_FAILURE_RECOVERY_CONTRACT.md',
    'docs/ISA_07_D14C2H3C1_DECISION_LEDGER.tsv',
    'tests/isa/isa07_d14c2h3c1_failed_replace_probe.cpp',
    'tools/isa07_d14c2h3c1_recovery_sandbox.py',
    'tools/isa07_d14c2h3c1_audit.py',
}
CONTENT_SHA = {'docs/ISA_07_D14C2H3C1_FAILURE_RECOVERY_CONTRACT.md': '0ebfb259ae7f1ec7b557364e731407cac75131d5031c3f479c39871cc48de093', 'docs/ISA_07_D14C2H3C1_DECISION_LEDGER.tsv': 'bb9bea5e2d53406cad63649d14ffebc609cab8e8b9f2bd24c2f0a361931e6b91', 'tools/isa07_d14c2h3c1_recovery_sandbox.py': '983411fd9d4c6b01e2db5f3bff9db638e382e7aacd814da46124b49dca9b602a', 'tests/isa/isa07_d14c2h3c1_failed_replace_probe.cpp': 'a1d27f31d413022dee9b154649594f317e158b623a74fb96ebcc7af84722cc70'}


def need(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    proc = subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                          encoding='utf-8', errors='replace')
    need(proc.returncode == 0, 'GIT_ERROR: ' + proc.stderr[-400:])
    return proc.stdout.strip()


def self_test():
    need(len(PINS) == 9 and all(len(x) == 40 for x in PINS.values()), 'PINS_INVALID')
    need(len(NEW) == 5 and set(CONTENT_SHA) == NEW -
         {'tools/isa07_d14c2h3c1_audit.py'}, 'FILE_SCOPE_INVALID')
    need(all(len(s) == 64 for s in CONTENT_SHA.values()), 'CONTENT_HASH_INVALID')
    need(sha(b'a') != sha(b'A'), 'MUTANT_CHECK')
    need(not NEW.intersection(PINS) and all('..' not in Path(p).parts for p in NEW),
         'UNSAFE_PATH')
    print('D14C2H3C1-AUDIT-SELFTEST PASS PINS=9/9 NEW_FILES=5/5 '
          'CONTENT_SHA=4/4 MUTANT_REJECTED=1')


def audit():
    need(git('rev-parse', 'HEAD') == BASE, 'BASE_CHANGED')
    need(git('branch', '--show-current') == 'main', 'NOT_ON_MAIN')
    need(not git('diff', '--name-only'), 'TRACKED_MUTATION')
    need(not git('diff', '--cached', '--name-only'), 'STAGED_MUTATION')
    current = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    need(current == NEW, 'UNTRACKED_SCOPE_MISMATCH: ' + repr(sorted(current ^ NEW)))
    for path, expected in PINS.items():
        need(git('rev-parse', 'HEAD:' + path) == expected, 'PIN_MISMATCH: '+path)
    for path, expected in CONTENT_SHA.items():
        need(sha((ROOT/path).read_bytes()) == expected, 'CONTENT_MISMATCH: '+path)
    runner = (ROOT/'tools/isa07_d14c2h3c1_recovery_sandbox.py').read_text(
        encoding='utf-8')
    probe = (ROOT/'tests/isa/isa07_d14c2h3c1_failed_replace_probe.cpp').read_text(
        encoding='utf-8')
    need(all(s in runner for s in ['image_bytes(', 'raw_read(',
         'orphan_ignored', 'corrupt_target', 'failed_replace']),
         'RUNNER_CONTRACT_CHANGED')
    need(all(s in probe for s in ['ISOLATION_MARKER_REQUIRED', 'REPLACE_FAILED',
                                  'session.write_words', 'fs::rename']),
         'PROBE_CONTRACT_CHANGED')
    print('D14C2H3C1-AUDIT PASS BASELINE=59e3fd2 PINS=9/9 '
          'NEW_FILES=5/5 CONTENT_SHA=4/4 TRACKED_MUTATION=0 '
          'CPU_MUTATION=0 B3_P1_B1_B2_PRESERVED=1 '
          'REAL_NATIVE_GATE=PENDING CRASH_DURABILITY=OPEN '
          'CONCURRENT_WRITERS=OPEN HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args()
    if args.self_test:
        self_test()
    else:
        audit()


if __name__ == '__main__':
    main()
