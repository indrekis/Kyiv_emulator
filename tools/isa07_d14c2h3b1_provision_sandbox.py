#!/usr/bin/env python3
"""Independent byte/CRC oracle for explicit no-clobber KYIVDRM1 creation."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import random
import subprocess
import tempfile

POLY=0x42F0E1EBA9EA3693
MASK=(1 << 64)-1

def crc64(raw: bytes) -> int:
    crc=0
    for c in raw:
        crc ^= c << 56
        for _ in range(8):
            crc = ((crc << 1) ^ POLY) & MASK if crc & (1 << 63) else (crc << 1) & MASK
    return crc

def expected(profile: str, tracks: int, slots: int) -> bytes:
    label=profile.encode('ascii')
    count=3*tracks*slots
    header=(b'KYIVDRM1'
        + (1).to_bytes(4,'little')
        + (64).to_bytes(4,'little')
        + (3).to_bytes(8,'little')
        + tracks.to_bytes(8,'little')
        + slots.to_bytes(8,'little')
        + count.to_bytes(8,'little')
        + (0).to_bytes(8,'little')
        + len(label).to_bytes(4,'little')
        + (0).to_bytes(4,'little'))
    assert len(header)==64
    data=header+label+bytes((count+7)//8)+bytes(count*8)
    return data+crc64(data).to_bytes(8,'little')

def run(binary:Path,*args:str,timeout:float=12):
    return subprocess.run([str(binary),*map(str,args)],stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,text=True,timeout=timeout)

def new_entry_names(root: Path, before: set[str]) -> set[str]:
    # Compare directory *names*, not Path instances. Windows Python and the
    # C++ process may expose equivalent native paths with different spelling.
    return set(os.listdir(root)) - before

def check(condition:bool,why:str):
    if not condition:raise AssertionError(why)

def selftest():
    check(crc64(b'123456789')==0x6C40DF5F0B497347,'CRC64_STANDARD_VECTOR')
    a=expected('mini',1,2)
    check(len(a)==64+4+1+48+8,'EXPECTED_LENGTH')
    check(int.from_bytes(a[-8:],'little')==crc64(a[:-8]),'CRC64_TRAILER')
    mutant=bytearray(a);mutant[23]^=1
    check(int.from_bytes(mutant[-8:],'little')!=crc64(mutant[:-8]),'BAD_MUTANT_ACCEPTED')
    check({'a', 'fresh_0.kdr'}-{'a'}=={'fresh_0.kdr'},'NAME_DIFF_MODEL')
    print('D14C2H3B1-SANDBOX-SELFTEST PASS CRC_STANDARD=1 BYTES=1 MUTANT_REJECTED=1 NAME_DIFF_MODEL=1')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--create-exe',type=Path)
    p.add_argument('--inspect-exe',type=Path)
    p.add_argument('--random-cases',type=int,default=20)
    p.add_argument('--timeout',type=float,default=12)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    selftest()
    if args.self_test:return
    if args.create_exe is None or args.inspect_exe is None:
        p.error('require both --create-exe and --inspect-exe')
    create=args.create_exe.resolve();inspect=args.inspect_exe.resolve()
    check(create.is_file() and inspect.is_file(),'EXE_MISSING')
    check(0 <= args.random_cases <= 100 and 1 <= args.timeout <= 60,'BAD_PARAMETERS')
    rnd=random.Random(0xD14C2B1)
    fixed=[('mini',1,1),('asym',2,3),('experiment-137',24,137),
           ('experiment-511',24,511),('X_Y.9',7,11)]
    random_cases=[(f'case_{i:03d}',rnd.randint(1,13),rnd.randint(1,37))
                  for i in range(args.random_cases)]
    with tempfile.TemporaryDirectory(prefix='d14c2h3b1_') as folder:
        root=Path(folder)
        for i,(profile,t,s) in enumerate(fixed+random_cases):
            image=root/f'fresh_{i}.kdr'
            before=set(os.listdir(root))
            cmd=run(create,'create',image,profile,t,s,timeout=args.timeout)
            check(cmd.returncode==0 and cmd.stdout.startswith('D14C2H3B1-CREATE PASS '),
                  f'CREATE_FAIL[{i}] {cmd.stdout!r} {cmd.stderr!r}')
            check(image.is_file() and image.read_bytes()==expected(profile,t,s),
                  f'BYTE_MISMATCH[{i}]')
            added=new_entry_names(root,before)
            check(added=={image.name},
                  f'TEMP_LEAK[{i}] expected={image.name!r} observed={sorted(added)!r}')
            verification=run(inspect,'inspect',image,profile,t,s,timeout=args.timeout)
            check(verification.returncode==0 and ' WRITTEN=0 GEOMETRY_EXACT=1' in verification.stdout,
                  f'CPP_READBACK_FAIL[{i}] {verification.stdout!r} {verification.stderr!r}')
            before_bytes=image.read_bytes()
            repeat=run(create,'create',image,'another',3,5,timeout=args.timeout)
            check(repeat.returncode!=0 and 'ERROR=IMAGE_EXISTS' in repeat.stderr,
                  f'EXISTING_NOT_REJECTED[{i}]')
            check(image.read_bytes()==before_bytes and new_entry_names(root,before)=={image.name},
                  f'EXISTING_MUTATED[{i}]')
            print(f'D14C2H3B1-CASE {i:02d} {profile}: PASS BYTES={len(before_bytes)} NO_CLOBBER=1')
        invalid=[
          ('missing-parent',root/'missing'/'new.kdr','good','2','3','IMAGE_PARENT_INVALID'),
          ('zero-tracks',root/'invalid0.kdr','good','0','3','CLI_ZERO_VALUE'),
          ('zero-slots',root/'invalid1.kdr','good','2','0','CLI_ZERO_VALUE'),
          ('signed',root/'invalid2.kdr','good','-2','3','CLI_INVALID_DECIMAL'),
          ('junk',root/'invalid3.kdr','good','2x','3','CLI_INVALID_DECIMAL'),
          ('overwide',root/'invalid4.kdr','good','9999999999999999999999','3','CLI_INVALID_DECIMAL'),
          ('profile',root/'invalid5.kdr','bad profile','2','3','INVALID_PROFILE'),
          ('capacity',root/'invalid6.kdr','good','500000','2','HOST_CAPACITY_LIMIT'),
        ]
        for name,image,profile,t,s,code in invalid:
            res=run(create,'create',image,profile,t,s,timeout=args.timeout)
            check(res.returncode!=0 and f'ERROR={code}' in res.stderr and not image.exists(),
                  f'INVALID_NOT_REJECTED[{name}] {res.stderr!r}')
            print(f'D14C2H3B1-INVALID {name}: PASS ERROR={code}')
        occupied=root/'arbitrary.kdr';occupied.write_bytes(b'NOT AN IMAGE\r\n')
        res=run(create,'create',occupied,'good',2,3,timeout=args.timeout)
        check('ERROR=IMAGE_EXISTS' in res.stderr and occupied.read_bytes()==b'NOT AN IMAGE\r\n',
              'ARBITRARY_CLOBBER')
        print('D14C2H3B1-INVALID arbitrary-existing: PASS BYTES_UNCHANGED=1')
        is_dir=root/'directory.kdr';is_dir.mkdir()
        res=run(create,'create',is_dir,'good',2,3,timeout=args.timeout)
        check('ERROR=IMAGE_EXISTS' in res.stderr and is_dir.is_dir(),'DIRECTORY_CLOBBER')
        print('D14C2H3B1-INVALID directory-existing: PASS UNCHANGED=1')
        valid=root/'verify_wrong.kdr'
        good=run(create,'create',valid,'good',2,3,timeout=args.timeout)
        check(good.returncode==0,'CREATE_VERIFY_IMAGE')
        mismatch=run(inspect,'inspect',valid,'good',2,4,timeout=args.timeout)
        check(mismatch.returncode!=0 and 'GEOMETRY_MISMATCH' in mismatch.stderr,'GEOMETRY_NOT_DETECTED')
        corrupt=bytearray(valid.read_bytes());corrupt[-9]^=0x01;valid.write_bytes(corrupt)
        corrupted=run(inspect,'inspect',valid,'good',2,3,timeout=args.timeout)
        check(corrupted.returncode!=0 and 'CHECKSUM_MISMATCH' in corrupted.stderr,'CORRUPT_ACCEPTED')
        print('D14C2H3B1-INVALID geometry+crc: PASS READBACK_REJECT=2/2')
        concurrent=root/'race.kdr'
        def candidate(k):
            return run(create,'create',concurrent,f'race_{k}',2,3,timeout=args.timeout)
        with ThreadPoolExecutor(max_workers=6) as pool:
            race=list(pool.map(candidate,range(6)))
        successes=[r for r in race if r.returncode==0]
        failures=[r for r in race if r.returncode!=0]
        check(len(successes)==1 and len(failures)==5 and
              all('ERROR=IMAGE_EXISTS' in r.stderr for r in failures),'CONCURRENT_CLOBBER')
        check(any(concurrent.read_bytes()==expected(f'race_{k}',2,3) for k in range(6)),
              'RACE_BYTES_NOT_CANONICAL')
        check(not list(root.glob('*.provision.*')),'RESIDUAL_TEMP')
        print('D14C2H3B1-RACE PASS WINNERS=1/6 NO_CLOBBER=1 TEMP_LEAK=0')
    print(f'D14C2H3B1-PROVISION PASS CASES={len(fixed)+len(random_cases)}/'
          f'{len(fixed)+len(random_cases)} INVALID=12/12 RACE=1/1 '
          'INDEPENDENT_BYTES=1 CRC64_ECMA=1 WRITTEN=0 NO_CLOBBER=1 '
          'AUTO_ATTACH=0 CPU_MUTATION=0 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')

if __name__=='__main__':main()
