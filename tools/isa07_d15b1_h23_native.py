#!/usr/bin/env python3
"""H23 38-word test of source continuation 0300-0345; independent HOST oracle.

HISTORICAL inputs (scratch, sign-of-normalizer-order) UNKNOWN.
All noncanonical source changes are PRIVATE and transient; external 0360 never executed.
"""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess,tempfile
IMAGE='examples/historical/gy1962/au1_batch38_0300_0345.k41'
SIGN=1<<40;MASK=SIGN-1; MASK41=2*SIGN-1
RX_RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
RX_WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
WATCH=('0003','0347','0350','0351')
ROM={0o3000:0,0o3012:1,0o3026:SIGN,0o3177:SIGN|1}
HALF=1<<39
# name, start PC, PRIVATE scratch words, PRIVATE modified program/data words, checkpoints
PROFILES=[
 ('A_SOURCE_0300','0300',{}, {},(1,2)),
 ('A_PRIVATE_NEGZERO_0300','0300',{'0350':SIGN},{},(1,2,3,4,5)),
 ('A_DIRECT_0302','0302',{}, {},(1,2,3,4)),
 ('A_DIRECT_STOP_0301','0301',{}, {},(1,)),
 ('B_SOURCE_SHIFT_0307','0307',{}, {},tuple(range(1,11))),
 ('B_PRIVATE_SHIFT_OFFBYONE','0315',{}, {'0340':f'{SIGN|0o13:014o}'},(1,2,3)),
 ('B_DIRECT_STOP_0311','0311',{}, {},(1,)),
 ('C_SOURCE_ZERO_0326','0326',{}, {},(1,2,3)),
 ('C_PRIVATE_NEGZERO_0326','0326',{'0003':SIGN},{},(1,2,3,4,5)),
 ('C_PRIVATE_BRANCH_PATCH','0326',{'0003':SIGN,'0351':HALF},{'0332':'16034703510334'},(1,2,3,4,5)),
 ('C_DIRECT_JUMP_0334','0334',{}, {},(1,)),
]
EXPECTED_LAST_C={
 'A_SOURCE_0300':'0302', 'A_PRIVATE_NEGZERO_0300':'0307','A_DIRECT_0302':'0307',
 'A_DIRECT_STOP_0301':'0302','B_SOURCE_SHIFT_0307':'0326',
 'B_PRIVATE_SHIFT_OFFBYONE':'0320','B_DIRECT_STOP_0311':'0312',
 'C_SOURCE_ZERO_0326':'0331','C_PRIVATE_NEGZERO_0326':'0334',
 'C_PRIVATE_BRANCH_PATCH':'0360','C_DIRECT_JUMP_0334':'0360',
}

def words_of(image):
 lines=[line.split() for line in image.splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)]
 assert len(lines)==38 and len({a for a,_ in lines})==38,'SOURCE_NOT_38'
 words={int(a,8):int(w,8) for a,w in lines}
 assert set(words)==set(range(0o300,0o346)),'NONCONTIGUOUS'
 assert all(0<=w<1<<41 for w in words.values()),'WORD_RANGE'
 return words

def decode(w):return w>>36,(w>>24)&0o3777,(w>>12)&0o3777,w&0o3777

def simulate(words,profile,count):
 name,start,extra,patch,_=profile
 mem={**ROM,**words}
 mem.update({int(k,8):v for k,v in extra.items()})
 mem.update({int(k,8):int(v,8) for k,v in patch.items()})
 pc=int(start,8);path=[];status='LIMIT'
 for _ in range(count):
  assert 0o300<=pc<=0o334,('EXECUTION_OUTSIDE_PROGRAM',f'{pc:04o}',path)
  ins=mem[pc];op,a,b,d=decode(ins);x=mem.get(a,0);y=mem.get(b,0)
  path.append(f'{pc:04o}')
  if op==0o05:
   pc=d if (x&MASK)<=(y&MASK) else pc+1
  elif op==0o16:
   pc=d if x==y else pc+1
  elif op==0o33:
   pc+=1;status='CPU_STOP';break
  elif op==0o35:
   magnitude=x&MASK;power=(40-magnitude.bit_length()) if magnitude else 0
   mem[b]=power
   mem[d]=(magnitude<<power)&MASK | (SIGN if x&SIGN else 0)
   pc+=1
  elif op==0o13:
   shift=(x&0o77)
   mem[d]=((y>>shift) if (x&SIGN) else (y<<shift)&MASK41)
   pc+=1
  else:raise AssertionError(('UNSUPPORTED_OPCODE',name,f'{pc:04o}',f'{op:02o}'))
 assert len(path)==count and ((status=='CPU_STOP')==(op==0o33)),'STOP_MISMATCH'
 return status,len(path),f'{pc:04o}',tuple(f'{mem.get(int(k,8),0):014o}' for k in WATCH),path

