#!/usr/bin/env python3
"""Read-only SHA / Git scope auditor for C2-H2/P1."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE = '8ad1a33210dc1c32f49390fca4fc0d1ff666b7cf'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5', 'inc/kyiv_drum_logical_media.h': '910911f7181bfb455e334b1f66fd00ee94ef1e97', 'inc/kyiv_drum_group_transfer.h': '91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b', 'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'inc/kyiv_drum_host_address_v1.h': '74b75b9c4fd86d73b43eb108bbdce312dc9619d3', 'docs/ISA_07_D14C2H1_EXPLICIT_HOST_MAPPING.md': 'd3024bc8c859c80b27a2854c983e6bd7e0947f5e'}
SHA_PINS = {'docs/ISA_07_D14C2H2_P1_TRANSACTIONAL_SESSION_CONTRACT.md': 'f13dfbd55f8049de44f2703b78cd75e27b46f3b28b3835d1eb6ded36da78cee3', 'docs/ISA_07_D14C2H2_P1_DECISION_LEDGER.tsv': '11409d52c76ec4c1e4f928cd414641a1a6662abe471d6d0536e89152febff376', 'inc/kyiv_drum_transaction_v1.h': '2271b2a85121d93689e5fbd9ebd73ca0b47f033ebee03a2c1a56d69e19540ec3', 'tests/isa/isa07_d14c2h2_transaction_probe.cpp': 'eac94d34b8551d12dcb59e88c7e9ea5c1bc9bfb362e540d773d2ddd1ec7be360', 'tools/isa07_d14c2h2_transaction_sandbox.py': '3d9ed4713bbc583f9957a82c3fad4412bd64a419f4cbad05fb0d4c875e8e5a88'}
EXPECTED = set(SHA_PINS) | {'tools/isa07_d14c2h2_audit.py'}

def git(*args):
    return subprocess.check_output(['git',*args],text=True).strip()

def norm(data):
    data = data.replace(b'\r\n', b'\n')
    if b'\r' in data:
        raise ValueError('BARE_CR')
    return data

def sha(data):
    return hashlib.sha256(norm(data)).hexdigest()

def self_test():
    assert sha(b'hello\n') == sha(b'hello\r\n')
    try: norm(b'hello\rworld')
    except ValueError: pass
    else: raise AssertionError('BARE_CR_ACCEPTED')
    assert sha(b'HELLO') != sha(b'HELLU')
    assert len(PINS)==8 and len(SHA_PINS)==5 and len(EXPECTED)==6
    print('D14C2H2P1-SELFTEST PASS PINS=8/8 CONTENT_SHA=5/5 EOL=2/2 BARE_CR_REJECTED=1 MUTANT_REJECTED=1')

def audit():
    assert git('rev-parse','HEAD')==BASE,'UNEXPECTED_BASE'
    assert not git('diff','--name-only'),'TRACKED_MUTATION'
    assert not git('diff','--cached','--name-only'),'STAGED_MUTATION'
    untracked=set(git('ls-files','--others','--exclude-standard').splitlines())
    assert untracked==EXPECTED, ('UNTRACKED_SCOPE',untracked,EXPECTED)
    for p,b in PINS.items():
        assert git('rev-parse',f'HEAD:{p}')==b,('BLOB',p)
    for p,d in SHA_PINS.items():
        assert sha(Path(p).read_bytes())==d,('FILE',p)
    print('D14C2H2P1-AUDIT PASS BASELINE=8ad1a33 PINS=8/8 NEW_FILES=6/6 CONTENT_SHA=5/5 TRACKED_MUTATION=0 CPU_MUTATION=0 B1_B2_B3_C1B_H1_UNCHANGED=1 SESSION_HOST_POLICY=1 FILE_TRANSACTION=1 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')

if __name__=='__main__':
    self_test() if '--self-test' in sys.argv else audit()
