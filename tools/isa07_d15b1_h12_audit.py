#!/usr/bin/env python3
"""H12 historical command addition: exact words, immutable sources, strict scope."""
from __future__ import annotations
import hashlib,pathlib,re,subprocess,sys
BASE='ef90df8b5718a0b20acdfca64ab15f9584207412';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_addcmd_0163_0165.k41';PROV='examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv'
NEW=['docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md', 'examples/historical/gy1962/au1_addcmd_0163_0165.k41', 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv', 'tools/isa07_d15b1_h12_audit.py', 'tools/isa07_d15b1_h12_native.py'];PINS={'examples/historical/gy1962/README.md': 'da21a8f695c12b79aec260a0adbd8f125738a48d', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c', 'examples/historical/gy1962/au1_subtraction_0155_0162.k41': '3428a04652d6f9a8ee070138a183b158406175d2', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '9c7737f526d313eef8243a4a4de592059d53f5af', 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': 'ef6ae41bae4075caddd292a4c11e537a86cc0218', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': '01cb2d553c1d97f6426c3adb16b3683250e97464', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'};WORDS={'0002': '12525252525252', '0003': '25252525252525', '0163': '03000200030347', '0164': '16034730360166', '0165': '33000000000000'};SHA={'examples/historical/gy1962/au1_addcmd_0163_0165.k41': '71d43f69898cb37bc4f88aa9eb24204cb9a9b1c7b892bb3d2c07a10625fb4057', 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv': '24a592ac5305105d484e1aee4d5656a4f282d1bf330bf5340c7bf1700cd9f168', 'docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv': 'fe6d9e9995ee591ed942ff7ee4b3170d98139420fe4543673d9e166290c60304', 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md': '65e04d9f7f7dc0c0c23a39a9196a353bbc9e445eac0ca82d2e31a5ad962cf156'};README_SHA='547884c4388debd91a26d25c0ecd687e904ddb9aa6c08ca9c79beed92ac8d7be'
EXPECTED='37777777777777';SIGN=1<<40;MAG=SIGN-1

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def rows(blob):
 lines=norm(blob).decode('ascii').splitlines()
 assert lines[0]=='KYIV41-OCT1','MAGIC'
 arr=[]
 for line in lines[1:]:
  if not line or line.startswith('#'):continue
  a,w=line.split();assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'WORD_SHAPE'
  arr.append((a,w))
 assert arr==list(WORDS.items()),'WORDS_MISMATCH'
 return arr
def provenance(blob):
 lines=norm(blob).decode('ascii').splitlines();assert len(lines)==6,'PROVENANCE_LINES'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\trole\tverification'
 parts=[line.split('\t') for line in lines[1:]]
 assert all(len(x)==5 and x[4]=='VISUAL_FIRST_PASS' for x in parts),'PROV_SHAPE'
 assert [(x[0],x[1]) for x in parts]==list(WORDS.items()),'PROV_WORDS'
 assert all(x[2]==('172' if i<2 else '173') for i,x in enumerate(parts)),'PROV_PAGE'
def oracle():
 a=int(WORDS['0002'],8);b=int(WORDS['0003'],8)
 assert not a&SIGN and b&SIGN and (a&MAG)>0 and (b&MAG)>0,'OPERAND_SIGNS'
 magnitude=(a&MAG)+(b&MAG)
 assert magnitude<MAG+1,'NO_OVERFLOW'
 assert format(magnitude,'014o')=='17777777777777','MAGNITUDE_ORACLE'
 assert (magnitude|SIGN)==int(EXPECTED,8),'ORACLE'
 assert WORDS['0163']=='03000200030347' and WORDS['0164']=='16034730360166' and WORDS['0165']=='33000000000000','PROGRAM'
def self_test():
 assert len(PINS)==16 and all(re.fullmatch(r'[0-9a-f]{40}',v) for v in PINS.values()),'INVALID_GIT_PIN'
 oracle()
 blob=('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode()
 assert rows(blob) and rows(blob.replace(b'\n',b'\r\n'))
 mutant=dict(WORDS);mutant['0163']='03000200020347'
 try:rows(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in mutant.items())+'\n').encode())
 except AssertionError:pass
 else:raise AssertionError('MUTANT_ACCEPTED')
 print('D15B1H12-AUDIT-SELFTEST PASS WORDS=5/5 MUTANTS_REJECTED=1 CRLF=1 SIGNED_COMMAND_ADD=1 GIT_PIN_WIDTH=16/16')
def audit():
 self_test()
 assert git('rev-parse','HEAD')==BASE,'WRONG_HEAD'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'NOT_MAIN_ROOT'
 assert not git('diff','--cached','--name-only'),'STAGED'
 for p,v in PINS.items():assert git('rev-parse','HEAD:'+p)==v,('GIT_PIN',p)
 for p,v in SHA.items():assert hashlib.sha256(norm(pathlib.Path(p).read_bytes())).hexdigest()==v,('SHA',p)
 assert hashlib.sha256(norm(pathlib.Path(README).read_bytes())).hexdigest()==README_SHA,'README_SHA'
 rows(pathlib.Path(IMAGE).read_bytes());provenance(pathlib.Path(PROV).read_bytes())
 exp=sorted([' M '+README]+['?? '+p for p in NEW]);got=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert got==exp,('GIT_SCOPE',got,exp)
 ledger=norm(pathlib.Path('docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv').read_bytes()).decode('utf-8')
 for k in ('H9_SOURCE_PROSE_CONFLICT','H10_CARRY_POLICY_CONFLICT','H11_SUBABS_SIGNED_ZERO_CONFLICT'):
  assert k+'\tOPEN_UNCHANGED' in ledger,'CONFLICT_LOST'
 print('D15B1H12-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=5/5 PROGRAM=3 DATA=2 SOURCE_PINS=16/16 CONTENT_SHA=4/4 ROM3036_PIN=1 CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 H9_H10_H11_CONFLICTS=OPEN_UNCHANGED REAL_NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:self_test() if '--self-test' in sys.argv else audit()
 except BaseException as e:raise SystemExit('D15B1H12-AUDIT FAIL '+repr(e))
