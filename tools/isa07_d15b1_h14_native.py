#!/usr/bin/env python3
"""Bounded native observation of GY1962 three rounded multiply tests."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41';WORDS={'0015': '00000000000001', '0021': '20000000000001', '0022': '30000000000000', '0023': '30000000000001', '0024': '17777777777775', '0171': '11002100220347', '0172': '16034700150174', '0173': '33000000000000', '0174': '11002330350347', '0175': '16034700220177', '0176': '33000000000000', '0177': '11303530350347', '0200': '16034700240202', '0201': '33000000000000'};SHA={'examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41': 'b8952d138ce706532ef70317ad753659c46bcdc4fee48ef023705904d93a0f77', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv': '8208df9f99a083e1b9f2cc695b53623d666e323213ffb8b9ceda99616821592f', 'docs/ISA_07_D15B1_H14_ROUNDED_MULTIPLICATION_OBSERVATION.md': '7b262d714064afc9d3088bc28911a2f93bc59072f07e2355df39ea69df4a97cd', 'docs/ISA_07_D15B1_H14_DECISION_LEDGER.tsv': 'de7bb4d44a8aae30ec857e093fbaff0013266fea8a08e4b5949e9420da8a5d08'};EXPECTED=['00000000000001', '30000000000000', '17777777777775'];HOST=['00000000000001', '30000000000000', '17777777777776'];ROM='17777777777777'
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
DATA={'0015':WORDS['0015'],'0021':WORDS['0021'],'0022':WORDS['0022'],'0023':WORDS['0023'],'0024':WORDS['0024'],'3035':ROM}
GROUPS=[('FIRST','0171','0172','0174','0173','0174','0172','16034700240174'),('SECOND','0174','0175','0177','0176','0177','0175','16034700150177'),('THIRD','0177','0200','0202','0201','0202',None,None)]

def selftest():
 assert len(WORDS)==14 and len(EXPECTED)==len(HOST)==3
 m=(1<<40)-1
 def rnd(a,b):return (a*b+(1<<39))>>40
 assert (f'{rnd(1,1<<39):014o}',f'{rnd((1<<39)+1,m)|(1<<40):014o}',f'{rnd(m,m):014o}')==tuple(HOST)
 assert EXPECTED[0:2]==HOST[0:2] and int(HOST[2],8)==int(EXPECTED[2],8)+1
 assert WORDS['0171']=='11002100220347' and WORDS['0172']=='16034700150174'
 assert WORDS['0174']=='11002330350347' and WORDS['0175']=='16034700220177'
 assert WORDS['0177']=='11303530350347' and WORDS['0200']=='16034700240202'
 assert all(WORDS[x]=='33000000000000' for x in ['0173','0176','0201'])
 assert ROM=='17777777777777'
 print('D15B1H14-RUNNER-SELFTEST PASS WORDS=14/14 GROUPS=3/3 ARITH_ORACLES=3/3 THIRD_OFF_BY_ONE=1 BOUNDARY_0202_NOT_EXECUTED=1')

def run(exe,img,cwd,start,n,timeout):
 cmd=[str(exe),'image',str(img),start,str(n),'--watch','0347']
 for addr in DATA:cmd+=['--watch',addr]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 r=R.search(p.stdout)
 return p,(r.groups() if r else None),dict(W.findall(p.stdout))

def private_source(src,addr,old,new):
 lines=src.splitlines(); target=addr+' '+old
 assert lines.count(target)==1,'PRIVATE_MUTANT_SOURCE'
 assert addr+' '+new not in lines,'MUTANT_ALREADY_PRESENT'
 return '\n'.join((addr+' '+new if line==target else line) for line in lines)+'\n'

def main():
 a=argparse.ArgumentParser();a.add_argument('--cli-exe');a.add_argument('--timeout',type=float,default=20);a.add_argument('--self-test',action='store_true');args=a.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'NO_EXE_TIMEOUT'
 root=pathlib.Path(__file__).resolve().parent.parent
 img=(root/IMAGE).resolve();exe=pathlib.Path(args.cli_exe).resolve()
 assert img.is_file() and exe.is_file() and (root/'tempkyiv').is_dir(),'MISSING_INPUT'
 sha=SHA[IMAGE];assert hashlib.sha256(img.read_bytes()).hexdigest()==sha,'SOURCE_IMAGE_SHA_PRE'
 src=img.read_text('ascii')
 total=0;positive=0;private_stop=0;original_stop=0;observed_profile=None;cw=0
 with tempfile.TemporaryDirectory(prefix='d15b1h14_external_') as td:
  external=pathlib.Path(td)
  for cwd_name,cwd in [('EXTERNAL',external),('TEMPKYIV',root/'tempkyiv')]:
   for idx,(kind,start,intermediate,success,stop_addr,stop_next,mut_addr,mut_word) in enumerate(GROUPS):
    raw=None;profile=None
    for n in [1,2]:
     p,r,w=run(exe,img,cwd,start,n,args.timeout)
     if p.returncode!=0 or r is None or any(w.get(x)!=v for x,v in DATA.items()):
      print(f'D15B1H14-CASE FAIL KIND={kind} CWD={cwd_name} STEPS={n} RC={p.returncode} RUN={r} WATCH={w}\nSTDOUT={p.stdout[-1600:]}\nSTDERR={p.stderr[-1600:]}')
      raise AssertionError('CLI_RUN_OR_WATCH_MISMATCH')
     got=w.get('0347');profile=('HISTORICAL' if got==EXPECTED[idx] else ('HOST_PLUS1' if kind=='THIRD' and got==HOST[idx] else 'UNKNOWN'))
     if kind!='THIRD':assert profile=='HISTORICAL',('POSITIVE_GROUP_MISMATCH',kind,got)
     else:assert profile in ('HISTORICAL','HOST_PLUS1'),('THIRD_UNCLASSIFIED',got)
     wantC=(intermediate if n==1 else (success if profile=='HISTORICAL' else stop_addr))
     assert r==('LIMIT',str(n),wantC),('RUN_STATE',kind,n,r,wantC)
     assert got==HOST[idx] if kind!='THIRD' else got in (EXPECTED[idx],HOST[idx]),('ARITH_RESULT',kind,got)
     if raw is not None:assert raw==got,'RESULT_INSTABILITY'
     raw=got;total+=1;positive+=1
     print(f'D15B1H14-CASE {total:02d} KIND={kind} CWD={cwd_name} STEPS={n} RC=0 RUN={r} RESULT={got} SOURCE={EXPECTED[idx]} HOST_POLICY={HOST[idx]} PROFILE={profile} PASS')
    if kind!='THIRD':
     # private altered JE second operand; original multiply and original STOP immutable
     mutated=private_source(src,mut_addr,WORDS[mut_addr],mut_word)
     temp=pathlib.Path(td)/f'h14_private_{cwd_name}_{kind}.k41'
     temp.write_text(mutated,encoding='ascii',newline='\n')
     p,r,w=run(exe,temp,cwd,start,3,args.timeout)
     assert p.returncode==0 and r==('CPU_STOP','3',stop_next) and w.get('0347')==EXPECTED[idx],('PRIVATE_STOP',kind,r,w.get('0347'),p.stderr[-1000:])
     assert all(w.get(x)==v for x,v in DATA.items()),('PRIVATE_INPUTS_CHANGED',kind)
     total+=1;private_stop+=1
     print(f'D15B1H14-CASE {total:02d} KIND={kind}_PRIVATE_STOP CWD={cwd_name} RC=0 RUN={r} ORIGINAL_STOP={stop_addr} PASS')
    elif profile=='HOST_PLUS1':
     p,r,w=run(exe,img,cwd,start,3,args.timeout)
     assert p.returncode==0 and r==('CPU_STOP','3',stop_next) and w.get('0347')==HOST[2],('ORIGINAL_STOP',r,w.get('0347'),p.stderr[-1000:])
     assert all(w.get(x)==v for x,v in DATA.items()),'ORIGINAL_INPUTS_CHANGED'
     total+=1;original_stop+=1
     print(f'D15B1H14-CASE {total:02d} KIND=THIRD_ORIGINAL_STOP CWD={cwd_name} RC=0 RUN={r} ORIGINAL_STOP=0201 PASS')
    if kind=='THIRD':
     if observed_profile is None:observed_profile=profile
     assert observed_profile==profile,'CWD_THIRD_PROFILE_MISMATCH'
   cw+=1
 assert hashlib.sha256(img.read_bytes()).hexdigest()==sha,'SOURCE_IMAGE_SHA_POST'
 want=18 if observed_profile=='HOST_PLUS1' else 16
 assert total==want and positive==12 and private_stop==4 and original_stop==(2 if want==18 else 0),'CASE_COUNT'
 print(f'D15B1H14-NATIVE-OBSERVATION PASS CASES={total}/{want} POSITIVE=12/12 PRIVATE_STOP=4/4 ORIGINAL_STOP={original_stop}/{2 if want==18 else 0} CWD_PARITY=1/1 GROUPS=3/3 OBSERVED_THIRD_PROFILE={observed_profile} THIRD_HISTORICAL_MATCH={1 if observed_profile=="HISTORICAL" else 0} HOST_ROUNDING_PLUS1_MATCH={1 if observed_profile=="HOST_PLUS1" else 0} SOURCE_EXPECTED=17777777777775 HOST_EXPECTED=17777777777776 BOUNDARY_0202_NOT_EXECUTED=1 ROM3035_PIN=1 H9_H10_H11_H13_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H14-NATIVE FAIL '+repr(e))
