#!/usr/bin/env python3
"""Independent integer reference for the D13-B textual sign-magnitude adapter."""
from __future__ import annotations
import argparse
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SIGN=1 << 40
MASK=(1 << 41)-1


def oracle(words):
    if not words or len(words)>0o2000: return ('INVALID_COUNT',b'')
    if any(w<0 or w>MASK for w in words): return ('INVALID_WORD',b'')
    return ('EXACT', ''.join(('-' if w&SIGN else '')+str(w&(SIGN-1))+' ' for w in words).encode('ascii'))


def invoke(exe, mode, words, path=None, cwd=None):
    argv=[str(exe),mode]+([str(path)] if path is not None else [])+[str(w) for w in words]
    return subprocess.run(argv,cwd=cwd,capture_output=True,encoding='utf-8',errors='replace',text=True,timeout=5)


def check(exe,label,words):
    expected,data=oracle(words)
    p=invoke(exe,'plan',words)
    match=re.fullmatch(r'D13B-PLAN state=(\S+) bytes=(\d+) hex=([0-9a-f]*)',p.stdout.strip())
    good=(p.returncode==0 and match is not None and
          (match.group(1),int(match.group(2)),match.group(3))==
          (expected,len(data),data.hex())) if match else False
    print(f'D13B-PLAN-CASE {label}: {"PASS" if good else "FAIL"} expected={expected}',flush=True)
    if not good: print(' output=',repr(p.stdout[-300:]),repr(p.stderr[-200:]))
    return good


def fs_cases(exe,root):
    passed=0
    with tempfile.TemporaryDirectory(prefix='d13b_plan_',dir=root) as d:
        p=Path(d)/'magnetic_drum.txt'
        p.write_bytes(b'ORIGINAL\n')
        q=invoke(exe,'commit',[5,SIGN,SIGN|123],p)
        ok=(q.returncode==0 and 'state=EXACT' in q.stdout and
            p.read_bytes()==b'5 -0 -123 ' and
            sorted(x.name for x in p.parent.iterdir())==['magnetic_drum.txt'])
        passed+=ok;print(f'D13B-FS-CASE overwrite: {"PASS" if ok else "FAIL"}',flush=True)
        p.write_bytes(b'ORIGINAL\n')
        q=invoke(exe,'commit',[MASK+1],p)
        ok=(q.returncode==0 and 'state=INVALID_WORD' in q.stdout and
            p.read_bytes()==b'ORIGINAL\n' and
            sorted(x.name for x in p.parent.iterdir())==['magnetic_drum.txt'])
        passed+=ok;print(f'D13B-FS-CASE reject-before-write: {"PASS" if ok else "FAIL"}',flush=True)
        p.unlink();p.mkdir()
        q=invoke(exe,'commit',[5,7],p)
        ok=(q.returncode==0 and 'state=REPLACE_FAILED' in q.stdout and
            p.is_dir() and list(p.iterdir())==[] and
            sorted(x.name for x in p.parent.iterdir())==['magnetic_drum.txt'])
        passed+=ok;print(f'D13B-FS-CASE replace-failure-cleanup: {"PASS" if ok else "FAIL"}',flush=True)
    return passed


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exe',required=True)
    ap.add_argument('--cases',type=int,default=200)
    args=ap.parse_args()
    if not 1<=args.cases<=1000:ap.error('cases range 1..1000')
    exe=Path(args.exe).resolve();root=ROOT/'tempkyiv'
    if not exe.is_file() or not root.is_dir():ap.error('exe and tempkyiv required')
    fixed=[
        [],[0],[1],[SIGN],[SIGN|1],[SIGN-1],[MASK],[0,SIGN,MASK],
        [1,2,3],[SIGN,SIGN],[MASK+1],[1,MASK+1],[SIGN|17,0,SIGN|23],
        [1<<41],[1<<45],[1<<63],[2**64-1],[7,8,9,10],
        [123456789],[SIGN|987654321],[0,0,0],[SIGN-1,SIGN-1],
        [12,34,56],[SIGN|5,SIGN|5],[99,100],
    ]
    rng=random.Random(0xD13B)
    random_cases=[]
    for _ in range(args.cases):
        count=rng.randint(1,4)
        words=[rng.choice((rng.randrange(MASK+1),rng.getrandbits(64),
                           SIGN,0,MASK)) for _ in range(count)]
        random_cases.append(words)
    passed=sum(check(exe,f'fixed{i:02d}',v) for i,v in enumerate(fixed))
    passed+=sum(check(exe,f'random{i:04d}',v) for i,v in enumerate(random_cases))
    fs=fs_cases(exe,root)
    total=len(fixed)+len(random_cases)
    print(f'ISA-07 D13-B PLAN PASS={passed}/{total} FS={fs}/3 '
          'INDEPENDENT_SIGN_MAGNITUDE=1 SIGNED_ZERO=1 HOST_POLICY=1 HARDWARE_ORACLE=0',flush=True)
    return 0 if passed==total and fs==3 else 1
if __name__=='__main__':raise SystemExit(main())
