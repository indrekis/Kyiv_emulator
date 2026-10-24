# D15/B1-H14 — rounded multiplication, source-vs-host observation

Pinned parent: `00fbea3187590d4d206a7cf56c76ec3194974099` (H13 published). **No CPU, ROM or earlier
historical image changes are admitted.** GY1962 means Glushkov–Yushchenko
(1962); page numbers below are *printed*, not PDF viewer page indices.

## First visual source reading (independent human witness PENDING)

Printed p.172 data table supplies RAM `0015`, `0021`–`0024` and the
arithmetic examples. Printed p.173 gives machine code at `0171`–`0201`.
No machine word has been inferred from prose; data are transcribed from
p.172, commands literally from p.173. ROM `3035` is the existing pinned
software image, not a newly invented source word.

| Octal address | Exact word (14 octal digits) | Printed page | Role |
|---|---|---|---|
| `0015` | `00000000000001` | 172 | expected_rounded_half_tie_positive_one |
| `0021` | `20000000000001` | 172 | negative_small_multiplicand |
| `0022` | `30000000000000` | 172 | negative_half_multiplicand_and_expected |
| `0023` | `30000000000001` | 172 | negative_half_plus_LSB |
| `0024` | `17777777777775` | 172 | historical_third_expected_positive_near_one |
| `0171` | `11002100220347` | 173 | rounded_mul_op11_first |
| `0172` | `16034700150174` | 173 | compare_0015_jump_0174 |
| `0173` | `33000000000000` | 173 | original_failure_STOP_first |
| `0174` | `11002330350347` | 173 | rounded_mul_op11_second |
| `0175` | `16034700220177` | 173 | compare_0022_jump_0177 |
| `0176` | `33000000000000` | 173 | original_failure_STOP_second |
| `0177` | `11303530350347` | 173 | rounded_mul_op11_third |
| `0200` | `16034700240202` | 173 | compare_0024_jump_0202 |
| `0201` | `33000000000000` | 173 | original_failure_STOP_third |

ROM `3035=17777777777777` is separately pinned by `mem/ROM.txt` Git
blob and is checked at execution by the CLI `--watch 3035`.

## Independent fixed-point oracle and expected control flow

The 41-bit fixed-point word is sign-magnitude: one sign bit and 40
fraction bits. For the **current CPU implementation of opcode 11**,
positive result magnitude is computed exactly as

```
rounded_magnitude = (abs(a)*abs(b) + 2^39) >> 40
result_sign = sign(a) XOR sign(b)
```

The calculation above is an explicit **CPU-policy prediction**. It is
not assumed to prove the historical rounding convention. The printed
p.172 outputs are independently represented as a *separate* comparison
column; the two are not silently reconciled.

| Start | Input operands | p.172 expected | CPU-policy predicted | After 1 | After 2 |
|---|---|---|---|---|---|
| `0171` | `0021×0022` (−1 LSB × −1/2) | `00000000000001` | `00000000000001` | `C=0172` | `C=0174` |
| `0174` | `0023×3035` (negative × positive near one) | `30000000000000` | `30000000000000` | `C=0175` | `C=0177` |
| `0177` | `3035×3035` (positive near one squared) | `17777777777775` | `17777777777776` | `C=0200` | `C=0201` if host policy, `C=0202` if historical code |

For the third case, the historical value is **one lower** than the
rounded magnitude under the current CPU policy. A native observation
of `17777777777776` predicts execution of the original, unmodified STOP at
`0201`, with `CPU_STOP STEPS=3 C=0202`. If the emulator instead emits
historical `17777777777775`, only 1-step and 2-step runs are permitted;
**do not execute `0202`** in either profile.

The original STOPs `0173` and `0176` are qualified with private temporary
images that change only the second compare operand of the `JE`, not the
multiply or STOP machine words, and cannot be committed as historical.
For a current-CPU outcome there are **18 cases** (3 groups × 2 workdirs ×
(1-step, 2-step, third-step STOP)); if the third group matches historical,
there are 16 canonical/private cases and no third-step historical STOP.
Each result and register `C` is checked independently of CLI exit code
and is compared against watched source cells and ROM as appropriate.

## Open provenance and ISA issues

- **H14 (new, unresolved):** p.172 third multiplication has `17777777777775`,
  while CPU policy computes `17777777777776`. Do not change opcode 11 or
  the historical expected data based on one software observation.
- H9: source-prose/source-code mismatch — OPEN_UNCHANGED.
- H10: cyclic addition carry — OPEN_UNCHANGED.
- H11: opcode 06 negative-zero — OPEN_UNCHANGED.
- H13: prose label `СлК` versus literal opcode 13 — OPEN_UNCHANGED.

`HARDWARE_ORACLE=0`; `HUMAN_INDEPENDENT_WITNESS=PENDING`.
A static audit marking `NATIVE_GATE=PENDING` describes the committed
source artifact, not the eventual native execution outcome, which must
be recorded in separate runtime logs or a later commit message.
