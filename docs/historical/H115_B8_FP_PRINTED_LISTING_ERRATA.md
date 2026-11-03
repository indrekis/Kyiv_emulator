# H115-B8: three candidate errata in the 1962 FP-simulation ROM listing

**Decision:** preserve 251 original `SOURCE_PRINTED` machine words unchanged; maintain an independently identifiable `SOURCE_DERIVED_CORRECTION_CANDIDATE` overlay. These are highly supported **printed-listing defects**, not demonstrated corrections found on historical machine media. This document does not claim a complete historical MP, hardware oracle, or corrected 256-word ROM.

## Witnesses and bibliographic evidence

1. V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina "Kiev"* (1962), printed p. **114**: the multiply/divide subroutine is described as splitting mantissas and orders, subtracting orders for division, and normalizing the result. On p. **114**, source commands `3434: 15 0020 3605 0021` and `3435: 15 0020 3606 0022` split the first operand correctly.
2. Same book, printed p. **115**: `3467: 15 0020 3607 0021`; `3470: 15 0020 3607 0022`; `3471: 15 0015 3605 0023`; `3472: 15 0015 3606 0024`; `3473: 02 0022 0024 0022`; `3474: 10 0022 3611 0022`. These are *confirmed printed bytes*, not OCR mistakes.
3. Same book, printed p. **115**: floating exponent is defined as `a = p + 64`. Printed p. **117** lists `3605 = 37777777777600` (mantissa mask), `3606 = 00000000000177` (order mask), `3607 = 00000000000041` (not a complete mask for either field), and `3611 = 00000000000100` (octal `0100`, decimal 64).
4. L. N. Dashevskii, S. B. Pogrebinskii, E. A. Shkabara, *Vychislitelnaya mashina "Kiev" (Proektirovanie i ekspluatatsiya)* (1964), printed **p. 17**: opcode `01` is addition; opcode `10` is multiplication without rounding. A fixed-point multiply by a small unscaled word does not add the exponent bias.
5. E. L. Yushchenko, *Nekotorye voprosy teorii algoritmicheskikh yazykov i avtomatizatsii programmirovaniya* (1964), bibliography item **27**: L. N. Ivanenko and I. V. Sergienko, *Modeliuvannia rezhyma plavaiuchoi zapiatoi na mashyni "Kiev"*, in *Obchysliuvalna matematyka i tekhnika* (1963). The **bibliographic listing is verified**, but the article's full text or any alternative ROM listing has **not been inspected**; this is an important pending source, not corroboration for any individual machine word.

## Proposed three-word overlay (all numbers octal)

| Address | 1962 SOURCE_PRINTED | Derived candidate | Independent rationale |
|---|---|---|---|
| `3467` | `15 0020 3607 0021` | `15 0020 3605 0021` | Extract numerator mantissa like `3434` and divisor `3471` |
| `3470` | `15 0020 3607 0022` | `15 0020 3606 0022` | Extract numerator exponent like `3435` and divisor `3472` |
| `3474` | `10 0022 3611 0022` | `01 0022 3611 0022` | After `3473`, compute difference of exponents plus octal `0100` bias |

H66 transcription is faithful to the printed code. **Do not alter it.** The overlay changes exactly three of the 251 printed words; all 69 unknown positions (including `3574`) stay absent. The helper `tools/historical/materialize_fp_errata_candidate.py` only produces a new private derived output under a fresh directory. It never mutates tracked inputs or CPU files.

## H115-B8 Windows native evidence (bounded HOST tests)

- Seven prior cases byte-identical to H115-B7 in each variant; 32 new exact-rational expected cases per variant.
- `SOURCE`: 13/39 exact; 26/39 mismatched (all 26 new division cases return zero).
- `BOTH_ADD_BIAS`: **39/39 exact** in the observed machine words, including all new positive-exponent, signed, mixed-mantissa, add/subtract/multiply cases.
- All 78 cases reached the bounded dispatcher boundary at `3305`; no unsafe/unknown boundaries and no after-instruction RAM intervention; unmodified production CPU.
- Source `251`-word ROM pinned SHA-256 `ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba`.
- Evidence ZIP: `H115_B8_FP_WIDE_NUMERIC_DIFFERENTIAL_EVIDENCE_V1.zip` (private, from user). The local archive is not imported to tracked source.

**Scope limits:** 39/39 is not 39/39 randomized stress tests; inputs were selected as exactly representable. No proof about rounding on inexact fractions, overflow/underflow, exponent boundaries, signed zeros, division by zero, all control paths, missing ROM `3574`, 256-vs-251 discrepancy or historical physical machine behavior.

## Resolution policy

- File an issue/documented erratum as `SOURCE_PRINTED_DEFECT_STRONGLY_SUPPORTED` for the **published listing**; `CORRECTED_OVERLAY_NATIVE_HOST_39_OF_39` for the **derived variant**.
- Do not classify as `HISTORICAL_MACHINE_ROM_VERIFIED`, `HARDWARE_ORACLE`, or an emulator opcode bug. No modifications to `src/`, `inc/`, `mem/ROM.txt`, or the canonical `fp_simulation_251_printed.k41` are supported by these tests.
- Follow-up H115-B9: stress inexact division/rounding, signed zero, zero divisors, exponent limits, overflow and cancellation; retain original-vs-derived differential and fail-closed bounds. Separately seek original 1963 article and later errata/media before calling the overlay historically authentic.
- The pending local `docs/historical/ROADMAP.md` modifications must be reconciled in a separate reviewed step; do not stage this pre-existing edit implicitly.
