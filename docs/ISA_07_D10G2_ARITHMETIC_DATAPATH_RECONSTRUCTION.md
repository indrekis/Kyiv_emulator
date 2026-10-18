# ISA-07 D10-G2 — Multiplier datapath and decimal-input conversion hypotheses

**Status:** documentary reconstruction + deliberately counterfactual numerical models. **No change to CPU, decimal input, or any existing file.**
**Pinned baseline:** `635de81301827128c900b390b374c3fc8bbd032c` (D10-G1 user committed, postcommit PASS and pushed).
**Decision for existing emulator:** retain D10-F2/F3 `floor(N*2^40/10^10)` as `INFERRED / PROVISIONAL`; the present study does *not* establish a hardware low-bit oracle.

## Sources, page mapping and limits

- **DPS64** — Л. Н. Дашевский, С. Б. Погребинский, Е. А. Шкабара, *Электронная вычислительная машина «Киев» (Проектирование и эксплуатация)* (1964), supplied `Kiev_1964_scan.pdf`, SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`. **Printed pages** throughout (the scanned PDF stores two printed pages per spread, so printed pp. 104–105 correspond to zero-based PDF index 52). Pages were read as images, not OCR-transcribed.
- **GY62** — В. М. Глушков, Е. Л. Ющенко, *Вычислительная машина «Киев»* (1962), SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`; multiplication commands `10`, `11` distinct (printed pp. 10–11). A multiplication-rounding rule is **not** thereby an IO20-rounding rule.
- D10-G1 reference `docs/ISA_07_D10G1_DECIMAL_MICROPROGRAM_RECONSTRUCTION.md` and its primary-source ledger remain the mathematical baseline. This stage adds a *datapath* interpretation, not a replacement for the G1 rational derivation.

## Findings grounded in DPS64

1. **Arithmetic unit layout, printed pp. 86–87 (fig. 61).** Arithmetic device `АУ` has registers `Р₁` and `Р₂` and a sum register/adder (`См`). Both registers are used for the operands in multiplication, division, normalization and shifting; `Р₁` also serves shift and digit counters. The architecture has a programmable multi-cycle control path; fig. 61 is a *simplified block diagram*, not a fully wired bit-by-bit diagram. `SOURCE_STRICT` for existence and basic roles, `OPEN` for exact wiring and width of every intermediate field.
2. **Arithmetic timing and controls, printed pp. 88–90 (table 2).** Register `Р₁` bit patterns and control signals steer multi-cycle algorithms. Decimal-number input uses the multi-cycle arithmetic unit, table 2 gives **264 µs** for arithmetic-unit time for numeric input (the later p.122 text gives an upper bound ~270 µs for conversion). These describe different measurement/reporting contexts and cannot settle low-bit rounding. `SOURCE_STRICT` for printed values, not for a cycle-exact conversion model.
3. **Machine-specific multiplier choice, printed p. 105.** The text states that Kyiv uses an **abbreviated multiplication scheme shifting the code of the multiplicand** (`схема сокращенного умножения со сдвигом кода множимого`). The running partial-product sum is kept in the adder; its repeated right shift is avoided. A multiplication example is expanded on pp.105–106. This is stronger *device-specific* evidence than merely noting both abstract alternatives on p.121. `SOURCE_STRICT` for the named multiplier architecture.
4. **Multiplication precision budget, printed pp.106–109.** The book explicitly analyzes loss of low bits in this *abbreviated multiplication* scheme as the multiplicand is shifted. Printed pp.108–109 derive a bound on additional bits; **printed p.109 chooses `m=5` extra bits in the adder for `q=2, n=40`**. The same page says the right-shift apparatus for the remaining dividend register of divider (`Р₂`) has additional bits; this does not document the number of bits allotted to stored decimal equivalents. `SOURCE_STRICT` for `m=5` in the discussed multiplication design; `OPEN` whether the same exact low-bit path, width and loss schedule apply to IO20.
5. **Decimal conversion and shared micro-operations, printed pp.120–122.** The 40 BCD bits describe 10 decimal digits; p.121 gives a left-shift `x_i=2x_(i-1)+a_i E_s` formulation *and* a second formulation for abbreviated multiplication, in which an equivalent code is loaded into the multiplicand register, added conditionally to the adder, and shifted. P.122 emphasizes micro-operation reuse. Combined with p.105, **the abbreviated/right-shift family is the preferred historical implementation hypothesis**; it is not a proven complete execution trace of the IO20 peripheral.
6. **Micro-control signals, printed pp.124–125 (fig.63 and table 5).** Numeric input `20` and binary command input `21` appear as separate operations. Common receive/control paths and arithmetic-unit control pulses appear, but this does not supply numeric constants `E_s`, their code representations, the last discarded bit, or an IO20 final carry correction. `SOURCE_STRICT` for opcode presence; `OPEN` for complete microstep and data-bit timing.

## A consequential notation ambiguity on p.121

