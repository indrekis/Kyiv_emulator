#!/usr/bin/env python3
"""H22 31-word source block: independent HOST interpreter, bounded multi-entry probes.

SOURCE_ZERO_INIT represents host RAM initialization, NOT historical seeded state.
No actual I/O commands (0252), program boundary 0300, or external branches are executed.
"""
from __future__ import annotations
import argparse,csv,hashlib,pathlib,re,subprocess,tempfile

IMAGE='examples/historical/gy1962/au1_batch31_0241_0277.k41'
SIGN=1<<40; MASK=SIGN-1
RX_RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
RX_WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
WATCH=('0347','0350','0352','0353','0354','0355','0356','0357')
ROM={0o3026:SIGN,0o3035:MASK}
# Six independent start-PC families, stop-checkpoint or boundary limits for each.
# Seed entries are explicitly PRIVATE; historical scratch at entry is UNKNOWN.
HALF=0o10000000000000
QUARTER=0o04000000000000
NEG_ONE=SIGN|1
PROFILES=[
 # (name, start, extra_ram, private instruction replacement, checkpoint counts)
 ('A_SOURCE_LOOP','0241',{}, {}, (1,2,3,4,5,6)),
 ('A_PRIVATE_EXIT','0241',{'0355':MASK},{},(1,2,3,4,5)),
 ('AB_PRIVATE_JOIN','0241',{'0355':MASK},{},(6,7,8)),
 ('B_PRIVATE_DIVZERO','0247',{}, {},(1,)),
 ('B_PRIVATE_EQUAL','0247',{'0354':QUARTER,'0355':HALF,'0356':HALF},{},(1,2,3)),
 ('B_PRIVATE_FALSE','0247',{'0354':QUARTER,'0355':HALF,'0356':QUARTER},{},(1,2,3)),
 ('C_SOURCE_0254','0254',{}, {},(1,)),
 ('C_SOURCE_0255','0255',{}, {},(1,)),
 ('C_SOURCE_0256','0256',{}, {},(1,)),
 ('C_SOURCE_0257','0257',{}, {},(1,)),
 ('C_PRIVATE_NEGATIVE','0254',{'0353':NEG_ONE},{'0254':'31035302140043'},(1,)),
 ('C_PRIVATE_NONNEG','0254',{'0353':1},{'0254':'31035302140043'},(1,)),
 ('E_SOURCE_NORMALIZE','0263',{}, {},(1,2,3,4)),
 ('F_SOURCE_NORMALIZE','0270',{}, {},(1,2,3,4)),
 ('F_PRIVATE_SIGNED_ZERO','0273',{'0350':SIGN},{},(1,2,3)),
 ('F_DIRECT_NEGZERO','0275',{}, {},(1,2)),
]

EXPECTED_C={
 'A_SOURCE_LOOP':'0242','A_PRIVATE_EXIT':'0247','AB_PRIVATE_JOIN':'0254','B_PRIVATE_DIVZERO':'0250',
 'B_PRIVATE_EQUAL':'0254','B_PRIVATE_FALSE':'0252',
 'C_SOURCE_0254':'0214','C_SOURCE_0255':'0214','C_SOURCE_0256':'0257',
 'C_SOURCE_0257':'0042','C_PRIVATE_NEGATIVE':'0043','C_PRIVATE_NONNEG':'0214',
 'E_SOURCE_NORMALIZE':'0270','F_SOURCE_NORMALIZE':'0275',
 'F_PRIVATE_SIGNED_ZERO':'0300','F_DIRECT_NEGZERO':'0300',
}

def words_of(image):
 rows=[line.split() for line in image.splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)]
 assert len(rows)==31 and len(set(r[0] for r in rows))==31,'SOURCE_ROWS_NOT_31'
 return {int(a,8):int(w,8) for a,w in rows}

def decode(w):return w>>36,(w>>24)&0o3777,(w>>12)&0o3777,w&0o3777

def encode(n,negative_zero=False):
 assert abs(n)<SIGN,('FIXED_POINT_OVERFLOW',n)
 return abs(n)|(SIGN if n<0 or (n==0 and negative_zero) else 0)

def mag(w):return w&MASK

def signed(w):return -mag(w) if w&SIGN else mag(w)

