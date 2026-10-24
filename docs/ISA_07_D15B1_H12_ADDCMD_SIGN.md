# D15/B1-H12 — signed command addition, GY1962 AU diagnostic

Pinned baseline: `ef90df8b5718a0b20acdfca64ab15f9584207412` (H11 committed/pushed).

## Historical source and scope

Glushkov and Yushchenko (1962), printed **p.172**: the AU test states
`12(52) СлК (25) = 3(7)` for the range `0163–0165`; the data list at
p.172 gives `0002=12525252525252` and `0003=25252525252525`.
Printed **p.173** contains the three original commands listed below.
The `.k41` file is a modern HOST representation, not original punched media.
One first-pass visual reading exists; independent human witness **PENDING**.

| Address (octal) | Full 41-bit word (14 octal digits) | Source |
|---|---|---|
| `0002` | `12525252525252` | GY1962 p.172 |
| `0003` | `25252525252525` | GY1962 p.172 |
| `0163` | `03000200030347` | GY1962 p.173, opcode `03` |
| `0164` | `16034730360166` | GY1962 p.173, opcode `16` |
| `0165` | `33000000000000` | GY1962 p.173, opcode `33` |

## CPU-independent arithmetic oracle

Kyiv's 41-bit words are sign-magnitude: bit 40 is the sign, lower 40
bits are magnitude. `0002` is positive, `0003` is negative. The command
addition operation (СлК) sums magnitudes and assigns the second operand's
sign independently of the sum sign. In octal:

```text
|12525252525252| + |25252525252525| = 17777777777777
sign(0003) = negative
result = 37777777777777
```

The reconstructed, immutable default ROM contains
`3036 = 37777777777777`; this value is checked both from the ROM Git blob
and by observing ROM `3036` during the real test. It is **not** independent
physical-hardware evidence.

## Bounded native cases

From `0163`, expect after 1 instruction: `LIMIT STEPS=1 C=0164`,
`0347=37777777777777`; after 2: `LIMIT STEPS=2 C=0166` (successful JE).
Never execute opcode `13` at `0166`. For a controlled negative path only,
replace the comparison word at `0164` on a **temporary image** from
`16 0347 3036 0166` to `16 0347 0002 0166`; the original ADD and STOP
are still byte-identical. After three instructions expect
`CPU_STOP STEPS=3 C=0166`. Two working directories yield **6 cases**.
Private mutants are never committed or used as historical source claims.

## Qualification boundary and unresolved items

The native runner distinguishes historical success from synthetic STOP
coverage; source audit alone never claims a real CPU pass. No CPU/ROM
mutations or changes to prior canonical examples are admitted. H9 source
prose conflict, H10 cyclic carry discrepancy and H11 opcode 06 signed-zero
mismatch all remain **OPEN_UNCHANGED**. `HARDWARE_ORACLE=0` and independent
human transcription remains pending. Do not extend test execution to `0166`.
