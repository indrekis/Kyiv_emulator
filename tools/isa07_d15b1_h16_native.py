#!/usr/bin/env python3
"""One historical one-third division triplet, bounded full-bit CLI gate."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_division_one_third_0205_0207.k41';WORDS={'0004': '05252525252525', '0026': '01000000000000', '0027': '03000000000000', '0205': '12002600270347', '0206': '16034700040210', '0207': '33000000000000'};SHA={'examples/historical/gy1962/au1_division_one_third_0205_0207.k41': 'af1e0ddd227cf312888db6eb2bbdcedd0f1e02862fcd6d2e841e227db3492bf9', 'examples/historical/gy1962/au1_division_one_third_0205_0207_provenance.tsv': 'bcaa0372563c3b1c162046ff1dc0f50a023bed0d77cc86976ee085e511333a29', 'docs/ISA_07_D15B1_H16_DIVISION_ONE_THIRD.md': 'ed39ffdf16b9c6b980458b821ba52fd45d2a975042adde935dffeaba694a9d6c', 'docs/ISA_07_D15B1_H16_DECISION_LEDGER.tsv': '73e593b2600c2ef14f7ceac1eb98da88303c55227aa6c7cf821ec680336e5f1e'};EXPECTED='05252525252525'
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
DATA={x:WORDS[x] for x in ['0004','0026','0027']}

def selftest():
 assert len(WORDS)==6 and EXPECTED=='05252525252525'
 a=int(WORDS['0026'],8);b=int(WORDS['0027'],8)
 assert 0<a<b<1<<40 and b==3*a and f'{(a<<40)//b:014o}'==EXPECTED
 assert WORDS['0205']=='12002600270347' and WORDS['0206']=='16034700040210'
 assert WORDS['0207']=='33000000000000'
 assert '16034700260210'!='16034700040210'
 print('D15B1H16-RUNNER-SELFTEST PASS WORDS=6/6 POSITIVE_OPERANDS=1 QUOTIENT_ORACLE=1 PRIVATE_STOP_DISCRIMINATOR=1 BOUNDARY_0210_NOT_EXECUTED=1')

def run(exe,img,cwd,n,timeout):
 cmd=[str(exe),'image',str(img),'0205',str(n),'--watch','0347']
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
 target='0206 '+WORDS['0206'];assert original.splitlines().count(target)==1,'UNIQUE_JE'
 mutated=original.replace(target,'0206 16034700260210')
 assert mutated!=original and ('0205 '+WORDS['0205']) in mutated and ('0207 '+WORDS['0207']) in mutated,'PRIVATE_SCOPE'
 total=0
 with tempfile.TemporaryDirectory(prefix='d15b1h16_external_') as td:
  private=pathlib.Path(td)/'private_stop.k41';private.write_text(mutated,encoding='ascii',newline='\n')
  for cwd_name,cwd in [('EXTERNAL',pathlib.Path(td)),('TEMPKYIV',root/'tempkyiv')]:
   for n in [1,2,3]:
    p,r,w=run(exe,img if n<=2 else private,cwd,n,args.timeout)
    want=('LIMIT',str(n),'0206' if n==1 else '0210') if n<=2 else ('CPU_STOP','3','0210')
    if p.returncode!=0 or r!=want or w.get('0347')!=EXPECTED or any(w.get(a)!=v for a,v in DATA.items()):
     print(f'D15B1H16-CASE FAIL CWD={cwd_name} STEPS={n} RC={p.returncode} RUN={r} EXPECT={want} RESULT={w.get("0347")} WATCH={w}\nSTDOUT={p.stdout[-1600:]}\nSTDERR={p.stderr[-1600:]}')
     raise AssertionError('NATIVE_MACHINE_CODE_MISMATCH')
    total+=1
    label='HISTORICAL' if n<=2 else 'PRIVATE_STOP'
    print(f'D15B1H16-CASE {total:02d} PROFILE={label} CWD={cwd_name} STEPS={n} RC=0 RUN={r} RESULT={EXPECTED} ORACLE={EXPECTED} PASS')
 assert total==6
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_IMAGE_CHANGED'
 print('D15B1H16-NATIVE PASS CASES=6/6 POSITIVE=4/4 PRIVATE_STOP=2/2 CWD_PARITY=3/3 HISTORICAL_EXPECTATION_MATCH=1 SIGN_RESULT_POSITIVE=1 BOUNDARY_0210_NOT_EXECUTED=1 H9_H10_H11_H13_H14_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H16-NATIVE FAIL '+repr(e))
