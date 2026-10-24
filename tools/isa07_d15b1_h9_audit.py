#!/usr/bin/env python3
"""H9 exact source, historical discrepancy, and change-scope audit."""
from __future__ import annotations
import hashlib,pathlib,subprocess,sys
BASE='b896eeb975662ce684572ae235135e119a2b0493';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_addition_0143_0150.k41';PROV='examples/historical/gy1962/au1_addition_0143_0150_provenance.tsv'
NEW=['docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md', 'docs/ISA_07_D15B1_H9_DECISION_LEDGER.tsv', 'examples/historical/gy1962/au1_addition_0143_0150.k41', 'examples/historical/gy1962/au1_addition_0143_0150_provenance.tsv', 'tools/isa07_d15b1_h9_audit.py', 'tools/isa07_d15b1_h9_native.py'];PIN={'examples/historical/gy1962/README.md': '7c9741e7258d7919378a2ffb12bf25ec7791226e', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0135_0142_provenance.tsv': 'd582e6a6eccb16fb5439b33f54a07fb7b811881b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'};WORDS={'0010': '00010004002001', '0013': '00400200100040', '0143': '01302600100347', '0144': '16034700100146', '0145': '33000000000000', '0146': '01302600130347', '0147': '16034700130151', '0150': '33000000000000'}
SHA={'examples/historical/gy1962/au1_addition_0143_0150.k41': '9ce78e80c2be1361c25248a8ff06c34cd6a16dd252d219c900264360cb250ac7', 'examples/historical/gy1962/au1_addition_0143_0150_provenance.tsv': '793df9e34899d9291adb5d4af4a9644a48df5d867808bcb458fe45f997d7f967', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': '7ebe4863fa4c5085f9545cd96ca568528cce9e416cec8b0b0ec1ac3c9d0df2b5', 'docs/ISA_07_D15B1_H9_DECISION_LEDGER.tsv': 'f0bc1aaf7801f75e4f7c8435802132f1030407d811766bb4c9a678b3d16dc3a2'}
README_SHA='b7e947722dad1770467922aff9c3d793f4271459249ee490a5b26e612a0a5d7b'
def git(*args):
 return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def transcript(b):
 lines=norm(b).decode('ascii').splitlines()
 assert lines and lines[0]=='KYIV41-OCT1','MAGIC'
 rows=[]
 for line in lines[1:]:
  if not line or line.startswith('#'):continue
  parts=line.split(' ')
  assert len(parts)==2,'TWO_COLS'
  a,w=parts
  assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'OCTAL'
  rows.append((a,w))
 assert rows==list(WORDS.items()),'SOURCE_WORD_MISMATCH'
 return rows
def prov(b):
 lines=norm(b).decode('ascii').splitlines()
 assert len(lines)==9,'PROVENANCE_ROWS'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\trole\tverification','HEADER'
 for (a,w),line in zip(WORDS.items(),lines[1:]):
  parts=line.split('\t')
  assert len(parts)==5 and parts[:2]==[a,w],'PROVENANCE_SOURCE'
  assert parts[2]==('172' if a in ('0010','0013') else '173'),'PAGE'
  assert parts[4]=='VISUAL_FIRST_PASS','STATUS'
 return 8
def selftest():
 original=pathlib.Path(IMAGE).read_bytes();transcript(original)
 prov(pathlib.Path(PROV).read_bytes())
 bad=original.replace(b'01302600100347',b'01302600110347',1)
 assert bad!=original,'MUTANT_ABSENT'
 try:transcript(bad)
 except AssertionError as e:assert str(e)=='SOURCE_WORD_MISMATCH',repr(e)
 else:raise AssertionError('MUTANT_ACCEPTED')
 assert norm(b'a\r\nb\r\n')==b'a\nb\n','CRLF'
 assert WORDS['0010']!='00000000000040' and WORDS['0010']!=WORDS['0013'],'PROSE_CONFLICT_NOT_CAPTURED'
 print('D15B1H9-AUDIT-SELFTEST PASS WORDS=8/8 MUTANT_REJECTED=1 CRLF=1 PRINTED_PROSE_DISCREPANCY=1')
def audit():
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main','BRANCH'
 assert not git('rev-parse','--show-prefix'),'ROOT'
 for path,sha in PIN.items():
  assert git('rev-parse','HEAD:'+path)==sha,('BLOB_PIN',path)
  if path!=README:assert not git('diff','--name-only','--',path),('TRACKED_MUTATION',path)
 old=subprocess.check_output(['git','show','HEAD:'+README]);current=pathlib.Path(README).read_bytes()
 assert norm(current).startswith(norm(old)),'README_NOT_APPEND_ONLY'
 assert hashlib.sha256(norm(current)).hexdigest()==README_SHA,'README_SHA'
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 expected=sorted([' M '+README]+['?? '+p for p in NEW]);assert actual==expected,('STATUS',actual)
 for p,sha in SHA.items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==sha,('SHA',p)
 transcript(pathlib.Path(IMAGE).read_bytes());prov(pathlib.Path(PROV).read_bytes())
 print('D15B1H9-AUDIT PASS BASELINE=b896eeb MOD=1/1 NEW=6/6 WORDS=8/8 PROGRAM=6 DATA=2 SOURCE_PINS=9/9 CONTENT_SHA=4/4 ROM3026_NEGATIVE_ZERO_PIN=1 PRINTED_PROSE_DISCREPANCY=1 CPU_MUTATION=0 ROM_IMMUTABLE=1 EARLIER_EXAMPLES_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:selftest() if '--self-test' in sys.argv else audit()
 except BaseException as e:raise SystemExit('D15B1H9-AUDIT FAIL '+repr(e))
