#!/usr/bin/env python3
"""Read-only D14-C1e pinned source/byte audit (LF/CRLF safe)."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE = "dbd045dab0b40dd834e21fb1ed3c4c8f75478331"
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5', 'inc/kyiv_nk_panel.h': '6ebcb09ae55df7ee7eb37b0e315e5b87bef39b14', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'docs/ISA_07_D14C1D_NK3000_TRACK_INCREMENT_REVIEW.md': 'f494093516d72e08e8990e3958cb452a4a675cc0', 'tools/isa07_d14c1d_increment_witness.py': '9baa0c997bee499193017c474940b037a238d8c4'}
HASHES = {'docs/ISA_07_D14C1E_REAL_CPU_NK3000_CHARACTERIZATION.md': '715989cd12105bcf79dca39e6ebe171fbfda215f6b8b291e1af8b4edc2c1ec49', 'docs/ISA_07_D14C1E_DECISION_LEDGER.tsv': 'bb44e232cbb6042a222d72b11799991286742259fad4ddc0fafb1f582bd9223e', 'tests/isa/isa07_d14c1e_nk3000_cpu_probe.cpp': '04149c118b9794a780aa69e5bf8e596929331f992c169bbe0220b3301e3574cd', 'tools/isa07_d14c1e_nk3000_cpu_sandbox.py': 'f69397f25beb8521dbeaaf27ea7cd9b2bbc0ae3b05de5f55397c9959d78bb49c'}
EXPECTED = set(HASHES) | {"tools/isa07_d14c1e_audit.py"}


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def normalized(data):
    data = data.replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("BARE_CR")
    return data


def sha(data):
    return hashlib.sha256(normalized(data)).hexdigest()


def main():
    if "--self-test" in sys.argv:
        assert sha(b"ok\n") == sha(b"ok\r\n")
        assert sha(b"ok\n") != sha(b"bad\n")
        try:
            normalized(b"bad\rtext")
        except ValueError:
            pass
        else:
            raise AssertionError("BARE_CR_ACCEPTED")
        print("D14C1E-SELFTEST PASS EOL=2/2 BARE_CR_REJECTED=1 MUTANT_REJECTED=1")
        return
    assert git("rev-parse", "HEAD") == BASE, "UNEXPECTED_HEAD"
    assert not git("diff", "--name-only"), "TRACKED_MODIFICATION"
    assert not git("diff", "--cached", "--name-only"), "STAGED_MODIFICATION"
    others = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    assert others == EXPECTED, ("NEW_FILE_SCOPE", others, EXPECTED)
    for p, blob in PINS.items():
        assert git("rev-parse", f"HEAD:{p}") == blob, p
    for p, expect in HASHES.items():
        assert sha(Path(p).read_bytes()) == expect, p
    print("D14C1E-AUDIT PASS BASELINE=dbd045d PINS=6/6 "
          "NEW_FILES=5/5 CONTENT_SHA=4/4 TRACKED_MUTATION=0 "
          "CPU_MUTATION=0 C1B_UNCHANGED=1 EOL_PORTABLE=1 "
          "REAL_CPU_GATE=PENDING HARDWARE_ORACLE=0")


if __name__ == "__main__":
    main()
