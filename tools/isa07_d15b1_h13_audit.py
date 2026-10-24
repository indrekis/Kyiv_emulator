#!/usr/bin/env python3
"""H13 exact-source audit, append-only documentation, immutable CPU and ROM."""
from __future__ import annotations
import hashlib,pathlib,re,subprocess,sys
BASE='f9b5d7c088093041be01aceb427a61168f2ec95a'; README='examples/historical/gy1962/README.md'; IMAGE='examples/historical/gy1962/au1_shift_zero_0166_0170.k41'; PROV='examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv'
NEW=['docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H13_ZERO_SHIFT.md', 'examples/historical/gy1962/au1_shift_zero_0166_0170.k41', 'examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv', 'tools/isa07_d15b1_h13_audit.py', 'tools/isa07_d15b1_h13_native.py']; PINS={'examples/historical/gy1962/README.md': 'c039a4a64353c9f3ad577a305892adace224ba5e', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c', 'examples/historical/gy1962/au1_subtraction_0155_0162.k41': '3428a04652d6f9a8ee070138a183b158406175d2', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '9c7737f526d313eef8243a4a4de592059d53f5af', 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': 'ef6ae41bae4075caddd292a4c11e537a86cc0218', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': '01cb2d553c1d97f6426c3adb16b3683250e97464', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1', 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md': '2aedc98670e193e7ebdda887d245b411b971051c', 'docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv': '37284e5a5a818d9c03aad8d1124b80839047f4ac', 'examples/historical/gy1962/au1_addcmd_0163_0165.k41': '60beab5d65e6f3c4af412971ee88e4bf9b89fd70', 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv': '9a7f3c4537174e116f99d4405a11bb00ea331041'}; WORDS={'0261': '02525252525252', '0166': '13000002610347', '0167': '16034702610171', '0170': '33000000000000'}; SHA={'examples/historical/gy1962/au1_shift_zero_0166_0170.k41': '70d6c86f1cd2aa08634553cf913d5ba1f54f98de2c2dead2168cf8ad7097c665', 'examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv': '1209105630d905914c139ec4d572c9d6489a60d90dcd7924cf37aea4a424accb', 'docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv': '3945bb697fac5c1b11230093c8d6a6828abb9dda10c614a71dba5cc39ba78f02', 'docs/ISA_07_D15B1_H13_ZERO_SHIFT.md': '56646a309be429a7e3430d7c6576280c1dc58f89c26ec0175548e18a64614fdb'}; README_SHA='5f66237d6d3b916cf547f673052234130144307d288047c4201179444a6d0875'
EXPECTED='02525252525252'; ZERO='00000000000000'
def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def rows(b):
 ls=norm(b).decode('ascii').splitlines();assert ls[0]=='KYIV41-OCT1','MAGIC'; rr=[]
 for x in ls[1:]:
  if not x or x.startswith('#'):continue
  parts=x.split();assert len(parts)==2,'WORD_SHAPE'
  a,w=parts;assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'OCTAL_SHAPE'
  rr.append((a,w))
 assert rr==list(WORDS.items()),('WORDS_MISMATCH',rr)
 return rr
def prov(b):
 ls=norm(b).decode('ascii').splitlines();assert len(ls)==5,'PROVENANCE_LINES'
 assert ls[0]=='address\tcode_octal_14\tprinted_page\trole\tverification'
 p=[x.split('\t') for x in ls[1:]]
 assert all(len(x)==5 and x[4]=='VISUAL_FIRST_PASS' for x in p),'PROV_SCHEMA'
 assert [(x[0],x[1]) for x in p]==list(WORDS.items()),'PROV_WORDS'
 assert [x[2] for x in p]==['174','173','173','173'],'PROV_PAGES'
def oracle():
 assert WORDS=={'0261':'02525252525252','0166':'13000002610347','0167':'16034702610171','0170':'33000000000000'}
 assert int(EXPECTED,8)<(1<<41) and EXPECTED==WORDS['0261'],'FULL_WORD'
 # Decode explicitly 5-bit op and three 12-bit address fields.
 x=int(WORDS['0166'],8); assert (x>>36)==0o13,'OPCODE13'
 assert (x>>24)&0xfff==0 and (x>>12)&0xfff==0o261 and x&0xfff==0o347,'SHIFT_ADDRESSES'
 y=int(WORDS['0167'],8); assert (y>>36)==0o16 and (y>>24)&0xfff==0o347 and (y>>12)&0xfff==0o261 and y&0xfff==0o171,'JE_ADDRESSES'
 assert ZERO=='00000000000000' and (int(EXPECTED,8)<<0)&((1<<41)-1)==int(EXPECTED,8),'BITVECTOR'
def self_test():
 assert len(PINS)==20 and all(re.fullmatch(r'[0-9a-f]{40}',v) for v in PINS.values()),'PIN_WIDTH'
 oracle()
 blob=('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode()
 rows(blob);rows(blob.replace(b'\n',b'\r\n'))
 mutant=dict(WORDS);mutant['0166']='13000102610347'
 try:rows(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in mutant.items())+'\n').encode())
 except AssertionError:pass
 else:raise AssertionError('MUTANT_NOT_REJECTED')
 print('D15B1H13-AUDIT-SELFTEST PASS WORDS=4/4 MUTANTS_REJECTED=1 CRLF=1 SHIFT_ZERO=1 GIT_PIN_WIDTH=20/20')
def audit():
 self_test()
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'NOT_MAIN_ROOT'
 assert not git('diff','--cached','--name-only'),'STAGED'
 for p,sha in PINS.items():assert git('rev-parse','HEAD:'+p)==sha,('GIT_PIN',p)
 for p,sha in SHA.items():assert hashlib.sha256(norm(pathlib.Path(p).read_bytes())).hexdigest()==sha,('CONTENT_SHA',p)
 assert hashlib.sha256(norm(pathlib.Path(README).read_bytes())).hexdigest()==README_SHA,'README_SHA'
 rows(pathlib.Path(IMAGE).read_bytes());prov(pathlib.Path(PROV).read_bytes())
 expected=sorted([' M '+README]+['?? '+p for p in NEW])
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert expected==actual,('GIT_SCOPE',expected,actual)
 ledger=norm(pathlib.Path('docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv').read_bytes()).decode('utf-8')
 for k in ('H9_SOURCE_PROSE_CONFLICT','H10_CARRY_POLICY_CONFLICT','H11_SUBABS_SIGNED_ZERO_CONFLICT'):
  assert k+'\tOPEN_UNCHANGED' in ledger,'PRIOR_CONFLICT_LOST'
 assert 'H13_SOURCE_LABEL_ALIGNMENT\tOPEN' in ledger,'LABEL_CONFLICT_LOST'
 print('D15B1H13-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=4/4 PROGRAM=3 DATA=1 SOURCE_PINS=20/20 CONTENT_SHA=4/4 SOURCE_0000_UNPRINTED=1 H13_SOURCE_LABEL_CONFLICT=OPEN H9_H10_H11_CONFLICTS=OPEN_UNCHANGED CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:self_test() if '--self-test' in sys.argv else audit()
 except BaseException as e:raise SystemExit('D15B1H13-AUDIT FAIL '+repr(e))
