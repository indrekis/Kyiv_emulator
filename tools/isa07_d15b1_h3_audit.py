#!/usr/bin/env python3
"""D15/B1-H3 exact source gate; no native result is claimed here."""
import hashlib
import subprocess
import sys
from pathlib import Path

# Importing the sibling transform must not generate an untracked __pycache__
# while the exact Git scope audit is executing.
sys.dont_write_bytecode = True
import isa07_d15b1_h3_transform as change

ROOT=Path(__file__).resolve().parents[1]
BASE='6f20450b656374e8c9ad199d3d2ae1e09424d297'
BLOBS={
 'src/main.cpp':'79604ea237e090e99f9da980c9b00567ae7bd804',
 'README.md':'b837a7a89189883ef19179cbf834a696e866e9a8',
 'documentation/documentation.txt':'5ee5c263544b7cf83a7b753638b24213e97ac876',
 'docs/isa_opcode_registry.csv':'1830a4d95c5ee6eb69923196cf6fb7709682230c',
 'docs/ISA_06_D1_LOGIC_AUDIT.md':'beb3546ae2bb9bda9a13dc2e165d0f0b31bd7f75',
 'docs/ISA_06_D2_LOGIC_SEQUENCE.md':'0d5ec027fc9bace0a5f67e893d938690759c3101',
 'examples/historical/gy1962/README.md':'92c528fc619dbb175256b862a068b1d0b9d5135c',
 'tests/isa/isa06_d1_logic_probe.cpp':'237717586b8c9b8d7ceba9a54c2005370de63e53',
 'tests/isa/isa06_d2_logic_sequence_probe.cpp':'a0ed3260e831ee19c6d83346094e19d8aff7dffb',
 'mem/ROM.txt':'b39868f9697c82fd3b9ba9b7448b8313293970c1',
 'examples/historical/gy1962/au1_logic.k41':'7349c96dcf38cde678515a35be56697d0e7931ad',
 'examples/historical/gy1962/au1_logic_provenance.tsv':'bbfea1c722f05a5fee26b0a4bccc323f18dc8f0d',
 'tools/isa07_d15b1_h2_opcode17_probe.py':'366c1661fe72e37acd255a445b1bf4ead2650e61',
}
NEW=(
 'docs/ISA_07_D15B1_H3_OPCODE17_CORRECTION.md',
 'docs/ISA_07_D15B1_H3_DECISION_LEDGER.tsv',
 'tools/isa07_d15b1_h3_transform.py',
 'tools/isa07_d15b1_h3_audit.py',
 'tools/isa07_d15b1_h3_regression.py',
)
# Manifest pins are filled by the authoring step. The auditor itself is excluded.
NEW_SHA={'docs/ISA_07_D15B1_H3_DECISION_LEDGER.tsv': '0ec246bd9d4b04ba4441ffa760a247cf0c26666212aa6f7d34be4f5bc3de826f', 'docs/ISA_07_D15B1_H3_OPCODE17_CORRECTION.md': 'f2f9e72b030230c5bc052b14b42a953f594f8e01e71ba666084c59048f936808', 'tools/isa07_d15b1_h3_regression.py': '74b7bb7712af3878d1496c38b7264d40ccd510053711e70252dde393de7c35fd', 'tools/isa07_d15b1_h3_transform.py': '41025cf457943d0dc592d36deb72163158445df9bcdc9ec50a507a7cfab42187'}

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

D1_PATH='tests/isa/isa06_d1_logic_probe.cpp'
D1_CANONICAL_SHA256='a3b1487ac86d25dc487f539a867249b2d649e8ea7043590b7437538d4e9fc86e'

def checked_blob(path,expected):
    actual=git('rev-parse','HEAD:'+path).decode().strip()
    if actual!=expected:
        raise AssertionError(('PIN',path,'expected='+expected,'actual='+actual))
    if path==D1_PATH:
        pinned=git('show','HEAD:'+path)
        digest=hashlib.sha256(pinned.replace(b'\r\n',b'\n')).hexdigest()
        if digest!=D1_CANONICAL_SHA256:
            raise AssertionError(('D1_CONTENT_PIN',path,'expected_sha256='+D1_CANONICAL_SHA256,'actual_sha256='+digest))
        print('D15B1H3-D1-EXACT-PIN PASS GIT_BLOB='+actual+' SHA256='+digest)

def canon(b):
    return b.replace(b'\r\n',b'\n')

