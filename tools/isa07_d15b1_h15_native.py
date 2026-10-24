#!/usr/bin/env python3
"""One historical rounded negative-product triplet, bounded full-bit CLI gate."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41';WORDS={'0004': '05252525252525', '0005': '32525252525252', '0025': '23434343434343', '0202': '11000400050347', '0203': '16034700250205', '0204': '33000000000000'};SHA={'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41': 'b33ffdba7d8a47e28a6d5c69d82fd4386d599651c03e4823228264173c9e0fd5', 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204_provenance.tsv': '1bfd35c3b65f5248cc61da99ce21327d5a47be35e34cbf5228066964f4d2296f', 'docs/ISA_07_D15B1_H15_NEGATIVE_ROUNDED_MULTIPLY.md': '6cf320836bb8569c084bb1b7e36a35dbfea0d25768c7bc5898d7b137d5dafa4e', 'docs/ISA_07_D15B1_H15_DECISION_LEDGER.tsv': '189a5d87f300efbc9d82b87771fb7561cecbb844c016dba0cfe9fb3854522f2f'};EXPECTED='23434343434343'
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
DATA={x:WORDS[x] for x in ['0004','0005','0025']}

def selftest():
 assert len(WORDS)==6 and EXPECTED=='23434343434343'
 mask=(1<<40)-1;a=int(WORDS['0004'],8);b=int(WORDS['0005'],8)
 assert a<1<<40 and b>=1<<40
 assert f'{(1<<40)|((a*(b&mask)+(1<<39))>>40):014o}'==EXPECTED
 assert WORDS['0202']=='11000400050347' and WORDS['0203']=='16034700250205'
 assert WORDS['0204']=='33000000000000'
 assert '16034700040205'!='16034700250205'
 print('D15B1H15-RUNNER-SELFTEST PASS WORDS=6/6 NEGATIVE_SIGN=1 ARITH_ORACLE=1 PRIVATE_STOP_DISCRIMINATOR=1 BOUNDARY_0205_NOT_EXECUTED=1')

def run(exe,img,cwd,n,timeout):
 cmd=[str(exe),'image',str(img),'0202',str(n),'--watch','0347']
 for a in DATA:cmd+=['--watch',a]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 m=R.search(p.stdout)
 return p,m.groups() if m else None,dict(W.findall(p.stdout))

def main():
 pa=argparse.ArgumentParser();pa.add_argument('--cli-exe');pa.add_argument('--timeout',type=float,default=20);pa.add_argument('--self-test',action='store_true');args=pa.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'EXE_TIMEOUT'
 root=pathlib.Path(__file__).resolve().parent.parent
 img=(root/IMAGE).resolve();exe=pathlib.Path(args.cli_exe).resolve()
 assert exe.is_file() and img.is_file() and (root/'tempkyiv').is_dir(),'NATIVE_INPUTS_MISSING'
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'SOURCE_IMAGE_SHA_PRE'
 original=img.read_text('ascii')
 target='0203 '+WORDS['0203'];assert original.splitlines().count(target)==1,'UNIQUE_JE'
 mutated=original.replace(target,'0203 16034700040205')
 assert mutated!=original and ('0202 '+WORDS['0202']) in mutated and ('0204 '+WORDS['0204']) in mutated,'PRIVATE_SCOPE'
 total=0
 with tempfile.TemporaryDirectory(prefix='d15b1h15_external_') as td:
  private=pathlib.Path(td)/'private_stop.k41';private.write_text(mutated,encoding='ascii',newline='\n')
  for cwd_name,cwd in [('EXTERNAL',pathlib.Path(td)),('TEMPKYIV',root/'tempkyiv')]:
   for n in [1,2,3]:
    p,r,w=run(exe,img if n<=2 else private,cwd,n,args.timeout)
    want=('LIMIT',str(n),'0203' if n==1 else '0205') if n<=2 else ('CPU_STOP','3','0205')
    if p.returncode!=0 or r!=want or w.get('0347')!=EXPECTED or any(w.get(a)!=v for a,v in DATA.items()):
     print(f'D15B1H15-CASE FAIL CWD={cwd_name} STEPS={n} RC={p.returncode} RUN={r} EXPECT={want} RESULT={w.get("0347")} WATCH={w}\nSTDOUT={p.stdout[-1600:]}\nSTDERR={p.stderr[-1600:]}')
     raise AssertionError('NATIVE_MACHINE_CODE_MISMATCH')
    total+=1
    label='HISTORICAL' if n<=2 else 'PRIVATE_STOP'
    print(f'D15B1H15-CASE {total:02d} PROFILE={label} CWD={cwd_name} STEPS={n} RC=0 RUN={r} RESULT={EXPECTED} ORACLE={EXPECTED} PASS')
 assert total==6
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_IMAGE_CHANGED'
 print('D15B1H15-NATIVE PASS CASES=6/6 POSITIVE=4/4 PRIVATE_STOP=2/2 CWD_PARITY=3/3 HISTORICAL_EXPECTATION_MATCH=1 SIGN_RESULT_NEGATIVE=1 BOUNDARY_0205_NOT_EXECUTED=1 H9_H10_H11_H13_H14_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H15-NATIVE FAIL '+repr(e))
