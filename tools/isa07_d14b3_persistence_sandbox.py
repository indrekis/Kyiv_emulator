#!/usr/bin/env python3
"""D14-B3 independent byte oracle, CRC64 and failure-injection sandbox.
No C++ codec reused, no CPU, no historical device-format claims.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SIGN=1<<40
MASK=(1<<41)-1
POLY=0x42F0E1EBA9EA3693
MAGIC=b'KYIVDRM1'

def crc64(data:bytes)->int:
    result=0
    for b in data:
        result ^= b<<56
        for _ in range(8):
            result=(((result<<1)^POLY) if (result>>63) else (result<<1)) & ((1<<64)-1)
    return result

def reference(profile:str,d:int,t:int,s:int,cells:dict[int,int])->bytes:
    n=d*t*s
    assert 0<n<=1_000_000 and 0<=len(cells)<=n
    bitmap=bytearray((n+7)//8)
    payload=bytearray(8*n)
    for idx,value in cells.items():
        assert 0<=idx<n and 0<=value<=MASK
        bitmap[idx//8]|=1<<(idx%8)
        struct.pack_into('<Q',payload,8*idx,value)
    name=profile.encode('ascii')
    h=struct.pack('<8sIIQQQQQII',MAGIC,1,64,d,t,s,n,len(cells),len(name),0)
    assert len(h)==64
    contents=h+name+bitmap+payload
    return contents+struct.pack('<Q',crc64(contents))

def fix_checksum(data:bytes)->bytes:
    assert len(data)>=8
    return data[:-8]+struct.pack('<Q',crc64(data[:-8]))

def run(exe:Path,argv:list[str],data:str='',timeout:float=5):
    proc=subprocess.run([str(exe),*argv],input=data,stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,text=True,encoding='utf-8',
                        errors='replace',timeout=timeout)
    if proc.returncode!=0 or proc.stderr:
        raise AssertionError(f'EXIT={proc.returncode} OUT={proc.stdout[-300:]!r} ERR={proc.stderr[-500:]!r}')
    return proc.stdout.splitlines()

def expect_cells(lines,profile,d,t,s,cells):
    header=f'D14B3-READ OK {profile} {d} {t} {s} {len(cells)}'
    wanted=[header]+[f'CELL {idx} {v}' for idx,v in sorted(cells.items())]
    if lines!=wanted:
        raise AssertionError(f'BAD_READ observed={lines[:6]!r}... expected={wanted[:6]!r}...')

def case_save(exe,folder,profile,d,t,s,cells,seq,timeout):
    image=folder/f'case-{seq}.kdr'
    command=[]
    for idx,value in sorted(cells.items()):
        q=idx//(t*s);rem=idx%(t*s)
        command.append(f'PUT {q} {rem//s} {rem%s} {value}\n')
    expected=reference(profile,d,t,s,cells)
    # Force replacement of an existing file without leaving temp files.
    if seq%3==0: image.write_bytes(b'STALE MAGIC / should be replaced')
    lines=run(exe,['save',str(image),profile,str(d),str(t),str(s)],''.join(command),timeout)
    assert lines==[f'D14B3-SAVE OK {len(cells)}'], lines
    found=image.read_bytes()
    assert found==expected, f'NONCANONICAL_BYTES case={seq} len={len(found)} expected={len(expected)}'
    expect_cells(run(exe,['read',str(image)],timeout=timeout),profile,d,t,s,cells)
    expect_cells(run(exe,['loadinto',str(image),profile,str(d),str(t),str(s)],timeout=timeout),profile,d,t,s,cells)
    assert list(folder.glob(image.name+'.tmp.*'))==[], 'SIBLING_TEMP_LEAK'
    print(f'D14B3-ROUNDTRIP {profile}-{seq}: PASS BYTES={len(found)} WRITTEN={len(cells)} INDEPENDENT_FORMAT=1')
    return 1

def expect_error(exe,folder,name,blob,code,timeout):
    file=folder/f'negative-{name}.kdr'
    if blob is not None:file.write_bytes(blob)
    lines=run(exe,['read',str(file)],timeout=timeout)
    expected=[f'D14B3-ERROR {code}']
    assert lines==expected, (name,lines,expected)
    print(f'D14B3-INVALID {name}: PASS EXPECTED={code}')
    return 1

def negative_cases(exe,folder,timeout):
    base=reference('tiny',1,1,3,{0:SIGN,2:42})
    name_len=4
    bstart=64+name_len
    wstart=bstart+1
    muts=[]
    def setbytes(name,offset,data,code,rec=True):
        x=bytearray(base)
        x[offset:offset+len(data)]=data
        muts.append((name,fix_checksum(bytes(x)) if rec else bytes(x),code))
    setbytes('magic',0,b'XXXXXXXX','BAD_MAGIC')
    setbytes('version',8,struct.pack('<I',2),'UNSUPPORTED_VERSION')
    setbytes('header-size',12,struct.pack('<I',60),'INVALID_HEADER')
    setbytes('reserved',60,struct.pack('<I',1),'INVALID_HEADER')
    setbytes('bad-profile',64,b'!', 'INVALID_PROFILE')
    setbytes('empty-profile',56,struct.pack('<I',0),'INVALID_PROFILE')
    setbytes('wrong-count',40,struct.pack('<Q',4),'INVALID_COUNT')
    setbytes('wrong-written-count',48,struct.pack('<Q',3),'INVALID_COUNT')
    setbytes('zero-geometry',16,struct.pack('<Q',0),'INVALID_GEOMETRY')
    setbytes('noncanonical-bitmap',bstart,bytes([base[bstart]|0x80]),'NONCANONICAL_BITMAP')
    setbytes('unwritten-payload',wstart+8,struct.pack('<Q',22),'NONCANONICAL_UNWRITTEN')
    setbytes('overwide-word',wstart,struct.pack('<Q',1<<41),'INVALID_WORD')
    setbytes('crc-corrupt',wstart,bytes([base[wstart]^0x01]),'CHECKSUM_MISMATCH',False)
    setbytes('crc-tail',len(base)-1,bytes([base[-1]^0x11]),'CHECKSUM_MISMATCH',False)
    muts.append(('truncated',base[:-1],'INVALID_LENGTH'))
    muts.append(('trailing',base+b'!', 'INVALID_LENGTH'))
    muts.append(('tiny-image',b'0'*12, 'TRUNCATED_IMAGE'))
    muts.append(('huge',b'Z'*(9*1024*1024+1),'IMAGE_TOO_LARGE'))
    muts.append(('missing',None,'IMAGE_OPEN_FAILED'))
    return sum(expect_error(exe,folder,*m,timeout) for m in muts)

def fs_failures(exe,folder,timeout):
    profile='filesystem'; d,t,s=1,1,2
    bad=folder/'target-is-directory.kdr'
    bad.mkdir()
    (bad/'keep.txt').write_text('MUST STAY',encoding='ascii')
    data=f'PUT 0 0 0 {SIGN}\n'
    output=run(exe,['save',str(bad),profile,str(d),str(t),str(s)],data,timeout)
    assert output==['D14B3-ERROR REPLACE_FAILED'],output
    assert (bad/'keep.txt').read_text(encoding='ascii')=='MUST STAY'
    assert not list(folder.glob(bad.name+'.tmp.*'))
    print('D14B3-FS replace-directory: PASS PREVIOUS_UNCHANGED=1 TEMP_CLEANUP=1')
    missing=folder/'missing-parent'/'image.kdr'
    output=run(exe,['save',str(missing),profile,str(d),str(t),str(s)],data,timeout)
    assert output==['D14B3-ERROR IMAGE_WRITE_FAILED'],output
    assert not list(folder.glob('image.kdr.tmp.*'))
    print('D14B3-FS missing-parent: PASS ERROR_BEFORE_RENAME=1')
    valid=folder/'valid.kdr'
    valid.write_bytes(reference('tiny',1,1,3,{0:1}))
    output=run(exe,['loadinto',str(valid),profile,str(d),str(t),str(s)],timeout=timeout)
    assert output==['D14B3-LOADINTO ERROR GEOMETRY_MISMATCH UNCHANGED=1'],output
    print('D14B3-FS geometry-mismatch: PASS DESTINATION_UNCHANGED=1')
    damaged=folder/'damaged.kdr'
    damaged.write_bytes(b'INVALID FILE')
    output=run(exe,['loadinto',str(damaged),profile,str(d),str(t),str(s)],timeout=timeout)
    assert output==['D14B3-LOADINTO ERROR TRUNCATED_IMAGE UNCHANGED=1'],output
    print('D14B3-FS invalid-load: PASS DESTINATION_UNCHANGED=1')
    return 4

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exe',required=True)
    p.add_argument('--random-cases',type=int,default=20)
    p.add_argument('--timeout',type=float,default=5)
    a=p.parse_args()
    exe=Path(a.exe).resolve()
    if not exe.is_file() or not .3<=a.timeout<=60 or not 0<=a.random_cases<=100:
        p.error('invalid exe, timeout, or random-cases')
    (ROOT/'tempkyiv').mkdir(exist_ok=True)
    rng=random.Random(0xD14B3)
    assert crc64(b'123456789')==0x6C40DF5F0B497347, 'PYTHON_CRC64_NOT_ECMA'
    assert run(exe,['crc'],timeout=a.timeout)==['D14B3-CRC 6c40df5f0b497347'], 'CPP_CRC64_NOT_ECMA'
    print('D14B3-CRC STANDARD_VECTOR: PASS PYTHON=1 CPP=1')
    passed=0;cases=0
    with tempfile.TemporaryDirectory(prefix='d14b3_',dir=ROOT/'tempkyiv') as tmp:
        folder=Path(tmp)
        profiles=[('mini',2,3,4),('one',1,1,1),('asymmetric',3,4,5),
                  ('experiment-137',3,24,137),('experiment-511',3,24,511)]
        for i,(name,d,t,s) in enumerate(profiles):
            count=d*t*s
            base={0:0,count-1:SIGN}
            if count>3:base[count//2]=(1<<40)-1
            passed+=case_save(exe,folder,name,d,t,s,base,i,a.timeout);cases+=1
        for j in range(a.random_cases):
            d,t,s=rng.randint(1,3),rng.randint(1,4),rng.randint(1,7)
            n=d*t*s
            cells={idx:rng.choice([0,SIGN,MASK,rng.getrandbits(41)])
                   for idx in range(n) if rng.random()<.5}
            passed+=case_save(exe,folder,f'random_{j:03}',d,t,s,cells,100+j,a.timeout);cases+=1
        passed+=negative_cases(exe,folder,a.timeout)
        passed+=fs_failures(exe,folder,a.timeout)
    total=cases+19+4
    print(f'ISA-07 D14-B3 IMAGE {"PASS" if passed==total else "FAIL"}={passed}/{total} '
          f'ROUNDTRIP={cases}/{cases} NEGATIVE=19/19 FS=4/4 '
          'INDEPENDENT_BYTE_ORACLE=1 CRC64_ECMA=1 CRC_STANDARD_VECTOR=1 RAW41=1 '
          'SIGNED_ZERO=1 UNWRITTEN_DISTINCT=1 ATOMIC_REPLACE=1 '
          'CPU_MUTATION=0 HARDWARE_ORACLE=0')
    return 0 if passed==total else 1

if __name__=='__main__':raise SystemExit(main())
