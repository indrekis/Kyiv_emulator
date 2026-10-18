# ISA-07 D10-G1 — Decimal-to-binary conversion: documentary reconstruction

**State:** research / documentation, no CPU modifications and no claim of a bit-exact historic hardware oracle.
**Pinned baseline:** `6ac9660b20218de2d28e89d6eca5336905f5a6e0` (D10-F3 committed; prior user postcommit gate PASS). The independently validated, provisional IO20 implementation remains unchanged.

## Primary sources and page convention

1. **DPS64:** Л. Н. Дашевский, С. Б. Погребинский, Е. А. Шкабара, *Электронная вычислительная машина «Киев» (Проектирование и эксплуатация)*, 1964. `Kiev_1964_scan.pdf`, SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`. All pages below are **printed pages**. The supplied image PDF contains two pages per landscape spread: printed pp.118–119 on zero-based PDF page 59, 120–121 on 60, 122–123 on 61, and 124–125 on 62.
2. **GY62:** В. М. Глушков, Е. Л. Ющенко, *Вычислительная машина «Киев»*, 1962. `Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf`, SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`.

The page-to-claim provenance is independently listed in `ISA_07_D10G1_EVIDENCE_LEDGER.tsv`. DPS64 pp.119–125 were **visually inspected** in the supplied scan; the pages have no extractable text layer. Mathematical formulas below are transcribed and interpreted from the image, without OCR-as-authority.

## What the books actually specify

**DPS64 p.119:** The input apparatus receives numbers in BCD and instructions in binary; automatic conversion is included in the machine's numeric input mechanism. This is context; the punched format and electronics are not reconstructed here.

**DPS64 p.120:** For a 10-digit decimal fraction with 40 BCD bits `a_{s,l}`, decimal digit index `s=1,...,10` and within-digit bit position `l=1,...,4` (weights `8,4,2,1`):

```
  digit_s = sum_{l=1}^4 a_{s,l} * 2^(4-l)
  x       = sum_{s=1}^10 sum_{l=1}^4 a_{s,l} * 2^(4-l) * 10^(-s)
  i       = 4*(s-1)+l
  s       = floor((i+3)/4)
```

**DPS64 p.121** defines binary equivalents and reindexes this sum for `n=40`:

```
  E_s = 10^(-s) / 2^(n-4*s)
  x   = sum_{i=1}^n a_i * 2^(n-i) * E_s
```

It then gives the left-shift recurrence (`x_0=0`):

```
  x_i = 2*x_(i-1) + a_i*E_s,
  s = floor((i+3)/4), i=1..40.
```

This exact **rational** recurrence is mathematically identical to `N/10^10`, where `N` is the ten-digit decimal integer. A second recurrence is shown for the abbreviated-multiplication scheme using right shifts and digit-equivalent values. The text describes loading the current `E_s`, conditionally transferring the multiplicand to the adder when the corresponding BCD bit is `1`, shifting the multiplicand and repeating for each group of four bits, then changing the constant. It explicitly relates the control sequence to multiplication micro-operations.

**DPS64 p.122:** Similarity to the multiplier microprogram is emphasized; maximum conversion time is stated as about 270 microseconds. The following section switches to normalization/shift. **DPS64 pp.124–125** show numeric input (`20`) in the multicycle control-signal table, but not a table of bit-accurate `E_s` constants, intermediate fractional-point positions, or an explicit last-bit rounding correction.

**GY62 pp.10–11, 17, 117–118** provide corroborating context but no IO20-specific last-bit rule. In particular, commands `10`/`11` distinguish unrounded from rounded *multiplication*. Rounding described for *software floating point* (mode II) must not be generalized to IO20. The manual decimal-to-binary conversion on p.17 is not a machine execution trace.

## Why mathematical reconstruction is not yet hardware-bit-exact

Two choices are absent from the examined pages: (a) the scaling and internal precision of the register holding the equivalent `E_s`, and (b) rounding/truncation at each intermediate add/shift or at the final transfer. A mathematical recurrence alone does **not** resolve either issue. In particular, the symbols `E_s` are rational quantities, not documentary evidence of actual 40-bit register codes.

For clarity, the companion independent Python reference allows a deliberately **counterfactual** experiment:

