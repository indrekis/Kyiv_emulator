#!/usr/bin/env python3
"""Standalone C++ transaction test with independent Python KYIVDRM1 byte oracle.

No Kyiv_t or source-derived physical track addressing is implied.
"""
import argparse
import random
import struct
import subprocess
import tempfile
from pathlib import Path

SIGN = 1 << 40
MASK = (1 << 41) - 1
POLY = 0x42F0E1EBA9EA3693
PROFILE = "h2v1-test"
TRACKS, SLOTS = 2, 4
COUNT = 3 * TRACKS * SLOTS


def crc64(data):
    c = 0
    for b in data:
        c ^= b << 56
        for _ in range(8):
            c = ((c << 1) ^ (POLY if c & (1 << 63) else 0)) & ((1 << 64) - 1)
    return c


def wire(cells, profile=PROFILE, tracks=TRACKS, slots=SLOTS):
    assert len(cells) == 3 * tracks * slots
    n = len(cells)
    bitmap = bytearray((n + 7) // 8)
    payload = bytearray()
    for i, word in enumerate(cells):
        if word is not None:
            assert 0 <= word <= MASK
            bitmap[i // 8] |= (1 << (i % 8))
        payload.extend(struct.pack('<Q', 0 if word is None else word))
    head = (b'KYIVDRM1' + struct.pack('<IIQQQQQII',
            1, 64, 3, tracks, slots, n,
            sum(x is not None for x in cells), len(profile), 0))
    content = head + profile.encode('ascii') + bitmap + payload
    return content + struct.pack('<Q', crc64(content))


def ins(op=0o25, direction=0, a2=0o100, a3=0, marks=(0, 0, 0)):
    f1, f2, f3 = marks
    return ((op << 36) | (f1 << 35) | (direction << 24) |
            (f2 << 23) | (a2 << 12) | (f3 << 11) | a3)


def initial():
    cells = [None] * COUNT
    cells[10] = 0  # WRITTEN +0 on another drum
    cells[20] = SIGN  # WRITTEN -0 on another drum
    return cells


class Model:
    def __init__(self, cells, lock=1):
        self.cells = list(cells)
        self.lock = lock
        self.r = None
        self.w = None

    def span(self, start, count):
        if count == 0:
            return 'INVALID_COUNT'
        if (start % (TRACKS * SLOTS)) + count > TRACKS * SLOTS:
            return 'END_OF_DRUM'
        return None

    def act(self, item):
        op = item[0]
        if op == 'P':
            word = item[1]
            if word > MASK:
                return 'ERR INVALID_WORD'
            if (word >> 36) & 0o37 != 0o25:
                return 'ERR INVALID_OPCODE'
            direction = (word >> 24) & 0o3777
            a2 = (word >> 12) & 0o3777
            a3 = word & 0o3777
            if direction not in (0, 1):
                return 'ERR INVALID_DIRECTION'
            drum = (a2 >> 6) & 7
            if drum not in (1, 2, 3):
                return 'ERR INVALID_DRUM'
            if (word & ((1 << 35) | (1 << 23) | (1 << 11))):
                return 'ERR UNQUALIFIED_MODIFICATION_MARK'
            if a2 != (drum << 6):
                return 'ERR UNQUALIFIED_TRACK_MAPPING'
            if drum != self.lock:
                return 'ERR HOST_DRUM_LOCK_MISMATCH'
            if a3 >= TRACKS * SLOTS:
                return 'ERR HOST_POSITION_OUT_OF_RANGE'
            start = (drum - 1) * (TRACKS * SLOTS) + a3
            if direction == 0:
                self.r = start
            else:
                self.w = start
            return f'P {"R" if direction == 0 else "W"} {drum - 1} {a3 // SLOTS} {a3 % SLOTS}'
        if op in ('W', 'X'):
            words = item[1]
            if self.w is None:
                return 'ERR UNPREPARED_WRITE'
            error = self.span(self.w, len(words))
            if error:
                return f'ERR {error}'
            if any(x > MASK for x in words):
                return 'ERR INVALID_WORD'
            if op == 'X':
                return 'ERR REPLACE_FAILED'
            for i, word in enumerate(words):
                self.cells[self.w + i] = word
            end = (self.w % (TRACKS * SLOTS)) + len(words) - 1
            return f'W {end // SLOTS} {end % SLOTS}'
        if op == 'R':
            n = item[1]
            if self.r is None:
                return 'ERR UNPREPARED_READ'
            error = self.span(self.r, n)
            if error:
                return f'ERR {error}'
            words = self.cells[self.r:self.r + n]
            if any(x is None for x in words):
                return 'ERR UNWRITTEN'
            return 'R ' + str(n) + ''.join(' ' + str(x) for x in words)
        if op == 'S':
            return f'S {sum(x is not None for x in self.cells)} {int(self.r is not None)} {int(self.w is not None)}'
        if op == 'I':
            d,t,s = item[1:]
            if d >= 3:
                return 'ERR INVALID_DRUM'
            if t >= TRACKS:
                return 'ERR INVALID_TRACK'
            if s >= SLOTS:
                return 'ERR INVALID_SLOT'
            x = self.cells[(d * TRACKS + t) * SLOTS + s]
            return f'I {int(x is not None)} {0 if x is None else x}'
        raise AssertionError(item)


def protocol(item):
    if item[0] == 'P':
        return f'P {item[1]}'
    if item[0] in ('W','X'):
        return item[0] + ' ' + str(len(item[1])) + ''.join(' ' + str(x) for x in item[1])
    if item[0] == 'R':
        return f'R {item[1]}'
    if item[0] == 'S':
        return 'S'
    if item[0] == 'I':
        return f'I {item[1]} {item[2]} {item[3]}'
    raise AssertionError(item)


def suite(lock, rng, steps=0):
    a2 = lock << 6
    seq = [ ('S',), ('R', 1), ('W', [1]),
            ('P', ins(direction=1,a2=a2,a3=3)),
            ('W', [0, SIGN, 9]), ('S',),
            ('P', ins(direction=0,a2=a2,a3=3)),
            ('R', 3), ('I',lock-1,0,3), ('I',lock-1,1,0),
            ('P', ins(direction=1,a2=a2,a3=0,marks=(0,1,0))),
            ('W',[SIGN]), ('P', ins(direction=0,a2=a2+1,a3=0)),
            ('S',), ('X',[12]), ('S',),
            ('P', ins(direction=1,a2=a2,a3=7)),
            ('W',[1,2]), ('W',[MASK+1]),
            ('P', ins(direction=1,a2=a2,a3=2)),
            ('W',[MASK+1,2]), ('S',),
            ('P', ins(direction=0,a2=a2,a3=7)),
            ('R',2), ('R',0),
            ('P', ins(direction=0,a2=a2,a3=6)), ('R',2),
            ('P', ins(direction=0,a2=a2,a3=100)),
            ('P', ins(direction=0,a2=(1 if lock != 1 else 2)<<6,a3=0)),
            ('P', ins(direction=2,a2=a2,a3=0)),
            ('I',0,0,0), ('I',3,0,0), ('I',0,2,0), ('I',0,0,4)]
    # Independent random mixture across valid/invalid/overwide words.
    for _ in range(steps):
        choice = rng.randrange(6)
        if choice == 0:
            seq.append(('P',ins(direction=rng.randrange(3),
                         a2=rng.choice([a2,a2+1,0o100,0o400]),
                         a3=rng.randrange(11))))
        elif choice == 1:
            seq.append(('W', [rng.choice([0,1,SIGN,MASK,MASK+1,17])
                              for _ in range(rng.randrange(5))]))
        elif choice == 2:
            seq.append(('R',rng.randrange(11)))
        elif choice == 3:
            seq.append(('S',))
        elif choice == 4:
            seq.append(('I',rng.randrange(4),rng.randrange(3),rng.randrange(5)))
        else:
            seq.append(('P',ins(direction=rng.randrange(2),a2=a2,
                                 a3=rng.randrange(8))))
    return seq


def one_case(exe, lock, seed, random_steps, timeout):
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix='kyiv-d14c2h2-') as temp:
        path = Path(temp) / 'media.kdr'
        original = initial()
        path.write_bytes(wire(original))
        model = Model(original, lock)
        operations = suite(lock, rng, random_steps)
        expected = [model.act(op) for op in operations]
        payload = '\n'.join(protocol(op) for op in operations)+'\n'
        process = subprocess.run(
            [exe,str(path),PROFILE,str(TRACKS),str(SLOTS),str(lock)],
            input=payload,text=True,capture_output=True,timeout=timeout,check=True)
        lines = process.stdout.splitlines()
        if not lines or lines[0] != 'INIT OK':
            raise AssertionError(f'INIT {lines[:4]} stderr={process.stderr[:300]}')
        actual = lines[1:]
        if len(actual) != len(expected):
            raise AssertionError(f'COUNT {len(actual)} != {len(expected)}; {actual[-5:]}')
        for i,(want,got) in enumerate(zip(expected,actual)):
            if want != got:
                raise AssertionError(f'SEED={seed} STEP={i} {operations[i]}: {want} != {got}')
        if path.read_bytes() != wire(model.cells):
            raise AssertionError(f'SEED={seed} BINARY_IMAGE_MISMATCH')
        leftovers = list(Path(temp).glob('media.kdr.tmp.*'))
        if leftovers:
            raise AssertionError(f'TEMP_FILES_LEFT: {leftovers}')
        return len(expected)


def negative_init(exe, timeout):
    with tempfile.TemporaryDirectory(prefix='kyiv-d14c2h2-init-') as temp:
        path=Path(temp)/'media.kdr'
        args=lambda profile,tracks,slots,pin: [exe,str(path),profile,str(tracks),str(slots),str(pin)]
        missing=subprocess.run(args(PROFILE,TRACKS,SLOTS,1),input='',text=True,
                               capture_output=True,timeout=timeout,check=True)
        assert missing.stdout.strip() == 'INIT ERR IMAGE_OPEN_FAILED',missing.stdout
        path.write_bytes(wire(initial()))
        mismatched=subprocess.run(args(PROFILE,TRACKS,SLOTS+1,1),input='',text=True,
                                  capture_output=True,timeout=timeout,check=True)
        assert mismatched.stdout.strip() == 'INIT ERR GEOMETRY_MISMATCH',mismatched.stdout
        badlock=subprocess.run(args(PROFILE,TRACKS,SLOTS,4),input='',text=True,
                               capture_output=True,timeout=timeout,check=True)
        assert badlock.stdout.strip() == 'INIT ERR HOST_INVALID_DRUM_LOCK',badlock.stdout
        assert path.read_bytes() == wire(initial())
    return 3


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exe',required=True)
    p.add_argument('--random-cases',type=int,default=20)
    p.add_argument('--random-steps',type=int,default=50)
    p.add_argument('--timeout',type=float,default=5)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    if args.self_test:
        assert crc64(b'123456789') == 0x6C40DF5F0B497347
        assert len(wire(initial())) == 64 + len(PROFILE) + 3 + 8*COUNT + 8
        assert ins(0o25,1,0o100,0) >> 36 == 0o25
        print('D14C2H2-SANDBOX-SELFTEST PASS CRC_VECTOR=1 RAW_ENCODING=1 CANONICAL_IMAGE=1')
        return
    assert args.random_cases>=0 and args.random_steps>=0
    n=0
    for lock in (1,2,3):
        count=one_case(args.exe,lock,0xD14C2200+lock,0,args.timeout)
        n+=count
        print(f'D14C2H2-CASE lock-{lock}: PASS COMMANDS={count}')
    for i in range(args.random_cases):
        lock=i%3+1
        count=one_case(args.exe,lock,0xD14C2201+i,args.random_steps,args.timeout)
        n+=count
        print(f'D14C2H2-CASE random-{i}: PASS COMMANDS={count}')
    negative_init(args.exe,args.timeout)
    print(f'D14C2H2-SESSION PASS CASES={args.random_cases+6}/{args.random_cases+6} '
          f'COMMANDS={n} INITIALIZATION_NEGATIVE=3/3 INDEPENDENT_BYTES=1 '
          'PREP_SEPARATE=1 FS_ROLLBACK=1 SIGNED_ZERO=1 UNWRITTEN=1 '
          'CPU_MUTATION=0 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


if __name__=='__main__':
    main()
