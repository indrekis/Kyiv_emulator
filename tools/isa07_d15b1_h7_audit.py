#!/usr/bin/env python3
"""D15/B1-H7 exact-scope source audit, no CPU mutation, mutation tests."""
from __future__ import annotations
import hashlib,pathlib,subprocess,sys
BASE='fa5b491a5a15fe97b9ec5f9bba5066b12f77a76d'
README='examples/historical/gy1962/README.md'
NEW=['examples/historical/gy1962/au1_addition_0127_0134.k41', 'examples/historical/gy1962/au1_addition_0127_0134_provenance.tsv', 'docs/ISA_07_D15B1_H7_SIGNED_ADDITIONS.md', 'docs/ISA_07_D15B1_H7_DECISION_LEDGER.tsv', 'tools/isa07_d15b1_h7_audit.py', 'tools/isa07_d15b1_h7_native.py']
PIN={'examples/historical/gy1962/README.md': '172b9d87319c39e9bb5155fbe7fa14d2631afb0e', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0116_0126_provenance.tsv': 'c6714c8e730ab9938e9e3b3fa07f3cb62d4b879c', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'}
EXPECTED={'0010': '00010004002001', '0011': '30004002001000', '0012': '20200100040020', '0013': '00400200100040', '0014': '00200100040020', '0017': '27773775776777', '0127': '01001000110347', '0130': '16034700170132', '0131': '33000000000000', '0132': '01001200130347', '0133': '16034700140135', '0134': '33000000000000'}
IMAGE='examples/historical/gy1962/au1_addition_0127_0134.k41'
PROV='examples/historical/gy1962/au1_addition_0127_0134_provenance.tsv'
IMAGE_SHA='afeebbc0da7ab28ee2f6b8b3c97894f5cd7225932030ab05ed92112e34676f8d'
PROV_SHA='d1c28b0171a441036c6bb359d0426c50894979dd4360d884e3a939dfb76ae50e'
DOC_SHA='1b7f12ad49dd55d47347363ee9d15771eec73fdd62053bf76b6394a7a20f4384'
LED_SHA='24a26219c9d6bc50995ead4e6cae9061294d5a18f518baa93a28d7784c7b40ff'

def git(*args):
 return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')

def canonical(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')

def records(b):
 lines=canonical(b).decode().splitlines()
 assert lines and lines[0]=='KYIV41-OCT1','MAGIC'
 rows=[]
 for ln in lines[1:]:
  if not ln or ln.startswith('#'):continue
  x=ln.split(' ')
  assert len(x)==2,'TWO_COLUMNS'
  k,w=x
  assert len(k)==4 and len(w)==14 and set(k+w)<=set('01234567'),'WIDTH_OCTAL'
  rows.append((k,w))
 assert rows==list(EXPECTED.items()),'SOURCE_WORD_MISMATCH'
 assert len(rows)==12,'WORD_COUNT'
 return rows

def prov(b):
 lines=canonical(b).decode().splitlines()
 assert len(lines)==13,'PROVENANCE_ROWS'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\tprinted_role\tverification','HEADER'
 for (a,w),line in zip(EXPECTED.items(),lines[1:]):
  v=line.split('\t')
  assert len(v)==5 and v[:2]==[a,w],'PROVENANCE_VALUE'
  assert v[2]==('172' if a in {'0010': '00010004002001', '0011': '30004002001000', '0012': '20200100040020', '0013': '00400200100040', '0014': '00200100040020', '0017': '27773775776777'} else '173'),'PAGE'
  assert v[4]=='VISUAL_FIRST_PASS','FIRST_PASS_ONLY'
 return len(lines)-1

def selftest():
 orig=pathlib.Path(IMAGE).read_bytes()
 records(orig);prov(pathlib.Path(PROV).read_bytes())
 changed=orig.replace(b'27773775776777',b'27773775776776',1)
 assert changed!=orig,'MUTATION_MISSING'
 try:records(changed)
 except AssertionError as e:assert str(e)=='SOURCE_WORD_MISMATCH','BAD_REJECTION'
 else:raise AssertionError('MUTANT_ACCEPTED')
 assert canonical(b'a\r\nb\r\n')==b'a\nb\n'
 print('D15B1H7-AUDIT-SELFTEST PASS WORDS=12/12 MUTANTS_REJECTED=1/1 CRLF=1')

def audit():
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main','NOT_MAIN'
 assert not git('rev-parse','--show-prefix'),'NOT_ROOT'
 for p,sha in PIN.items():
  assert git('rev-parse','HEAD:'+p)==sha,('PIN',p)
  if p!=README: assert not git('diff','--name-only','--',p),('TRACKED_MUTATION',p)
 original=subprocess.check_output(['git','show','HEAD:'+README])
 current=pathlib.Path(README).read_bytes()
 assert canonical(current).startswith(canonical(original)) and current!=original,'README_APPEND_ONLY'
 expected_status=sorted([' M '+README]+['?? '+p for p in NEW])
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert actual==expected_status,('STATUS',actual)
 for p,val in [(IMAGE,IMAGE_SHA),(PROV,PROV_SHA),('docs/ISA_07_D15B1_H7_SIGNED_ADDITIONS.md',DOC_SHA),('docs/ISA_07_D15B1_H7_DECISION_LEDGER.tsv',LED_SHA)]:
  assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==val,('CONTENT_SHA',p)
 records(pathlib.Path(IMAGE).read_bytes());prov(pathlib.Path(PROV).read_bytes())
 print('D15B1H7-AUDIT PASS BASELINE=fa5b491 MOD=1/1 NEW=6/6 WORDS=12/12 PROGRAM=6 DATA=6 SOURCE_PINS=7/7 CONTENT_SHA=4/4 CPU_MUTATION=0 ROM_IMMUTABLE=1 EARLIER_EXAMPLES_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')

if __name__=='__main__':
 try:
  if '--self-test' in sys.argv:selftest()
  else:audit()
 except BaseException as e:raise SystemExit('D15B1H7-AUDIT FAIL '+repr(e))
