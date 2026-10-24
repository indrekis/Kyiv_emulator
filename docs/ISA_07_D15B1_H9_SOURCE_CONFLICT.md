# D15/B1-H9 — two negative-zero additions and source-prose conflict

Pinned baseline: `b896eeb975662ce684572ae235135e119a2b0493` (H8 committed and pushed).

## Strict source account

Glushkov–Yushchenko 1962, printed **p.172** supplies data and prose, and
printed **p.173** supplies the machine-code listing. Words in this package
are from the printed machine-code listing, not reconstructed from prose.
There is one visual reading; a second **human** witness is pending.

**Contradiction, not a candidate fix:** the p.172 range annotation
`0143–0145` describes a result written `(0)20`, whereas its p.173
ADD/JE commands use data address `0010`, whose complete word is
`00010004002001`. The p.172 row for `0146–0150` describes
`00 0100 0400 2001` (the `0010` word), yet the printed p.173
ADD/JE at that address explicitly use `0013`, whose word is
`00400200100040`. Earlier rows also group `0135–0142` across two
historical command triplets. This discrepancy is left **unresolved**;
there is no silent reassignment of dates, addresses, or words.

These conflicting p.172 explanations **must not** be recorded as passed
by the native runner. The runner checks only the literal instruction
semantics against an independent sign-magnitude arithmetic calculation.

## Exact words and provenance

| Address (oct) | Word (14 octal digits) | Printed page | Meaning |
|---|---|---|---|
| `0010` | `00010004002001` | 172 | positive_operand_large_first |
| `0013` | `00400200100040` | 172 | positive_operand_large_second |
| `0143` | `01302600100347` | 173 | add_negative_zero_plus_0010 |
| `0144` | `16034700100146` | 173 | JE_compare_0010_skip_STOP |
| `0145` | `33000000000000` | 173 | failure_STOP |
| `0146` | `01302600130347` | 173 | add_negative_zero_plus_0013 |
| `0147` | `16034700130151` | 173 | JE_compare_0013_skip_STOP |
| `0150` | `33000000000000` | 173 | failure_STOP |

## CPU-independent prediction for the literal machine code

The pinned ROM cell `3026 = 20000000000000` is 41-bit **negative zero**
(sign bit set, all magnitude bits clear). The decoder evaluates `−0 + x`
as `+x` for these two **nonzero positive** operands:

| First instruction | Input at A2 | Expected destination `0347` | After 1 step | After 2 steps |
|---|---|---|---|---|
| `0143`: `01 3026 0010 0347` | `0010` | `00010004002001` | `C=0144` | `C=0146` |
| `0146`: `01 3026 0013 0347` | `0013` | `00400200100040` | `C=0147` | `C=0151` |

Opcodes `16` at `0144` and `0147` compare destination `0347`
with the very same source data cell. The original STOP at `0145` and
`0150` is checked with a **private**, retargeted A2 in ADD only; compare
and STOP remain byte-for-byte the printed commands. No private mutant
is a canonical example.

## Gate and limitations

Native qualification: 2 groups × 2 working directories ×
(1-step, 2-step, synthetic 3-step STOP) = **12 scenarios**.
All exact result words, C values, ROM3026, and input data are checked;
never run `0151` in this bounded test. SHA of the source image must remain
constant. CPU, ROM, and all pre-H9 canonical images are immutable.

`HISTORICAL_MACHINE_CODE_EXPECTATION=1` can be claimed only following real
native tests; `PRINTED_PROSE_DISCREPANCY=1` remains true even if they pass.
`HARDWARE_ORACLE=0`. Neither a hardware proof nor resolution of the
historical source conflict is claimed.
