#!/usr/bin/env python3
"""D15/B1-H10: read-only native observation of opcode 07 carry candidate."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_addcyc_0151_0154.k41'
IMAGE_SHA='3ec33a741fe2dee54243f8624c7a2160158e75c3f92c9f401b057434f4454c7c'
WORDS={'0007':'17367573675712','0020':'16757367573624','0151':'07000700070347','0152':'16034700200154','0153':'33000000000000','0154':'31300001100155'}
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SIGN=1<<40;MASK=SIGN-1

def oracle():
 x=int(WORDS['0007'],8);ref=int(WORDS['0020'],8)
 assert x<SIGN and (2*x)>=SIGN and (2*x)<(SIGN<<1)
 historical=(2*x)&MASK;plus1=(2*x+1)&MASK
 assert historical==ref and plus1==ref+1 and plus1!=ref
 assert format(historical,'014o')=='16757367573624'
 assert format(plus1,'014o')=='16757367573625'
 assert WORDS['0154']=='31300001100155'
 print('D15B1H10-RUNNER-SELFTEST PASS WORDS=6/6 CARRY=1 SOURCE_TRUNCATION=16757367573624 HOST_PLUS1=16757367573625 NK3000_NOT_EXECUTED=1')
 return format(historical,'014o'),format(plus1,'014o')

def run(exe,image,cwd,n,timeout):
 cmd=[str(exe),'image',str(image),'0151',str(n),'--watch','0347','--watch','0007','--watch','0020']
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout)
 return p,m.groups() if m else None,dict(WATCH.findall(p.stdout))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 historical,plus1=oracle()
 if a.self_test:return
 assert a.cli_exe,'MISSING_CLI_EXE'
 root=pathlib.Path(__file__).resolve().parent.parent;image=root/IMAGE
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'SOURCE_IMAGE_MUTATED'
 exe=pathlib.Path(a.cli_exe).resolve();assert exe.is_file(),('NO_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'NO_TEMPKYIV'
 cases=0;profiles=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h10_external_') as td:
  for cwdname,cwd in [('EXTERNAL',pathlib.Path(td)),('TEMPKYIV',root/'tempkyiv')]:
   observed=[]
   for n in (1,2):
    p,out,w=run(exe,image,cwd,n,a.timeout)
    word=w.get('0347')
    profile='SOURCE_TRUNCATION' if word==historical else 'HOST_PLUS1' if word==plus1 else 'UNKNOWN'
    end='0152' if n==1 else '0154' if profile=='SOURCE_TRUNCATION' else '0153'
    good=(p.returncode==0 and out==('LIMIT',str(n),end) and
          w.get('0007')==WORDS['0007'] and w.get('0020')==WORDS['0020'] and
          profile!='UNKNOWN')
    cases+=1;observed.append(profile)
    print(f'D15B1H10-CASE {cases:02d} CWD={cwdname} STEPS={n} RC={p.returncode} RUN={out} RESULT={word} SOURCE={historical} HOST_PLUS1={plus1} PROFILE={profile} '+('OBSERVED' if good else 'FAIL'),flush=True)
    if not good:
     print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
     raise AssertionError('UNQUALIFIED_OBSERVATION')
   assert observed[0]==observed[1],('PROFILE_CHANGED',observed)
   profiles.append(observed[0])
   if observed[0]=='HOST_PLUS1':
    # Only fallthrough permits a bounded 3rd step; never execute 0154.
    p,out,w=run(exe,image,cwd,3,a.timeout)
    good=(p.returncode==0 and out==('CPU_STOP','3','0154') and
          w.get('0347')==plus1 and w.get('0007')==WORDS['0007'] and w.get('0020')==WORDS['0020'])
    cases+=1
    print(f'D15B1H10-CASE {cases:02d} CWD={cwdname} STEPS=3 RC={p.returncode} RUN={out} PROFILE=ORIGINAL_FAILURE_STOP '+('OBSERVED' if good else 'FAIL'),flush=True)
    if not good:
     print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
     raise AssertionError('FAILURE_STOP_NOT_OBSERVED')
 assert len(set(profiles))==1,('CWD_DISAGREEMENT',profiles)
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_SOURCE_IMAGE_MUTATED'
 profile=profiles[0];hist=int(profile=='SOURCE_TRUNCATION');host=int(profile=='HOST_PLUS1')
 assert (cases==4 if hist else cases==6),'CASE_COUNT'
 print(f'D15B1H10-NATIVE-OBSERVATION PASS CASES={cases}/{cases} CWD_PARITY=1/1 OBSERVED_PROFILE={profile} HISTORICAL_ORACLE_MATCH={hist} HOST_POLICY_PLUS1_MATCH={host} ORIGINAL_STOP_OBSERVED={host} NK3000_NOT_EXECUTED=1 H9_SOURCE_PROSE_CONFLICT=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H10-NATIVE FAIL '+repr(e))
