#!/usr/bin/env python3
"""H20 native qualification: operand-swap rounded product and bounded failure branch."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_rounded_products_swap_0227_0233.k41';WORDS={'0227': '11035303540355', '0230': '11035403530356', '0231': '16035503560234', '0232': '22035303560233', '0233': '33000000000000'};SHA={'examples/historical/gy1962/au1_rounded_products_swap_0227_0233.k41': '7e942000bb3c94f94a87cce492bb1ab0bb0734f3a436f4f71668b5b04bb37a57', 'examples/historical/gy1962/au1_rounded_products_swap_0227_0233_provenance.tsv': '27f5b7d78a9a00ecefd5fa51a2a653b9dc84c2e7e6342ec406363f839928c50e', 'docs/ISA_07_D15B1_H20_ROUNDED_PRODUCTS_COMPARISON.md': '05279deb87590d0aad7f74b60a8e1a4e9319971cd220c5e907460cf97c7848b4', 'docs/ISA_07_D15B1_H20_DECISION_LEDGER.tsv': '0af1be7351f609e1618aceae0d0fa93472aef8d7857439972b18653a451fe9c3'}
MASK=(1<<40)-1;SIGN=(1<<40);MASK41=(1<<41)-1
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SCRATCH=('0353','0354','0355','0356')
SEEDS={
 'SOURCE_ZERO_INIT':None,
 'PRIVATE_POSITIVE':(0o14000000000000,0o10000000000000),
 'PRIVATE_MIXED_SIGN':(0o14000000000000,0o24000000000000),
 'PRIVATE_MISMATCH_COMPARE':(0o14000000000000,0o10000000000000),
}
def decode(w):return (w>>36,(w>>24)&0o3777,(w>>12)&0o3777,w&0o3777)
def mag(w):return w&MASK
def mulround(a,b):
 n=(mag(a)*mag(b)+(1<<39))>>40
 assert n<SIGN,'UNEXPECTED_OVERFLOW'
 return n | (SIGN if bool(a&SIGN)!=bool(b&SIGN) else 0)
def simulate(seed,count,broken=False):
 mem={0:0}
 for a,w in WORDS.items():mem[int(a,8)]=int(w,8)
 if seed is not None:mem[0o353],mem[0o354]=seed
 if broken:mem[0o231]=0o16035503540234
 pc=0o227; visited=[]
 for _ in range(count):
  assert f'{pc:04o}' in WORDS and pc not in (0o232,0o233),'BOUNDARY_OR_IO_VIOLATION'
  op,a,b,d=decode(mem[pc]);x=mem.get(a,0);y=mem.get(b,0);visited.append(f'{pc:04o}')
  if op==0o11:mem[d]=mulround(x,y);pc+=1
  elif op==0o16:pc=d if x==y else pc+1
  else:raise AssertionError(('UNSUPPORTED_OPCODE',op))
 return f'{pc:04o}',{a:f'{mem.get(int(a,8),0):014o}' for a in SCRATCH},visited
def selftest():
 assert len(WORDS)==5 and WORDS['0231']=='16035503560234' and WORDS['0232'][:2]=='22'
 assert len(SEEDS)==4 and all(len(v)==2 for v in SEEDS.values() if v is not None)
 assert mulround(*SEEDS['PRIVATE_POSITIVE'])==0o06000000000000
 assert mulround(*SEEDS['PRIVATE_MIXED_SIGN'])==0o23000000000000
 assert mulround(*SEEDS['PRIVATE_POSITIVE'])==mulround(*reversed(SEEDS['PRIVATE_POSITIVE']))
 for name,seed in SEEDS.items():
  bad=name=='PRIVATE_MISMATCH_COMPARE'
  pc,reg,visited=simulate(seed,3,bad)
  assert visited==['0227','0230','0231'] and pc==('0232' if bad else '0234'),(name,pc,visited)
  assert reg['0355']==reg['0356'],name
  for count in [1,2]:
   c,r,v=simulate(seed,count,bad); assert c in ('0230','0231') and v==visited[:count]
 assert simulate(None,3)[1]['0355']=='00000000000000'
 print('D15B1H20-RUNNER-SELFTEST PASS WORDS=5/5 PROFILES=4/4 HOST_INTEGER_ROUNDING_ORACLE=1 MUTATED_COMPARE_FALSE=1 FAIL_IO_NOT_EXECUTED=1 BOUNDARIES_0232_0234_NOT_EXECUTED=1')
def run(exe,img,cwd,count,timeout):
 cmd=[str(exe),'image',str(img),'0227',str(count)]
 for a in SCRATCH:cmd+=['--watch',a]
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
 original=img.read_text('ascii')
 words={a:w for a,w in [line.split() for line in original.splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)]}
 assert words==WORDS and not any(a in words for a in ['0353','0354','0234']),'SOURCE_CHANGED'
 total=0;parity=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h20_external_') as td:
  d=pathlib.Path(td);images={'SOURCE_ZERO_INIT':img}
  for name,seed in SEEDS.items():
   if seed is None:continue
   p=d/(name.lower()+'.k41')
   addition=f'0353 {seed[0]:014o}\n0354 {seed[1]:014o}\n'
   if name=='PRIVATE_MISMATCH_COMPARE':
    assert '0231 16035503560234' in original
    content=original.replace('0231 16035503560234','0231 16035503540234')+addition
   else:content=original+addition
   p.write_text(content,encoding='ascii',newline='\n');images[name]=p
  pristine={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in images.items()}
  for cwdname,cwd in [('EXTERNAL',d),('TEMPKYIV',root/'tempkyiv')]:
   results=[]
   for name,seed in SEEDS.items():
    mismatch=name=='PRIVATE_MISMATCH_COMPARE'
    for count in (1,2,3):
     pc,regs,visited=simulate(seed,count,mismatch)
     p,r,w=run(exe,images[name],cwd,count,args.timeout)
     ok=(p.returncode==0 and r==('LIMIT',str(count),pc) and all(w.get(a)==regs[a] for a in SCRATCH))
     if not ok:
      print(f'D15B1H20-CASE FAIL PROFILE={name} CWD={cwdname} STEPS={count} RC={p.returncode} RUN={r} EXPECT_PC={pc} WATCH={w} EXPECT_REGS={regs}\nSTDOUT={p.stdout[-2200:]}\nSTDERR={p.stderr[-2200:]}')
      raise AssertionError('PRODUCT_BRANCH_MEMORY_OR_BOUNDARY_MISMATCH')
     total+=1;results.append((name,count,r,tuple(w.get(a) for a in SCRATCH)))
     print(f'D15B1H20-CASE {total:02d} PROFILE={name} CWD={cwdname} STEPS={count} RC=0 RUN={r} RAM0353={regs["0353"]} RAM0354={regs["0354"]} RAM0355={regs["0355"]} RAM0356={regs["0356"]} PASS')
   parity.append(results)
  assert parity[0]==parity[1],'CWD_PARITY'
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==pristine[name] for name,p in images.items()),'PRIVATE_MUTATED'
 assert total==24 and hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_MUTATED'
 print('D15B1H20-NATIVE-OBSERVATION PASS CASES=24/24 SOURCE_ZERO_INIT=6/6 PRIVATE_POSITIVE=6/6 PRIVATE_MIXED_SIGN=6/6 PRIVATE_MISMATCH_COMPARE=6/6 CWD_PARITY=12/12 OPERAND_SWAP_EQUALITY=1 NEGATIVE_PRODUCT=1 PRIVATE_FALSE_C0232=1 SOURCE_TRUE_C0234=1 IO_0232_NOT_EXECUTED=1 STOP_0233_NOT_EXECUTED=1 BOUNDARY_0234_NOT_EXECUTED=1 HISTORICAL_SCRATCH_INPUTS=UNKNOWN H19_SEED=UNKNOWN H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H20-NATIVE FAIL '+repr(e))