def selftest():
 root=pathlib.Path(__file__).resolve().parent.parent
 path=root/IMAGE
 if not path.is_file():
  pkg=pathlib.Path(__file__).resolve().parents[3] if 'payload' in __file__ else None
  assert pkg and (pkg/'payload'/IMAGE).is_file(),'SELFTEST_IMAGE_MISSING'
  path=pkg/'payload'/IMAGE
 words=words_of(path.read_text('ascii'))
 assert len(PROFILES)==11 and len(EXPECTED_LAST_C)==len(PROFILES)
 assert words[0o302]==int('35317703500347',8),'NORMALIZER'
 assert words[0o335]==int('30000000000000',8),'HISTORICAL_EXPECTED_NEG_HALF'
 assert words[0o336]==int('20000000000047',8),'HISTORICAL_EXPECTED_NEG_ORDER'
 assert words[0o337]==0o14 and words[0o340]==(SIGN|0o14),'SHIFT_12'
 assert words[0o341]==0o50 and words[0o342]==(SIGN|0o50),'SHIFT_40'
 assert words[0o344]==(SIGN|0o100) and words[0o345]==(SIGN|0o101),'SHIFT_WRAP_64'
 assert words[0o343]==(1<<28),'BIT28_WITNESS'
 assert all(decode(words[a])[0] in (0o05,0o13,0o16,0o33,0o35) for a in range(0o300,0o335))
 assert all(len(p)==5 for p in PROFILES)
 for p in PROFILES:
  last=None
  for n in p[4]:
   last=simulate(words,p,n)
   assert last[1]==n
  assert last[2]==EXPECTED_LAST_C[p[0]],(p[0],last[2],EXPECTED_LAST_C[p[0]])
 assert simulate(words,PROFILES[1],3)[2]=='0305'
 assert simulate(words,PROFILES[1],4)[2]=='0306'
 assert simulate(words,PROFILES[1],4)[3][2]=='00000000000047','HOST_ORDER_MAGNITUDE'
 assert words[0o336]!=0o47,'SOURCE_NEGATIVE_ORDER'
 assert simulate(words,PROFILES[4],10)[2]=='0326'
 assert simulate(words,PROFILES[9],5)[2]=='0360'
 assert simulate(words,PROFILES[8],5)[0]=='CPU_STOP'
 mutant=dict(words);mutant[0o340]=SIGN|0o13
 assert simulate(mutant,PROFILES[4],6)[2]=='0317','MUTANT_BRANCH_DISCRIMINATOR'
 print('D15B1H23-RUNNER-SELFTEST PASS WORDS=38/38 PROGRAM=29 DATA=9 PROFILES=11/11 SHIFT_OPCODE13=1 NORMALIZATION_SIGN_DISCRIMINATOR=1 BIT_SHIFT_MUTANT_REJECTED=1 BOUNDARY_0360_NOT_EXECUTED=1')

