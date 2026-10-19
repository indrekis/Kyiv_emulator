#!/usr/bin/env python3
"""D14-B2: independent Python reference for bounded, atomic track-spanning API."""
from __future__ import annotations
import argparse
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGN = 1 << 40
MAX = (1 << 41) - 1

class Reference:
    def __init__(self, geometry):
        self.profile, self.drums, self.tracks, self.slots = geometry
        self.cells = {}

    def at(self, d, t, s):
        if not 0 <= d < self.drums: raise ValueError('INVALID_DRUM')
        if not 0 <= t < self.tracks: raise ValueError('INVALID_TRACK')
        if not 0 <= s < self.slots: raise ValueError('INVALID_SLOT')

    def span(self, d, t, s, count):
        if not count: raise ValueError('INVALID_COUNT')
        self.at(d,t,s)
        if count > (self.tracks-t)*self.slots-s:
            raise ValueError('END_OF_DRUM')
        positions = []
        for _ in range(count):
            positions.append((d,t,s))
            s += 1
            if s == self.slots:
                s = 0
                t += 1
        return positions

    def execute(self, command):
        parts = command.split()
        op = parts[0]
        if op == 'CAP': return f'CAP {self.drums*self.tracks*self.slots}'
        if op == 'COUNT': return f'COUNT {len(self.cells)}'
        try:
            d,t,s = map(int,parts[1:4])
            if op == 'GET':
                self.at(d,t,s)
                if (d,t,s) not in self.cells: return 'UNWRITTEN'
                return f'CELL {self.cells[d,t,s]}'
            if op == 'ERASE':
                self.at(d,t,s)
                self.cells.pop((d,t,s),None)
                return 'OK'
            count = int(parts[4]); positions = self.span(d,t,s,count)
            if op == 'READ':
                for p in positions:
                    if p not in self.cells: raise ValueError('UNWRITTEN')
                return 'WORDS ' + ' '.join(str(self.cells[p]) for p in positions)
            if op == 'WRITE':
                words = tuple(map(int,parts[5:]))
                assert len(words) == count
                if any(w < 0 or w > MAX for w in words):
                    raise ValueError('INVALID_WORD')
                for p,w in zip(positions, words): self.cells[p] = w
                last = positions[-1]
                return f'OK {last[0]} {last[1]} {last[2]}'
            raise AssertionError(op)
        except ValueError as e:
            return 'ERROR '+str(e)

def W(d,t,s,*words):
    return 'WRITE ' + ' '.join(map(str,(d,t,s,len(words),*words)))
def R(d,t,s,n): return f'READ {d} {t} {s} {n}'
def G(d,t,s): return f'GET {d} {t} {s}'
def E(d,t,s): return f'ERASE {d} {t} {s}'

MINI=('mini',2,3,4)
FIXED = [
  ('single', MINI, [W(0,0,0,123),R(0,0,0,1),G(0,0,0)]),
  ('track-cross', MINI, [W(0,0,3,1,SIGN,MAX),R(0,0,3,3)]),
  ('multi-cross', MINI, [W(0,0,2,*range(11)),R(0,0,2,11)]),
  ('exact-end', MINI, [W(0,2,2,91,92),R(0,2,2,2)]),
  ('end-overflow', MINI, [W(0,2,2,91,92),W(0,2,2,44,55,66),R(0,2,2,3),G(0,2,3)]),
  ('unwritten-read', MINI, [R(0,0,0,1),G(0,0,0)]),
  ('read-cross-gap', MINI, [W(0,0,3,5),R(0,0,3,2),G(0,1,0)]),
  ('invalid-first-word', MINI, [W(0,0,0,2,3),W(0,0,0,1<<41,7),R(0,0,0,2)]),
  ('invalid-middle-word', MINI, [W(0,0,1,2,3,4),W(0,0,1,5,1<<50,6),R(0,0,1,3)]),
  ('invalid-last-word', MINI, [W(0,0,3,7,8,9),W(0,0,3,2,3,1<<41),R(0,0,3,3)]),
  ('bad-coordinate', MINI, [W(2,0,0,1),W(0,3,0,1),W(0,0,4,1),R(1,0,4,1)]),
  ('empty-group', MINI, [W(0,0,0),R(0,0,0,0),G(0,0,0)]),
  ('isolate-drum', MINI, [W(0,0,3,77,88),R(1,0,3,2),W(1,0,3,99,100),R(0,0,3,2)]),
  ('erase-and-rewrite', MINI, [W(0,0,3,1,2),E(0,1,0),R(0,0,3,2),W(0,1,0,3),R(0,0,3,2)]),
  ('overlap', MINI, [W(0,0,0,1,2,3,4),W(0,0,2,MAX,SIGN),R(0,0,0,4)]),
  ('signed-zero', MINI, [W(0,1,0,0,SIGN,MAX),R(0,1,0,3)]),
  ('last-track', MINI, [W(1,2,0,1,2,3,4),R(1,2,0,4),W(1,2,3,5,6),R(1,2,0,4)]),
  ('capacity', MINI, ['CAP','COUNT',W(1,2,0,0), 'COUNT']),
]