def simulate(words,profile,count):
 name,start,extra,patch,_=profile;mem={**ROM,**words}
 mem.update({int(a,8):w for a,w in extra.items()})
 mem.update({int(a,8):int(w,8) for a,w in patch.items()})
 pc=int(start,8);path=[];status='LIMIT'
 for n in range(count):
  assert pc in words and pc not in (0o252,0o260,0o261,0o262),('UNAUTHORIZED_EXECUTION',f'{pc:04o}',path)
  instr=mem[pc];op,a,b,d=decode(instr);x=mem.get(a,0);y=mem.get(b,0);path.append(f'{pc:04o}')
  if op==0o01:
   value=signed(x)+signed(y)
   mem[d]=encode(value,negative_zero=(value==0 and bool((x|y)&SIGN)));pc+=1
  elif op==0o02:
   value=signed(x)-signed(y)
   mem[d]=encode(value,negative_zero=(value==0));pc+=1
  elif op==0o05:pc=d if mag(x)<=mag(y) else pc+1
  elif op==0o11:
   m=((mag(x)*mag(y))+(1<<39))>>40
   assert m<SIGN
   mem[d]=m|(SIGN if bool(x&SIGN)!=bool(y&SIGN) else 0);pc+=1
  elif op==0o12:
   if mag(y)==0:
    pc+=1;status='CPU_STOP';break
   q=(mag(x)<<40)//mag(y)
   assert q<SIGN,('DIV_OVERFLOW_UNQUALIFIED',name)
   mem[d]=q|(SIGN if bool(x&SIGN)!=bool(y&SIGN) else 0);pc+=1
  elif op==0o16:pc=d if x==y else pc+1
  elif op==0o31:pc=d if x&SIGN else b
  elif op==0o33:pc+=1;status='CPU_STOP';break
  elif op==0o35:
   m=mag(x);power=40-m.bit_length() if m else 0
   mem[b]=power;mem[d]=(m<<power)&MASK | (SIGN if x&SIGN else 0);pc+=1
  else:raise AssertionError(('UNSUPPORTED_OR_IO_OPCODE',f'{pc:04o}',f'{op:02o}'))
 assert (status=='LIMIT' and len(path)==count) or (status=='CPU_STOP' and len(path)==count)
 return status,len(path),f'{pc:04o}',tuple(f'{mem.get(int(k,8),0):014o}' for k in WATCH),path

def selftest():
 root=pathlib.Path(__file__).resolve().parent.parent
 # When running from an installed repo, the canonical image is present.
 img=root/IMAGE
 if img.is_file():
  words=words_of(img.read_text('ascii'))
 else:
  # Package self-tests run from payload before the installer has applied anything.
  pkg=pathlib.Path(__file__).resolve().parents[3] if 'payload' in __file__ else None
  assert pkg is not None and (pkg/'payload'/IMAGE).is_file(),'IMAGE_FOR_SELFTEST_MISSING'
  words=words_of((pkg/'payload'/IMAGE).read_text('ascii'))
 assert len(words)==31 and len(PROFILES)==16 and all(len(r)==5 for r in PROFILES)
 assert words[0o252] == int('22035403570253',8)
 assert words[0o260] == int('01777777777777',8)
 assert decode(words[0o254])[0]==0o31
 assert decode(words[0o263])[0]==0o35
 assert decode(words[0o275])[0]==0o35
 assert (0o300 not in words) and (0o252 in words)
 for profile in PROFILES:
  name,_,_,_,counts=profile
  for count in counts:
   status,steps,pc,regs,path=simulate(words,profile,count)
   assert steps==count
  assert pc==EXPECTED_C[name],(name,pc,EXPECTED_C[name])
 assert simulate(words,next(p for p in PROFILES if p[0]=='B_PRIVATE_EQUAL'),3)[2]=='0254'
 assert simulate(words,next(p for p in PROFILES if p[0]=='B_PRIVATE_FALSE'),3)[2]=='0252'
 assert simulate(words,next(p for p in PROFILES if p[0]=='F_PRIVATE_SIGNED_ZERO'),3)[2]=='0300'
 assert simulate(words,next(p for p in PROFILES if p[0]=='E_SOURCE_NORMALIZE'),4)[0]=='CPU_STOP'
 assert simulate(words,next(p for p in PROFILES if p[0]=='F_SOURCE_NORMALIZE'),4)[0]=='CPU_STOP'
 mutant=dict(words);mutant[0o251]=int('05035230020252',8)
 assert simulate(mutant,next(p for p in PROFILES if p[0]=='B_PRIVATE_EQUAL'),3)[2]=='0252'
 # 37-bit mask is not a 40-bit mask.
 assert words[0o260]==(1<<37)-1
 print(f'D15B1H22-RUNNER-SELFTEST PASS WORDS=31/31 PROFILES={len(PROFILES)}/{len(PROFILES)} HOST_INTEGER_ORACLE=1 OPCODE31_TRUE_FALSE=1 SIGNED_ZERO_GATE=1 IO_0252_NOT_EXECUTED=1 BOUNDARY_0300_NOT_EXECUTED=1')

