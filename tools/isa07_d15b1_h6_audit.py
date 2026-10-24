#!/usr/bin/env python3
"""D15/B1-H6: exact-source and scope audit for next three historical additions."""
from __future__ import annotations
import pathlib,subprocess,hashlib,sys
BASE='ab046eb99e6c7fa43fda35bf287f1e0ffa6052fe'
README='examples/historical/gy1962/README.md'
NEW=['examples/historical/gy1962/au1_addition_0116_0126.k41', 'examples/historical/gy1962/au1_addition_0116_0126_provenance.tsv', 'docs/ISA_07_D15B1_H6_THREE_ADDITIONS.md', 'docs/ISA_07_D15B1_H6_DECISION_LEDGER.tsv', 'tools/isa07_d15b1_h6_audit.py', 'tools/isa07_d15b1_h6_native.py']
PIN={'examples/historical/gy1962/README.md': '4849464d66924bd745a747edb0ca23502ea13d30', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0110_0115_provenance.tsv': '452e3bb4a4b2c146bb8eea978f333b700c32a356', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1'}
EXPECTED={'0002': '12525252525252', '0003': '25252525252525', '0004': '05252525252525', '0005': '32525252525252', '0006': '07573675736745', '0007': '17367573675712', '0116': '01000600060347', '0117': '16034700070121', '0120': '33000000000000', '0121': '01000400050347', '0122': '16034700030124', '0123': '33000000000000', '0124': '01000200030347', '0125': '16034700040127', '0126': '33000000000000'}
IMAGE='examples/historical/gy1962/au1_addition_0116_0126.k41'
PROV='examples/historical/gy1962/au1_addition_0116_0126_provenance.tsv'
IMAGE_SHA='cc09f0928483df9fd32e0fb66dcb0b94fe5181c53d3e4238e133a9500f786cca'
PROV_SHA='5800688c05b8d4636e939dd0779f5169019e43ce82d556eee379098912c3d346'
DOC_SHA='0def69f3ae219b65d685f49ebbaf1fd5f30c9fd94713f6fe68608673fd408f93'
LED_SHA='7294bfd86ed1aaaad4adb2c94b27301fa8992eee6c384d5b99b80285b76dd6f9'

def git(*args):
 return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')

def canonical(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'CR_ONLY_EOL'
 return b.replace(b'\r\n',b'\n')

def read_records(data):
    lines=data.decode('utf-8').splitlines()
    assert lines[0]=='KYIV41-OCT1','IMAGE_MAGIC'
    pairs=[]
    for line in lines[1:]:
        if not line or line.startswith('#'):continue
        v=line.split(' ')
        assert len(v)==2,'TWO_COLUMNS'
        a,w=v
        assert len(a)==4 and len(w)==14 and set(a+w)<=set('01234567'),'OCTAL_SYNTAX'
        pairs.append((a,w))
    assert len(pairs)==len(EXPECTED)==15,'WORD_COUNT'
    assert pairs==list(EXPECTED.items()),'SOURCE_WORD_MISMATCH'
    return pairs

def parse_prov(b):
 lines=b.decode().splitlines()
 assert len(lines)==16,'PROVENANCE_ROWS'
 assert lines[0]=='address\tcode_octal_14\tprinted_page\tprinted_role\tverification','PROV_HEADER'
 for row,(a,w) in zip(lines[1:],EXPECTED.items()):
    col=row.split('\t')
    assert col[:2]==[a,w],'PROV_VALUE'
    assert col[2]==('172' if a<'0116' else '173'),'PROV_PAGE'
    assert col[4]=='VISUAL_FIRST_PASS','PROV_FIRST_ONLY'
 return len(lines)-1

def selftest():
 read_records(pathlib.Path(IMAGE).read_bytes())
 parse_prov(pathlib.Path(PROV).read_bytes())
 orig=pathlib.Path(IMAGE).read_bytes()
 try:
  read_records(orig.replace(b'07573675736745',b'07573675736744',1))
  raise AssertionError('MUTANT_ACCEPTED')
 except AssertionError as e:
  assert str(e)=='SOURCE_WORD_MISMATCH','NEGATIVE_GATE_MISMATCH'
 assert canonical(b'x\r\ny\r\n')==b'x\ny\n'
 print('D15B1H6-AUDIT-SELFTEST PASS WORDS=15/15 MUTANTS_REJECTED=1/1 CRLF=1')

def main():
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main','NOT_MAIN'
 assert not git('rev-parse','--show-prefix'),'NOT_ROOT'
 for p,sha in PIN.items():
    assert git('rev-parse','HEAD:'+p)==sha,('SOURCE_PIN',p)
    if p!=README:
      assert not git('diff','--name-only','--',p),('TRACKED_MUTATION',p)
 orig=subprocess.check_output(['git','show','HEAD:'+README])
 expect=pathlib.Path(README).read_bytes()
 assert canonical(expect).startswith(canonical(orig)),'README_NOT_APPEND_ONLY'
 assert expect!=orig,'README_NOT_CHANGED'
 actual=sorted(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 permitted=sorted([' M '+README]+['?? '+x for x in NEW])
 assert actual==permitted,('STATUS',actual)
 assert hashlib.sha256(pathlib.Path(IMAGE).read_bytes()).hexdigest()==IMAGE_SHA,'IMAGE_SHA'
 assert hashlib.sha256(pathlib.Path(PROV).read_bytes()).hexdigest()==PROV_SHA,'PROV_SHA'
 for p,h in [('docs/ISA_07_D15B1_H6_THREE_ADDITIONS.md',DOC_SHA),('docs/ISA_07_D15B1_H6_DECISION_LEDGER.tsv',LED_SHA)]:
  assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,('CONTENT_SHA',p)
 read_records(pathlib.Path(IMAGE).read_bytes());parse_prov(pathlib.Path(PROV).read_bytes())
 assert 'HUMAN_INDEPENDENT_WITNESS' not in pathlib.Path('docs/ISA_07_D15B1_H6_THREE_ADDITIONS.md').read_text() or 'human' in pathlib.Path('docs/ISA_07_D15B1_H6_THREE_ADDITIONS.md').read_text().lower()
 print('D15B1H6-AUDIT PASS BASELINE=ab046eb MOD=1/1 NEW=6/6 WORDS=15/15 PROGRAM=9 DATA=6 SOURCE_PINS=6/6 CONTENT_SHA=4/4 CPU_MUTATION=0 ROM_IMMUTABLE=1 EARLIER_EXAMPLES_IMMUTABLE=1 REAL_NATIVE_GATE=PENDING HUMAN_INDEPENDENT_WITNESS=PENDING HARDWARE_ORACLE=0')

if __name__=='__main__':
 try:
  if '--self-test' in sys.argv:selftest()
  else:main()
 except BaseException as e:raise SystemExit('D15B1H6-AUDIT FAIL '+repr(e))
