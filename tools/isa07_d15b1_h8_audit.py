#!/usr/bin/env python3
"""D15/B1-H8 strict source/ROM/scope auditor and mutation negative tests."""
from __future__ import annotations
import hashlib,pathlib,subprocess,sys
BASE='e795f1959d97bf3f34251fc2131447e86d51c611'
README='examples/historical/gy1962/README.md'
NEW=['examples/historical/gy1962/au1_addition_0135_0142.k41', 'examples/historical/gy1962/au1_addition_0135_0142_provenance.tsv', 'docs/ISA_07_D15B1_H8_NEGATIVE_ZERO_ADDITIONS.md', 'docs/ISA_07_D15B1_H8_DECISION_LEDGER.tsv', 'tools/isa07_d15b1_h8_audit.py', 'tools/isa07_d15b1_h8_native.py']
PIN={'examples/historical/gy1962/README.md': 'ff0bc8e9e5b93fb38ae3ca979552a826167db5a4', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0127_0134_provenance.tsv': 'cd676bfd0acace73446eb095a29f9585a0a51d32', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'}
EXPECTED={'0015': '00000000000001', '0016': '00000000000040', '0135': '01302600150347', '0136': '16034700150140', '0137': '33000000000000', '0140': '01302600160347', '0141': '16034700160143', '0142': '33000000000000'}
IMAGE='examples/historical/gy1962/au1_addition_0135_0142.k41';PROV='examples/historical/gy1962/au1_addition_0135_0142_provenance.tsv'
SHA={'examples/historical/gy1962/au1_addition_0135_0142.k41':'ea33ba319d6a6d86f789f71e18eaab54ff991c574507b099752685fd44633a45','examples/historical/gy1962/au1_addition_0135_0142_provenance.tsv':'18629f063974587d81d348c67cb3e9a4f3db76fb2bfeaf49f382674e0d697f9b','docs/ISA_07_D15B1_H8_NEGATIVE_ZERO_ADDITIONS.md':'01b1969934e1c93bec5f0054fed4640d00a5d73f851a94410b55343ae9a93fbe','docs/ISA_07_D15B1_H8_DECISION_LEDGER.tsv':'8e3e685a1a09e3c54c22275ca6cdaec1f2b436e28e3576795f07e446af691bd7'}
README_SHA='666600ea9104d7690c08ddc4509257f4e2a38dac17661e4ae7d021abb04f95ac'

def git(*args):
 return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def canonical(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def records(b):
 lines=canonical(b).decode().splitlines()
 assert lines and lines[0]=='KYIV41-OCT1','MAGIC'
 rows=[]
 for line in lines[1:]:
  if not line or line.startswith('#'):continue
  parts=line.split(' ')
  assert len(parts)==2,'TWO_COLUMNS'
  addr,word=parts
  assert len(addr)==4 and len(word)==14 and set(addr+word)<=set('01234567'),'OCTAL_WIDTH'
  rows.append((addr,word))
 assert rows==list(EXPECTED.items()),'SOURCE_WORD_MISMATCH'
 assert len(rows)==8,'WORD_COUNT'
 return rows
def provenance(b):
 lines=canonical(b).decode().splitlines()
 assert len(lines)==9,'PROVENANCE_ROWS'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\tprinted_role\tverification','PROV_HEADER'
 for (a,w),line in zip(EXPECTED.items(),lines[1:]):
  cols=line.split('\t')
  assert len(cols)==5 and cols[:2]==[a,w],'PROVENANCE_CODE'
  assert cols[2]==('172' if a in ('0015','0016') else '173'),'PROVENANCE_PAGE'
  assert cols[4]=='VISUAL_FIRST_PASS','VERIFICATION_STATUS'
 return len(lines)-1
def selftest():
 image=pathlib.Path(IMAGE).read_bytes()
 records(image);provenance(pathlib.Path(PROV).read_bytes())
 mutant=image.replace(b'16034700150140',b'16034700150141',1)
 assert mutant!=image,'MUTATION_MISSING'
 try:records(mutant)
 except AssertionError as e:assert str(e)=='SOURCE_WORD_MISMATCH','BAD_REJECTION'
 else:raise AssertionError('MUTANT_ACCEPTED')
 assert canonical(b'a\r\nb\r\n')==b'a\nb\n','CRLF'
 negzero=int('20000000000000',8)
 assert (negzero>>40)==1 and (negzero&((1<<40)-1))==0,'SIGN_ZERO'
 print('D15B1H8-AUDIT-SELFTEST PASS WORDS=8/8 MUTANTS_REJECTED=1/1 CRLF=1 NEGATIVE_ZERO=1')
def audit():
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main','NOT_MAIN'
 assert not git('rev-parse','--show-prefix'),'NOT_REPO_ROOT'
 for path,pin in PIN.items():
  assert git('rev-parse','HEAD:'+path)==pin,('BLOB_PIN',path)
  if path!=README:assert not git('diff','--name-only','--',path),('TRACKED_MUTATION',path)
 original=subprocess.check_output(['git','show','HEAD:'+README])
 current=pathlib.Path(README).read_bytes()
 assert canonical(current).startswith(canonical(original)),'README_NOT_APPEND_ONLY'
 assert hashlib.sha256(canonical(current)).hexdigest()==README_SHA,'README_CONTENT_SHA'
 expected=sorted([' M '+README]+['?? '+p for p in NEW])
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert actual==expected,('STATUS',actual)
 for path,sha in SHA.items():
  assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==sha,('CONTENT_SHA',path)
 records(pathlib.Path(IMAGE).read_bytes());provenance(pathlib.Path(PROV).read_bytes())
 print('D15B1H8-AUDIT PASS BASELINE=e795f19 MOD=1/1 NEW=6/6 WORDS=8/8 PROGRAM=6 DATA=2 SOURCE_PINS=8/8 CONTENT_SHA=5/5 ROM3026_NEGATIVE_ZERO_PIN=1 CPU_MUTATION=0 ROM_IMMUTABLE=1 EARLIER_EXAMPLES_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:
  if '--self-test' in sys.argv:selftest()
  else:audit()
 except BaseException as e:raise SystemExit('D15B1H8-AUDIT FAIL '+repr(e))