def main():
 p=argparse.ArgumentParser();p.add_argument('--cli-exe');p.add_argument('--timeout',type=float,default=20);p.add_argument('--self-test',action='store_true');args=p.parse_args()
 selftest()
 if args.self_test:return
 assert args.cli_exe and args.timeout>0,'CLI_REQUIRED'
 root=pathlib.Path(__file__).resolve().parent.parent
 exe=pathlib.Path(args.cli_exe).resolve();image=(root/IMAGE).resolve()
 assert image.is_file() and exe.is_file() and (root/'tempkyiv').is_dir(),'INPUT_MISSING'
 source=image.read_bytes();words=words_of(source.decode('ascii'))
 source_hash=hashlib.sha256(source).hexdigest()
 assert all(a not in words for a in (0o347,0o350,0o351)),'SCRATCH_IN_CANONICAL'
 n_expected=sum(len(p[4]) for p in PROFILES)
 total=0;first=[];second=[]
 with tempfile.TemporaryDirectory(prefix='d15b1h23_private_') as folder:
  ext=pathlib.Path(folder);images={}
  for name,start,ram,patch,counts in PROFILES:
   if not ram and not patch:images[name]=image;continue
   f=ext/(name.lower()+'.k41');private=source.decode('ascii')
   for a,w in patch.items():
    original=f'{a} {words[int(a,8)]:014o}';replacement=f'{a} {int(w,8):014o}'
    assert private.splitlines().count(original)==1,'MUTANT_SOURCE_ADDRESS'
    private=private.replace(original,replacement,1)
   suffix=''.join(f'{a} {value:014o}\n' for a,value in ram.items())
   f.write_bytes(private.encode('ascii')+suffix.encode('ascii'));images[name]=f
  sha={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in images.items()}
  for cwdname,cwd,store in [('EXTERNAL',ext,first),('TEMPKYIV',root/'tempkyiv',second)]:
   for profile in PROFILES:
    name,start,ram,patch,counts=profile
    for count in counts:
     status,n,c,reg,path=simulate(words,profile,count)
     cmd=[str(exe),'image',str(images[name]),start,str(count)]
     for a in WATCH:cmd+=['--watch',a]
     r=subprocess.run(cmd,cwd=cwd,capture_output=True,encoding='utf8',errors='replace',text=True,timeout=args.timeout)
     m=RX_RUN.search(r.stdout);run=m.groups() if m else None;ws=dict(RX_WATCH.findall(r.stdout))
     ok=(r.returncode==0 and run==(status,str(n),c) and tuple(ws.get(k) for k in WATCH)==reg)
     if not ok:
      print(f'D15B1H23-CASE FAIL PROFILE={name} CWD={cwdname} STEPS={count} RC={r.returncode} RUN={run} EXPECT={(status,str(n),c)} WATCH={ws} EXPECT_WATCH={dict(zip(WATCH,reg))} PATH={path}\nSTDOUT={r.stdout[-3000:]}\nSTDERR={r.stderr[-1500:]}')
      raise AssertionError('NATIVE_OBSERVATION_MISMATCH')
     total+=1;store.append((name,count,run,reg))
     print(f'D15B1H23-CASE {total:03d} PROFILE={name} CWD={cwdname} STEPS={count} RUN={run} PATH={"-".join(path)} '+ ' '.join(f'RAM{k}={reg[i]}' for i,k in enumerate(WATCH))+' PASS')
  assert first==second,'CWD_PARITY'
  assert all(hashlib.sha256(v.read_bytes()).hexdigest()==sha[k] for k,v in images.items()),'PRIVATE_IMAGE_MUTATION'
 assert hashlib.sha256(image.read_bytes()).hexdigest()==source_hash,'CANONICAL_MUTATED'
 assert total==2*n_expected
 print(f'D15B1H23-NATIVE-OBSERVATION PASS CASES={total}/{total} SOURCE_WORDS=38/38 CHECKPOINTS={n_expected}/{n_expected} CWD_PARITY={n_expected}/{n_expected} SUBGROUPS=A_B_C STOP_PATHS=1 SHIFT_OPCODE13=1 BOUNDARY_0360_NOT_EXECUTED=1 HISTORICAL_ENTRY_SCRATCH=UNKNOWN NORMALIZER_ORDER_SIGN_ORACLE=OPEN HOST_POSITIVE_ORDER=1 SOURCE_NEGATIVE_ORDER_WORD=1 H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')
if __name__=='__main__':
 try:main()
 except BaseException as ex:raise SystemExit('D15B1H23-RUNNER FAIL '+repr(ex))
