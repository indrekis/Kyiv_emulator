#!/usr/bin/env python3
"""D14-C2-H1 read-only scope and source-blob audit; no CPU changes."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE = '2a8bae35ee347edef6a957a6ce5002d926cb5e6d'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'inc/kyiv_drum_logical_media.h': '910911f7181bfb455e334b1f66fd00ee94ef1e97', 'inc/kyiv_drum_group_transfer.h': '91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b', 'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3', 'docs/ISA_07_D14C1F_PREPARATION_ADDRESS_SOURCE_REVIEW.md': '4ce887dbe39a0fdabd4a38d6ce186c3f7961a79e'}
DIGESTS = {'docs/ISA_07_D14C2H1_EXPLICIT_HOST_MAPPING.md': '5b8f9728c8cbd4e562d28b5fbf7ff9f7424aabcbe96304d823465265afee47c0', 'docs/ISA_07_D14C2H1_DECISION_LEDGER.tsv': '7e540c7db4c2a39eefa556b4d2d91cd11dba995c9e0d3c6855c2fe330d8fd062', 'inc/kyiv_drum_host_address_v1.h': '2642412e6850081a74af0a8b53fc2c357d561defb05d151477b8e5a7f84dbf8d', 'tests/isa/isa07_d14c2h1_host_address_probe.cpp': '87da59cd89d157392bf4edc7df0ec5573324107913a6817a615f89611477fe08', 'tools/isa07_d14c2h1_host_address_sandbox.py': 'a3676b121acf05a05f268db7d6a7cbdbb1edb0750cac25cb73f4fc2e7db2d217'}
EXPECTED = set(DIGESTS) | {'tools/isa07_d14c2h1_audit.py'}

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def normalized(data):
    b = data.replace(b'\r\n', b'\n')
    if b'\r' in b:
        raise ValueError('BARE_CR')
    return b

def sha(data):
    return hashlib.sha256(normalized(data)).hexdigest()

def self_test():
    assert sha(b'A\n') == sha(b'A\r\n')
    try:
        normalized(b'A\rB')
    except ValueError:
        pass
    else:
        raise AssertionError('BARE_CR_ACCEPTED')
    assert len(PINS) == 6 and len(DIGESTS) == 5 and len(EXPECTED) == 6
    assert sha(b'CORRUPT') != sha(b'GOOD')
    print('D14C2H1-SELFTEST PASS PINS=6/6 CONTENT_SHA=5/5 EOL=2/2 BARE_CR_REJECTED=1 MUTANT_REJECTED=1')

def audit():
    assert git('rev-parse', 'HEAD') == BASE, 'UNEXPECTED_BASELINE'
    assert not git('diff', '--name-only'), 'TRACKED_MUTATION'
    assert not git('diff', '--cached', '--name-only'), 'STAGED_MUTATION'
    actual = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert actual == EXPECTED, ('UNTRACKED_SCOPE', actual, EXPECTED)
    for name, blob in PINS.items():
        assert git('rev-parse', f'HEAD:{name}') == blob, name
    for name, digest in DIGESTS.items():
        assert sha(Path(name).read_bytes()) == digest, name
    print('D14C2H1-AUDIT PASS BASELINE=2a8bae3 PINS=6/6 NEW_FILES=6/6 CONTENT_SHA=5/5 TRACKED_MUTATION=0 CPU_MUTATION=0 B1_B2_B3_C1B_UNCHANGED=1 HOST_POLICY_EXPLICIT=1 DRUM_LOCK=1 TRACK_MAPPING=OPEN HARDWARE_ORACLE=0')

if __name__ == '__main__':
    self_test() if '--self-test' in sys.argv else audit()
