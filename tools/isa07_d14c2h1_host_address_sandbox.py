#!/usr/bin/env python3
"""Independent model for explicitly opt-in experimental drum address policy.

The model deliberately does NOT decode historical track numbering.
"""
import argparse
import random
import subprocess


WORD_MASK = (1 << 41) - 1


def word25(direction, a2, a3, flags=(0, 0, 0), opcode=0o25):
    x, y, z = flags
    return (opcode << 36) | (x << 35) | (direction << 24) | (
        y << 23) | (a2 << 12) | (z << 11) | a3


def oracle(word, pinned, drums, tracks, slots, count, mode):
    if word > WORD_MASK:
        return 'ERR INVALID_WORD'
    if (word >> 36) & 0o37 != 0o25:
        return 'ERR INVALID_OPCODE'
    direction = (word >> 24) & 0o3777
    a2 = (word >> 12) & 0o3777
    a3 = word & 0o3777
    if direction > 1:
        return 'ERR INVALID_DIRECTION'
    drum = (a2 >> 6) & 7
    if drum not in (1, 2, 3):
        return 'ERR INVALID_DRUM'
    if not drums or not tracks or not slots:
        return 'ERR INVALID_GEOMETRY'
    if drums * tracks * slots > 1000000:
        return 'ERR HOST_CAPACITY_LIMIT'
    if mode == 3:
        return 'ERR UNSUPPORTED_HOST_POLICY'
    if drums != 3:
        return 'ERR HOST_REQUIRES_THREE_DRUMS'
    if ((word >> 35) & 1) or ((word >> 23) & 1) or ((word >> 11) & 1):
        return 'ERR UNQUALIFIED_MODIFICATION_MARK'
    if a2 != (drum << 6):
        return 'ERR UNQUALIFIED_TRACK_MAPPING'
    if pinned not in (1, 2, 3):
        return 'ERR HOST_INVALID_DRUM_LOCK'
    if drum != pinned:
        return 'ERR HOST_DRUM_LOCK_MISMATCH'
    if a3 >= tracks * slots:
        return 'ERR HOST_POSITION_OUT_OF_RANGE'
    first_drum, first_track, first_slot = drum-1, a3 // slots, a3 % slots
    if mode == 0:
        return f'OK {direction} {first_drum} {first_track} {first_slot}'
    if mode not in (1, 2, 4):
        return 'ERR BAD_MODE'
    if count <= 0:
        return 'ERR INVALID_COUNT UNCHANGED=1'
    if a3 + count > tracks * slots:
        return 'ERR END_OF_DRUM UNCHANGED=1'
    if mode == 4:
        return 'ERR INVALID_WORD UNCHANGED=1'
    if mode == 2:
        return 'ERR UNWRITTEN UNCHANGED=1'
    end = a3 + count - 1
    return (f'OK {direction} {first_drum} {first_track} {first_slot} '
            f'{end // slots} {end % slots} {count}')


