# ISA-07 D10-C — exact ten-decimal-digit BCD → 41-bit word converter (standalone)

**Baseline:** `9fd7c4c` (D10-B committed source qualification). **CPU and `inc/kyiv.h`: READ-ONLY.** No change to IO20 or physical device emulation. The new header `inc/kyiv_decimal_exact.h` is not included by `src/main.cpp`; D10-C therefore does **not** fix numeric input in the running emulator. It is a separately testable digital arithmetic component.

## Documentary basis (`SOURCE_STRICT`)

- **GY62** — Glushkov–Yushchenko (1962), printed pp. **6–7, 16–17, 58**; SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`. Numeric input is decimal/BCD-coded with **ten fractional digits plus separate sign**; the 41-bit result is **one sign bit plus 40 binary fractional magnitude bits**. Printed p. 17 explicitly gives `+0.625` → `12000000000000` and `−0.625` → `32000000000000` (14-digit octal). IO20 performs numerical conversion; IO21 does not.
- **DPS64** — Dashevskii–Pogrebinskii–Shkabara (1964), printed pp. **15–16**, scan SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`. The ten decimal digits occupy ten four-bit BCD groups, and the input hardware performs BCD-to-binary conversion.
- **D10-B** — `docs/ISA_07_D10B_DECIMAL_INPUT_SOURCE_QUALIFICATION.md` and `tools/isa07_d10b_numeric_vectors.py`, source-pinned at `9fd7c4c`. Preserve their seven strict word vectors; do not reinterpret the current IO20 ASCII observations as correct numeric input.

## Exact arithmetic without floating point (`SOURCE_STRICT` word encoding)

Interpret the ten nibbles, most significant first, as decimal integer `N` (0…9,999,999,999) and rational magnitude `x = N/10^10`. For the sign bit `s ∈ {0,1}`, a **mathematically exact** machine word is

```
word = (s << 40) | (N * 2^40 / 10^10)
     = (s << 40) | ((N / 9765625) << 30),  provided N % 9765625 == 0.
```

The divisor `9,765,625 = 5^10`, and `10^10 = 2^10 × 5^10`. This equivalence avoids 64-bit multiplication overflow and permits exact integer calculation with `uint64_t`. There are 1024 exactly representable fractional magnitudes between 0 and 1 in the ten-decimal-digit grid, with **two sign encodings** each. Signed zero is preserved in the *encoded output word*; preservation of an input minus-zero sign in a historical reader remains `OPEN`.

`convert_bcd10(packed, negative)` consumes **exactly ten BCD nibbles**, with the sign supplied as an independent Boolean by the caller. It returns one of:

- `exact`: the complete 41-bit sign-magnitude code;
- `nonexact`: decimal value requires a conversion rule that is **not yet qualified** (this includes 0.1 and positive sub-LSB input);
- `invalid_bcd`: any nibble >9 or any bit beyond the 40-bit BCD payload.

On rejection the `word` field is always zero and **MUST NOT be written to memory**. This is an API policy, not a claim that historical hardware halted or rejected such inputs. Invalid BCD handling, underflow, and rounding on the physical machine are `OPEN`.

## Host I/O adapter remains separate

No textual sign syntax, decimal dot, line framing, or conversion of `punch_cards_in.txt` is specified here. BCD packing is a **digital payload model**, not an assertion about card punch-hole positions, transmission direction, sign coding or input speed. The test probe accepts hexadecimal BCD solely as an internal testing interface. IO20 still uses its existing erroneous octal ASCII parser; do not run the old D10-B ASCII `HOST_OBS` runner as a post-fix pass criterion after any future IO20 conversion patch.

## Gates

- `SOURCE_STRICT`: seven existing GY62/D10-B source word vectors tested against **literal expected octal words** and an independent Python `Fraction` oracle.
- `EXACT_MATH`: six additional exactly representable values, including minimum positive tenth-digit-grid exact step `1/1024` and maximum `1023/1024`.
- `REJECT_POLICY`: five nonexact decimal fractions plus four invalid BCD payloads are rejected, with no fabricated rounding or sign handling.
- `EXHAUSTIVE_EXACT`: 1024 magnitudes × both signs = **2048/2048** conversions, including positive and negative zero.
- `CPU_IMMUTABLE`: Git blob and working bytes of `src/main.cpp` and six source/evidence files match baseline `9fd7c4c`; `inc/kyiv.h` likewise unchanged.
- `NEGATIVE`: a deliberately incorrect converter must fail the test runner (the test harness's sensitivity, not a source oracle).

## Open for the next stage

Choose and document `HOST_POLICY` for presenting ten decimal digits and signs in ASCII files; qualify historical conversion for nonexact fractions and negative underflow zero. Only after those decisions should IO20 be integrated with the pure converter under independent, narrow CPU modification gates. **Do not fix IO20 by simply changing `std::stoi(..., 8)` to base ten.** No analog device timing is modeled.
