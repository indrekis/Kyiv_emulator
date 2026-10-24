#!/usr/bin/env python3
"""H9 real CPU: two literal machine-code negative-zero cases; printed prose conflicts."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_addition_0143_0150.k41';IMAGE_SHA='9ce78e80c2be1361c25248a8ff06c34cd6a16dd252d219c900264360cb250ac7'
DATA={'0010':'00010004002001','0013':'00400200100040'}
ROM_NEG_ZERO='20000000000000'
GROUPS=[('0143','0144','0146','0010','0145'),('0146','0147','0151','0013','0150')]
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SIGN=1<<40;MASK=SIGN-1
def dec(s):
 w=int(s,8);return -(w&MASK) if w&SIGN else w&MASK
def oracle():
 assert len(DATA)==2 and len(GROUPS)==2
 assert int(ROM_NEG_ZERO,8)&SIGN and dec(ROM_NEG_ZERO)==0
 assert all(0<dec(v)<SIGN and dec(ROM_NEG_ZERO)+dec(v)==dec(v) for v in DATA.values())
 assert DATA['0010']!=DATA['0013'] and DATA['0010']!='00000000000040'
 print('D15B1H9-RUNNER-SELFTEST PASS GROUPS=2/2 INPUTS=2/2 NEGATIVE_ZERO=1 MACHINE_CODE_ORACLE=2/2 PRINTED_PROSE_DISCREPANCY=1')
def run(exe,image,cwd,start,n,timeout):
 cmd=[str(exe),'image',str(image),start,str(n),'--watch','0347','--watch','3026']
 for a in DATA:cmd+=['--watch',a]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout)
 return p,(m.groups() if m else None),dict(WATCH.findall(p.stdout))
def main():
 p=argparse.ArgumentParser();p.add_argument('--cli-exe');p.add_argument('--timeout',type=float,default=20);p.add_argument('--self-test',action='store_true');args=p.parse_args()
 oracle()
 if args.self_test:return
 assert args.cli_exe,'MISSING_CLI_EXE'
 root=pathlib.Path(__file__).resolve().parent.parent;image=root/IMAGE
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'IMAGE_MUTATED'
 exe=pathlib.Path(args.cli_exe).resolve();assert exe.is_file(),('MISSING_EXE',exe)
 assert (root/'tempkyiv').is_dir(),'MISSING_TEMPKYIV'
 cases=positive=negative=0
 with tempfile.TemporaryDirectory(prefix='d15b1h9_cwd_') as tempdir:
  temp=pathlib.Path(tempdir)
  for start,c1,c2,ref,stop in GROUPS:
   expected=DATA[ref];alternate='0013' if ref=='0010' else '0010'
   for cwdname,cwd in [('EXTERNAL',temp),('TEMPKYIV',root/'tempkyiv')]:
    for n,pc in [(1,c1),(2,c2)]:
     proc,out,w=run(exe,image,cwd,start,n,args.timeout)
     ok=(proc.returncode==0 and out==('LIMIT',str(n),pc) and w.get('0347')==expected and w.get('3026')==ROM_NEG_ZERO and all(w.get(a)==v for a,v in DATA.items()))
     cases+=1;positive+=1
     print(f'D15B1H9-CASE {cases:02d} PROFILE=LITERAL_SOURCE START={start} STEPS={n} CWD={cwdname} RC={proc.returncode} RUN={out} RESULT={w.get("0347")} MACHINE_ORACLE={expected} '+('PASS' if ok else 'MISMATCH'),flush=True)
     if not ok:
      print('STDOUT:\n'+proc.stdout[-2500:]+'\nSTDERR:\n'+proc.stderr);raise AssertionError('LITERAL_SOURCE_MISMATCH')
    old=start+' 013026'+ref+'0347';new=start+' 013026'+alternate+'0347'
    lines=image.read_text().splitlines(keepends=True)
    assert sum(line.strip()==old for line in lines)==1,('MUTATION_ANCHOR',old)
    mutated=''.join((new+'\n') if line.strip()==old else line for line in lines)
    path=temp/f'private_{start}_{cwdname}.k41';path.write_text(mutated)
    proc,out,w=run(exe,path,cwd,start,3,args.timeout)
    endpoint=format(int(stop,8)+1,'04o')
    ok=(proc.returncode==0 and out==('CPU_STOP','3',endpoint) and w.get('0347')==DATA[alternate] and w.get('3026')==ROM_NEG_ZERO and all(w.get(a)==v for a,v in DATA.items()))
    cases+=1;negative+=1
    print(f'D15B1H9-CASE {cases:02d} PROFILE=PRIVATE_STOP START={start} CWD={cwdname} RC={proc.returncode} RUN={out} EXPECTED=CPU_STOP,3,{endpoint} '+('PASS' if ok else 'MISMATCH'),flush=True)
    if not ok:
     print('STDOUT:\n'+proc.stdout[-2500:]+'\nSTDERR:\n'+proc.stderr);raise AssertionError('STOP_MISMATCH')
 assert (cases,positive,negative)==(12,8,4)
 assert hashlib.sha256(image.read_bytes()).hexdigest()==IMAGE_SHA,'POST_IMAGE_CHANGED'
 print('D15B1H9-NATIVE PASS CASES=12/12 POSITIVE=8/8 PRIVATE_STOP=4/4 GROUPS=2/2 CWD_PARITY=6/6 LITERAL_MACHINE_CODE_MATCH=1 PRINTED_PROSE_DISCREPANCY=1 NEGATIVE_ZERO_ROM_PIN=1 CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H9-NATIVE FAIL '+repr(e))
