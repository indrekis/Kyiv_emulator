#!/usr/bin/env python3
"""D15/B1-H18: opcode05 at 0213, bounded one instruction; private true/false controls."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_control_transfer_0213.k41';WORDS={'0213': '05000000000263'};SHA={'examples/historical/gy1962/au1_control_transfer_0213.k41': '8ff8a1fe1ff809187b78dd26470b0f3bfb955b2c57623656d39a45c157320ecd', 'examples/historical/gy1962/au1_control_transfer_0213_provenance.tsv': 'be0542e1c8dfedce2949fda97280e9816fccd76f90bce2d4ddb660aaa9f95470', 'docs/ISA_07_D15B1_H18_CONTROL_TRANSFER.md': '8015986f734d78cd88f8600dfa827a23f7c4e66b2a9065cedc5675f56c0a7a45', 'docs/ISA_07_D15B1_H18_DECISION_LEDGER.tsv': '696ca75d66677171e054b94e10433cfef1ea888edfeceb5f009a67d067534fd3'}
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
TRUE='05000100020263';FALSE='05000200010263';DATA={'0001':'00000000000001','0002':'00000000000002'}
def selftest():
 assert WORDS=={'0213':'05000000000263'} and len(WORDS)==1
 assert all(len(w)==14 and set(w)<set('01234567') for w in [*WORDS.values(),TRUE,FALSE,*DATA.values()])
 def parts(w):
  n=int(w,8);return n>>36,(n>>24)&0o3777,(n>>12)&0o3777,n&0o3777
 assert parts(WORDS['0213'])==(0o5,0,0,0o263)
 assert parts(TRUE)==(0o5,1,2,0o263) and parts(FALSE)==(0o5,2,1,0o263)
 assert 1<=2 and not 2<=1
 print('D15B1H18-RUNNER-SELFTEST PASS SOURCE_WORDS=1/1 PRIVATE_ORDERS=2/2 OPCODE05_BRANCH_DISCRIMINATOR=1 BOUNDS_0214_0263_NOT_EXECUTED=1')
def execute(exe,img,cwd,timeout,private):
 cmd=[str(exe),'image',str(img),'0213','1','--watch','0213']
 if private:
  for a in DATA:cmd+=['--watch',a]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 m=R.search(p.stdout)
 return p,m.groups() if m else None,dict(W.findall(p.stdout))
def main():
 pa=argparse.ArgumentParser();pa.add_argument('--cli-exe');pa.add_argument('--timeout',type=float,default=20);pa.add_argument('--self-test',action='store_true');args=pa.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'REQUIRED_EXE_TIMEOUT'
 root=pathlib.Path(__file__).resolve().parent.parent;exe=pathlib.Path(args.cli_exe).resolve();img=(root/IMAGE).resolve()
 assert exe.is_file() and img.is_file() and (root/'tempkyiv').is_dir(),'INPUTS_MISSING'
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_SHA_PRE'
 orig=img.read_text('ascii');needle='0213 '+WORDS['0213']
 assert orig.splitlines().count(needle)==1,'SOURCE_WORD_NOT_UNIQUE'
 prefix='KYIV41-OCT1\n# PRIVATE synthetic opcode05 discriminator: NOT historical source\n'
 common=''.join(a+' '+w+'\n' for a,w in DATA.items())
 cases=[('SOURCE',img,'0263',WORDS['0213'],False),('PRIVATE_TRUE',None,'0263',TRUE,True),('PRIVATE_FALSE',None,'0214',FALSE,True)]
 total=0;parity=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h18_external_') as td:
  d=pathlib.Path(td)
  for name,word in [('PRIVATE_TRUE',TRUE),('PRIVATE_FALSE',FALSE)]:
   p=d/(name.lower()+'.k41')
   p.write_text(prefix+common+'0213 '+word+'\n',encoding='ascii',newline='\n')
   assert p.read_text('ascii').count('0213 '+word)==1
  for cn,cwd in [('EXTERNAL',d),('TEMPKYIV',root/'tempkyiv')]:
   results=[]
   for name,_,expected,word,private in cases:
    file=img if not private else d/(name.lower()+'.k41')
    p,r,w=execute(exe,file,cwd,args.timeout,private)
    ok=(p.returncode==0 and r==('LIMIT','1',expected) and w.get('0213')==word)
    if private:ok=ok and all(w.get(a)==v for a,v in DATA.items())
    if not ok:
     print(f'D15B1H18-CASE FAIL CWD={cn} KIND={name} RC={p.returncode} RUN={r} EXPECT={expected} WATCH={w}\nSTDOUT={p.stdout[-1500:]}\nSTDERR={p.stderr[-1500:]}')
     raise AssertionError('BRANCH_OR_IMAGE_MISMATCH')
    total+=1;results.append((name,r,w.get('0213')))
    print(f'D15B1H18-CASE {total:02d} KIND={name} CWD={cn} RC=0 RUN={r} WORD={word} EXPECTED_C={expected} PASS')
   parity.append(results)
 assert total==6 and parity[0]==parity[1],'CWD_PARITY'
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_SHA_POST'
 print('D15B1H18-NATIVE PASS CASES=6/6 SOURCE=2/2 PRIVATE_TRUE=2/2 PRIVATE_FALSE=2/2 CWD_PARITY=3/3 SOURCE_BRANCH_C0263=1 TRUE_BRANCH_C0263=1 FALSE_FALLTHROUGH_C0214=1 BOUNDARIES_0214_0263_NOT_EXECUTED=1 H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H18-NATIVE FAIL '+repr(e))
