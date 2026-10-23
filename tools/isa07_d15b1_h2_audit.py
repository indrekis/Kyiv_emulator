#!/usr/bin/env python3
"""D15/B1-H2 — exact-scope source evidence & opcode17 probe audit."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='b2e498bfa7715c645708c7c143a80deeb5ce65e9'
OLD_BLOBS={
 'src/main.cpp':'79604ea237e090e99f9da980c9b00567ae7bd804',
 'inc/kyiv.h':'501180b5e81a30fb1b49db4a4079bc82604161d7',
 'mem/ROM.txt':'b39868f9697c82fd3b9ba9b7448b8313293970c1',
 'examples/historical/gy1962/au1_logic.k41':'7349c96dcf38cde678515a35be56697d0e7931ad',
 'examples/historical/gy1962/au1_logic_provenance.tsv':'bbfea1c722f05a5fee26b0a4bccc323f18dc8f0d',
 'tools/isa07_d15b1_h1_native.py':'0c8d02824303d3967c6757f76f3ed921175f36a3',
}
NEW=(
 'docs/ISA_07_D15B1_H2_OPCODE17_SOURCE_ADJUDICATION.md',
 'docs/ISA_07_D15B1_H2_DECISION_LEDGER.tsv',
 'tools/isa07_d15b1_h2_audit.py',
 'tools/isa07_d15b1_h2_opcode17_probe.py',
)
# All additional source hashes are canonical LF.  This audit script is self-excluded.
PAYLOAD_SHA={
    'docs/ISA_07_D15B1_H2_OPCODE17_SOURCE_ADJUDICATION.md':'ac66a4e9229dedc9ff37cbaa352dd19ea7b3d7e3684d1733b90b27be829c8689',
    'docs/ISA_07_D15B1_H2_DECISION_LEDGER.tsv':'de390c3a92b6ea90d6091447349c35fc5d4639d0389d0956b04edf05a074f5cd',
    'tools/isa07_d15b1_h2_opcode17_probe.py':'9532f106db1e5b83f1bd77519a856557de8cee40e11e87bc885665d6636710a4',
}
EXPECTED_EXCERPT=b'kmem.write_memory(addr3_shifted.destination, kmem.read_memory(addr3_shifted.source_1) ^ kmem.read_memory(addr3_shifted.source_2));'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def canonical(b):
    return b.replace(b'\r\n',b'\n')


def verify_semantics(src):
    assert src.count(EXPECTED_EXCERPT)==1, 'BASELINE_XOR_ANCHOR'
    # Exactly one opcode17 dispatch occurs; no H2 mutation permitted.
    assert src.count(b'case logic_operations_t::opcode_log_xor:')==1,'OP17_CASE'


def verify_evidence(doc,ledger):
    doc=doc.decode('utf-8')
    ledger=ledger.decode('utf-8')
    for part in ('printed p. 11','printed pp. 172','printed p. 18',
                 '00→0, 01→1, 10→1, 11→0',
                 '00→1, 01→0, 10→0, 11→1',
                 'XNOR_PREFERRED','HARDWARE_ORACLE=0'):
        assert part in doc or part in ledger, ('EVIDENCE_LOST',part)
    assert '1962_op17_text\tXOR' in ledger
    assert '1962_op17_test\tXNOR' in ledger
    assert '1964_op17_text\tXNOR' in ledger
    assert 'historical_program\tIMMUTABLE' in ledger


def audit():
    assert git('rev-parse','HEAD').decode().strip()==BASE, 'BASELINE'
    assert git('branch','--show-current').decode().strip()=='main', 'BRANCH'
    assert git('rev-parse','--show-prefix').strip()==b'', 'NOT_ROOT'
    assert git('diff','--name-only')==b'', 'TRACKED_DIFF'
    assert git('diff','--cached','--name-only')==b'', 'STAGED_DIFF'
    for path,sha in OLD_BLOBS.items():
        actual=git('rev-parse','HEAD:'+path).decode().strip()
        assert actual==sha, ('SOURCE_PIN',path,actual)
    verify_semantics(git('show','HEAD:src/main.cpp'))
    old_image=git('show','HEAD:examples/historical/gy1962/au1_logic.k41')
    assert hashlib.sha256(old_image).hexdigest()=='56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c','H1_IMAGE_SHA'
    assert b'0073 17000200030347' in old_image and b'0101 17000200020347' in old_image,'H1_ANCHORS'
    expected=sorted('?? '+p for p in NEW)
    status=sorted(git('status','--porcelain=v1','--untracked-files=all').decode().splitlines())
    assert status==expected,('WORKTREE_SCOPE',status)
    for p in NEW:
        assert (ROOT/p).is_file(), ('NEW_MISSING',p)
    for p,sha in PAYLOAD_SHA.items():
        assert hashlib.sha256(canonical((ROOT/p).read_bytes())).hexdigest()==sha, ('CONTENT_SHA',p)
    verify_evidence(canonical((ROOT/NEW[0]).read_bytes()),canonical((ROOT/NEW[1]).read_bytes()))
    probe=canonical((ROOT/NEW[3]).read_bytes())
    assert b"choices=('xor','xnor')" in probe and b'1 << 41' in probe and b'--watch' in probe,'PROBE_CONTRACT'
    print('D15B1H2-AUDIT PASS BASELINE=b2e498b SOURCE_PINS=6/6 NEW=4/4 '
          'CONTENT_SHA=3/3 PRIMARY_SOURCES=3/3 HISTORICAL_IMAGE_IMMUTABLE=1 '
          'SOURCE_ADJUDICATION=XNOR_PREFERRED GY1962_DESCRIPTION_CONFLICT=OPEN '
          'CPU_MUTATION=0 HARDWARE_ORACLE=0 REAL_NATIVE_GATE=PENDING')


def selftest():
    sample=b'case logic_operations_t::opcode_log_xor:{\n'+EXPECTED_EXCERPT+b'\n}'
    verify_semantics(sample)
    try:
        verify_semantics(sample.replace(b' ^ ',b' | '))
    except AssertionError: pass
    else: raise AssertionError('MUTANT_ADMITTED_OPCODE')
    doc=canonical((ROOT/NEW[0]).read_bytes())
    ledger=canonical((ROOT/NEW[1]).read_bytes())
    verify_evidence(doc,ledger)
    try:
        verify_evidence(doc,ledger.replace(b'1964_op17_text\tXNOR',b'1964_op17_text\tXOR '))
    except AssertionError: pass
    else: raise AssertionError('MUTANT_ADMITTED_SOURCE')
    assert hashlib.sha256(canonical(b'A\r\nB\r\n')).digest()==hashlib.sha256(b'A\nB\n').digest()
    print('D15B1H2-AUDIT-SELFTEST PASS SOURCE_MUTANT_REJECTED=1 OPCODE_MUTANT_REJECTED=1 CRLF=1')

if __name__=='__main__':
    try:
        if sys.argv[1:]==['--self-test']:selftest()
        elif len(sys.argv)==1:audit()
        else:raise AssertionError('USAGE [--self-test]')
    except Exception as e:
        print('D15B1H2-AUDIT FAIL',e,file=sys.stderr)
        sys.exit(1)
