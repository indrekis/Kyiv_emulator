# ISA-07 D10-F2 — Decision record: provisional truncation for decimal input 20 (В1)

**Status:** PROVISIONAL / INFERRED; **NOT** SOURCE_STRICT for non-exact inputs.
**Scope:** documented hypothesis and a standalone integer BCD converter; NO CPU, ASCII parser, input planner, source-book or IO20 changes.
**Baseline:** Git commit `5c2ff45229ae536d50462dc22859b0337d4c82d5` (D10-E3 integrated, pushed and user postcommit PASS).
**Next gate:** D10-F3, deliberate opt-in integration into existing D10-D/E2/IO20 with new real CPU regressions; don't silently reinterpret old E3 nonexact-rejection expectations.

## Primary sources and citation convention

All page numbers below are **printed book pages**, not PDF indexes.

- **GY62:** В. М. Глушков, Е. Л. Ющенко, *Вычислительная машина «Киев»* (1962); `Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf` SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`.
- **DPS64:** Л. Н. Дашевский, С. Б. Погребинский, Е. А. Шкабара, *Электронная вычислительная машина «Киев» (Проектирование и эксплуатация)* (1964); `Kiev_1964_scan.pdf` SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`.

The PDF hashes were rechecked for the supplied files. DPS64 is image-only; printed pp. 120–122 were examined as images. **Absence** of a visible final rounding instruction in those pages is not proof that the electronics never rounded.

## Arguments for choosing truncation *as the default reconstruction*

1. **Direct conversion method (highest relevance, DPS64 pp. 120–122).** Printed p. 120 expresses a decimal value as a sum of powers-of-two-weighted decimal digit contributions. Printed p. 121 introduces binary equivalents `Э_s` for decimal positions and describes repeated addition and shifting (including the recurrence `x_i = 2*x_(i-1) + a_i*Э_s` for one implementation), a sequence of loading equivalents, conditionally adding, shifting and repeating. Printed p. 122 notes that conversion reuses multiplier micro-operations. The presented list contains no *explicit terminal round-up step*. **Inference:** discarding lower fractional bits is a simpler first implementation than inventing an unmentioned final increment. **Caveat:** intermediate equivalent constants `Э_s` have finite representation and the add/shift micro-operations may themselves discard bits. Therefore the hardware result could differ in low bits from *ideal mathematical truncation*.

2. **Rounding is explicit when intended elsewhere (GY62 pp. 10–11; DPS64 p. 17).** GY62 distinguishes opcode `10` (multiplication without rounding) from opcode `11` (multiplication with rounding); for `11` it describes adding one in the most significant discarded bit. That is evidence that rounding is not a blanket property of all arithmetic. **Inference, not a proof:** since opcode `20` is not so qualified in its descriptions (GY62 pp. 16, 58), do not transfer opcode `11`'s rounding step to it.

3. **Hand-conversion scheme (GY62 printed p. 17).** The described decimal-to-octal conversion takes integer parts after successive multiplication by 2 and then 8 and continues until zero remainder or the required precision. No increment of the final octal digit is described. **Inference:** this closely resembles truncation at a finite precision. **Caveat:** it is a manual notation procedure rather than a complete hardware microprogram or a declaration of opcode `20` rounding semantics.

4. **Contrasting, clearly scoped rounding rule (GY62 printed pp. 117–118).** The text under `Округление чисел` explicitly rounds according to the top discarded bit, but the context is *software simulation of floating-point arithmetic (режим II)* and forming a word from mantissa and exponent. It does **not** specify rounding for decimal-input opcode `20`; applying it there would be an unsupported generalization.

## Source-strict boundaries and competing hypotheses

**SOURCE_STRICT:** GY62 pp. 6–7, 16–17, 58 and DPS64 pp. 15–16 support ten decimal fractional digits, separate sign, conversion to a 40-bit binary fraction on numeric input opcode `20`, and inclusive RAM destination interval. They do **not** uniquely specify the low bits of a *nonexact* decimal input.