def randomized(seed, geometry, steps):
    rnd=random.Random(seed)
    _,dmax,tmax,smax=geometry
    commands=['CAP','COUNT']
    for i in range(steps):
        d = rnd.choice((0,dmax-1,rnd.randrange(dmax),dmax))
        t = rnd.choice((0,tmax-1,rnd.randrange(tmax),tmax))
        s = rnd.choice((0,smax-1,rnd.randrange(smax),smax))
        count=rnd.choice((0,1,2,3,smax,smax+1, min(12,tmax*smax+1)))
        op=rnd.choice(('WRITE','READ','GET','ERASE','COUNT','WRITE','READ'))
        if op=='WRITE':
            words=[rnd.choice((0,1,SIGN,MAX,MAX+1,rnd.randrange(MAX+1)))
                   for _ in range(count)]
            commands.append(W(d,t,s,*words))
        elif op=='READ':commands.append(R(d,t,s,count))
        elif op=='GET':commands.append(G(d,t,s))
        elif op=='ERASE':commands.append(E(d,t,s))
        else: commands.append('COUNT')
    return commands

def execute_case(exe, label, geometry, commands, timeout):
    ref=Reference(geometry)
    wanted = [ref.execute(c) for c in commands]
    # Final state oracle: every slot for mini profiles, deterministic sampling for large.
    allcoords = [(d,t,s) for d in range(geometry[1])
                 for t in range(geometry[2]) for s in range(geometry[3])]
    if len(allcoords) > 500:
        rnd = random.Random(1212)
        allcoords = [allcoords[i] for i in sorted(set(
            [0,len(allcoords)-1] + [rnd.randrange(len(allcoords)) for _ in range(80)]))]
    final=['COUNT']+[G(*p) for p in allcoords]
    wanted += [ref.execute(c) for c in final]
    commands += final
    input_text='\n'.join(commands)+'\n'
    try:
        p=subprocess.run([str(exe),geometry[0],*map(str,geometry[1:])],
              input=input_text, capture_output=True, text=True, encoding='utf-8',
              errors='replace', timeout=timeout)
        lines=p.stdout.splitlines()
        header=f'D14B2-INIT {geometry[1]*geometry[2]*geometry[3]}'
        received=[]
        for i,line in enumerate(lines[1:]):
            prefix=f'D14B2-RESULT {i} '
            if not line.startswith(prefix): raise ValueError('BAD_RESULT_PREFIX '+repr(line[:90]))
            received.append(line[len(prefix):])
        ok=p.returncode==0 and lines[:1]==[header] and received==wanted
        if not ok:
            mismatch=next((i for i,(a,b) in enumerate(zip(wanted,received)) if a!=b), None)
            print('  DIAG exit=',p.returncode,'want=',len(wanted),'got=',len(received),
                  'mismatch=',mismatch,'stderr_tail=',repr(p.stderr[-300:]))
            if mismatch is not None:
                print('  CMD=',repr(commands[mismatch]),'EXPECTED=',repr(wanted[mismatch]),'GOT=',repr(received[mismatch]))
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        ok=False
        print('  DIAG ERROR=',repr(exc))
    print(f'D14B2-CASE {label}: {"PASS" if ok else "FAIL"} '
          f'COMMANDS={len(commands)} PROFILE={geometry[0]}')
    return ok,len(commands)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--random-steps',type=int,default=200)
    ap.add_argument('--timeout',type=float,default=5)
    args=ap.parse_args()
    exe=Path(args.exe).resolve()
    if not exe.is_file() or not (ROOT/'tempkyiv').is_dir():ap.error('exe/tempkyiv missing')
    if not 1<=args.random_steps<=2000:ap.error('random steps 1..2000')
    if not 0.5<=args.timeout<=120:ap.error('timeout 0.5..120')
    cases=list(FIXED)
    for name,geom,seed in [
        ('random-mini',MINI,7301),
        ('random-asymmetric',('asym-3x4x5',3,4,5),7302),
        ('random-exp137',('experiment-137',3,24,137),7303),
        ('random-exp511',('experiment-511',3,24,511),7304),
    ]:
        cases.append((name,geom,randomized(seed,geom,args.random_steps)))
    total=0;passed=0
    for label,geom,seq in cases:
        ok,n=execute_case(exe,label,geom,list(seq),args.timeout)
        total+=n;passed+=bool(ok)
    good=passed==len(cases)
    print(f'ISA-07 D14-B2 GROUP {"PASS" if good else "FAIL"}={passed}/{len(cases)} '
          f'COMMANDS={total} INDEPENDENT_PYTHON=1 TRACK_WRAP=1 '
          'NO_CROSS_DRUM=1 UNWRITTEN_REJECTED=1 ATOMIC_WRITE=1 '
          'PROFILE_EXPLICIT=1 CPU_MUTATION=0 PERSISTENCE=DEFERRED HARDWARE_ORACLE=0')
    return 0 if good else 1

if __name__=='__main__':sys.exit(main())
