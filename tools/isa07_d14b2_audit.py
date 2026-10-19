#!/usr/bin/env python3
"""Read-only D14-B2 precommit audit for new group-transfer API only."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='31a3c3c26326dcc0ee05ea601300182ab7fd3dcd'
PINS={
    'src/main.cpp':'145cbf8725405b52c12c3c75fa8f3141f2671dc1',
    'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
    'inc/kyiv_drum_logical_media.h':'910911f7181bfb455e334b1f66fd00ee94ef1e97',
    'docs/ISA_07_D14A_SHARED_DRUM_MODEL_CONTRACT.md':'9096fc7bddfa59052c539b065c1e0b9ee0062b5d',
    'tests/isa/isa07_d14b1_logical_media_probe.cpp':'2d3d00677f0058d61d112688ef78fd4eb16369de',
}
NEW=(
    'docs/ISA_07_D14B2_GROUP_TRANSFERS.md',
    'inc/kyiv_drum_group_transfer.h',
    'tests/isa/isa07_d14b2_group_transfer_probe.cpp',
    'tools/isa07_d14b2_group_transfer_sandbox.py',
    'tools/isa07_d14b2_audit.py',
)
CONTENT_SHA={'docs/ISA_07_D14B2_GROUP_TRANSFERS.md': 'fe62948e9d5e52fa8ff918643ebe4b9a3bc07f6f9f5d2fa6078c0a50aa967b48', 'inc/kyiv_drum_group_transfer.h': 'fa609ca5d50f1f763a3f73d6a17844809fa01162fc7cc1344181357169dbc1fb', 'tests/isa/isa07_d14b2_group_transfer_probe.cpp': '57856bc3f6ca30477ccae4847dd68d7d6419911d71de9c7a97095436af548976', 'tools/isa07_d14b2_group_transfer_sandbox.py': '373d68816695e947f4ced025347c9369945b6497e468ecb515bb231c2889debf'}  # Exact LF-normalized bytes; auditor itself excluded.

def require(p,msg):
    if not p:raise RuntimeError(msg)

def norm(data:bytes)->bytes:
    require(b'\r' not in data.replace(b'\r\n',b''),'INVALID_BARE_CR')
    return data.replace(b'\r\n',b'\n')

def git(*args):
    return subprocess.check_output(['git',*args], cwd=ROOT, stderr=subprocess.PIPE)

def static_checks():
    require(len(NEW)==5 and len(CONTENT_SHA)==4 and len(PINS)==5,'MATRIX_LENGTH')
    require(set(CONTENT_SHA)==set(NEW[:-1]),'MATRIX_COVERAGE')
    for name,sha in CONTENT_SHA.items():
        path=ROOT/name
        require(path.is_file(),'MISSING '+name)
        require(hashlib.sha256(norm(path.read_bytes())).hexdigest()==sha,'CONTENT_SHA '+name)
    header=norm((ROOT/'inc/kyiv_drum_group_transfer.h').read_bytes()).decode()
    require(header.count('write_group(')==1 and header.count('read_group(')==1 and
            'validate_span(' in header and 'END_OF_DRUM' in header and
            'UNWRITTEN' in header and 'INVALID_WORD' in header,
            'GROUP_HEADER_CONTRACT')
    runner=norm((ROOT/'tools/isa07_d14b2_group_transfer_sandbox.py').read_bytes()).decode()
    require('FIXED = [' in runner and 'INDEPENDENT_PYTHON=1' in runner,
            'INDEPENDENT_CASE_MATRIX')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    try:
        static_checks()
        if a.self_test:
            require(norm(b'a\r\nb\n')==b'a\nb\n','MIXED_EOL')
            try:norm(b'a\rb')
            except RuntimeError: pass
            else:raise RuntimeError('BARE_CR_NOT_REJECTED')
            print('D14B2-SELFTEST PASS PINS=5/5 NEW_FILES=5/5 '
                  'CONTENT_SHA=4/4 LF_CRLF_MIXED=1 INVALID_CR_REJECTED=1 '
                  'GROUP_API=1 CPU_MUTATION=0 GIT_BASE_CHECK=DEFERRED_TO_AUDIT')
            return 0
        require(git('rev-parse','--show-prefix').strip()==b'','RUN_AT_REPO_ROOT')
        require(git('rev-parse','HEAD').decode().strip()==BASE,'UNEXPECTED_HEAD')
        require(not git('diff','--name-only').strip(),'TRACKED_MODIFICATIONS')
        require(not git('diff','--cached','--name-only').strip(),'STAGED_MODIFICATIONS')
        existing=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
        require(existing==set(NEW),'UNTRACKED_SCOPE '+repr(existing^set(NEW)))
        for path,blob in PINS.items():
            require(git('rev-parse','HEAD:'+path).decode().strip()==blob,'BLOB_PIN '+path)
            require(norm((ROOT/path).read_bytes())==norm(git('show','HEAD:'+path)),
                    'BASE_CONTENT_MUTATED '+path)
        print('D14B2-AUDIT PASS BASELINE=31a3c3c PINS=5/5 NEW_FILES=5/5 '
              'CONTENT_SHA=4/4 TRACKED_MUTATION=0 CPU_MUTATION=0 '
              'B1_UNCHANGED=1 GROUP_API=1 EOL_PORTABLE=1 '
              'PERSISTENCE=DEFERRED HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError,RuntimeError,ValueError,subprocess.CalledProcessError) as ex:
        print('D14B2-AUDIT FAIL',ex,file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