def audit():
    assert git('rev-parse','HEAD').decode().strip()==BASE,'HEAD_PIN'
    assert git('branch','--show-current').decode().strip()=='main','BRANCH_MAIN'
    assert git('rev-parse','--show-prefix').strip()==b'','NOT_ROOT'
    assert git('diff','--cached','--name-only').strip()==b'','STAGED_CHANGES'
    assert set(change.MODIFIED)==set(BLOBS)-{
        'mem/ROM.txt','examples/historical/gy1962/au1_logic.k41',
        'examples/historical/gy1962/au1_logic_provenance.tsv',
        'tools/isa07_d15b1_h2_opcode17_probe.py'},'MODIFIED_SET'
    for p,sha in BLOBS.items():
        checked_blob(p,sha)
    for p in change.MODIFIED:
        historic=git('show','HEAD:'+p)
        desired=change.transform_bytes(p,canon(historic))
        actual=(ROOT/p).read_bytes()
        assert canon(actual)==canon(desired),('UNEXPECTED_MODIFICATION',p)
    expected=set(' M '+p for p in change.MODIFIED)|set('?? '+p for p in NEW)
    observed=set(git('status','--porcelain=v1','--untracked-files=all').decode().splitlines())
    assert observed==expected,('STATUS',sorted(observed^expected))
    assert set(NEW_SHA)==set(NEW)-{'tools/isa07_d15b1_h3_audit.py'},'NEW_SHA_SET'
    for p, sha in NEW_SHA.items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,('NEW_SHA',p)
    assert hashlib.sha256((ROOT/'mem/ROM.txt').read_bytes()).hexdigest()==\
        'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38', 'ROM_SHA'
    assert hashlib.sha256((ROOT/'examples/historical/gy1962/au1_logic.k41').read_bytes()).hexdigest()==\
        '56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c', 'HIST_SHA'
    assert git('diff','--name-only').decode().splitlines()==sorted(change.MODIFIED), 'TRACKED_DIFF_SET'
    cpu=canon((ROOT/change.CPU).read_bytes())
    assert cpu.count(b'(~(source_1 ^ source_2)) & mask41')==1,'CPU_XNOR'
    assert cpu.count(b'case logic_operations_t::opcode_log_xor:{')==1,'CASE_COUNT'
    print('D15B1H3-AUDIT PASS BASELINE=6f20450 MOD=9/9 NEW=5/5 '
          'SOURCE_PINS=13/13 CONTENT_SHA=4/4 DOCUMENTATION_UPDATED=1 '
          'ISA06_D1_D2_UPDATED=1 CPU_OPCODE17_ONLY=1 '
          'ROM_IMMUTABLE=1 HISTORICAL_IMAGE_IMMUTABLE=1 '
          'H2_SOURCE_EVIDENCE_PRESERVED=1 NATIVE_GATE=PENDING HARDWARE_ORACLE=0')

def selftest():
    old=b'case logic_operations_t::opcode_log_xor:{\n            kmem.write_memory(addr3_shifted.destination, kmem.read_memory(addr3_shifted.source_1) ^ kmem.read_memory(addr3_shifted.source_2));\n}'
    out=change.transform_bytes(change.CPU,old)
    assert b'(~(source_1 ^ source_2)) & mask41' in out
    assert change.transform_bytes(change.CPU,old.replace(b'\n',b'\r\n')).count(b'\r\n')==out.count(b'\n')
    try:
        change.transform_bytes(change.CPU,old.replace(b'write_memory(',b'write_RAM(',1))
    except AssertionError:pass
    else:raise AssertionError('MUTANT_ACCEPTED')
    mask=(1<<41)-1
    for a,b in [(0,0),(0,1),(1,0),(1,1),(1<<40,0),(mask,mask),(mask,0)]:
        result=~(a^b)&mask
        assert result^((a^b)&mask)==mask
    assert len(change.MODIFIED)==9 and len(NEW)==5
    assert sys.dont_write_bytecode, 'BYTECODE_NOT_DISABLED'
    print('D15B1H3-AUDIT-SELFTEST PASS NO_PYC=1 MASK41=1 SIGN_BIT=1 CRLF=1 '
          'MUTANTS_REJECTED=1 SOURCE_TRANSFORM=1 MOD=9/9')

if __name__=='__main__':
    try:
        if sys.argv[1:]==['--self-test']:selftest()
        elif not sys.argv[1:]:audit()
        else:raise AssertionError('USAGE: [--self-test]')
    except Exception as exc:
        print('D15B1H3-AUDIT FAIL',exc,file=sys.stderr)
        sys.exit(1)
