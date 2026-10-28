# H17 — division: bounded disposition after independent and native probes (2026-10-28)

**Decision: OPEN — source/host discrepancy retained; do not change opcode `12`.**

This note supplements, rather than replaces, the original historical observations
in `ISA_07_D15B1_H16_DIVISION_ONE_THIRD.md`,
`ISA_07_D15B1_H17_NEGATIVE_DIVISION_OBSERVATION.md`, and the H17 decision ledger.
The latter remain records of their original qualifications; historical `PENDING`
fields must not be silently rewritten as if their original tests had changed.

## Source-grounded examples

- G-Y 1962, printed pp. 172–173: H16 divides `01000000000000`
  by `03000000000000`. Printed RAM `0004 = 05252525252525`.
  The unmodified CPU's 40-bit integer quotient matches this word.
- Same source pages: H17 divides `20002000000000` by
  `00016000000000`. Printed RAM `0032 = 22222222222200`;
  exact 40-bit integer quotient is `22222222222222`.
  The discrepancy is `00000000000022` (octal, magnitude), or 18 decimal.
- The printed H17 digits occur both in the illustrated arithmetic example
  and in the source program's comparison constant. This excludes a simple
  transcription error in the modern `.k41` image, but does **not** prove
  that the historical hardware produced that constant.
- D-P-S 1964, printed pp. 150–151, describes shift-based division:
  P1 accumulates successive quotient digits while P2 holds the shifted
  divisor; completion is tied to passage of the first generated digit
  through the register. The cited passage does **not** specify a fixed
  33-, 34-, or 35-bit quotient precision or a rule for clearing the last
  six bits of the negative quotient.

## Completed checks, not historical hardware oracles

From `KYIV_H17_PRECISION_V1` native MSYS2 run, on the production CPU after
H14 commit `679f6c4`:

- Independent serial integer divider: 40/40 quotient bits verified.
- Native CPU: 68/68 cases match full 40-bit integer division, spanning
  17 scaling variants and four sign variants. This proves **emulator-policy**
  consistency over those tests, not historical sign handling.
- H16 historical expected value matches; H17 does not.
- Truncating the H17 full quotient to **any of 33, 34, or 35** leading bits
  produces the same printed H17 word. Therefore the example does not
  discriminate among those precisions.
- A **global** precision reduction is refuted by the H16 source word,
  which requires all 40 fraction bits under a truncation model.
- H17 experiment made no production changes; the earlier H14 historical
  batch had 10/10 valid runs, 9 source matches, H17 as the only remaining
  numerical source mismatch.

## Interpretation and boundary

A special historical divide procedure, operand-dependent termination,
negative-quotient coding, and an approximate/erroneous printed check value
remain distinct **hypotheses**. The available two source examples and the
cited division description do not uniquely identify one mechanism.
A fix that simply clears low bits or special-cases H17 would be overfitting.

**Policy:** keep the source image, expected word, and CPU `opcode_div`
unchanged. Treat H17 as a bounded **OPEN source-vs-emulator discrepancy**,
not as a PASS, a demonstrated hardware defect, or a blocker for Qt GUI work.
Reopen only if new independent source evidence, an exact scheme-level
simulation with discriminating examples, or a hardware oracle emerges.

**Provenance:** local `H17_ANALYSIS=PASS`, `H17_NATIVE=PASS; CASES=68/68`,
`H17_PRIVATE=PASS`; no separate hardware witness, no CPU change.
