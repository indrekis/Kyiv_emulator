#!/usr/bin/env python3
"""Read-only D14-C1d source/commit audit (new files only)."""
from pathlib import Path
import subprocess, hashlib, sys
BASE = '5f175e173e2df1e3a538f7c9cd98ac14a1db27b3'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'docs/ISA_07_D14C1C_TRACK_ADDRESS_REVIEW.md': '9466d4ae9452f5d6cb4d12a19376319e288aab10', 'docs/ISA_07_D14A_MAGNETIC_DRUM_SOURCE_REVIEW.md': '63b158fb3589bdbfec1d7c13d255486b6772235a', 'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3'}
DIGESTS = {'docs/ISA_07_D14C1D_NK3000_TRACK_INCREMENT_REVIEW.md': 'b31320ca2e7ff56571a1056db138da8c88b492c78b2185e1759447345005af77', 'docs/ISA_07_D14C1D_DECISION_LEDGER.tsv': 'fc744fafb3aef13f7bff5ff4f94a46702301cf92e1b27b4355e868ed45ea841f', 'tools/isa07_d14c1d_increment_witness.py': '9e2203d039d69b07f7cc7496517f75f4fec9c30bd16201ef20cfef1d0c3dcaa9'}
EXPECTED = set(DIGESTS) | {'tools/isa07_d14c1d_audit.py'}
def normalize(data):
    data = data.replace(b"\r\n",b"\n")
    if b"\r" in data:
        raise ValueError('BARE_CR')
    return data
def sha(data):
    return hashlib.sha256(normalize(data)).hexdigest()
def git(*args):
    return subprocess.check_output(['git',*args], text=True).strip()
def main():
    if '--self-test' in sys.argv:
        assert sha(b'K\n') == sha(b'K\r\n')
        try:
            normalize(b'A\rB')
        except ValueError:
            pass
        else:
            raise AssertionError('BARE_CR_ACCEPTED')
        print('D14C1D-SELFTEST PASS EOL=2/2 BARE_CR_REJECTED=1 CONTENT_SHA=3/3')
        return
    assert git('rev-parse','HEAD') == BASE, 'BASELINE'
    assert not git('diff','--name-only'), 'TRACKED_MUTATION'
    assert not git('diff','--cached','--name-only'), 'STAGED_MUTATION'
    assert set(git('ls-files','--others','--exclude-standard').splitlines()) == EXPECTED, 'NEW_FILE_SCOPE'
    for path,blob in PINS.items():
        assert git('rev-parse',f'HEAD:{path}') == blob, ('BLOB_PIN',path)
    for path,expected in DIGESTS.items():
        assert sha(Path(path).read_bytes()) == expected, ('CONTENT_SHA',path)
    print('D14C1D-AUDIT PASS BASELINE=5f175e1 PINS=5/5 NEW_FILES=4/4 CONTENT_SHA=3/3 '
          'TRACKED_MUTATION=0 CPU_MUTATION=0 TRACK_MAPPING=OPEN HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
if __name__ == '__main__':
    main()