The first decomposition on p.120 describes a decimal BCD digit using bit weights `8,4,2,1` (high-to-low). The later abbreviated-multiplier section prints `E_(s,1)=10^-s` and repeats halving `E_(s,l)=E_(s,l-1)/2`, but does not sufficiently identify for a *literal bit-exact transcription* how the within-digit bit iteration is ordered and pre-scaled in the actual register. A naive MSB-first start from `10^-s` would weight the first bit `1` rather than `8` and violate the explicit p.120 decomposition. **Do not silently treat that naive transcription as historically correct.** Our numerical models normalize to the mathematically explicit `8,4,2,1` weights and test the effect of separately truncated right shifts. The chosen normalization is `DERIVED_MATH`, not an assertion about wiring.

## Three independent sources of numerical discrepancy

- **Coefficient quantization:** how is `10^-s` / equivalent loaded? Floor versus nearest versus precomputed codes from an external table; scale and representation unknown. The book does *not* give a ROM of ten exact 40-/45-/80-bit equivalent codes.
- **Intermediate right shifts:** even with the same initial register bits, truncating the low bit *at each shift* differs from computing each `2^k * 10^-s` exact and then quantizing it. The DPS64 shortened multiplier explicitly exposes such truncation as a concern (pp.106–109).
- **Final extraction / correction:** whether a rounding unit, guard-bit carries, or last-step correction is applied to `20` is not documented in those passages. None should be inferred from rounded multiplication opcode `11`.

## Reproducible, intentionally counterfactual models

`tools/isa07_d10g2_hypotheses.py` contains all-integer, parameterized *sensitivity models*. For each 10-digit magnitude `N` it computes the exact rational BCD expansion and the mathematically ideal final truncation `floor(N*2^40/10^10)`. Comparison results show **signed delta in final 40-bit ULPs**, not actual machine traces.

For a `P`-fraction-bit **hypothetical** arithmetic field (test `P=40,45,48`):

- `digit_terms`: compute ten rounded/floored fixed-point digit contributions `digit_s * 10^-s`, then add them; **one quantization per digit**.
- `bit_terms`: compute and quantize every active BCD bit term `2^k * 10^-s` separately; **one quantization per active bit**.
- `shift_multiplicand`: initialize each digit's hypothetical multiplicand register with the fixed-point code for `8*10^-s`, scan its bits MSB-first and right-shift the register by one after each bit; **low bits may be discarded at each internal shift**. This implements a plausible normalized *class* of abbreviated-multiplier algorithms, not an exact transcription of a verified physical code sequence.

The specific choice `P=45` is **motivated by**, but **does not follow uniquely from**, the five additional adder bits documented for multiplication on p.109. An extra-5-bit adder is *not* a 45-bit converter coefficient register. `P=80` in D10-G1 likewise remained purely hypothetical.

### Important discriminating examples (exact value vs hypothetical deltas)

The regenerated file `ISA_07_D10G2_QUANTIZATION_COMPARISON.tsv` contains the full 14-case comparison. Example `+0.6250000000` (mathematically exact; octal `12000000000000`):

| Model | Final output delta |
|---|---:|
| Ideal rational conversion + final truncation | 0 ULP |
| `P=45`, floor ten digit contributions | -1 ULP |
| `P=45`, nearest ten digit contributions | 0 ULP |
| `P=45`, nearest initial multiplicand, right-shift each BCD bit | -1 ULP |

Thus even 45 nominal fractional bits plus *nearest coefficients* do not ensure the exact 40-bit result when lower coefficient bits are subsequently lost. Passing an ideal `0.625` test constrains an entire *conversion procedure*, not just width or rounding of stored coefficients.

## Ranked hypotheses and immediate engineering decision

1. **Best architectural candidate:** reuse Kyiv's p.105 **abbreviated multiplication, multiplicand right shifts**, accumulator holding partial sum (pp.105, 121–122). `INFERRED_HIGH` as IO20 circuit mapping; `SOURCE_STRICT` for named multiplier design and generic conversion microprogram description.
2. **Most credible precision consideration:** track **five guard bits of the adder** as documented for shortened multiplication (p.109) and test loss per shift. `SOURCE_STRICT` in multiplication context, `PROVISIONAL` when mapped to IO20 and to hypothetical coefficient width. No claim of a 45-bit ROM or 80-bit register.
3. **Default value of emulator IO20:** preserve **ideal rational conversion followed by truncation** (D10-F2/F3). `INFERRED_PROVISIONAL`. Existing CPU and program behavior remain protected until a documentary or physical witness determines exact low bits.
4. **Rejected literal shortcut:** 40-bit `E_s` with unscaled G1 left shift, or p.121 `E_(s,1)=10^-s` naïvely used as the 8-weight MSB value. Both violate simple numeric checks under those specific interpretations; neither rules out all 40-bit hardware organizations.

## Remaining OPEN items / next evidence gate (D10-G3)

Exact binary equivalents storage or fabrication, decimal-digit input bit sequencing, number of accumulator/multiplicand bits active *during input*, multiplier wiring and carry paths, code-injection or correction at last conversion step, timing of control signal `20`, and any original machine printout. Next step: investigate figures/tables or archival schematics for these. Until then **no CPU changes or claim of historical bit identity**.
