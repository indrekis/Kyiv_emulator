# ISA-07 D10-G3 — Decimal input 20: abstract control microprogram and BCD ordering

**Status:** source-grounded reconstruction of *logical* operations with explicitly hypothetical datapath details. **No change to the emulator CPU, converters, or previously committed files.**

**Pinned baseline:** `ed80fdb90ee42ba8ebcc8add336a3baade3d76ea` (D10-G2 committed, postcommit PASS, pushed).
**Engineering decision:** preserve the D10-F2/F3 ideal mathematical **truncation** for current IO20. No candidate trace here is an observed device trace or sufficient grounds to change the low bits.

## Source and page conventions

- **DPS64:** Л. Н. Дашевский, С. Б. Погребинский, Е. А. Шкабара, *Электронная вычислительная машина «Киев» (Проектирование и эксплуатация)* (1964); project PDF `Kiev_1964_scan.pdf`, SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`.
- **GY62:** В. М. Глушков, Е. Л. Ющенко, *Вычислительная машина «Киев»* (1962), project PDF SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`.
- Page numbers here are **printed pages**, not zero-based PDF page indices: DPS64 pp. 120–121 = PDF spread index 60; p. 122 = index 61; pp. 124–125 = index 62. Image-only source; quoted symbols checked visually. No OCR as an authority.
- See the committed D10-G1/G2 source ledgers and numerical sensitivity models. This stage does not supersede their caveats.

## What the book actually establishes (`SOURCE_STRICT`)

1. **BCD decomposition — DPS64 printed p.120.** A ten-digit decimal fraction is represented by *40* BCD bits. Within each digit the mathematical contributions have weights **8, 4, 2, 1**, each multiplied by `10^-s`, `s=1..10` (p.120 uses a 4-bit digit decomposition). The total is `N/10^10`.
2. **Abbreviated multiplier — DPS64 pp. 105, 120–122.** Kyiv uses shortened multiplication with shifts of the multiplicand. The alternate recurrence for decimal conversion, printed p.121, accumulates conditional equivalent codes and shifts a multiplicand register. The listed logical recipe is: (1) load an equivalent `Э_s`; (2) transfer/add it conditionally when the current input bit is `1`; (3) shift multiplicand code; (4) repeat the bit-work within the digit; (5) replace the equivalent for the next decimal digit; (6) continue to completion.
3. **Shared micro-operations — DPS64 p.122.** The conversion is described as reusing multiplier microprogram operations numbered 2 and 3. The text states a conversion maximum time of about **270 µs**, but does not give a cycle-accurate `IO20` bit trajectory.
4. **Arithmetic datapath — DPS64 pp. 86–90, 105–109.** Registers `Р₁`, `Р₂`, accumulator/adder `См`, shift mechanisms and conditional transfers exist. The explicit choice of **five additional adder bits** on p.109 was derived for abbreviated *multiplication*. It does **not** imply five additional bits in the stored decimal coefficients.
5. **Control scheme — DPS64 pp. 123–125, fig.63/table 5.** The control-pulse diagram describes common multi-cycle arithmetic steering. Table 5 has distinct rows for opcode **20 («Ввод чисел»)** and **21 («Ввод команд»)**; the row for 20 includes register-zeroing / control or reception terms such as `ИВА₁`, `НИ₁`, `НИ₂`, `НИ₄`, `ИСдв`, `ИКЛ`, `ИК` and conditions, but **not** a standalone 40-entry instruction-level step table. The printed table cannot be converted to a pulse-accurate trace solely from its row cells.

## Critical ambiguity — scaling in p.121 (`INFERRED`, not silently repaired)

DPS64 p.121, shortened-multiply paragraph, prints the coefficient sequence `Э_(s,1)=10^-s` and `Э_(s,l)=Э_(s,l-1)*2^-1` alongside a per-digit bit loop. Meanwhile p.120 unambiguously assigns BCD bit weights `8,4,2,1` to a decimal digit. For an **MSB-first** scan, the *literal unscaled* coefficient series is `1,1/2,1/4,1/8` times `10^-s`: the computed magnitude is exactly **one eighth** of the source-defined value. Example `0.6250000000` → **0.078125** rather than 0.625. This falsifies only that unscaled literal combination, not the printed source or a differently wired register.

**Most probable engineering normalization:** scan each BCD digit high-to-low (`8,4,2,1`) while starting with a code for `8*10^-s`, then right shift to `4*10^-s`, `2*10^-s`, `10^-s`; reload for each next digit. This matches the p.120 decomposition and the p.105 shortened-multiplier right-shift family. `INFERRED_HIGH` for the broad method, **PROVISIONAL** for preload ×8 location/representation and exact bit order in hardware.

