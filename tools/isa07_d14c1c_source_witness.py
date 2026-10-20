#!/usr/bin/env python3
"""Symbolic witness for the original GY62 drum-test transformations.

Checks instruction-word arithmetic only, NOT a physical track oracle.
"""
def instruction(op, a1, a2, a3):
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3

MASK = (1 << 41) - 1
write_template = instruction(0o25, 1, 0, 0)
read_template = instruction(0o25, 0, 0, 0)

cases = 0
for drum in (1, 2):
    for starting_place in (0, 1, 0o17, 0o77):
        # NK 3002: source diagram 0k00 | b.
        nk3002 = instruction(0, 0, drum << 6, starting_place)
        write = write_template + nk3002
        read = read_template + nk3002

        assert ((write >> 36) & 0o37) == 0o25
        assert ((read >> 36) & 0o37) == 0o25
        assert ((write >> 12) & 0o3777) == drum << 6
        assert ((read >> 12) & 0o3777) == drum << 6
        assert (write & 0o3777) == starting_place
        assert (read & 0o3777) == starting_place
        assert write - read == (1 << 24)
        cases += 1

        # Shared additions at 0035/0036. Values are SYNTHETIC:
        # we do not claim the contents of historical cell 0060.
        for delta in (0, 1, 0o10):
            w2 = write + delta
            r2 = read + delta
            assert w2 <= MASK and r2 <= MASK
            assert w2 - r2 == (1 << 24)
            assert ((w2 >> 36) & 0o37) == 0o25
            assert ((r2 >> 36) & 0o37) == 0o25
            cases += 1

print(
    f"D14C1C-WITNESS PASS={cases}/{cases} "
    "ORIGINAL_TEMPLATES=1 SHARED_ADDITIONS=1 "
    "TRACK_MAPPING=OPEN CPU_MUTATION=0 HARDWARE_ORACLE=0"
)