def main():
 p=argparse.ArgumentParser();p.add_argument('--cli-exe');p.add_argument('--timeout',type=float,default=20);p.add_argument('--self-test',action='store_true');args=p.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'CLI_REQUIRED'
 root=pathlib.Path(__file__).resolve().parent.parent
 exe=pathlib.Path(args.cli_exe).resolve()
 image=(root/IMAGE).resolve()
 assert image.is_file() and exe.is_file() and (root/'tempkyiv').is_dir(),'INPUTS'
 original=image.read_bytes();words=words_of(original.decode('ascii'))
 canonical_sha=hashlib.sha256(original).hexdigest()
 assert not any(a in words for a in (0o350,0o351,0o352,0o353,0o354,0o355,0o356,0o357)),'SEED_IN_CANONICAL'
 total=0;first=[];second=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h22_external_') as folder:
  ext=pathlib.Path(folder);images={}
  for name,start,ram,patch,counts in PROFILES:
   if not ram and not patch:images[name]=image;continue
   f=ext/(name.lower()+'.k41');lines=[f'{a} {w:014o}' for a,w in ram.items()]
   private_source=original.decode('ascii')
   for a,w in patch.items():
    old=f'{a} {words[int(a,8)]:014o}';new=f'{a} {int(w,8):014o}'
    assert private_source.splitlines().count(old)==1,'PATCH_ADDRESS_NOT_UNIQUE'
    private_source=private_source.replace(old,new,1)
   f.write_bytes(private_source.encode('ascii')+(''.join(line+'\n' for line in lines)).encode('ascii'))
   images[name]=f
  hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in images.items()}
  for cwdname,cwd,store in [('EXTERNAL',ext,first),('TEMPKYIV',root/'tempkyiv',second)]:
   for profile in PROFILES:
    name,start,_,_,counts=profile
    for count in counts:
     status,n,pc,regs,path=simulate(words,profile,count)
     cmd=[str(exe),'image',str(images[name]),start,str(count)]
     for a in WATCH:cmd+=['--watch',a]
     r=subprocess.run(cmd,cwd=cwd,capture_output=True,encoding='utf-8',errors='replace',text=True,timeout=args.timeout)
     match=RX_RUN.search(r.stdout);run=match.groups() if match else None
     ws=dict(RX_WATCH.findall(r.stdout))
     ok=(r.returncode==0 and run==(status,str(n),pc) and tuple(ws.get(a) for a in WATCH)==regs)
     if not ok:
      print(f'D15B1H22-CASE FAIL PROFILE={name} CWD={cwdname} COUNT={count} RC={r.returncode} RUN={run} EXPECT={(status,str(n),pc)} WATCH={ws} EXPECT_WATCH={dict(zip(WATCH,regs))} VISIT={path}\nSTDOUT={r.stdout[-4000:]}\nSTDERR={r.stderr[-2500:]}')
      raise AssertionError('NATIVE_MISMATCH')
     total+=1;store.append((name,count,run,regs))
     print(f'D15B1H22-CASE {total:03d} PROFILE={name} CWD={cwdname} STEPS={count} RUN={run} PATH={"-".join(path)} '+ ' '.join(f'RAM{a}={regs[i]}' for i,a in enumerate(WATCH))+' PASS')
  assert first==second,'CWD_PARITY'
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[name] for name,p in images.items()),'IMAGE_MUTATION'
 assert hashlib.sha256(image.read_bytes()).hexdigest()==canonical_sha,'SOURCE_MUTATED'
 n=sum(len(p[4]) for p in PROFILES)
 assert total==2*n
 print(f'D15B1H22-NATIVE-OBSERVATION PASS CASES={total}/{total} SOURCE_WORDS=31/31 CHECKPOINTS={n}/{n} CWD_PARITY={n}/{n} SUBGROUPS=A_B_C_D_E_F SIGNED_ZERO_HOST_POLICY=1 SOURCE_ENTRY_SCRATCH=UNKNOWN H19_SEED=UNKNOWN H20_H21_SCRATCH=UNKNOWN B_DIV_ZERO_STOP=1 F_SIGNED_ZERO_BRANCH=1 IO_0252_NOT_EXECUTED=1 BOUNDARIES_0214_0042_0043_0300_NOT_EXECUTED=1 H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as e:raise SystemExit('D15B1H22-NATIVE FAIL '+repr(e))