**Alternative still OPEN:** start from `10^-s` as printed, accumulate smaller weights and multiply / left-shift by 8 elsewhere, or present BCD bits differently in the incoming register. Final perfect-precision arithmetic does not distinguish these equivalent rescalings; finite-precision errors can.

## Proposed *logical* microstep table — not a clock / gate trace

| Stage | Count for ten digits | Explicit basis | Current model assumption |
|---|---:|---|---|
| `LOAD Э_s` | 10 | DPS64 p.121 steps 1,5 | load **scaled** `8*10^-s` code for each digit (provisional) |
| `TEST BCD BIT` | 40 | pp.120–121, ten × four | MSB to LSB, bit weights `8,4,2,1` (derived from p.120) |
| `CONDITIONAL ACCUMULATE` | population count of input BCD bits | p.121 step 2 | bounded accumulator, 40+guard hypothesis |
| `RIGHT SHIFT MULTIPLICAND` | 30 useful, or 40 including final non-contributing shifts | p.121 steps 3–4 | bit discarded on each shift (counterfactual P-bit field) |
| `RELOAD / ADVANCE DIGIT` | 9 transitions plus first load | p.121 steps 5–6 | end-of-digit coefficient state discarded |
| `SIGN / STORE / PC` | unspecified here | opcode 20 described elsewhere (GY62) | do **not** project host policy or CPU register timing to microclock |

The wording "repeat four times operations 2 and 3" supports a four-bit *loop* but does not unambiguously answer whether the **fourth/rightmost shift** is physically executed or optimized away at each digit boundary. Both options yield exactly the same accumulated result when the next digit unconditionally reloads the register. In this hypothesis, shift-count totals are **40** versus **30**; without a timing/control witness, neither is promoted to hardware fact. A logical step is not a real clock pulse. `264 µs` table time (pp.88–90) and `~270 µs` maximum (p.122) cannot resolve this at present.

## Independent executable exploratory model

`tools/isa07_d10g3_microsteps.py` provides:

- Full 40-bit BCD schedule and exact rational (`fractions.Fraction`) running total;
- `microstep_model(digits,p,rounding,terminal_shift)`: LOAD ×10, BIT ×40 with conditional ADD and shift, hypothetical `P` fractional bits (`P=40,45,48,64`), choice of coefficient rounding and 30 vs 40 effective shift counts;
- `unscaled_literal_rational(digits)` to expose the missing ×8 in the **uncompensated** interpretation;
- exact ideal `floor(N*2^40/10^10)` and signed delta in output ULPs; **no floating point**, no historical card encoding, CPU, or real timing.

The independent test compares all generated values against a separate `Fraction` oracle and the already committed D10-G2 shifted-multiplicand sensitivity model, including random input patterns, zero, signedness-independent magnitudes, limits and deliberately malformed digits. The expected successful diagnostic is **1014/1014** for `--cases 1000`. These tests establish consistency of the *hypothesis*, not identity with historic hardware.

## Ranked outcome and decision

| Question | Best current answer | Qualification |
|---|---|---|
| Number and mathematical weights of input BCD bits | 40; 8,4,2,1 × decimal powers | `SOURCE_STRICT` / `DERIVED_MATH` |
| Primary architecture | shortened multiplier with shifted multiplicand | `SOURCE_STRICT` for multiplier; `INFERRED_HIGH` for IO20 mapping |
| MSB-first per-digit processing, initial coefficient 8× | best internally consistent candidate | `INFERRED / PROVISIONAL` |
| Total shift pulses and actual clock timing | unresolved; 30 vs 40 logical candidate shifts | `OPEN` |
| Coefficient storage, guard precision and final rounding | unresolved, no binary coefficient ROM printed | `OPEN` |
| Emulator's current nonexact IO20 output | retain ideal final truncation, D10-F2/F3 | `INFERRED / PROVISIONAL`, not changed here |

### Next discriminating evidence for D10-G4

Inspect high-resolution signal definitions and any original controller schematics or coefficient-code listings; seek a trace of `ИВА₁/НИ₁/НИ₂/НИ₄/ИКЛ/ИК`, a specific addressing/source for `Э_s`, and a record of register width/bit carry behavior during opcode 20. If nothing settles it, retain the preferred MSB-first, ×8-scaled abbreviated-multiply model as `PROVISIONAL`, **not** as an authoritative oracle. No emulator source change on documentation alone.
