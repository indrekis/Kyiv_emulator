#!/usr/bin/env python3
"""D14-C2-H3/B2 strict precommit scope/source auditor. Never modify repo."""
import argparse
import hashlib
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = 'cf4357fe70806ed83a22e9dccd97c57bc96cff93'
PINS = {
    'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19',
    'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804',
    'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
    'inc/kyiv_drum_provision_v1.h': '19f3a4e3f6a6f7dad744b83aeedcbf44361ceb12',
    'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3',
    'inc/kyiv_drum_cli_v1.h': '3925ec9503b92c614a43f877686a47fc6884a2b6',
    'inc/kyiv_drum_transaction_v1.h': '1aab83a4735280df0cf4331191c5521dcc5ddcb4',
    'tools/isa07_d14c2h3b1_create.cpp': 'b9630c2fbebd2f4cb0594c9f4cc36a198553185f',
}
NEW = {
    'docs/ISA_07_D14C2H3B2_CROSS_PROCESS_RESTART_CONTRACT.md',
    'docs/ISA_07_D14C2H3B2_DECISION_LEDGER.tsv',
    'tools/isa07_d14c2h3b2_audit.py',
    'tools/isa07_d14c2h3b2_restart_sandbox.py',
}
# Replaced during packaging; pure SHA256 of three non-auditor new files.
CONTENT_SHA = {'docs/ISA_07_D14C2H3B2_CROSS_PROCESS_RESTART_CONTRACT.md': '785a5c0b5e1afaed367f85cb08dc2ed1a74864bb798e08f034480d5184aade91',
 'docs/ISA_07_D14C2H3B2_DECISION_LEDGER.tsv': '9d0e74e8fd2110f8d45475863fdd87b174b848a05f94a120d28008da66f86a45',
 'tools/isa07_d14c2h3b2_restart_sandbox.py': '9301974f1905c7de62457367d8370476eced4f8c213444bbc60dc0a3c130923f'}


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def git(*argv):
    p = subprocess.run(['git', *argv], cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, check=False)
    need(p.returncode == 0, 'GIT_ERROR: ' + p.stderr[-250:])
    return p.stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def self_test():
    need(len(PINS) == 8 and all(len(x) == 40 for x in PINS.values()),
         'INVALID_PINS')
    need(len(NEW) == 4 and len(CONTENT_SHA) == 3, 'INVALID_FILE_SCOPE')
    need(set(CONTENT_SHA) == NEW - {'tools/isa07_d14c2h3b2_audit.py'},
         'INVALID_CONTENT_SCOPE')
    need(digest_bytes(b'x') != digest_bytes(b'X'), 'HASH_MUTANT_NOT_REJECTED')
    need('src/main.cpp' not in NEW and all('..' not in pathlib.PurePosixPath(x).parts
                                           for x in NEW), 'INVALID_NEW_PATH')
    print('D14C2H3B2-AUDIT-SELFTEST PASS PINS=8/8 NEW_FILES=4/4 '
          'CONTENT_SHA=3/3 MUTANT_REJECTED=1')


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    need(git('rev-parse', 'HEAD') == BASE, 'BASE_CHANGED')
    need(git('branch', '--show-current') == 'main', 'NOT_MAIN')
    need(git('diff', '--name-only') == '', 'TRACKED_MUTATION')
    need(git('diff', '--cached', '--name-only') == '', 'STAGED_MUTATION')
    actual = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    need(actual == NEW, 'UNEXPECTED_UNTRACKED: '+repr(sorted(actual ^ NEW)))
    for path, expected in PINS.items():
        need(git('rev-parse', 'HEAD:' + path) == expected,
             'PIN_BLOB_CHANGED: '+path)
    for path, sha in CONTENT_SHA.items():
        need(digest(ROOT / path) == sha, 'NEW_CONTENT_CHANGED: '+path)
    source = (ROOT / 'tools/isa07_d14c2h3b2_restart_sandbox.py').read_text(
        encoding='utf-8')
    need('fresh' in source.lower() and 'canonical(' in source and
         'orr' in source and '--experimental-drum' in source,
         'RUNNER_CONTRACT_CHANGED')
    print('D14C2H3B2-AUDIT PASS BASELINE=cf4357f PINS=8/8 '
          'NEW_FILES=4/4 CONTENT_SHA=3/3 TRACKED_MUTATION=0 '
          'CPU_MUTATION=0 PRODUCTION_CLI_UNCHANGED=1 '
          'B1_B2_B3_UNCHANGED=1 CREATE_NEW_ONLY_UNCHANGED=1 '
          'REAL_RESTART_GATE=PENDING HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--self-test', action='store_true')
    args = a.parse_args()
    if args.self_test:
        self_test()
    else:
        audit()


if __name__ == '__main__':
    main()
