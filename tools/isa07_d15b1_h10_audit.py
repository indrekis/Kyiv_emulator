#!/usr/bin/env python3
"""D15/B1-H10: exact source and read-only observation package audit."""
from __future__ import annotations
import hashlib,pathlib,subprocess,sys
BASE='cc688d3298eae645624b99195e28a5c6fe8012c4';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_addcyc_0151_0154.k41';PROV='examples/historical/gy1962/au1_addcyc_0151_0154_provenance.tsv';NEW=['docs/ISA_07_D15B1_H10_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41', 'examples/historical/gy1962/au1_addcyc_0151_0154_provenance.tsv', 'tools/isa07_d15b1_h10_audit.py', 'tools/isa07_d15b1_h10_native.py'];PINS={'examples/historical/gy1962/README.md': '839a8634cd8bebc238b2a032308d7cc5b1b24494', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addition_0143_0150_provenance.tsv': '227e233f356e1cd058b8f1269e2f8087d1bb0b39', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'docs/ISA_07_D15B1_H9_DECISION_LEDGER.tsv': '45db1808db660cb36b741d0fb71c0b46443a1a38', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'};WORDS={'0007': '17367573675712', '0020': '16757367573624', '0151': '07000700070347', '0152': '16034700200154', '0153': '33000000000000', '0154': '31300001100155'}
SHA={'examples/historical/gy1962/au1_addcyc_0151_0154.k41': '3ec33a741fe2dee54243f8624c7a2160158e75c3f92c9f401b057434f4454c7c', 'examples/historical/gy1962/au1_addcyc_0151_0154_provenance.tsv': 'a44c4da8fa766f2090bc92f4cb440410b828136b5e6dd323052084b99db7edd8', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '71d69f7a9a7fcab63fdb60198cecfe486c5e9802a930323a0090937b3a1bba71', 'docs/ISA_07_D15B1_H10_DECISION_LEDGER.tsv': '5bc7fecb54ea8fd0c9259086f3d21b5f83272c0956020e75cfb728a84a18a3ff'};README_SHA='23f3ca2d6659c38ce5295566d53ab13fd371042ed8ac3b2860af61e2d381ff57'
def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def rows(blob):
 lines=norm(blob).decode('ascii').splitlines()
 assert lines[0]=='KYIV41-OCT1','MAGIC'
 pairs=[]
 for s in lines[1:]:
  if not s or s.startswith('#'):continue
  assert len(s.split())==2,'COLUMNS';a,w=s.split()
  assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'OCTAL'
  pairs.append((a,w))
 assert pairs==list(WORDS.items()),'WORDS_MISMATCH'
 return pairs
def provenance(blob):
 lines=norm(blob).decode('ascii').splitlines()
 assert len(lines)==7,'PROVENANCE_COUNT'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\trole\tverification','HEADER'
 for (a,w),line in zip(WORDS.items(),lines[1:]):
  parts=line.split('\t');assert len(parts)==5 and parts[:2]==[a,w],'SOURCE_FIELDS'
  assert parts[2]==('172' if a in ('0007','0020') else '173'),'PAGE'
  assert parts[-1]=='VISUAL_FIRST_PASS','STATUS'
 return True
def selftest():
 image=pathlib.Path(IMAGE).read_bytes();rows(image)
 provenance(pathlib.Path(PROV).read_bytes())
 mutated=image.replace(b'07000700070347',b'07000700060347',1)
 assert mutated!=image,'MUTANT_ABSENT'
 try:rows(mutated)
 except AssertionError as e:assert str(e)=='WORDS_MISMATCH',repr(e)
 else:raise AssertionError('MUTANT_ACCEPTED')
 assert norm(b'a\r\nb\r\n')==b'a\nb\n','CRLF'
 x=int(WORDS['0007'],8);y=int(WORDS['0020'],8);mask=(1<<40)-1
 assert (2*x)&mask==y and ((2*x+1)&mask)==y+1,'CARRY_ORACLE'
 assert WORDS['0154'].startswith('313000')
 print('D15B1H10-AUDIT-SELFTEST PASS WORDS=6/6 MUTANTS_REJECTED=1 CRLF=1 CARRY_DISCRIMINATOR=1 NK3000_BOUNDARY=1')
def audit():
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main','BRANCH'
 assert not git('rev-parse','--show-prefix'),'ROOT'
 for p,sha in PINS.items():
  assert git('rev-parse','HEAD:'+p)==sha,('GIT_PIN',p)
  if p!=README:assert not git('diff','--name-only','--',p),('TRACKED_MUTATION',p)
 old=subprocess.check_output(['git','show','HEAD:'+README]);current=pathlib.Path(README).read_bytes()
 assert norm(current).startswith(norm(old)),'README_NOT_APPEND_ONLY'
 assert hashlib.sha256(norm(current)).hexdigest()==README_SHA,'README_SHA'
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 expected=sorted([' M '+README]+['?? '+p for p in NEW])
 assert actual==expected,('STATUS',actual)
 for p,sha in SHA.items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==sha,('CONTENT_SHA',p)
 rows(pathlib.Path(IMAGE).read_bytes());provenance(pathlib.Path(PROV).read_bytes())
 assert 'H9_SOURCE_PROSE_CONFLICT=OPEN_UNCHANGED' in pathlib.Path('docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md').read_text()
 print('D15B1H10-AUDIT PASS BASELINE=cc688d3 MOD=1/1 NEW=6/6 WORDS=6/6 PROGRAM=4 DATA=2 SOURCE_PINS=12/12 CONTENT_SHA=4/4 CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_EXAMPLES_IMMUTABLE=1 SOURCE_CARRY_POLICY_CONFLICT=OPEN H9_CONFLICT=OPEN_UNCHANGED NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:selftest() if '--self-test' in sys.argv else audit()
 except BaseException as e:raise SystemExit('D15B1H10-AUDIT FAIL '+repr(e))
