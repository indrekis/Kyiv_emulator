# ISA-04 D2 — audit of cyclic carry, signed zero and normalization

Baseline: `3b2fdfd` (ISA-01–04 D1, pushed to `main`). This document is a
supplement to `ISA_04_ARITHMETIC_AUDIT.md`, not a replacement.

## Evidence, not assumptions

- **GY62, printed p. 11, operation 07**: no overflow interlock; carry from the
  sign position is returned to the least significant summator position.
- **DPS64, printed p. 102, table 4 and paragraph “Циклическое сложение”**:
  states that for sums exceeding +1 the machine emits `a1+a2-1`, for sums
  below -1 it emits `a1+a2+1`. It does not give a separate exact bit pattern
  for the `|sum| = 1` boundary. The text of GY62 suggests end-around carry,
  which in a discrete code may differ by one unit in the last place (ULP)
  from the DPS64 fractional formula. The combination is **not** enough to
  certify either end-state for all boundary codes.
- **GY62, printed p. 11, 10/11**: multiplication with/without rounding, where
  rounding adds one at the highest discarded digit. It does **not** explicitly
  specify the sign bit of a zero product in these paragraphs.
- **GY62, printed pp. 11–12, 35**: normalized nonzero mantissa and six-bit
  order sent to address II, mantissa to III. **Zero is not covered by the
  mathematical definition.** No definite machine code for normalizing -0
  has been established here.
- **DPS64, printed pp. 94–97, 102–103**: arithmetic summator uses complement
  codes and a carry network. That explains why direct fixed-point integer
  arithmetic is not by itself a sufficiently strong hardware oracle.

## D2 scope and explicit policy

The `07` implementation is only **refactored**, NOT changed semantically:
for algebraic integer sum `s`, `m=abs(s)`, `M=2^40`, compute
`(m + (m>=M ? 1 : 0)) & (M-1)`, retaining sign of `s`. This is the existing
emulator **end-around-carry policy**. No `double` or debug decision controls
output anymore. `POLICY`-tests preserve this choice across refactors;
`OBS` records how it differs from the exact `mod M` mathematical remainder.

`10/11` and `35` are **not changed** in D2. Their `-0` behavior remains OBS,
not verified as historical. In particular, D1's `35(+0/-0)` order `047` (octal,
39 decimal) is a consequence of the current implementation, not an ISA fact.

## Test classes

- `STRICT`: documented unambiguous behavior, nonzero operands, no disputed carry.
- `POLICY`: deterministic emulator convention for disputed carry cases;
  regression only; **not** evidence of authentic historical behavior.
- `OBS`: outputs printed without PASS/FAIL historical judgment.

## Open research before modifying historical semantics

1. Establish exact 41-bit gate-level carry for 07 using DPS64 summator wiring
   and, if available, historic test vectors. In particular, test `M` and
   `M+1` algebraic sums with both signs.
2. Derive the sign of a zero product after 10/11 (input -0 and results
   rounded/truncated to zero) from the microoperation sequence, not analogy
   with IEEE 754 or other sign-magnitude machines.
3. Reconstruct 35 for +0/-0 and output aliasing from the register transfer
   timing. Avoid a speculative fixed zero order or sign.

No changes to root README, ROM, existing mnemonic table, or peripherals.
