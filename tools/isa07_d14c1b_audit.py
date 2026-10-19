#!/usr/bin/env python3
"""Read-only baseline and file-scope audit for D14-C1b."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE = '33126885a38626265521e715bc3282b216c1a1cb'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5', 'inc/kyiv_drum_logical_media.h': '910911f7181bfb455e334b1f66fd00ee94ef1e97', 'inc/kyiv_drum_group_transfer.h': '91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b', 'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3'}
DIGESTS = {'inc/kyiv_drum_prepare_decode.h': '1cd134ed4fac04cf9aa4beabf58d4d794e7878ff4b527511f75e5e1ea8e64378', 'tests/isa/isa07_d14c1b_preparation_probe.cpp': 'b555798e7c19d8a534ee5ca00c2a8751cb315bcdb12e0d115163e826a1b518c2', 'tools/isa07_d14c1b_preparation_sandbox.py': '9b9ed64c7defd4cd7062b16c70c913e65dedb83b7b77a241735537258b03c445', 'docs/ISA_07_D14C1B_PARTIAL_PREPARATION_DECODE.md': '80fc8b2f1b85e329d81b68a4eb0a8c025328d0420fc995a6a40820c606045d19'}

EXPECTED = set(DIGESTS) | {
    "tools/isa07_d14c1b_audit.py"
}

def git(*args):
    return subprocess.check_output(
        ["git", *args], text=True
    ).strip()

def normalized(data):
    data = data.replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("BARE_CR")
    return data

def sha(data):
    return hashlib.sha256(normalized(data)).hexdigest()

def main():
    if "--self-test" in sys.argv:
        assert sha(b"hello\n") == sha(b"hello\r\n")
        try:
            normalized(b"hello\rthere")
        except ValueError:
            pass
        else:
            raise AssertionError("BARE_CR_ACCEPTED")
        print(
            "D14C1B-SELFTEST PASS "
            "EOL=2/2 BARE_CR_REJECTED=1"
        )
        return

    assert git("rev-parse", "HEAD") == BASE
    assert not git("diff", "--name-only")
    assert not git("diff", "--cached", "--name-only")

    untracked = set(
        git("ls-files", "--others", "--exclude-standard").splitlines()
    )
    assert untracked == EXPECTED, (untracked, EXPECTED)

    for name, blob in PINS.items():
        assert git("rev-parse", f"HEAD:{name}") == blob, name

    for name, digest in DIGESTS.items():
        assert sha(Path(name).read_bytes()) == digest, name

    print(
        "D14C1B-AUDIT PASS BASELINE=3312688 "
        "BLOB_PINS=5/5 NEW_FILES=5/5 CONTENT_SHA=4/4 "
        "TRACKED_MUTATION=0 CPU_MUTATION=0 "
        "RAW_PREPARATION=1 TRACK_MAPPING=OPEN "
        "HARDWARE_ORACLE=0"
    )

if __name__ == "__main__":
    main()
