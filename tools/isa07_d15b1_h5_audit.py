#!/usr/bin/env python3
"""D15/B1-H5 source-first 9-word historical-image audit."""
from __future__ import annotations
import hashlib, pathlib, subprocess, argparse
BASE='29011c27a5ae64afe75442de13cafea95871d42c'
README='examples/historical/gy1962/README.md'
IMG='examples/historical/gy1962/au1_addition_0110_0115.k41'
PROV='examples/historical/gy1962/au1_addition_0110_0115_provenance.tsv'
DOC='docs/ISA_07_D15B1_H5_FIRST_TWO_ADDITIONS.md'
LED='docs/ISA_07_D15B1_H5_DECISION_LEDGER.tsv'
RUN='tools/isa07_d15b1_h5_native.py'
AUD='tools/isa07_d15b1_h5_audit.py'
NEW=[IMG,PROV,DOC,LED,RUN,AUD]
PINS={'examples/historical/gy1962/README.md': 'e12b7712aa800b91d681fee9c8e83a6d05cb5d90', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_logic_provenance.tsv': 'bbfea1c722f05a5fee26b0a4bccc323f18dc8f0d', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'}
EXPECTED_SHA={'examples/historical/gy1962/au1_addition_0110_0115.k41': '661c2cf6fcd948c2bb6fca22d7a49c02364b7616bb305f39fe6df480506ff585', 'examples/historical/gy1962/au1_addition_0110_0115_provenance.tsv': 'd0c30b02598357ec6f264dc1d88cc577aa2581729500bee9d5f49238f68603cd', 'docs/ISA_07_D15B1_H5_FIRST_TWO_ADDITIONS.md': '57e4eda84f6641d10e9cc10b1592ab06ef9c508fdbdadec58994069b51c73c5a', 'docs/ISA_07_D15B1_H5_DECISION_LEDGER.tsv': '21c39b11492d512916970a409b4a01828e85d603bf7c424d3a054f1f647451ca', 'tools/isa07_d15b1_h5_native.py': 'f28354e9e7b2c814bc16ef10c932f687f24cd50ff919bde913c10dfe48d15930'}
EXPECTED_WORDS=[
    ('0002', '12', '5252', '5252', '5252', 172, 'INPUT', 'positive code 12(52)'),
    ('0003', '25', '2525', '2525', '2525', 172, 'INPUT', 'negative code (25)'),
    ('0004', '05', '2525', '2525', '2525', 172, 'INPUT', 'positive code 05(25)'),
    ('0110', '01', '0004', '0004', '0347', 173, 'ADD', '05(25)+05(25)=12(52)'),
    ('0111', '16', '0347', '0002', '0113', 173, 'COMPARE', 'branch to next check'),
    ('0112', '33', '0000', '0000', '0000', 173, 'FAIL_STOP', 'first failure stop'),
    ('0113', '01', '0003', '0002', '0347', 173, 'ADD', '(25)+12(52)=05(25)'),
    ('0114', '16', '0347', '0004', '0116', 173, 'COMPARE', 'branch to next group'),
    ('0115', '33', '0000', '0000', '0000', 173, 'FAIL_STOP', 'second failure stop'),
]

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def canonical(b):
    assert b'\r' not in b.replace(b'\r\n',b'\n'),'ILLEGAL_EOL'
    return b.replace(b'\r\n',b'\n')
def check_words(raw,provenance):
    raw=canonical(raw)
    assert hashlib.sha256(raw).hexdigest()==EXPECTED_SHA[IMG], 'IMAGE_SHA'
    lines=raw.decode('utf8').splitlines()
    assert lines[0]=='KYIV41-OCT1'
    pairs=[]
    for line in lines[1:]:
        if not line or line.startswith('#'):continue
        addr,word=line.split()
        assert len(addr)==4 and len(word)==14 and all(ch in '01234567' for ch in addr+word),'BAD_WORD'
        pairs.append((addr,word))
    expected=[(x[0],''.join(x[1:5]))for x in EXPECTED_WORDS]
    assert pairs==expected,('WORDS',pairs)
    rows=canonical(provenance).decode('utf8').splitlines()
    assert len(rows)==10, 'PROVENANCE_ROWS'
    assert rows[0].split('\t')==['address','opcode','field1','field2','field3','printed_page','pdf_page','role','first_pass_status','historical_expectation'],'HEADER'
    table=[]
    for line in rows[1:]:
        fields=line.split('\t');assert len(fields)==10, 'FIELDS'
        addr,op,a,b,c,p,pdf,role,state,_=fields
        assert state=='VISUAL_SINGLE_PASS'
        assert (p,pdf)==(('172','171') if addr.startswith('000') else ('173','172'))
        table.append((addr,op,a,b,c))
    assert table==[tuple(x[:5]) for x in EXPECTED_WORDS], 'PROVENANCE_VALUES'
    return len(pairs)

