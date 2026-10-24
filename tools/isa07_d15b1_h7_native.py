#!/usr/bin/env python3
"""H7 real production CLI: historical mixed-sign additions and private STOP fallbacks."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile

IMAGE='examples/historical/gy1962/au1_addition_0127_0134.k41'
IMAGE_SHA='afeebbc0da7ab28ee2f6b8b3c97894f5cd7225932030ab05ed92112e34676f8d'
DATA={'0010': '00010004002001', '0011': '30004002001000', '0012': '20200100040020', '0013': '00400200100040', '0014': '00200100040020', '0017': '27773775776777'}
GROUPS=[
    # start, after one step, after two, expected result, comparison cell, STOP address
    ('0127','0130','0132','27773775776777','0017','0131'),
    ('0132','0133','0135','00200100040020','0014','0134'),
]
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SIGN=1<<40;MAG=SIGN-1

def signed(v):
 w=int(v,8)
 return -(w&MAG) if w&SIGN else w&MAG

def oracle():
 assert len(DATA)==6 and len(GROUPS)==2
 assert len(set(DATA))==6
 assert all(len(a)==4 and len(w)==14 and set(a+w)<=set('01234567') for a,w in DATA.items())
 for x,y,z in [('0010','0011','0017'),('0012','0013','0014')]:
  # result is the historical reference; its arithmetic equality is CPU-independent
  s=signed(DATA[x])+signed(DATA[y])
  encoded=(SIGN if s<0 else 0) | abs(s)
  assert encoded == int(DATA[z],8),(x,y,z)
 assert int(DATA['0017'],8)&SIGN and not int(DATA['0014'],8)&SIGN
 print('D15B1H7-RUNNER-SELFTEST PASS GROUPS=2/2 INPUTS=6/6 ARITH_ORACLE=2/2 BOTH_SIGNS=1')

def run(exe,image,cwd,start,n,timeout):
 cmd=[str(exe),'image',str(image),start,str(n),'--watch','0347']
 for a in DATA:cmd+=['--watch',a]
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
 image=(root/IMAGE)
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'IMAGE_MUTATED'
 exe=pathlib.Path(a.cli_exe).resolve();assert exe.is_file(),('NO_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'NO_TEMPKYIV'
 cases=pos=neg=0
 with tempfile.TemporaryDirectory(prefix='d15b1h7_cwd_') as d:
  temp=pathlib.Path(d)
  for start,after1,after2,result,reference,stop in GROUPS:
   for cwdname,cwd in [('EXTERNAL',temp),('TEMPKYIV',root/'tempkyiv')]:
    for steps,end in [(1,after1),(2,after2)]:
     p,out,w=run(exe,image,cwd,start,steps,a.timeout)
     good=p.returncode==0 and out==('LIMIT',str(steps),end) and w.get('0347')==result and all(w.get(k)==v for k,v in DATA.items())
     cases+=1;pos+=1
     print(f'D15B1H7-CASE {cases:02d} PROFILE=HISTORICAL START={start} STEPS={steps} CWD={cwdname} RC={p.returncode} RUN={out} RESULT={w.get("0347")} ORACLE={result} '+('PASS' if good else 'MISMATCH'),flush=True)
     if not good:
      print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
      raise AssertionError('HISTORICAL_MISMATCH')
    lines=image.read_text().splitlines(keepends=True)
    anchor=reference+' '+DATA[reference]
    assert sum(v.strip()==anchor for v in lines)==1,('PRIVATE_ANCHOR',reference)
    replacement=reference+' 00000000000000\n'
    private=''.join(replacement if v.strip()==anchor else v for v in lines)
    path=temp/f'private_{start}_{cwdname}.k41';path.write_text(private)
    p,out,w=run(exe,path,cwd,start,3,a.timeout)
    stop_after=format(int(stop,8)+1,'04o')
    good=p.returncode==0 and out==('CPU_STOP','3',stop_after) and w.get('0347')==result
    cases+=1;neg+=1
    print(f'D15B1H7-CASE {cases:02d} PROFILE=PRIVATE_STOP START={start} CWD={cwdname} RC={p.returncode} RUN={out} EXPECTED=CPU_STOP,3,{stop_after} '+('PASS' if good else 'MISMATCH'),flush=True)
    if not good:
     print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
     raise AssertionError('STOP_MISMATCH')
 assert cases==12 and pos==8 and neg==4
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_IMAGE_MUTATION'
 print('D15B1H7-NATIVE PASS CASES=12/12 POSITIVE=8/8 PRIVATE_STOP=4/4 GROUPS=2/2 CWD_PARITY=6/6 HISTORICAL_EXPECTATION_MATCH=1 BOTH_SIGNS=1 CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')

if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H7-NATIVE FAIL '+repr(e))