1. Encode each exact `E_s` as `floor(2^P * E_s)` or to the nearest integer (hypothetical `P` fractional bits).
2. Evaluate `X_i = 2*X_(i-1) + a_i*encoded(E_s)` using **unbounded** exact Python integers; thus only *constant quantization* is modeled, not hardware-sized accumulators or carry losses.
3. Produce a 40-bit magnitude by removing the `P-40` low bits. Classify overflow instead of silently wrapping it into a sign bit.

This is a controlled sensitivity analysis; neither `P=80`, nearest encoded constants, nor unbounded accumulators are asserted to have existed in Kyiv's electronics.

### Results and choices

- **Naive, unscaled `P=40` equivalent constants — rejected as a plausible direct realization.** `E_1` has only one nonzero 40-bit unit; `E_10` has 109. After 40 left shifts this produces **large** loss of numerical accuracy, even for simple 0.625. The actual device must therefore have had some different precision or scaling arrangement *if the p.121 left-shift recurrence was used directly*. This does not itself prove an 80-bit register.
- **Hypothetical `P=64/72`:** error from equivalent-constant truncation can be thousands/dozens of final 40-bit ULPs (see numerical table). These models are not verified hardware implementations and may be inaccurate without richer shifting conventions.
- **Hypothetical `P=80`:** quantized `E_s` with floor produce errors `−1..0` final ULPs in the 1,014 deterministic vectors tested; nearest encoded `E_s` gives `0..+1`. For example, `0.6250000000` becomes one ULP too small with floored `P=80` constants, but is exactly represented with nearest `P=80` constants. This **does not** establish the historical width or rounding policy. The properties reflect the chosen arithmetic experiment.
- **Even `P=88`:** with naive downward quantization, an exact input may still become one ULP smaller because any nonzero intermediate coefficient error can push a mathematically integral output below the integer. A finite collection of passing random vectors cannot certify hardware equivalence.

A useful upper bound follows from the recurrence: if each *floored* `E_s` has fractional error less than `2^-P`, amplification of the 40 shifts gives total error below `(2^40-1)*2^-P`. For `P=80` this is less than a single **40-bit output ULP**. The floor model must then differ from ideal final truncation by either 0 or −1 ULP. This **mathematical** bound makes `P≈80` a valuable comparison regime, not a measured internal register width.

### Preferred model and ranked alternatives

1. **Default for the emulator — ideal mathematical conversion, final truncation toward zero:** `floor(N*2^40/10^10)` plus separate sign. `INFERRED / PROVISIONAL`, exactly the D10-F2/F3 behavior. Keeps documented BCD interpretation and avoids inventing an unverified microarchitectural encoding. The source does not uniquely prove this rounding rule.
2. **First historical sensitivity candidate — left-shift recurrence with high-precision `E_s` storage and unknown carry/constant rounding:** `PLAUSIBLE / UNDERDETERMINED`. Directly follows DPS64 p.121 but needs physical register scale, coefficient codes, accumulator details. The 80-bit hypothesis remains a **test configuration**, not a sourced hardware property.
3. **Alternate implementation — p.121 abbreviated/right-shift recurrence:** `SOURCE-DESCRIBED / DEVICE-CHOICE-OPEN`. Described by the book as another feasible multiplier organization; no demonstrated link to a concrete revision of Kyiv's numeric-input circuit here.
4. **Literal 40-bit fixed-fraction codes for `E_s` with the same recurrence:** `UNLIKELY / REJECTED_AS_DIRECT_MODEL` because of catastrophic numerical errors, not because a source explicitly prohibits this register size.

## Decision and future gates

- **No change to `inc/`, `src/main.cpp`, IO20, CPU control, or the D10-F2/F3 numeric behavior.** The `INFERRED / PROVISIONAL` qualification remains mandatory.
- The Python reference demonstrates source algebra using exact rational arithmetic (`fractions.Fraction`) and compares finite-precision *models* using only integers. It is **not** a simulator for undocumented micro-ops.
- In follow-up **D10-G2**, trace `E_s` storage and the multiplier datapath in DPS64 schematics/other pages: exact register size/scale, add/shift direction, working precision, sources of constant codes, arithmetic overflow/rounding, and whether the abbreviated multiplication form is actually used in instruction 20. Only upgrade claims to `SOURCE_STRICT` when evidence warrants.
- Prefer a documented **specific numerical IO20 witness** (machine printout, historical test program plus known result, original coefficient table, or circuit diagram) before modifying low-bit behavior of the emulator.
- Existing CPU and regression gates remain evidence for **the chosen emulator policy**, not proof of historical conversion details.