def cases(random_steps):
    fixed = []
    for drum in (1, 2, 3):
        for direction in (0, 1):
            for start, count in ((0, 1), (3, 2), (11, 1)):
                fixed.append((f'qualified-{drum}-{direction}-{start}',
                              word25(direction, drum << 6, start), drum, 3, 3, 4,
                              count, 1))
    fixed.extend([
        ('ambiguous-0200-after-delta', word25(1, 0o0200, 0), 1, 3, 3, 4, 2, 0),
        ('raw-0101-rejected', word25(1, 0o0101, 0), 1, 3, 3, 4, 1, 0),
        ('raw-1100-rejected', word25(1, 0o1100, 0), 1, 3, 3, 4, 1, 0),
        ('raw-0177-rejected', word25(0, 0o0177, 0), 1, 3, 3, 4, 1, 0),
        ('all-modifier-flags-rejected', word25(0, 0o0100, 0, (1, 1, 1)), 1, 3, 3, 4, 1, 0),
        ('a2-modifier-rejected', word25(0, 0o0100, 0, (0, 1, 0)), 1, 3, 3, 4, 1, 0),
        ('a3-modifier-rejected', word25(0, 0o0100, 0, (0, 0, 1)), 1, 3, 3, 4, 1, 0),
        ('zero-drum-rejected', word25(0, 0o0000, 0), 1, 3, 3, 4, 1, 0),
        ('bad-drum-4', word25(0, 0o0400, 0), 1, 3, 3, 4, 1, 0),
        ('bad-direction', word25(2, 0o0100, 0), 1, 3, 3, 4, 1, 0),
        ('bad-opcode', word25(0, 0o0100, 0, opcode=0o24), 1, 3, 3, 4, 1, 0),
        ('overwide', word25(0, 0o0100, 0) | (1 << 41), 1, 3, 3, 4, 1, 0),
        ('zero-drums', word25(0, 0o0100, 0), 1, 0, 3, 4, 1, 0),
        ('not-three-drums', word25(0, 0o0100, 0), 1, 2, 3, 4, 1, 0),
        ('outside-last-slot', word25(0, 0o0100, 12), 1, 3, 3, 4, 1, 0),
        ('zero-group', word25(1, 0o0100, 11), 1, 3, 3, 4, 0, 1),
        ('end-of-drum-write', word25(1, 0o0100, 11), 1, 3, 3, 4, 2, 1),
        ('last-track-valid', word25(1, 0o0100, 11), 1, 3, 3, 4, 1, 1),
        ('track-wrap-write', word25(1, 0o0100, 3), 1, 3, 3, 4, 3, 1),
        ('track-wrap-read-unwritten', word25(0, 0o0100, 3), 1, 3, 3, 4, 3, 2),
        ('unwritten-read', word25(0, 0o0100, 0), 1, 3, 3, 4, 1, 2),
        ('invalid-last-word-atomic', word25(1, 0o0100, 0), 1, 3, 3, 4, 5, 4),
        ('unknown-host-policy', word25(1, 0o0100, 0), 1, 3, 3, 4, 1, 3),
        ('missing-drum-lock', word25(1, 0o0100, 0), 0, 3, 3, 4, 1, 0),
        ('pin-mismatch', word25(1, 0o0300, 0), 2, 3, 3, 4, 1, 0),
        ('host-capacity-limit', word25(0, 0o0100, 0), 1, 3, 300, 2000, 1, 0),
        ('profile-137', word25(1, 0o0200, 136), 2, 3, 24, 137, 2, 1),
        ('profile-511', word25(1, 0o0300, 511), 3, 3, 24, 511, 3, 1),
        ('max-a3', word25(0, 0o0300, 0o3777), 3, 3, 24, 137, 1, 0),
    ])
    rng = random.Random(0xD14C2A1)
    for i in range(random_steps):
        a2 = rng.choice((0o0100, 0o0200, 0o0300, 0o0101,
                         0o0177, 0o1100, 0o0000, 0o0400))
        g = rng.choice(((3, 2, 3), (3, 3, 4), (3, 24, 137),
                        (3, 24, 511), (2, 3, 4)))
        a3 = rng.choice((0, 1, 2, 3, 5, 11, 12, 63, 64,
                         136, 137, 255, 511, 1023, 2047))
        direction = rng.choice((0, 1, 2))
        flags = rng.choice(((0, 0, 0), (0, 0, 0), (0, 1, 0), (1, 0, 0)))
        count = rng.choice((0, 1, 2, 3, 4, 8))
        mode = rng.choice((0, 1, 2, 4))
        pinned = rng.choice((1, 2, 3, (a2 >> 6) & 7))
        fixed.append((f'random-{i}', word25(direction, a2, a3, flags),
                      pinned, *g, count, mode))
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe')
    ap.add_argument('--random-steps', type=int, default=200)
    ap.add_argument('--timeout', type=float, default=5)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        assert oracle(word25(1, 0o0100, 3), 1, 3, 3, 4, 3, 1) == \
            'OK 1 0 0 3 1 1 3'
        assert oracle(word25(1, 0o0101, 0), 1, 3, 3, 4, 1, 1) == \
            'ERR UNQUALIFIED_TRACK_MAPPING'
        assert oracle(word25(0, 0o0100, 0), 1, 3, 3, 4, 1, 2) == \
            'ERR UNWRITTEN UNCHANGED=1'
        print('D14C2H1-SANDBOX-SELFTEST PASS HOST_POLICY_EXPLICIT=1 TRACK_MAPPING=REJECTED')
        return
    if not args.exe:
        ap.error('--exe required')
    tests = cases(args.random_steps)
    inp = ''.join(' '.join(str(v) for v in t[1:]) + '\n' for t in tests)
    process = subprocess.run([args.exe], input=inp, text=True,
                             capture_output=True, check=True, timeout=args.timeout)
    got = process.stdout.splitlines()
    if len(got) != len(tests):
        raise AssertionError(f'COUNT {len(got)} != {len(tests)}; STDERR={process.stderr!r}')
    for (name, *params), actual in zip(tests, got):
        expected = oracle(*params)
        if actual != expected:
            raise AssertionError(f'{name}: expected={expected!r} got={actual!r}')
    print(f'D14C2H1-HOST-MAP PASS={len(tests)}/{len(tests)} '
          'INDEPENDENT_PYTHON=1 RAW_A2_EXACT=1 A3_LINEAR=HOST_POLICY '
          'DRUM_PIN_GUARD=1 NO_CROSS_DRUM=1 ATOMIC_B2=1 UNWRITTEN=1 '
          'CPU_MUTATION=0 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


if __name__ == '__main__':
    main()
