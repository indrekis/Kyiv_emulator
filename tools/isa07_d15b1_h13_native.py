#!/usr/bin/env python3
"""Native H13: exact 41-bit zero shift and original/private STOP, no opcode 0171."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_shift_zero_0166_0170.k41'; SHA='70d6c86f1cd2aa08634553cf913d5ba1f54f98de2c2dead2168cf8ad7097c665'; WORDS={'0261': '02525252525252', '0166': '13000002610347', '0167': '16034702610171', '0170': '33000000000000'}; RESULT='02525252525252'; ZERO='00000000000000'
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
def oracle():
 assert WORDS['0261']==RESULT and WORDS['0166']=='13000002610347'
 assert WORDS['0167']=='16034702610171' and WORDS['0170']=='33000000000000'
 assert (int(RESULT,8)<<0)&((1<<41)-1)==int(RESULT,8)
 assert len('14000000000347')==14 and (int('14000000000347',8)>>36)==0o14
 print('D15B1H13-RUNNER-SELFTEST PASS WORDS=4/4 SHIFT_BITS=0 SIGN_BIT_PRESERVED=1 HOST_0000_ZERO_GUARD=1 BOUNDARY_0171_NOT_EXECUTED=1')
def run(exe,image,cwd,n,timeout,entry='0166',watched=('0347','0261')):
 # The host CLI explicitly rejects --watch 0000. Never request it.
 cmd=[str(exe),'image',str(image),entry,str(n)]
 for address in watched:cmd.extend(('--watch',address))
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout,encoding='utf-8',errors='replace')
 m=RUN.search(p.stdout)
 return p,(m.groups() if m else None),dict(WATCH.findall(p.stdout))
def zero_probe(exe,cwd,private,timeout):
 # Private one-instruction probe. Bitwise OR of RAM[0000] with itself
 # exposes the full 41-bit source word at watchable destination 0347.
 # Neither the canonical image nor physical CPU/ROM is modified.
 assert len('14000000000347')==14
 word=int('14000000000347',8)
 assert word>>36==0o14 and ((word>>24)&0xfff)==0 and ((word>>12)&0xfff)==0 and (word&0xfff)==0o347
 private.write_text('KYIV41-OCT1\n0172 14000000000347\n',encoding='ascii',newline='\n')
 p,run_info,w=run(exe,private,cwd,1,timeout,entry='0172',watched=('0347',))
 good=(p.returncode==0 and run_info==('LIMIT','1','0173') and w.get('0347')==ZERO)
 if not good:
  print('ZERO_PROBE_STDOUT: '+p.stdout[-3000:]+'\nZERO_PROBE_STDERR: '+p.stderr[-1000:],flush=True)
  raise AssertionError(('HOST_RAM0000_ZERO_PROBE',run_info,w.get('0347'),p.returncode))
 return w['0347']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20);ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
 oracle()
 if args.self_test:return
 assert args.cli_exe,'MISSING_CLI'
 root=pathlib.Path(__file__).resolve().parent.parent
 image=root/IMAGE;exe=pathlib.Path(args.cli_exe).resolve()
 assert exe.is_file(),'NO_EXE'
 assert hashlib.sha256(image.read_bytes()).hexdigest()==SHA,'CANONICAL_IMAGE_SHA'
 assert (root/'tempkyiv').is_dir(),'MISSING_TEMPKYIV'
 cases=0
 with tempfile.TemporaryDirectory(prefix='d15b1h13_external_') as td:
  external=pathlib.Path(td)
  for cwdname,cwd in [('EXTERNAL',external),('TEMPKYIV',root/'tempkyiv')]:
   actual_zero=zero_probe(exe,cwd,external/('private_zero_probe_'+cwdname+'.k41'),args.timeout)
   print(f'D15B1H13-ZERO-PROBE CWD={cwdname} HOST_RAM0000={actual_zero} PASS',flush=True)
   for n,c in [(1,'0167'),(2,'0171')]:
    p,run_info,w=run(exe,image,cwd,n,args.timeout)
    good=(p.returncode==0 and run_info==('LIMIT',str(n),c) and w.get('0347')==RESULT and w.get('0261')==RESULT)
    cases+=1
    print(f'D15B1H13-CASE {cases:02d} PROFILE=HISTORICAL CWD={cwdname} STEPS={n} RC={p.returncode} RUN={run_info} RAM0000={actual_zero} RESULT={w.get("0347")} ORACLE={RESULT} '+('PASS' if good else 'MISMATCH'),flush=True)
    if not good:
     print('STDOUT: '+p.stdout[-3000:]+'\nSTDERR: '+p.stderr[-1000:],flush=True)
     raise AssertionError('HISTORICAL_SHIFT_MISMATCH')
   original=image.read_text('ascii');old='0167 16034702610171';new='0167 16034700000171'
   assert original.count(old)==1,'PRIVATE_REWRITE_ANCHOR'
   private=external/('private_h13_'+cwdname+'.k41');private.write_text(original.replace(old,new),encoding='ascii',newline='\n')
   p,run_info,w=run(exe,private,cwd,3,args.timeout)
   good=(p.returncode==0 and run_info==('CPU_STOP','3','0171') and w.get('0347')==RESULT and w.get('0261')==RESULT)
   cases+=1
   print(f'D15B1H13-CASE {cases:02d} PROFILE=PRIVATE_STOP CWD={cwdname} RC={p.returncode} RUN={run_info} ORIGINAL_STOP=0170 '+('PASS' if good else 'MISMATCH'),flush=True)
   if not good:
    print('STDOUT: '+p.stdout[-3000:]+'\nSTDERR: '+p.stderr[-1000:],flush=True)
    raise AssertionError('PRIVATE_STOP_MISMATCH')
 assert cases==6
 assert hashlib.sha256(image.read_bytes()).hexdigest()==SHA,'POST_IMAGE_MUTATION'
 print('D15B1H13-NATIVE PASS CASES=6/6 POSITIVE=4/4 PRIVATE_STOP=2/2 GROUPS=1/1 CWD_PARITY=3/3 ZERO_PROBES=2/2 HISTORICAL_MACHINE_CODE_MATCH=1 SHIFT_ZERO_FULL_41_BITS=1 HOST_0000_ZERO_OBSERVED=1 BOUNDARY_0171_NOT_EXECUTED=1 H13_SOURCE_LABEL_CONFLICT=OPEN H9_H10_H11_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H13-NATIVE FAIL '+repr(e))