def selftest():
    b=pathlib.Path(IMG).read_bytes();p=pathlib.Path(PROV).read_bytes()
    assert check_words(b,p)==9
    try:check_words(b.replace(b'0110 01000400040347',b'0110 02000400040347'),p)
    except AssertionError:pass
    else:raise AssertionError('MUTANT_NOT_REJECTED')
    assert canonical(b'abc\r\ndef\r\n')==b'abc\ndef\n'
    print('D15B1H5-AUDIT-SELFTEST PASS WORDS=9/9 MUTANT_REJECTED=1 CRLF=1')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');o=ap.parse_args()
    if o.self_test:selftest();return
    assert git('rev-parse','HEAD')==BASE, 'BASELINE'
    assert git('branch','--show-current')=='main', 'BRANCH'
    assert not git('rev-parse','--show-prefix'), 'NOT_ROOT'
    for p,v in PINS.items():assert git('rev-parse','HEAD:'+p)==v,('BLOB_PIN',p)
    actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
    expected=sorted([' M '+README]+['?? '+p for p in NEW])
    assert actual==expected,('STATUS',actual)
    for p,v in EXPECTED_SHA.items():
        assert hashlib.sha256(canonical(pathlib.Path(p).read_bytes())).hexdigest()==v,('CONTENT_SHA',p)
    assert check_words(pathlib.Path(IMG).read_bytes(),pathlib.Path(PROV).read_bytes())==9
    r=canonical(pathlib.Path(README).read_bytes())
    original=canonical(subprocess.check_output(['git','show','HEAD:'+README]))
    addon=canonical(bytes.fromhex('0a23232041552074657374206e6f2e20312c206164646974696f6e3a2066697273742074776f20636865636b7320284431352f42312d4835290a0a2d20606175315f6164646974696f6e5f303131305f303131352e6b34316020e280942073656c662d636f6e7461696e6564202a2a392d776f72642a2a206d6f6465726e20484f535420696d6167653a0a2020746872656520736f75726365206461746120776f7264732060303030322e2e303030346020287072696e74656420702e20313732292c20666f6c6c6f776564206279207468650a202074776f206f726967696e616c206164646974696f6e2f636f6d706172652f53544f5020747269706c6574732060303131302e2e303131356020287072696e74656420702e20313733292e0a2d20606175315f6164646974696f6e5f303131305f303131355f70726f76656e616e63652e7473766020e28094206f6e65202a2a76697375616c2066697273742d706173732a2a20736f757263650a20207265636f72642070657220776f72642e20416e6f7468657220726561646572277320696e646570656e64656e7420766572696669636174696f6e2072656d61696e732070656e64696e672e0a2d20456163682067726f75702069732065786563757465642066726f6d20697473206f776e20656e74727920666f72202a2a74776f20696e737472756374696f6e73206f6e6c792a2a3a0a20206030313130602073686f756c642072656163682060433d303131336020776974682065787065637465642060303334373d3132353235323532353235323532602c207768696c650a20206030313133602073686f756c642072656163682060433d303131366020776974682065787065637465642060303334373d3035323532353235323532353235602e0a2020546865736520617265202a2a686973746f726963616c2070726564696374696f6e732c206e6f74206f62736572766564207061737365732a2a20756e74696c207468652048350a20206e61746976652072756e6e657220686173206578656375746564207375636365737366756c6c792e0a2d20546865206e65787420736f7572636520696e737472756374696f6e20603031313660206973202a2a6e6f742a2a20696e636c756465642e205468697320626f756e64656420746573740a20206d757374206e6f7420616476616e636520696e746f2069742e20546865206f726967696e616c206661696c7572652053544f50732072656d61696e20766572626174696d2e0a2d2060707974686f6e202d4220746f6f6c732f69736130375f64313562315f68355f6e61746976652e7079202d2d636c692d6578652074656d706b7969762f6b796976656d752e657865202d2d74696d656f7574203230600a202072756e7320626f746820656e74727920706f696e74732066726f6d2074776f20776f726b696e67206469726563746f7269657320616e6420707265736572766573206f62736572766174696f6e732e0a0a5365652060646f63732f4953415f30375f44313542315f48355f46495253545f54574f5f4144444954494f4e532e6d646020666f722073636f706520616e6420736f7572636520756e6365727461696e746965732e0a'))
    assert r==original+addon,'README_SCOPE'
    assert git('diff','--name-only')==README,'TRACKED_SCOPE'
    print('D15B1H5-AUDIT PASS BASELINE=29011c2 MOD=1/1 NEW=6/6 WORDS=9/9 PROGRAM=6 DATA=3 SOURCE_VISUAL_FIRST_PASS=1 HISTORICAL_PREDICTIONS=2 CPU_MUTATION=0 ROM_IMMUTABLE=1 LOGIC_EXAMPLE_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
    try:main()
    except BaseException as e:raise SystemExit('D15B1H5-AUDIT FAIL '+repr(e))
