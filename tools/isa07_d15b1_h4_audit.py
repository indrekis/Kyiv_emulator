#!/usr/bin/env python3
"""D15/B1-H4: evidence-only fresh visual cross-check audit."""
from __future__ import annotations
import argparse, hashlib, pathlib, subprocess, os

BASE="8857d97361fce920990c5ebf6b2584bd68dc58de"
DOC="docs/ISA_07_D15B1_H4_SECOND_PASS.md"
TSV="docs/ISA_07_D15B1_H4_SECOND_VISUAL_READ.tsv"
LED="docs/ISA_07_D15B1_H4_DECISION_LEDGER.tsv"
SELF="tools/isa07_d15b1_h4_audit.py"
README="examples/historical/gy1962/README.md"
K41="examples/historical/gy1962/au1_logic.k41"
PROV="examples/historical/gy1962/au1_logic_provenance.tsv"
ROM="mem/ROM.txt"
MOD=(README,)
NEW=(DOC,TSV,LED,SELF)
EXPECTED_K41="56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c"
PIN={
 README:"1736f406c612db527cf59c78d10b744ac41862bc",
 K41:"7349c96dcf38cde678515a35be56697d0e7931ad",
 PROV:"bbfea1c722f05a5fee26b0a4bccc323f18dc8f0d",
 ROM:"b39868f9697c82fd3b9ba9b7448b8313293970c1",
}

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode('utf8').rstrip('\n')

def sha(b):return hashlib.sha256(b).hexdigest()

def canonical(b):
    assert b'\r' not in b.replace(b'\r\n',b'\n'), 'BAD_EOL'
    return b.replace(b'\r\n',b'\n')

def evidence(t: bytes, k: bytes, prov: bytes):
    lines=canonical(t).decode('utf-8').splitlines()
    assert lines[0]=='address\topcode\tfield1\tfield2\tfield3\tprinted_page\tpdf_page\treader\tmethod', 'TSV_HEADER'
    assert len(lines)==40, ('TSV_RECORDS',len(lines)-1)
    a=[]
    for l in lines[1:]:
        addr,code,p1,p2,p3,page,pdf,reader,method=l.split('\t')
        assert len(addr)==4 and len(code)==2 and all(len(x)==4 for x in (p1,p2,p3)), 'WORD_WIDTH'
        assert all('0'<=c<='7' for c in (addr+code+p1+p2+p3)), 'NOT_OCTAL'
        exp_page,exp_pdf=('172','171') if addr in ('0002','0003') else ('173','172')
        assert (page,pdf,reader,method)==(exp_page,exp_pdf,'SAME_ASSISTANT','FRESH_VISUAL_READ'), 'PROVENANCE'
        a.append((addr,code+p1+p2+p3))
    assert len({x[0] for x in a})==39, 'DUPLICATE'
    expect_addrs=['0002','0003']+[format(i,'04o') for i in range(0o43,0o110)]
    assert [x[0] for x in a]==expect_addrs, 'ADDRESS_ORDER'
    assert sha(k)==EXPECTED_K41, 'IMAGE_SHA'
    expected=[]
    for l in canonical(k).decode('utf-8').splitlines():
        if l and l[0].isdigit():
            a1,r=l.split();assert len(r)==14, 'IMAGE_WIDTH'
            expected.append((a1,r))
    assert a==expected, 'FRESH_TRANSCRIPTION_MISMATCH'
    p=canonical(prov).decode('utf-8').splitlines()
    assert len(p)==40, 'ORIGINAL_PROVENANCE_COUNT'
    assert [x.split('\t')[0:2] for x in p[1:]]==[[addr,code]for addr,code in a], 'ORIGINAL_PROVENANCE_MISMATCH'
    assert all(x.split('\t')[6]=='VISUAL_SINGLE_PASS' for x in p[1:]), 'ALTERED_FIRST_PASS'
    return len(a)

def selftest():
    # Use bundled filesystem inputs to prove mutant rejection. No Python bytecode files.
    t=pathlib.Path(TSV).read_bytes();k=pathlib.Path(K41).read_bytes();p=pathlib.Path(PROV).read_bytes()
    assert evidence(t,k,p)==39
    # Single-octal-digit mutation is valid syntax but must be rejected by crosscheck.
    m=t.replace(b'0043\t14\t0000',b'0043\t15\t0000',1)
    assert m!=t
    try:evidence(m,k,p)
    except AssertionError:pass
    else:raise AssertionError('SOURCE_MUTANT_NOT_REJECTED')
    m2=k.replace(b'0043 14',b'0043 15',1)
    assert m2!=k
    try:evidence(t,m2,p)
    except AssertionError:pass
    else:raise AssertionError('K41_MUTANT_NOT_REJECTED')
    print('D15B1H4-AUDIT-SELFTEST PASS VISUAL_ROWS=39/39 MUTANTS_REJECTED=2/2')

def main():
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');args=p.parse_args()
    if args.self_test:selftest();return
    assert git('rev-parse','HEAD')==BASE, 'BASELINE'
    assert git('branch','--show-current')=='main', 'BRANCH'
    assert not git('rev-parse','--show-prefix'), 'ROOT'
    for path,blob in PIN.items():
        assert git('rev-parse','HEAD:'+path)==blob, ('SOURCE_PIN',path)
    for path in NEW+MOD:assert pathlib.Path(path).is_file(), ('MISSING',path)
    actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
    expected=sorted([' M '+x for x in MOD]+['?? '+x for x in NEW])
    assert actual==expected, ('STATUS',actual)
    assert evidence(pathlib.Path(TSV).read_bytes(),pathlib.Path(K41).read_bytes(),pathlib.Path(PROV).read_bytes())==39
    assert 'same assistant' in pathlib.Path(DOC).read_text().lower(), 'CLAIM_HONESTY'
    assert 'independent' in pathlib.Path(README).read_text().lower(), 'README_STATUS'
    # Make sure the README change is restricted to the two specific source-status updates.
    original=canonical(subprocess.check_output(['git','show','HEAD:'+README]))
    current=canonical(pathlib.Path(README).read_bytes())
    first=b'- `au1_logic_provenance.tsv` \xe2\x80\x94 address, source page, original notation and single visual verification for each record.'
    new=b'- `au1_logic_provenance.tsv` \xe2\x80\x94 original first-pass source record for each word.\n- A fresh visual cross-check against printed pp. 172\xe2\x80\x93173 matched all 39/39 words; see `docs/ISA_07_D15B1_H4_SECOND_PASS.md`.'
    old2=b'physical-hardware oracle. Independent second visual transcription is pending.'
    new2=b'physical-hardware oracle. The 39-word second visual read matched the source image\n(2026-10-24); it was performed by the same assistant, so independent\nverification by a second researcher remains outstanding.'
    assert original.count(first)==1 and original.count(old2)==1, 'README_ORIGINAL_ANCHORS'
    assert original.replace(first,new).replace(old2,new2)==current, 'README_SCOPE'
    assert git('diff','--name-only')==README, 'TRACKED_SCOPE'
    print('D15B1H4-AUDIT PASS BASELINE=8857d97 VISUAL_SECOND_READ=39/39 DIFFERENCES=0 MOD=1/1 NEW=4/4 CANONICAL_EXAMPLE_UNCHANGED=1 FIRST_PASS_UNCHANGED=1 CPU_MUTATION=0 HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')

if __name__=='__main__':
    try:main()
    except Exception as e:
        raise SystemExit('D15B1H4-AUDIT FAIL '+repr(e))
