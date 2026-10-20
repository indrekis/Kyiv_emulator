#!/usr/bin/env python3
"""D14-C1f read-only base, original blobs, file scope and content audit."""
import hashlib
import subprocess
import sys
from pathlib import Path

BASE = '297c4a113a5eee0b469625d7646e9c5eeac1b2e8'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'docs/ISA_07_D14C1C_TRACK_ADDRESS_REVIEW.md': '9466d4ae9452f5d6cb4d12a19376319e288aab10', 'docs/ISA_07_D14C1D_NK3000_TRACK_INCREMENT_REVIEW.md': 'f494093516d72e08e8990e3958cb452a4a675cc0', 'docs/ISA_07_D14C1E_REAL_CPU_NK3000_CHARACTERIZATION.md': 'cd4b4be16f4bcd26e30c4be5f34dd8019ec0fa50'}
DIGESTS = {'docs/ISA_07_D14C1F_PREPARATION_ADDRESS_SOURCE_REVIEW.md': 'ee5c67bfbec142f4d67dc4ecd944c428e94303315c696e18175c2c33d778b636', 'docs/ISA_07_D14C1F_DECISION_LEDGER.tsv': '9e79209aef5386cbd1578ce652b7bef190fb90dbefc367590a6d60f72ebf7ae4', 'tools/isa07_d14c1f_address_witness.py': '7feb63b4e1dc76490d76661272dbfb69722bd40ab9525fe0d1e3570b2d7f6323'}
EXPECTED = set(DIGESTS) | {'tools/isa07_d14c1f_audit.py'}

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def norm(data):
    data = data.replace(b'\r\n', b'\n')
    if b'\r' in data:
        raise ValueError('BARE_CR')
    return data

def sha(data):
    return hashlib.sha256(norm(data)).hexdigest()

def main():
    if '--self-test' in sys.argv:
        assert sha(b'A\n') == sha(b'A\r\n')
        try:
            norm(b'A\rB')
        except ValueError:
            pass
        else:
            raise AssertionError('BARE_CR_NOT_REJECTED')
        assert len(DIGESTS) == 3 and len(PINS) == 5
        print('D14C1F-SELFTEST PASS EOL=2/2 BARE_CR_REJECTED=1 CONTENT_SHA=3/3 PINS=5/5')
        return
    assert git('rev-parse','HEAD') == BASE, 'WRONG_BASELINE'
    assert not git('diff','--name-only'), 'TRACKED_MODIFICATIONS'
    assert not git('diff','--cached','--name-only'), 'STAGED_MODIFICATIONS'
    actual = set(git('ls-files','--others','--exclude-standard').splitlines())
    assert actual == EXPECTED, (actual,EXPECTED)
    for path,blob in PINS.items():
        assert git('rev-parse',f'HEAD:{path}') == blob, path
    for path,exp in DIGESTS.items():
        assert sha(Path(path).read_bytes()) == exp, path
    print('D14C1F-AUDIT PASS BASELINE=297c4a1 PINS=5/5 NEW_FILES=4/4 '
          'CONTENT_SHA=3/3 TRACKED_MUTATION=0 CPU_MUTATION=0 '
          'SOURCE_CONFLICTS=OPEN TRACK_MAPPING=OPEN HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')

if __name__=='__main__':
    main()
