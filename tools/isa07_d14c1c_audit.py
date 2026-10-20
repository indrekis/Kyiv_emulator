from pathlib import Path
import hashlib, subprocess
BASE = '0160c33abcb7a9565df481d8d781985917409056'
PINS = {'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv_drum_prepare_decode.h': '3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b', 'docs/ISA_07_D14A_MAGNETIC_DRUM_SOURCE_REVIEW.md': '63b158fb3589bdbfec1d7c13d255486b6772235a', 'docs/ISA_07_D14C1B_PARTIAL_PREPARATION_DECODE.md': '1e6c3a0cb0b7a3bfd0ebda8c43bc09712ede90e2'}
DIGESTS = {'docs/ISA_07_D14C1C_TRACK_ADDRESS_REVIEW.md': '7e4dcaa613c02b0db4b3be1abc2cfb4c1f41a58a8283276e2d66ca81421c9ac5', 'docs/ISA_07_D14C1C_EVIDENCE_LEDGER.tsv': 'e367ee945be60324eac7cf5f0b44b8c48ceffb4dd41835fd8026bc9f0bbf839e', 'tools/isa07_d14c1c_source_witness.py': 'ba434cddc7506522801dec0a2caa9d90b49277f24e6da270bcfeb730e95bb2d6'}
def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()
def sha(data):
    data = data.replace(b"\r\n", b"\n")
    assert b"\r" not in data
    return hashlib.sha256(data).hexdigest()
assert git("rev-parse", "HEAD") == BASE
assert not git("diff", "--name-only")
assert not git("diff", "--cached", "--name-only")
expected = set(DIGESTS) | {"tools/isa07_d14c1c_audit.py"}
actual = set(git("ls-files", "--others", "--exclude-standard").splitlines())
assert actual == expected, (actual, expected)
for path, blob in PINS.items():
    assert git("rev-parse", f"HEAD:{path}") == blob
for path, digest in DIGESTS.items():
    assert sha(Path(path).read_bytes()) == digest, path
print("D14C1C-AUDIT PASS BASELINE=0160c33 "
      "PINS=4/4 NEW_FILES=4/4 CONTENT_SHA=3/3 "
      "TRACKED_MUTATION=0 CPU_MUTATION=0 "
      "TRACK_MAPPING=OPEN HARDWARE_ORACLE=0")
