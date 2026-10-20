# ISA-07 D14-C1c — джерельна звірка адресації барабана

Baseline: 0160c33abcb7a9565df481d8d781985917409056.
Status: SOURCE REVIEW; no CPU changes; HARDWARE_ORACLE=0.

## Evidence

GY62, printed p.15: opcode 25 uses unmodified address II
for drum/track and unmodified address III for initial position.
The drum identifier occupies the third octal digit of address II.

GY62, printed p.59: formal description of opcode 25.
The formula for address II needs separate typographic verification
before use as an independent numeric oracle.

GY62, printed p.124: drum-test description and NK 3002
diagram with fields 0k00 and b, where k=1,2 is the drum
number and b is the starting position.

GY62, printed pp.177–179: drum-test program.
0003/0005 install opcode-25 write/read templates into 0024/0026.
0016/0017 add NK 3002 to those two instructions.
0035/0036 add cell 0060 to those two instructions.
0020/0021 modify the corresponding transfer instructions.
The contents of 0060 depend on the test program and inputs.

DPS64, printed pp.230–233: internal track/position counters
and automatic track advancement. Internal counter bit numbering
must not silently be equated with opcode-25 field encoding.

## Qualified observations

SOURCE_STRICT: 25 selects direction via raw address I.
SOURCE_STRICT: address II identifies drum and track.
SOURCE_STRICT: address III identifies initial position.
SOURCE_DERIVED: drum=(raw_a2>>6)&7, values 1,2 in test;
3 is consistent with the documented three-drum configuration.
SOURCE_DERIVED: NK 3002 adds the same selection and initial
position to write/read preparation templates.
SOURCE_DERIVED: 0035 and 0036 apply the same later correction.

## Unresolved

OPEN: precise program-visible track encoding within address II.
OPEN: meaning of high II bits and permissible track values.
OPEN: position numbering and encoding across a track boundary.
OPEN: exact contents/effect of 0060 for each test configuration.
OPEN: 9864 total codes (GY62) versus 511 per track (DPS64).
OPEN: behavior after the final physical track.

The D14-C1b partial decoder is not a complete drum controller.
In particular, raw_a2 & 03077 is an unresolved bit set, NOT
a proven numeric track identifier.

## Integration gate

Do not add an implicit default historical geometry or track mask.
Do not alter Kyiv_t, opcodes 23/24/25, C/K, or address modifier A
under this documentary step. Any provisional controller mapping
must carry an explicit HOST_POLICY profile and separate tests.
