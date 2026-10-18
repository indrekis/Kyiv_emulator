# ISA-07 D10-B — decimal numeric input: documentary contract before code changes

**Baseline:** `a152049` (D10-A). **CPU: READ-ONLY**. This is a source/host-observation qualification, not a proposed implementation of the physical input devices. The old D7/D10-A source files and their Git blob identities remain pinned. This document resolves the **numerical representation model**, not every aspect of IO20 conversion.

## Direct historical sources

1. **GY62** — V. M. Glushkov, E. L. Yushchenko, *Vychislitel'naya mashina «Kiev»* (1962), local PDF SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`:
   - Printed **p. 6**: numeric input/output uses **10 decimal digits plus sign**, instruction input/output uses **14 octal digits**. Decimal-to-binary conversion takes place on numeric input; output requires a separate conversion program.
   - Printed **p. 7**, Fig. 1 and following text: 41-bit numeric word = 40 fractional magnitude bits, sign in bit 41 (0 positive, 1 negative), fixed radix point *before* the highest magnitude bit. Input decimal words use four bits per decimal digit and ten decimal digits; BCD is used for punched input and specially preconverted output memory, while ordinary stored numbers are binary.
   - Printed **p. 8**: memory cell `0000` stores zero, independently relevant to fixture construction.
   - Printed **pp. 16–17**: numeric input converts decimal to binary; printed p. 17 explains sign/magnitude octal transcription and gives **+0.625 = `12000000000000` and −0.625 = `32000000000000`** (spacing omitted), with 14 octal digits representing 41 bits. Describes representable binary range ±(1−2^-40), states that magnitudes below 2^-40 become machine zero, and distinguishes `-0` and `+0`.
   - Printed **p. 58**: operation `20` (В1) converts incoming decimal-coded values to binary, while operation `21` (В2) transfers command codes without this conversion. The sequential `C+1→C` and instruction-register reload are already fixed in D10-A.
2. **DPS64** — L. N. Dashevskii, S. B. Pogrebinskii, E. A. Shkabara, *Vychislitel'naya mashina «Kiev»* (1964), scan PDF SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`:
   - Printed **p. 15** (scan PDF page **8**, right page): decimal numeric input/output has **10 digits**; numeric word has 40 binary digits plus sign; ten decimal digits are stored in ten four-bit BCD groups; sign is separate.
   - Printed **p. 16** (scan PDF page **9**, left page): BCD→binary transformation is performed by the arithmetic hardware **during input**; binary→decimal output preparation is performed by a **separate program**.

Source classifications below cite *printed* pages. This source-backed description is a DIGITAL contract, not a model of the paper-tape/card electrical coding or transport.

## Source-strict word representations (41-bit digital result)

For exact rational values `x` in (-1,1), the 40-bit **magnitude** is `|x| × 2^40` whenever this is an integer; bit 41 is the sign. `SOURCE_STRICT_WORD` test vectors therefore include:

| Value | 10 decimal digits (BCD payload, sign separate) | BCD magnitude (hex) | binary word (octal, 14 digits) | Basis |
|---|---|---|---|---|
| `+0.625` | `6250000000` | `0x6250000000` | `12000000000000` | GY62 p.17 example, GY62 p.7 decimal digits |
| `-0.625` | `6250000000` | `0x6250000000` | `32000000000000` | GY62 p.17 example |
| `+0.5` | `5000000000` | `0x5000000000` | `10000000000000` | derived exactly from sign and fixed point |
| `-0.5` | `5000000000` | `0x5000000000` | `30000000000000` | derived exactly |
| `+0.25` | `2500000000` | `0x2500000000` | `04000000000000` | derived exactly |
| `+0` | `0000000000` | `0x0000000000` | `00000000000000` | sign-magnitude encoding |
| `-0` | `0000000000` | `0x0000000000` | `20000000000000` | distinct sign-magnitude zero code; **retention after numeric input OPEN** |

The `6250000000` *digit string* describes 0.625 in ten-place **fractional** BCD representation; it is NOT an integer input value 6,250,000,000. The BCD hex code is a mathematical packing of four-bit digits, not an assertion about card-column punch layout. No rounding vector for non-binary-exact fractions is qualified at this stage.

## Present emulator observations (not physical input oracles)

At `a152049`, `src/main.cpp` uses **base-8** text parsing in BOTH branches of IO20 (`std::stol(...,8)` and `std::stoi(...,8)`) and writes that host integer straight to a 41-bit word. An isolated ASCII mock file demonstrates:

- Text token `10` stored as raw **8**, not decimal 10 (`HOST_OBS` only: decimal 10 is not a valid unscaled fractional machine number).
- Decimal-fraction-looking token `0.625` stored as **0**: `std::stol` accepts an octal prefix and does not check full-token consumption. **ASCII punctuation is not qualified as a historical punched representation.**
- Token `6250000000` (ten decimal digits representing 0.625 when interpreted as ten-place BCD) is parsed as an **octal integer** and not converted to the 41-bit `0.625` word (`HOST_OBS` of adapter limitations; not a device oracle).
- ASCII `-0` loses the input sign in the current host parser. Historical distinct `-0` storage is documented, but whether physical numeric input preserves that sign remains **OPEN**.
- Command `21` continues to parse octal text without numeric conversion; this is a control, not a new assertion about tape-hole format.

D10-B tests pin **observed host behavior**, including its discrepancies, and deliberately **PASS** when the known behavior is reproduced. These are not tests asserting historical correctness of an ASCII adapter. The vector generator separately checks documentary `SOURCE_STRICT_WORD` encodings. Do not interpret `HOST_OBS PASS` as closing the numeric conversion gap.

## Unresolved before a CPU implementation

- Exact punched-card/tape ten-digit framing and sign coding versus a chosen text fixture grammar (`HOST_POLICY`, OPEN).
- Conversion of fractions not exactly representable in 40 bits: rounding/truncation/tie behavior (`OPEN`). The **numerical underflow threshold** |x| < 2^-40 → machine zero is in GY62 p. 17; however, the input conversion mechanism, sign of underflowed zero, and reaction to out-of-range data remain `OPEN`.
- Preservation of input `-0`, invalid BCD nibbles and malformed tokens (`OPEN`).
- Treatment of a 12th-bit address-modification marker for group input, reversed address intervals, register A destruction, and device selection (`OPEN` elsewhere).
- A conservative next phase should specify a **new host decimal-token grammar** (e.g. signed `0.dddddddddd`, with an explicit convention for implicit radix digits) and only then implement a pure, integer-arithmetic BCD→fixed-point converter with independently qualified vectors. Do not silently use floating point or conflate BCD payload bits with final binary memory bits.

**D10-B changes no CPU code and no historical evidence files.** Re-run ISA-06/D10-A after any later CPU patch, but not for this documentary-only stage.
