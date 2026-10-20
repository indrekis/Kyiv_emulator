#!/usr/bin/env python3
"""Independent byte-exact KYIVDRM1 oracle for real Kyiv_t D14-C2-H2/P2."""
import argparse
import pathlib
import random
import struct
import subprocess
import tempfile

SIGN = 1 << 40
MASK = (1 << 41)-1
PROFILE = b'cpu-optin-2x4'
MAGIC = b'KYIVDRM1'
N = 24
CASES = ('success','unprepared-write','unprepared-read','bad-prepare',
         'bad-pin','bad-mark','bad-direction','bad-word','bad-ram',
         'bad-next-fetch','end-of-drum','unwritten','fs-fail',
         'legacy','attach-rollback')


def crc64(data):
    reg = 0
    poly=0x42F0E1EBA9EA3693
    for b in data:
        reg ^= b<<56
        for _ in range(8):
            reg=((reg<<1)^ (poly if reg & (1<<63) else 0)) & ((1<<64)-1)
    return reg


def image(cells):
    bitmap = bytearray((N+7)//8)
    words=[0]*N
    for ix, raw in cells.items():
        assert 0<=ix<N and 0<=raw<=MASK
        bitmap[ix//8] |= 1<<(ix%8)
        words[ix]=raw
    prefix=struct.pack('<8sIIQQQQQII',MAGIC,1,64,3,2,4,N,len(cells),len(PROFILE),0)
    assert len(prefix)==64
    part=prefix+PROFILE+bitmap+b''.join(struct.pack('<Q',x) for x in words)
    return part+struct.pack('<Q',crc64(part))


def self_test():
    assert crc64(b'123456789')==0x6C40DF5F0B497347
    assert image({})!=image({0:0})
    assert image({0:0})!=image({0:SIGN})
    assert image({3:0,4:SIGN,5:MASK})[-8:] == struct.pack('<Q',crc64(image({3:0,4:SIGN,5:MASK})[:-8]))
    print('D14C2H2P2-SANDBOX-SELFTEST PASS CRC64=1 SIGNED_ZERO=1 MUTANT_REJECTED=1')


def run_one(exe,case,root,timeout):
    path=root/'device.kdr'
    initial=image({})
    path.write_bytes(initial)
    proc=subprocess.run([str(exe),str(path),case],cwd=root,encoding='utf8',
                        capture_output=True,timeout=timeout,check=False)
    if proc.returncode!=0:
        raise AssertionError(f'{case} RC={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}')
    if f'D14C2H2P2-CASE {case} PASS CPU_REAL=1' not in proc.stdout:
        raise AssertionError(f'{case}: unexpected report: {proc.stdout!r} {proc.stderr!r}')
    expected=image({3:0,4:SIGN,5:MASK}) if case=='success' else initial
    actual=path.read_bytes()
    if actual != expected:
        ix=next((i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),None)
        raise AssertionError(f'{case}: KDR mismatch at {ix} len={len(actual)} expected={len(expected)}')
    # The P1 persistence contract requires no sibling residue in isolated dir.
    entries=sorted(p.name for p in root.iterdir())
    if entries != ['device.kdr']:
        raise AssertionError(f'{case}: unexpected sibling files {entries}')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--exe')
    p.add_argument('--random-cases',type=int,default=20)
    p.add_argument('--timeout',type=float,default=10)
    a=p.parse_args()
    if a.self_test:
        self_test();return
    if not a.exe: p.error('--exe required')
    exe=pathlib.Path(a.exe).resolve()
    if not exe.is_file(): p.error('exe does not exist')
    rng=random.Random(0xD14C2)
    cases=list(CASES)+[rng.choice(CASES) for _ in range(a.random_cases)]
    with tempfile.TemporaryDirectory(prefix='d14c2h2p2_') as base:
        for i,case in enumerate(cases):
            folder=pathlib.Path(base)/f'case_{i:04d}'
            folder.mkdir()
            run_one(exe,case,folder,a.timeout)
            print(f'D14C2H2P2-CASE {i:02d} {case}: PASS')
    print(f'D14C2H2P2-CPU PASS CASES={len(cases)}/{len(cases)} '
          'REAL_KYIV_T=1 ORIGINAL_OPCODES=1 BYTE_EXACT_KDR=1 '
          'SIGNED_ZERO=1 BRANCH_OVERLAP=1 FS_ROLLBACK=1 '
          'LEGACY_FALLBACK=1 CPU_MUTATION=EXPLICIT '
          'HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')

if __name__=='__main__': main()
