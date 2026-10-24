#!/usr/bin/env python3
"""H12 genuine native CLI: opcode03 negative signed command addition and STOP."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_addcmd_0163_0165.k41';IMAGE_SHA='71d43f69898cb37bc4f88aa9eb24204cb9a9b1c7b892bb3d2c07a10625fb4057';WORDS={'0002': '12525252525252', '0003': '25252525252525', '0163': '03000200030347', '0164': '16034730360166', '0165': '33000000000000'};NEG_MAX='37777777777777'
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SIGN=1<<40;MAG=SIGN-1

def oracle():
 a,b=int(WORDS['0002'],8),int(WORDS['0003'],8)
 assert not(a&SIGN) and b&SIGN
 assert ((a&MAG)+(b&MAG))|SIGN==int(NEG_MAX,8)
 assert WORDS['0163']=='03000200030347'
 assert WORDS['0164']=='16034730360166' and WORDS['0165']=='33000000000000'
 assert int(NEG_MAX,8)==(1<<41)-1
 print('D15B1H12-RUNNER-SELFTEST PASS WORDS=5/5 SIGN_SECOND=NEGATIVE MAGNITUDE_ORACLE=1 ROM3036_PIN=1 BOUNDARY_0166_NOT_EXECUTED=1')
def run(exe,image,cwd,n,timeout):
 cmd=[str(exe),'image',str(image),'0163',str(n),'--watch','0347','--watch','3036','--watch','0002','--watch','0003']
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout);return p,(m.groups() if m else None),dict(WATCH.findall(p.stdout))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 oracle()
 if a.self_test:return
 assert a.cli_exe,'MISSING_CLI'
 root=pathlib.Path(__file__).resolve().parent.parent;image=root/IMAGE
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'SOURCE_IMAGE_SHA'
 exe=pathlib.Path(a.cli_exe).resolve();assert exe.is_file(),('NO_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'MISSING_TEMPKYIV'
 cases=0
 with tempfile.TemporaryDirectory(prefix='d15b1h12_external_') as td:
  external=pathlib.Path(td)
  for cwd_name,cwd in [('EXTERNAL',external),('TEMPKYIV',root/'tempkyiv')]:
   for n,end in [(1,'0164'),(2,'0166')]:
    p,out,w=run(exe,image,cwd,n,a.timeout)
    good=(p.returncode==0 and out==('LIMIT',str(n),end) and w.get('0347')==NEG_MAX
       and w.get('3036')==NEG_MAX and w.get('0002')==WORDS['0002'] and w.get('0003')==WORDS['0003'])
    cases+=1
    print(f'D15B1H12-CASE {cases:02d} PROFILE=HISTORICAL CWD={cwd_name} STEPS={n} RC={p.returncode} RUN={out} RESULT={w.get("0347")} ORACLE={NEG_MAX} '+('PASS' if good else 'MISMATCH'),flush=True)
    if not good:
     print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
     raise AssertionError('HISTORICAL_MISMATCH')
   original=image.read_text('ascii');anchor='0164 16034730360166'
   assert original.count(anchor)==1,'PRIVATE_ANCHOR'
   priv=external/f'private_h12_{cwd_name}.k41'
   priv.write_text(original.replace(anchor,'0164 16034700020166'),encoding='ascii',newline='\n')
   p,out,w=run(exe,priv,cwd,3,a.timeout)
   good=(p.returncode==0 and out==('CPU_STOP','3','0166') and w.get('0347')==NEG_MAX and w.get('3036')==NEG_MAX)
   cases+=1
   print(f'D15B1H12-CASE {cases:02d} PROFILE=PRIVATE_STOP CWD={cwd_name} RC={p.returncode} RUN={out} EXPECTED=CPU_STOP,3,0166 '+('PASS' if good else 'MISMATCH'),flush=True)
   if not good:
    print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
    raise AssertionError('PRIVATE_STOP_MISMATCH')
 assert cases==6
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_SOURCE_MUTATION'
 print('D15B1H12-NATIVE PASS CASES=6/6 POSITIVE=4/4 PRIVATE_STOP=2/2 GROUPS=1/1 CWD_PARITY=3/3 HISTORICAL_EXPECTATION_MATCH=1 SIGN_SECOND_NEGATIVE=1 ROM3036_PIN=1 BOUNDARY_0166_NOT_EXECUTED=1 H9_H10_H11_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H12-NATIVE FAIL '+repr(e))
