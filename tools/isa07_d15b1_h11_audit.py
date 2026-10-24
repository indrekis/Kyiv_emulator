#!/usr/bin/env python3
"""Fail-closed D15/B1-H11 source and Git-scope auditor, not a native CPU proof."""
from __future__ import annotations
import hashlib,pathlib,re,subprocess,sys
BASE='e5df6e27d2bccd7f0bf97fab3f9ec41a4c7d6abf';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_subtraction_0155_0162.k41';PROV='examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv';NEW=['docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md', 'examples/historical/gy1962/au1_subtraction_0155_0162.k41', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv', 'tools/isa07_d15b1_h11_audit.py', 'tools/isa07_d15b1_h11_native.py'];PINS={'examples/historical/gy1962/README.md': 'fa0c3333cc62ff9e4af5b07184142e580940bf1c', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c', 'examples/historical/gy1962/au1_addcyc_0151_0154_provenance.tsv': '505c47d9635545f2717a4cf7cf592127eaa1d66e', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310', 'docs/ISA_07_D15B1_H10_DECISION_LEDGER.tsv': '144e2a73f8d923b59c5fb098def8e2b4c14af3ed', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'};WORDS={'0002': '12525252525252', '0003': '25252525252525', '0155': '02000200020347', '0156': '16034730260160', '0157': '33000000000000', '0160': '06000300030347', '0161': '16034730260163', '0162': '33000000000000'}
SHA={'examples/historical/gy1962/au1_subtraction_0155_0162.k41': 'fd339a4302279a9c010df4cc43f66127fb59c9a10ab8d7f67935cc6e0d8a8740', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '18913e608de3411ee789fdc843c6936d544c679a850741919355e4942097d944', 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': '49377004b7a68576db28c492fab1687c57132297cfa9c5c3ff6d785078753b4a', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': 'f1a90afb5b8acf7235848a447517e8fdec72e54370a5e8a4224bd9030e1e1209'};README_SHA='5a14f051fbc7b33c473e51062dca65e1a4d7d5beab225fd90df75fc67f937f62'
def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def rows(blob):
 lines=norm(blob).decode('ascii').splitlines();assert lines[0]=='KYIV41-OCT1','MAGIC'
 pairs=[]
 for s in lines[1:]:
  if not s or s.startswith('#'):continue
  cols=s.split();assert len(cols)==2,'COLUMNS'
  a,w=cols;assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'OCTAL'
  pairs.append((a,w))
 assert pairs==list(WORDS.items()),'WORDS_MISMATCH'
 return pairs
def provenance(blob):
 lines=norm(blob).decode('ascii').splitlines();assert len(lines)==9,'PROVENANCE_LINES'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\trole\tverification','PROVENANCE_HEADER'
 parsed=[line.split('\t') for line in lines[1:]]
 assert all(len(v)==5 and v[4]=='VISUAL_FIRST_PASS' for v in parsed)
 assert [(v[0],v[1]) for v in parsed]==list(WORDS.items()),'PROVENANCE_VALUES'
 assert all(v[2]==('172' if v[0] in ('0002','0003') else '173') for v in parsed),'PRINTED_PAGE'
def oracle():
 assert int(WORDS['0002'],8)!=0 and int(WORDS['0003'],8)!=0
 assert int(WORDS['0155'],8)>>36==0o2 and int(WORDS['0160'],8)>>36==0o6
 assert WORDS['0156']=='16034730260160' and WORDS['0161']=='16034730260163'
 assert WORDS['0157']==WORDS['0162']=='33000000000000'
 assert int('20000000000000',8)==1<<40
 # 2/6 equal-operand subtraction = mathematical zero; sign is historical code claim.
def self_test():
 assert all(re.fullmatch(r'[0-9a-f]{40}',v) for v in PINS.values()),'INVALID_GIT_PIN_WIDTH'
 oracle();rows(('KYIV41-OCT1\n'+'\n'.join(a+' '+v for a,v in WORDS.items())+'\n').encode())
 assert rows(('KYIV41-OCT1\r\n'+'\r\n'.join(a+' '+v for a,v in WORDS.items())+'\r\n').encode())
 mutant=dict(WORDS);mutant['0160']='06000300020347'
 try:rows(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in mutant.items())+'\n').encode())
 except AssertionError:pass
 else:raise AssertionError('MUTANT_NOT_REJECTED')
 print('D15B1H11-AUDIT-SELFTEST PASS WORDS=8/8 MUTANTS_REJECTED=1 CRLF=1 SIGNED_ZERO=1')
def audit():
 self_test()
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'NOT_MAIN_OR_ROOT'
 assert git('rev-parse','HEAD')==BASE,'WRONG_BASELINE'
 assert not git('diff','--cached','--name-only'),'PREEXISTING_STAGED'
 for p,blob in PINS.items():assert git('rev-parse','HEAD:'+p)==blob,('SOURCE_PIN',p)
 for p,sha in SHA.items():assert hashlib.sha256(norm(pathlib.Path(p).read_bytes())).hexdigest()==sha,('CONTENT_SHA',p)
 assert hashlib.sha256(norm(pathlib.Path(README).read_bytes())).hexdigest()==README_SHA,'README_SHA'
 rows(pathlib.Path(IMAGE).read_bytes());provenance(pathlib.Path(PROV).read_bytes())
 status=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 expect=sorted([' M '+README]+['?? '+x for x in NEW])
 assert status==expect,('GIT_SCOPE',status,expect)
 ledger=norm(pathlib.Path('docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv').read_bytes()).decode()
 assert 'H9_SOURCE_PROSE_CONFLICT\tOPEN_UNCHANGED' in ledger
 assert 'H10_CARRY_POLICY_CONFLICT\tOPEN_UNCHANGED' in ledger
 assert 'SUBABS_EQUAL_NEGATIVE_ZERO\tNATIVE_PENDING' in ledger
 print('D15B1H11-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=8/8 PROGRAM=6 DATA=2 SOURCE_PINS=14/14 CONTENT_SHA=4/4 ROM3026_NEGATIVE_ZERO_PIN=1 H9_CONFLICT=OPEN_UNCHANGED H10_CONFLICT=OPEN_UNCHANGED CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 NATIVE_OBSERVATION=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:
  if '--self-test' in sys.argv:self_test()
  else:audit()
 except BaseException as e:raise SystemExit('D15B1H11-AUDIT FAIL '+repr(e))
