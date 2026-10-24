#!/usr/bin/env python3
"""D15/B1-H17: observe source-vs-host negative division at 0210, bounded."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_division_negative_0210_0212.k41';WORDS={'0030': '20002000000000', '0031': '00016000000000', '0032': '22222222222200', '0210': '12003000310347', '0211': '16034700320213', '0212': '33000000000000'};SHA={'examples/historical/gy1962/au1_division_negative_0210_0212.k41': 'c328c13b566f1ac7601466deea98306144c3a09f7e6c834d3f0b2a834bec54d8', 'examples/historical/gy1962/au1_division_negative_0210_0212_provenance.tsv': '5dba20f0599eb888878d3fad96ea25795428284ab9c6247e7eccf354d1c50091', 'docs/ISA_07_D15B1_H17_NEGATIVE_DIVISION_OBSERVATION.md': '623d12097ffb31e35df1173ef176e8d3677d2b4aca2bc48d573d62fbbbad869f', 'docs/ISA_07_D15B1_H17_DECISION_LEDGER.tsv': '5f8cd2f732e970185ebb343ccabd811136ae235f3a844a55fd589b1d1e768c65'};EXPECTED='22222222222200';HOST='22222222222222'
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
DATA={x:WORDS[x] for x in ['0030','0031','0032']}

def selftest():
 assert len(WORDS)==6 and EXPECTED=='22222222222200' and HOST=='22222222222222'
 sgn=1<<40;m=sgn-1;a=int(WORDS['0030'],8);b=int(WORDS['0031'],8)
 assert a&sgn and not b&sgn and (a&m)>0 and (b&m)>0
 assert f'{sgn|(((a&m)<<40)//(b&m)):014o}'==HOST
 assert int(HOST,8)-int(EXPECTED,8)==0o22
 assert WORDS['0210']=='12003000310347' and WORDS['0211']=='16034700320213'
 assert WORDS['0212']=='33000000000000'
 assert '16034700300213'!='16034700320213'
 print('D15B1H17-RUNNER-SELFTEST PASS WORDS=6/6 NEGATIVE_SIGN=1 HOST_SOURCE_DELTA_OCT22=1 PROFILE_DISCRIMINATOR=1 BOUNDARY_0213_NOT_EXECUTED=1')

def execute(exe,img,cwd,n,timeout):
 cmd=[str(exe),'image',str(img),'0210',str(n),'--watch','0347']
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
 orig=img.read_text('ascii');needle='0211 '+WORDS['0211']
 assert orig.splitlines().count(needle)==1,'JE_NOT_UNIQUE'
 private_text=orig.replace(needle,'0211 16034700300213')
 assert private_text!=orig and ('0210 '+WORDS['0210']) in private_text and ('0212 '+WORDS['0212']) in private_text,'MUTANT_SCOPE'
 results=[];total=0
 with tempfile.TemporaryDirectory(prefix='d15b1h17_external_') as td:
  private=pathlib.Path(td)/'private_stop.k41';private.write_text(private_text,encoding='ascii',newline='\n')
  for cn,cwd in [('EXTERNAL',pathlib.Path(td)),('TEMPKYIV',root/'tempkyiv')]:
   p,r,w=execute(exe,img,cwd,1,args.timeout)
   result=w.get('0347');profile='HOST_LOW22' if result==HOST else 'HISTORICAL' if result==EXPECTED else None
   if profile is None or p.returncode!=0 or r!=('LIMIT','1','0211') or any(w.get(a)!=v for a,v in DATA.items()):
    print(f'D15B1H17-CASE FAIL CWD={cn} N=1 RC={p.returncode} RUN={r} RESULT={result} SOURCE={EXPECTED} HOST={HOST} WATCH={w}\nSTDOUT={p.stdout[-1600:]}\nSTDERR={p.stderr[-1600:]}')
    raise AssertionError('DIVISION_FIRST_STEP_MISMATCH')
   for n in [1,2,3]:
    if n!=1:p,r,w=execute(exe,img if profile=='HOST_LOW22' else img if n==2 else private,cwd,n,args.timeout)
    target=('LIMIT',str(n),'0211' if n==1 else '0212' if profile=='HOST_LOW22' and n==2 else '0213') if n<3 else ('CPU_STOP','3','0213')
    ok=(p.returncode==0 and r==target and w.get('0347')==result and all(w.get(a)==v for a,v in DATA.items()))
    if not ok:
     print(f'D15B1H17-CASE FAIL CWD={cn} N={n} PROFILE={profile} RC={p.returncode} RUN={r} EXPECT={target} RESULT={w.get("0347")} SOURCE={EXPECTED} HOST={HOST} WATCH={w}\nSTDOUT={p.stdout[-1600:]}\nSTDERR={p.stderr[-1600:]}')
     raise AssertionError('DIVISION_PROFILE_MISMATCH')
    total+=1
    status='ORIGINAL_STOP' if n==3 and profile=='HOST_LOW22' else 'PRIVATE_STOP' if n==3 else 'HISTORICAL_CODE'
    print(f'D15B1H17-CASE {total:02d} KIND={status} CWD={cn} STEPS={n} RC=0 RUN={r} RESULT={result} SOURCE={EXPECTED} HOST_POLICY={HOST} PROFILE={profile} PASS')
   results.append((profile,result))
 assert total==6 and results[0]==results[1],('CWD_PARITY',results)
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_SHA_POST'
 profile,result=results[0];hist=int(profile=='HISTORICAL');host=int(profile=='HOST_LOW22')
 print('D15B1H17-NATIVE-OBSERVATION PASS CASES=6/6 POSITIVE=4/4 STOP_WITNESS=2/2 CWD_PARITY=3/3 OBSERVED_PROFILE='+profile+' HISTORICAL_EXPECTATION_MATCH='+str(hist)+' HOST_TRUNC_MATCH='+str(host)+' ORIGINAL_STOP_OBSERVED='+str(host)+' SOURCE_EXPECTED='+EXPECTED+' HOST_EXPECTED='+HOST+' SIGN_RESULT_NEGATIVE=1 BOUNDARY_0213_NOT_EXECUTED=1 H9_H10_H11_H13_H14_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H17-NATIVE FAIL '+repr(e))
