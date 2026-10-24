#!/usr/bin/env python3
"""D15/B1-H21: independent exact HOST sign-magnitude oracle, true/false paths."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_absolute_predivision_0234_0240.k41';WORDS={'0234': '06035300000355', '0235': '05035403550240', '0236': '06035400000355', '0237': '01035300000354', '0240': '01035400000356'};SHA={'examples/historical/gy1962/au1_absolute_predivision_0234_0240.k41': 'e404f0c4d7ae4133e8f02c240822c16f067b987084999acf7558caef872fe23d', 'examples/historical/gy1962/au1_absolute_predivision_0234_0240_provenance.tsv': 'dad7042adbd3d4fdb9e3c9b99bf012037a5a7ab962c3a8561807fa1659b9bc2f', 'docs/ISA_07_D15B1_H21_ABSOLUTE_PREDIVISION_BRANCH.md': '608f6a2f9ebfada8376bc3bd015bf94d273b846938bd24f214e144bba9419b40', 'docs/ISA_07_D15B1_H21_DECISION_LEDGER.tsv': 'bf7bd1a53378b410ffb7ae566f77b4d081f6a18f8693acf0a52b1972f6efbb2f'};SIGN=1<<40;MASK=SIGN-1
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SCRATCH=('0353','0354','0355','0356')
SEEDS={
 'SOURCE_ZERO_INIT':None,
 'PRIVATE_TRUE_NONZERO':(0o04000000000000,0o02000000000000),
 'PRIVATE_FALSE_POSITIVE':(0o02000000000000,0o04000000000000),
 'PRIVATE_FALSE_NEGATIVE':(0o22000000000000,0o24000000000000),
}
COUNTS={name:(1,2,3) if name in ('SOURCE_ZERO_INIT','PRIVATE_TRUE_NONZERO') else (1,2,3,4,5) for name in SEEDS}
def decode(w):return (w>>36,(w>>24)&0o3777,(w>>12)&0o3777,w&0o3777)
def mag(w):return w&MASK
def signvalue(w):return -mag(w) if (w&SIGN) else mag(w)
def encode(n):
 assert abs(n)<SIGN,('OVERFLOW',n)
 return abs(n)|(SIGN if n<0 else 0)
def simulate(seed,count,mutant=None):
 mem={0:0}
 for a,w in WORDS.items():mem[int(a,8)]=int(w,8)
 if seed is not None:mem[0o353],mem[0o354]=seed
 if mutant is not None:mem[int(mutant[0],8)]=int(mutant[1],8)
 pc=0o234;visited=[];stages=[]
 for _ in range(count):
  assert f'{pc:04o}' in WORDS and pc!=0o241,'BOUNDARY_0241'
  op,a,b,d=decode(mem[pc]);x=mem.get(a,0);y=mem.get(b,0);visited.append(f'{pc:04o}')
  if op==0o06:
   mem[d]=encode(mag(x)-mag(y));pc+=1
  elif op==0o05:
   pc=d if mag(x)<=mag(y) else pc+1
  elif op==0o01:
   z=signvalue(x)+signvalue(y)
   v=encode(z)
   if z==0 and ((x&SIGN) or (y&SIGN)):v=SIGN # HOST provisional signed zero
   mem[d]=v;pc+=1
  else:raise AssertionError(('OP',op))
  stages.append((f'{pc:04o}',tuple(f'{mem.get(int(a,8),0):014o}' for a in SCRATCH)))
 return f'{pc:04o}',{a:f'{mem.get(int(a,8),0):014o}' for a in SCRATCH},visited,stages
def selftest():
 assert len(WORDS)==5 and len(SEEDS)==4
 assert decode(int(WORDS['0234'],8))[0]==0o06
 assert decode(int(WORDS['0235'],8))[0]==0o05
 assert decode(int(WORDS['0240'],8))[0]==0o01
 expected={'SOURCE_ZERO_INIT':(['0234','0235','0240'],'0241'), 'PRIVATE_TRUE_NONZERO':(['0234','0235','0240'],'0241'), 'PRIVATE_FALSE_POSITIVE':(['0234','0235','0236','0237','0240'],'0241'), 'PRIVATE_FALSE_NEGATIVE':(['0234','0235','0236','0237','0240'],'0241')}
 for name,seed in SEEDS.items():
  vis,pc=expected[name]
  got,regs,path,stages=simulate(seed,len(COUNTS[name]))
  assert (path,got)==(vis,pc) and all(x[0] in WORDS or x[0]=='0241' for x in stages),(name,path,got)
  for count in COUNTS[name]:
   mid,reg,path2,states=simulate(seed,count)
   assert path2==vis[:count] and len(states)==count
 assert simulate(SEEDS['PRIVATE_TRUE_NONZERO'],3)[1]['0355']=='04000000000000'
 assert simulate(SEEDS['PRIVATE_FALSE_POSITIVE'],5)[1]['0355']=='04000000000000'
 assert simulate(SEEDS['PRIVATE_FALSE_NEGATIVE'],5)[1]['0356']=='22000000000000'
 assert simulate(SEEDS['PRIVATE_FALSE_NEGATIVE'],5)[1]['0354']=='22000000000000'
 # Independent discriminator: force a false profile onto TRUE path, and
 # mutate the second subtraction's source address; both must diverge.
 mutant_true=simulate(SEEDS['PRIVATE_FALSE_POSITIVE'],3,('0235','05000000000240'))
 assert mutant_true[0]=='0241' and mutant_true[2]!=expected['PRIVATE_FALSE_POSITIVE'][0][:3]
 mutant_copy=simulate(SEEDS['PRIVATE_FALSE_POSITIVE'],5,('0236','06035300000355'))
 assert mutant_copy[1]['0355'] != simulate(SEEDS['PRIVATE_FALSE_POSITIVE'],5)[1]['0355']
 assert (len(COUNTS['SOURCE_ZERO_INIT'])+len(COUNTS['PRIVATE_TRUE_NONZERO'])+len(COUNTS['PRIVATE_FALSE_POSITIVE'])+len(COUNTS['PRIVATE_FALSE_NEGATIVE']))*2==32
 print('D15B1H21-RUNNER-SELFTEST PASS WORDS=5/5 PROFILES=4/4 BRANCH_PATHS=4/4 HOST_SIGNMAG_ORACLE=1 FALSE_BRANCH_DISCRIMINATOR=1 NEGATIVE_OPERANDS=1 BOUNDARY_0241_NOT_EXECUTED=1')
def run(exe,image,cwd,count,timeout):
 cmd=[str(exe),'image',str(image),'0234',str(count)]
 for a in SCRATCH:cmd+=['--watch',a]
 p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 match=R.search(p.stdout)
 return p,match.groups() if match else None,dict(W.findall(p.stdout))
def main():
 a=argparse.ArgumentParser();a.add_argument('--cli-exe');a.add_argument('--timeout',type=float,default=20);a.add_argument('--self-test',action='store_true');args=a.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'EXE_TIMEOUT_REQUIRED'
 root=pathlib.Path(__file__).resolve().parent.parent;exe=pathlib.Path(args.cli_exe).resolve();img=(root/IMAGE).resolve()
 assert exe.is_file() and img.is_file() and (root/'tempkyiv').is_dir(),'INPUTS'
 assert hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'CANONICAL_PRE'
 original=img.read_text('ascii')
 rows=dict(line.split() for line in original.splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line))
 assert rows==WORDS and not any(a in rows for a in SCRATCH),'SOURCE_MUTATED_OR_PRIVATE_SEED'
 total=0;parity=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h21_external_') as td:
  d=pathlib.Path(td);images={'SOURCE_ZERO_INIT':img}
  for name,seed in SEEDS.items():
   if seed is None:continue
   p=d/(name.lower()+'.k41');p.write_text(original+f'0353 {seed[0]:014o}\n0354 {seed[1]:014o}\n',encoding='ascii',newline='\n');images[name]=p
  pristine={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in images.items()}
  for cwdname,cwd in [('EXTERNAL',d),('TEMPKYIV',root/'tempkyiv')]:
   results=[]
   for name,seed in SEEDS.items():
    for count in COUNTS[name]:
     pc,regs,path,stages=simulate(seed,count)
     p,r,w=run(exe,images[name],cwd,count,args.timeout)
     ok=(p.returncode==0 and r==('LIMIT',str(count),pc) and all(w.get(a)==regs[a] for a in SCRATCH))
     if not ok:
      print(f'D15B1H21-CASE FAIL PROFILE={name} CWD={cwdname} STEPS={count} RC={p.returncode} RUN={r} EXPECT_C={pc} WATCH={w} EXPECT_REGS={regs} VISITED={path}\nSTDOUT={p.stdout[-2500:]}\nSTDERR={p.stderr[-2500:]}')
      raise AssertionError('NATIVE_BRANCH_OR_MEMORY_MISMATCH')
     total+=1;results.append((name,count,r,tuple(w.get(a) for a in SCRATCH)))
     print(f'D15B1H21-CASE {total:02d} PROFILE={name} CWD={cwdname} STEPS={count} RC=0 RUN={r} PATH={"-".join(path)} RAM0353={regs["0353"]} RAM0354={regs["0354"]} RAM0355={regs["0355"]} RAM0356={regs["0356"]} PASS')
   parity.append(results)
  assert parity[0]==parity[1],'CWD_PARITY'
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==pristine[name] for name,p in images.items()),'PRIVATE_IMAGES_MUTATED'
 assert total==32 and hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'TOTAL_OR_CANONICAL_SHA'
 print('D15B1H21-NATIVE-OBSERVATION PASS CASES=32/32 SOURCE_ZERO_INIT=6/6 PRIVATE_TRUE_NONZERO=6/6 PRIVATE_FALSE_POSITIVE=10/10 PRIVATE_FALSE_NEGATIVE=10/10 CWD_PARITY=16/16 BRANCH_TRUE_TO_0240=1 BRANCH_FALSE_VIA_0236_0237=1 NEGATIVE_COPY_SIGN=1 BOUNDARY_0241_NOT_EXECUTED=1 HISTORICAL_ENTRY_SCRATCH=UNKNOWN H19_SEED=UNKNOWN H20_SCRATCH=UNKNOWN H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H21-NATIVE FAIL '+repr(e))
