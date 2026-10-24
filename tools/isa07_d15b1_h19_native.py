#!/usr/bin/env python3
"""H19 source-exact pseudorandom block: independent integer HOST-policy trace."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_pseudorandom_0214_0226.k41';WORDS={'0260': '01777777777777', '0214': '01035300000354', '0215': '10035430420353', '0216': '31035302210217', '0217': '02000003530353', '0220': '01035330420353', '0221': '15035402600352', '0222': '12035230440352', '0223': '15035430440351', '0224': '05000003510226', '0225': '02000003520352', '0226': '17035203530353'};SHA={'examples/historical/gy1962/au1_pseudorandom_0214_0226.k41': '4d0e09f25b75f0aa280a758324cd3346c9af77149a77d5e584cc09c4c22943d9', 'examples/historical/gy1962/au1_pseudorandom_0214_0226_provenance.tsv': 'df9bda622cf5f7f1ef349c8d3d39bc059a6744eb3518a7fa81a2127ffa35845f', 'docs/ISA_07_D15B1_H19_PSEUDORANDOM_CONTROL_TRACE.md': '3809b9d50b90640ec64cb4606d59cd9a6179c236d5815eb0becff365016b4684', 'docs/ISA_07_D15B1_H19_DECISION_LEDGER.tsv': '22b48a00828dbe9afd4dd57c279ec04214193a168fdfa4fa34619966ed21db31'}
ROM={0o3042:0o10000000000000,0o3044:0o02000000000000}
MASK=(1<<40)-1;SIGN=(1<<40); MASK41=(1<<41)-1
R=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
W=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
SCRATCH=('0351','0352','0353','0354');SEEDS={'SOURCE':None,'PRIVATE_PLUS_ONE':0o1,'PRIVATE_NEGATIVE_ONE':SIGN|1}
PATHS={'SOURCE':['0214','0215','0216','0221','0222','0223','0224','0226'],
       'PRIVATE_PLUS_ONE':['0214','0215','0216','0221','0222','0223','0224','0226'],
       'PRIVATE_NEGATIVE_ONE':['0214','0215','0216','0217','0220','0221','0222','0223','0224','0226']}
def pack(op,a,b,d):return (op<<36)|(a<<24)|(b<<12)|d
def sig(w):return -1 if (w&SIGN) else 1
def mag(w):return w&MASK
def num(w):return sig(w)*mag(w)
def signmag(value,negzero=False):
 n=abs(value)
 assert n<SIGN,('UNEXPECTED_ARITH_OVERFLOW',value)
 return n | (SIGN if (value<0 or value==0 and negzero) else 0)
def simulate(seed, count):
 mem={0:0,0o260:int(WORDS['0260'],8),**ROM}
 for a,w in WORDS.items():mem[int(a,8)]=int(w,8)
 if seed is not None:mem[0o353]=seed
 pc=0o214
 visited=[]
 for _ in range(count):
  w=mem.get(pc,0);op=w>>36;a=(w>>24)&0o3777;b=(w>>12)&0o3777;d=w&0o3777
  assert f'{pc:04o}' in WORDS and WORDS[f'{pc:04o}']==f'{w:014o}','MISMATCH_SOURCE_WORD'
  x=mem.get(a,0);y=mem.get(b,0);visited.append(f'{pc:04o}')
  if op==0o01:
   val=num(x)+num(y);mem[d]=signmag(val,negzero=(val==0 and bool((x|y)&SIGN)));pc+=1
  elif op==0o02:
   val=num(x)-num(y);mem[d]=signmag(val,negzero=(val==0));pc+=1
  elif op==0o10:
   val=(mag(x)*mag(y))>>40;mem[d]=val | (SIGN if sig(x)!=sig(y) else 0);pc+=1
  elif op==0o31:
   pc=d if (x&SIGN) else b
  elif op==0o15:
   mem[d]=x&y;pc+=1
  elif op==0o12:
   assert mag(y)!=0,'DIV_ZERO'
   val=(mag(x)<<40)//mag(y)
   assert val<SIGN,'DIV_OVERFLOW'
   mem[d]=val | (SIGN if sig(x)!=sig(y) else 0);pc+=1
  elif op==0o05:
   pc=d if mag(x)<=mag(y) else pc+1
  elif op==0o17:
   mem[d]=(~(x^y))&MASK41;pc+=1
  else:raise AssertionError(('UNMODELED_OPCODE',op))
 return f'{pc:04o}',{a:f'{mem.get(int(a,8),0):014o}' for a in SCRATCH},visited

def selftest():
 assert len(WORDS)==12 and WORDS['0216']=='31035302210217' and WORDS['0260']=='01777777777777'
 assert set(SEEDS)==set(PATHS) and len(SCRATCH)==4
 assert all(0<=n<=MASK41 for n in (SIGN|1,MASK41))
 for name,seed in SEEDS.items():
  path=PATHS[name];pc,regs,visited=simulate(seed,len(path))
  assert pc=='0227' and visited==path,(name,pc,visited,path)
  mid,midregs,visited3=simulate(seed,3)
  assert mid==('0217' if seed==SIGN|1 else '0221'),(name,mid)
  assert visited3==path[:3]
  assert '0225' not in visited
 assert simulate(None,8)[1]['0353']==f'{MASK41:014o}'
 assert simulate(1,8)[1]['0353']!=simulate(None,8)[1]['0353'],'SEED_DISCRIMINATOR'
 print('D15B1H19-RUNNER-SELFTEST PASS WORDS=12/12 PROFILES=3/3 BRANCH_PATHS=3/3 HOST_INTEGER_ORACLE=1 SOURCE_SEED_UNPRINTED=1 BOUNDARY_0227_NOT_EXECUTED=1')
def run(exe,img,cwd,count,timeout):
 cmd=[str(exe),'image',str(img),'0214',str(count)]
 for a in SCRATCH:cmd+=['--watch',a]
 cmd+=['--watch','0260']
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
 assert not re.search(r'^035[1-4] ',original,re.M),'UNPRINTED_SEED_IN_SOURCE'
 original_records={a:w for a,w in [line.split() for line in original.splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)]}
 assert original_records==WORDS,'SOURCE_IMAGES_DIFFER'
 cases=[(name,SEEDS[name],PATHS[name]) for name in ['SOURCE','PRIVATE_PLUS_ONE','PRIVATE_NEGATIVE_ONE']]
 total=0;parity=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h19_external_') as td:
  d=pathlib.Path(td);images={'SOURCE':img}
  for name,seed,path in cases:
   if seed is None:continue
   p=d/(name.lower()+'.k41')
   p.write_text(original+f'0353 {seed:014o}\n',encoding='ascii',newline='\n')
   assert p.read_text('ascii').count(f'0353 {seed:014o}')==1
   images[name]=p
  pristine={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in images.items()}
  for cn,cwd in [('EXTERNAL',d),('TEMPKYIV',root/'tempkyiv')]:
   results=[]
   for name,seed,path in cases:
    for n in [3,len(path)]:
     pc,reg,visited=simulate(seed,n)
     p,r,w=run(exe,images[name],cwd,n,args.timeout)
     ok=(p.returncode==0 and r==('LIMIT',str(n),pc) and all(w.get(a)==reg[a] for a in SCRATCH) and w.get('0260')==WORDS['0260'])
     if not ok:
      print(f'D15B1H19-CASE FAIL CWD={cn} PROFILE={name} STEPS={n} RC={p.returncode} RUN={r} EXPECT={pc} WATCH={w} EXPECT_REGS={reg}\nSTDOUT={p.stdout[-2400:]}\nSTDERR={p.stderr[-2400:]}')
      raise AssertionError('TRACE_STATE_OR_BOUNDARY_MISMATCH')
     total+=1;results.append((name,n,r,tuple(w.get(a) for a in SCRATCH)))
     branch='NEGATIVE_TO_0217' if name=='PRIVATE_NEGATIVE_ONE' else 'NONNEGATIVE_TO_0221'
     print(f'D15B1H19-CASE {total:02d} PROFILE={name} CWD={cn} STEPS={n} RC=0 RUN={r} BRANCH={branch} RAM0351={reg["0351"]} RAM0352={reg["0352"]} RAM0353={reg["0353"]} RAM0354={reg["0354"]} PASS')
   parity.append(results)
  assert parity[0]==parity[1],'CWD_PARITY'
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==pristine[name] for name,p in images.items()),'PRIVATE_IMAGE_MUTATED'
 assert total==12 and hashlib.sha256(img.read_bytes()).hexdigest()==SHA[IMAGE],'SOURCE_MUTATED'
 print('D15B1H19-NATIVE-OBSERVATION PASS CASES=12/12 SOURCE_ZERO_INIT=4/4 PRIVATE_PLUS_ONE=4/4 PRIVATE_NEGATIVE_ONE=4/4 CWD_PARITY=6/6 NEGATIVE_BRANCH_0217_OBSERVED=1 NONNEGATIVE_BRANCH_0221_OBSERVED=1 BOUNDARY_0227_NOT_EXECUTED=1 HISTORICAL_SEED=UNKNOWN HISTORICAL_RANDOM_SEQUENCE_ORACLE=0 SOURCE_WORDS=12/12 H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H19-NATIVE FAIL '+repr(e))
