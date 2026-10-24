# D15/B1-H15 — negative rounded multiplication: source qualification

Pinned parent: `90c8340b3c957707ea6586bdeaff352d492ccbb4`. No CPU, ROM, or H1–H14 canonical image modifications.
Historical source: Glushkov–Yushchenko (1962), *printed* p.172 for RAM
and formula, printed p.173 for three machine instructions.
The `.k41` image is a modern HOST text container, not original media.
A second **independent human transcription** is pending.

## First visual source record

| Octal address | Exact 41-bit word (14 octal digits) | Printed page | Role |
|---|---|---|---|
| `0004` | `05252525252525` | 172 | positive_operand |
| `0005` | `32525252525252` | 172 | negative_operand |
| `0025` | `23434343434343` | 172 | historical_negative_rounded_product |
| `0202` | `11000400050347` | 173 | opcode11_rounded_multiply |
| `0203` | `16034700250205` | 173 | opcode16_compare_and_skip_STOP |
| `0204` | `33000000000000` | 173 | original_failure_STOP |


Printed p.172 gives `05(25) × 32(52) = 23(43)` at `0202–0204`.
Source code at p.173: opcode `11` at `0202` consumes RAM `0004` and
`0005`, writes `0347`. Opcode `16` at `0203` compares `0347` with `0025`
for a jump to `0205`; `0204` is the literal original failure STOP.

## CPU-independent exact integer arithmetic

Sign/magnitude representation is 1 sign bit (bit 40), 40 fraction bits.
Operand `0004=05252525252525` has a positive sign; operand
`0005=32525252525252` has a negative sign. With magnitudes `a` and `b`,
current software rounded-multiply rule computes:

```
a = 0o5252525252525; b = 0o12525252525252
rounded_magnitude = (a*b + (1<<39)) >> 40
negative_result_word = (1<<40) | rounded_magnitude
```

This calculation predicts exact 41-bit `23434343434343` at `0347`, matching
p.172 RAM `0025` independently of simulator execution. This single
agreement does not settle H14's different rounded multiplication conflict.
After one instruction expect `LIMIT STEPS=1 C=0203`; after two expect
`LIMIT STEPS=2 C=0205`. **Do not execute address `0205`.**

The original STOP `0204` is checked on a temporary HOST-only image
retargeting *only JE's second operand*, `0203: 16034700250205` to
`0203: 16034700040205`. Thus the original multiplication and STOP
remain identical and the private image cannot be misidentified as a
canonical transcription. A 3-step run must stop at `C=0205`.

## Qualification and unresolved evidence

- Exact source records: 6 (3 data, 3 commands); expected native tests: 6
  (1, 2, 3 CPU steps in each of two working directories).
- Check the full input and expected RAM words, the exact result, the
  branch/STOP, and CWD parity; record historical match only after native execution.
- H9 (source/prose), H10 (cyclic carry), H11 (opcode 06 signed zero),
  H13 (source label), and H14 (third rounded multiplication) remain
  `OPEN_UNCHANGED`, not resolved by this narrow test.
- Historical arithmetic oracle: printed table, not physical hardware.
  `HARDWARE_ORACLE=0`; `HUMAN_INDEPENDENT_WITNESS=PENDING`.
- Static audit `NATIVE_GATE=PENDING` is a source artifact marker.
  Native observations belong in separate runtime evidence and commit metadata.