**INFERRED / PROVISIONAL:** default to mathematical truncation of the absolute fractional magnitude: never increment the 40-bit magnitude. Negative inputs are thus truncated *toward zero* (not mathematical floor on the signed number); the sign bit is preserved for `-0`.

**OPEN:** real device's bit-accurate constants `Э_s`, precision of intermediate computations, direction and count of micro-shifts, intermediate carries and final correction; possible historical revision differences; card-zone and BCD sign signaling. A real hardware witness, source constant table or gate-level evidence may override the provisional choice.

**Alternative A — nearest:** increment when the exact discarded fraction is >= 1/2. Not presently a source-strict claim about opcode `20`.
**Alternative B — arithmetic internal truncation:** repeated sums of *separately truncated* decimal equivalents may yield values differing by one or more ULPs from the mathematical truncation model. This is a distinct possibility: don't mislabel the ideal formula as an exact emulation of DPS64 p. 121 microcode.

## Pure integer mathematical reference (DERIVED_MATH)

For the ten decimal digits interpreted as `N` in `[0,10^10)`:

```
  |x| = N / 10^10
  magnitude_40 = floor( N*2^40 / 10^10 )
               = floor( N*2^30 / 5^10 )
  5^10 = 9_765_625
  sign-magnitude word = magnitude_40 | (negative ? (1ULL << 40) : 0)
```

No IEEE-754, floating point or third-party big-integer is necessary: `(10^10-1)*2^30 < 2^64`. The modulo remainder is the residue of the **mathematical** conversion, not a measured hardware register.

- `EXACT` iff `N % 9_765_625 == 0` (1,024 of 10,000,000,000 magnitudes).
- `TRUNCATED` iff valid input is not exactly representable.
- `INVALID_BCD` for any nibble >9 or any bits above the ten BCD nibbles.
- Both signed zero representations are supported by the word format, but physical input sign-of-zero fidelity remains OPEN.
- No exact halfway cases exist on the input grid (reduced denominator of fractional part divides the odd number `5^10`); the choice of tie-breaking rule is unobservable.

### Diagnostic vector table — *mathematical models, NOT hardware traces*

| Decimal token | Ideal truncate (octal, 14 digits) | Ideal nearest (octal, 14 digits) |
|---|---|---|
| `+0.1000000000` | `01463146314631` | `01463146314632` |
| `+0.3000000000` | `04631463146314` | `04631463146315` |
| `-0.1000000000` | `21463146314631` | `21463146314632` |
| `+0.0000000001` | `00000000000155` | `00000000000156` |
| `+0.6250000000` | `12000000000000` | `12000000000000` |
| `+0.9999999999` | `17777777777622` | `17777777777622` |

## Implementation staging and evidence

**This D10-F2 change adds only** `inc/kyiv_decimal_trunc.h`, a standalone C++ probe, an independent Python oracle and this decision record, plus a gate auditor. It deliberately does not modify `src/main.cpp` or the existing `kyiv_decimal_exact.h`, `kyiv_decimal_ascii.h`, and `kyiv_decimal_input_plan.h`; until D10-F3 `IO20` still rejects NONEXACT as before. No CPU tests in D10-F2.

The D10-F2 standalone tests use an independent Python arbitrary-precision integer oracle for all included inputs, reference-aligned exact words (`0.625`, `0.5`, `0.25`, signed zero), invalid BCD, leading/trailing decimal values, ten single-digit positions, pseudorandom fixed-seed inputs and sign parity. They certify **mathematical code correctness under this hypothesis**, not provenance of the hardware rounding rule.

**D10-F3 entry conditions:** confirmed user's MSYS2 C++ compile and test output + auditor PASS. Only then selectively adapt D10-D parser, D10-E2 whole-command planner and real `IO20` CPU integration; preserve atomicity, source sign/zero and `C,K` control, test exact oracle parity and nonexact provisional behavior, explicitly rewrite obsolete `NONEXACT` rejection cases, run ISA-06 regression + unaffected IO21–25 tests; don't change the public semantics of D10-C's `convert_bcd10()` exact-only API.
