#!/usr/bin/env python3
"""H8: negative-zero additions in real production CPU; two CWD and STOP mutant."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_addition_0135_0142.k41'
IMAGE_SHA='ea33ba319d6a6d86f789f71e18eaab54ff991c574507b099752685fd44633a45'
DATA={'0015':'00000000000001','0016':'00000000000040'}
ROM_NEG_ZERO='20000000000000'
GROUPS=[('0135','0136','0140','0015','0137'),('0140','0141','0143','0016','0142')]
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SIGN=1<<40;MAG=SIGN-1

def signed(s):
 w=int(s,8)
 return -(w&MAG) if w&SIGN else w&MAG

def oracle():
 assert len(DATA)==2 and len(GROUPS)==2
 assert signed(ROM_NEG_ZERO)==0 and (int(ROM_NEG_ZERO,8)&SIGN)!=0
 assert all(signed(ROM_NEG_ZERO)+signed(v)==signed(v) for v in DATA.values())
 assert all(0<int(v,8)<SIGN for v in DATA.values()),'EXPECTED_RESULTS_POSITIVE'
 assert set(DATA)=={g[3] for g in GROUPS}
 print('D15B1H8-RUNNER-SELFTEST PASS GROUPS=2/2 SOURCE_DATA=2/2 NEGATIVE_ZERO=1 ARITH_ORACLE=2/2 SIGN_BIT=1')

def run(exe,image,cwd,start,steps,timeout):
 cmd=[str(exe),'image',str(image),start,str(steps),'--watch','0347','--watch','3026']
 for address in DATA:cmd+=['--watch',address]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout)
 return p,(m.groups() if m else None),dict(WATCH.findall(p.stdout))

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20)
 ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 oracle()
 if a.self_test:return
 assert a.cli_exe,'MISSING_CLI_EXE'
 root=pathlib.Path(__file__).resolve().parent.parent
 image=root/IMAGE
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'CANONICAL_IMAGE_MISMATCH'
 exe=pathlib.Path(a.cli_exe).resolve();assert exe.is_file(),('NO_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'NO_TEMPKYIV'
 cases=pos=negative=0
 with tempfile.TemporaryDirectory(prefix='d15b1h8_cwd_') as temp_name:
  temp=pathlib.Path(temp_name)
  for start,after1,after2,ref,stop in GROUPS:
   result=DATA[ref]
   for cwd_name,cwd in [('EXTERNAL',temp),('TEMPKYIV',root/'tempkyiv')]:
    for steps,final in [(1,after1),(2,after2)]:
     p,out,watch=run(exe,image,cwd,start,steps,a.timeout)
     good=(p.returncode==0 and out==('LIMIT',str(steps),final)
           and watch.get('0347')==result and watch.get('3026')==ROM_NEG_ZERO
           and all(watch.get(k)==v for k,v in DATA.items()))
     cases+=1;pos+=1
     print(f'D15B1H8-CASE {cases:02d} PROFILE=HISTORICAL START={start} STEPS={steps} CWD={cwd_name} RC={p.returncode} RUN={out} RESULT={watch.get("0347")} ROM3026={watch.get("3026")} ORACLE={result} '+('PASS' if good else 'MISMATCH'),flush=True)
     if not good:
      print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
      raise AssertionError('HISTORICAL_MISMATCH')
    lines=image.read_text().splitlines(keepends=True)
    # In this historical program reference aliases the ADD source operand.
    # Changing the data reference would alter both sides of equality; instead
    # retarget ONLY the private ADD's second operand. The historical JE/STOP
    # and both source data words remain verbatim, so mismatch is guaranteed.
    orig=start+' '+('01302600150347' if ref=='0015' else '01302600160347')
    mutant=start+' '+('01302600160347' if ref=='0015' else '01302600150347')
    other=DATA['0016' if ref=='0015' else '0015']
    assert sum(v.strip()==orig for v in lines)==1,('PRIVATE_ADD_ANCHOR',start)
    private=''.join((mutant+'\n') if v.strip()==orig else v for v in lines)
    path=temp/f'private_{start}_{cwd_name}.k41';path.write_text(private)
    p,out,watch=run(exe,path,cwd,start,3,a.timeout)
    end=format(int(stop,8)+1,'04o')
    good=(p.returncode==0 and out==('CPU_STOP','3',end)
          and watch.get('0347')==other and watch.get('3026')==ROM_NEG_ZERO
          and all(watch.get(k)==v for k,v in DATA.items()))
    cases+=1;negative+=1
    print(f'D15B1H8-CASE {cases:02d} PROFILE=PRIVATE_STOP START={start} CWD={cwd_name} RC={p.returncode} RUN={out} EXPECTED=CPU_STOP,3,{end} '+('PASS' if good else 'MISMATCH'),flush=True)
    if not good:
     print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
     raise AssertionError('STOP_MISMATCH')
 assert cases==12 and pos==8 and negative==4
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_IMAGE_MUTATED'
 print('D15B1H8-NATIVE PASS CASES=12/12 POSITIVE=8/8 PRIVATE_STOP=4/4 GROUPS=2/2 CWD_PARITY=6/6 NEGATIVE_ZERO_ROM_PIN=1 RESULT_SIGN_POSITIVE=1 HISTORICAL_EXPECTATION_MATCH=1 CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')

if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H8-NATIVE FAIL '+repr(e))
