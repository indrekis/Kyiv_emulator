#!/usr/bin/env python3
"""D14-C1f SOURCE-DERIVED word encoding and mathematical ambiguity.

This is not an oracle for the hardware drum track, and it runs no CPU.
"""

OP = 0o25
SIGN_BIT = 1 << 40
WORD_MASK = (1 << 41) - 1
A2_MASK = 0o3777

def instruction(a1: int, a2: int, a3: int) -> int:
    assert 0 <= a1 <= 1 and 0 <= a2 < 0o4000 and 0 <= a3 < 0o4000
    return (OP << 36) | (a1 << 24) | (a2 << 12) | a3

def a2(word: int) -> int:
    return (word >> 12) & A2_MASK

count = 0
# GY62 printed p59: machine fixed point k*2^-22 -> raw magnitude k<<18.
# It must occupy the third octal digit of the raw II address.
for k in (1, 2, 3):
    raw_magnitude = k << (40 - 22)
    assert (raw_magnitude >> 12) & A2_MASK == k << 6
    assert (raw_magnitude & ((1 << 12) - 1)) == 0
    assert (k << 6) == k * 0o100
    count += 1

# GY62 p83: 3040 = 2^-12, raw fixed-point magnitude=2^28.
raw_rom3040 = 1 << (40 - 12)
assert raw_rom3040 == 0o002000000000
count += 1

# Illustrate under explicitly CONDITIONAL NK3000 n value: raw n in I
# address => n<<24, exact unrounded fixed-point multiplication >>40
# yields n<<12 (i.e. +n to raw II field, before field overflow).
for k in (1, 2, 3):
    for n in (0, 1, 63, 64, 137, 256, 500):
        for direction in (0, 1):
            original = instruction(direction, k << 6, 0)
            correction = ((n << 24) * raw_rom3040) >> 40
            assert correction == n << 12
            updated = original + correction
            assert updated <= WORD_MASK
            assert a2(updated) == (k << 6) + n
            count += 1

# Same FINAL 41-bit opcode 25 produced by distinct arithmetic histories.
# We do not assume actual drum semantics or track selection from this.
for (k1, n1, k2, n2) in [
    (1, 64, 2, 0),
    (1, 128, 3, 0),
    (2, 64, 3, 0),
    (1, 191, 3, 63),
]:
    for direction in (0, 1):
        for place in (0, 0o73, 0o777):
            left = instruction(direction, k1 << 6, place) + (n1 << 12)
            right = instruction(direction, k2 << 6, place) + (n2 << 12)
            assert left == right and left <= WORD_MASK
            assert a2(left) == (k1 << 6) + n1 == (k2 << 6) + n2
            count += 1

# DPS64 printed p231 INTERNAL 8+5 split (KShP1-8/KShP9-13).
# 612=2*256+100. This is NOT a decoder for raw II address.
for linear in (0, 100, 255, 256, 511, 512, 612, 8191):
    internal_track = (linear >> 8) & 31
    internal_place = linear & 255
    assert linear == (internal_track << 8) | internal_place
    if linear == 612:
        assert (internal_track, internal_place) == (2, 100)
    count += 1

print(
    f'D14C1F-WITNESS PASS={count}/{count} '
    'GY62_DRUM_ENCODING=1 ROM3040=1 '
    'FINAL_WORD_COLLISION=1 DPS64_INTERNAL_8_5=1 '
    'TRACK_MAPPING=OPEN HISTORICAL_CAPACITY=OPEN '
    'CPU_MUTATION=0 HARDWARE_ORACLE=0'
)
