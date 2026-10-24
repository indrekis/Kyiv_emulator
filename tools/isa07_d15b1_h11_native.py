#!/usr/bin/env python3
"""D15/B1-H11: bounded native observations of two negative-zero subtraction tests."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_subtraction_0155_0162.k41'
IMAGE_SHA='fd339a4302279a9c010df4cc43f66127fb59c9a10ab8d7f67935cc6e0d8a8740'
WORDS={'0002': '12525252525252', '0003': '25252525252525', '0155': '02000200020347', '0156': '16034730260160', '0157': '33000000000000', '0160': '06000300030347', '0161': '16034730260163', '0162': '33000000000000'}
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
NEG='20000000000000';POS='00000000000000'
GROUPS=[('0155','0156','0160','0002','SUB'),('0160','0161','0163','0003','SUBABS')]

def oracle():
 assert len(WORDS)==8 and all(len(a)==4 and len(w)==14 and set(a+w)<=set('01234567') for a,w in WORDS.items())
 assert WORDS['0155']=='02000200020347' and WORDS['0160']=='06000300030347'
 assert WORDS['0156']=='16034730260160' and WORDS['0161']=='16034730260163'
 assert WORDS['0157']==WORDS['0162']=='33000000000000'
 assert int(NEG,8)==1<<40 and int(POS,8)==0
 assert int(WORDS['0002'],8)&((1<<40)-1)>0 and int(WORDS['0003'],8)&((1<<40)-1)>0
 print('D15B1H11-RUNNER-SELFTEST PASS WORDS=8/8 GROUPS=2/2 SIGNED_ZERO_DISCRIMINATOR=1 NK3000_NOT_EXECUTED=1')

def run(exe,image,cwd,start,n,timeout):
 cmd=[str(exe),'image',str(image),start,str(n),'--watch','0347','--watch','3026','--watch','0002','--watch','0003']
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout)
 return p,m.groups() if m else None,dict(WATCH.findall(p.stdout))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 oracle()
 if a.self_test:return
 assert a.cli_exe,'MISSING_CLI_EXE'
 root=pathlib.Path(__file__).resolve().parent.parent;image=root/IMAGE
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'CANONICAL_IMAGE_CHANGED'
 exe=pathlib.Path(a.cli_exe).resolve();assert exe.is_file(),('NO_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'NO_TEMPKYIV'
 cases=0;first=[];second=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h11_external_') as td:
  external=pathlib.Path(td)
  for start,after1,after2,source,kind in GROUPS:
   for cwd_name,cwd in [('EXTERNAL',external),('TEMPKYIV',root/'tempkyiv')]:
    observed=[]
    for n in (1,2):
     p,out,w=run(exe,image,cwd,start,n,a.timeout)
     word=w.get('0347');profile='NEGATIVE_ZERO' if word==NEG else 'POSITIVE_ZERO' if word==POS else 'UNKNOWN'
     destination=after1 if n==1 else after2 if profile=='NEGATIVE_ZERO' else ('0157' if kind=='SUB' else '0162')
     good=(p.returncode==0 and out==('LIMIT',str(n),destination) and profile!='UNKNOWN' and
           w.get('3026')==NEG and w.get('0002')==WORDS['0002'] and w.get('0003')==WORDS['0003'])
     cases+=1;observed.append(profile)
     print(f'D15B1H11-CASE {cases:02d} KIND={kind} CWD={cwd_name} STEPS={n} RC={p.returncode} RUN={out} RESULT={word} HIST_NEGZERO={NEG} PROFILE={profile} '+('OBSERVED' if good else 'MISMATCH'),flush=True)
     if not good:
      print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
      raise AssertionError('UNQUALIFIED_ZERO_OBSERVATION')
    assert observed[0]==observed[1],('PROFILE_CHANGED',kind,observed)
    if kind=='SUB':
     first.append(observed[0]);assert observed[0]=='NEGATIVE_ZERO','OP02_SOURCE_REGRESSION'
     # Synthetic failure of JE, NOT a historical source change.
     original=image.read_text(encoding='ascii')
     assert original.count('0156 16034730260160')==1
     private=external/f'private_0155_{cwd_name}.k41'
     private.write_text(original.replace('0156 16034730260160','0156 16034700020160'),encoding='ascii',newline='\n')
     p,out,w=run(exe,private,cwd,start,3,a.timeout)
     good=p.returncode==0 and out==('CPU_STOP','3','0160') and w.get('0347')==NEG
     cases+=1
     print(f'D15B1H11-CASE {cases:02d} KIND=SUB_PRIVATE_STOP CWD={cwd_name} RC={p.returncode} RUN={out} '+('OBSERVED' if good else 'MISMATCH'),flush=True)
     if not good:raise AssertionError('SUB_PRIVATE_STOP_NOT_OBSERVED')
    else:
     second.append(observed[0])
     if observed[0]=='POSITIVE_ZERO':
      # Only failing JE branch permits executing the original STOP at 0162.
      p,out,w=run(exe,image,cwd,start,3,a.timeout)
      good=p.returncode==0 and out==('CPU_STOP','3','0163') and w.get('0347')==POS
      cases+=1
      print(f'D15B1H11-CASE {cases:02d} KIND=SUBABS_ORIGINAL_STOP CWD={cwd_name} RC={p.returncode} RUN={out} '+('OBSERVED' if good else 'MISMATCH'),flush=True)
      if not good:raise AssertionError('SUBABS_ORIGINAL_STOP_NOT_OBSERVED')
 assert len(set(first))==len(set(second))==1 and first[0]=='NEGATIVE_ZERO','CWD_PARITY'
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_CANONICAL_MUTATION'
 source_match=int(second[0]=='NEGATIVE_ZERO');host_match=int(second[0]=='POSITIVE_ZERO')
 assert cases==(10 if source_match else 12),('COUNT',cases)
 print(f'D15B1H11-NATIVE-OBSERVATION PASS CASES={cases}/{cases} GROUPS=2/2 CWD_PARITY=1/1 SUB_NEGZERO_MATCH=1 SUBABS_NEGZERO_MATCH={source_match} SUBABS_HOST_POSZERO_MATCH={host_match} ORIGINAL_SECOND_STOP_OBSERVED={host_match} NK3000_NOT_EXECUTED=1 H9_CONFLICT=OPEN_UNCHANGED H10_CONFLICT=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H11-NATIVE FAIL '+repr(e))
