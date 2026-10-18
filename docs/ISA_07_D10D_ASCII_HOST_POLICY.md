# ISA-07 D10-D — standalone ASCII decimal presentation, HOST_POLICY

**Baseline:** `46cfb2f` (D10-C exact converter). **NO modifications** to `src/main.cpp`, `inc/kyiv.h`, `inc/kyiv_decimal_exact.h`, or historical/pinned D10-B and D10-C evidence. This new component is **not wired into IO20**. Nothing here models physical punched-card character positions, card zones, electrical readout or device timing.

## What history supports (`SOURCE_STRICT`) and what it does not

- GY62 (Glushkov–Yushchenko, 1962), printed pp. **6–7, 16–17, 58** (SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`) and DPS64 (Dashevskii–Pogrebinskii–Shkabara, 1964), printed pp. **15–16** (SHA-256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`) document ten BCD decimal **fractional digits**, a separate sign and a sign/magnitude 41-bit binary word with **40 fractional bits** after numeric input.
- Existing `inc/kyiv_decimal_exact.h` (`46cfb2f`) converts this BCD magnitude to a machine word **only when exact**. D10-D does not duplicate the numerical conversion.
- Neither source specifies ASCII sign characters, ASCII decimal points, tabs, file framing or how modern `punch_cards_in.txt` must be parsed. Every such rule below is explicitly **HOST_POLICY**, not `SOURCE_STRICT` or a physical device oracle.

## Deliberately narrow token grammar (`HOST_POLICY`)

The standalone `parse_token(std::string_view)` accepts **only ASCII**:

```
[+-]? ( [0-9]{10} | 0.[0-9]{10} )
```

The two *equivalent host spellings* are `6250000000` (compact BCD digits) and `0.6250000000` (explicit radix point). For both, **all ten digits represent the decimal fraction** `N/10^10`; the compact spelling does **not** denote a large integer. A leading ASCII plus/minus is optional, default positive. The sign is kept separate from ten packed BCD nibbles; `-0000000000` and `-0.0000000000` retain a negative sign (an **encoding/host policy**, not proven historical sign retention on input).

Only exactly ten digits are accepted. `0.625`, `.6250000000`, `1.0000000000`, `10`, `62500000000`, decimal commas, exponent notation, non-ASCII numerals, and any embedded whitespace are `INVALID_TOKEN`. No locale, `std::stol` prefix parsing, floating-point conversion, implicit padding or normalization. An **ASCII sign** cannot be confused with a historical physical sign code.

- `EXACT`: D10-C returns a valid 41-bit word; provide its packed BCD and separate sign.
- `NONEXACT`: syntactically valid 10-digit decimal fraction but D10-C rejects because the exact 40-fractional-bit word is unavailable; `word=0` is an **inert rejection sentinel**, never a number to write.
- `INVALID_TOKEN`: syntactically rejected; `word=0`, `packed_bcd=0`, `negative=false` as inert sentinels. No memory writes or rounding.

The rejected input behavior is a **safe host API policy**, not proof of historical halt, rounding/truncation, underflow or error signaling. Invalid raw BCD nibbles are handled by D10-C; they cannot arise from the accepted ASCII grammar.

## Record tokenizer (`HOST_POLICY` only)

`parse_record` accepts one **already-extracted** host text record. It splits by ASCII SP (`0x20`) and TAB (`0x09`) only; repeated, leading and trailing separators are allowed. Empty/whitespace-only record yields `EMPTY` and no values. A record with any invalid or nonexact token yields `INVALID_TOKEN` or `NONEXACT` and **an empty values vector**: **all-or-nothing**, no partial output. This design prevents silent half-record memory writes when the caller later chooses an integration policy. A literal CR/LF inside a provided record is not whitespace and is rejected. Delimiting input lines, CRLF normalization, perfo-number selection, `a3` card-zone offsets, incomplete records, peripheral errors and error propagation into the CPU remain **OPEN**.

## Independent tests, source provenance and unresolved boundaries

- `tests/isa/isa07_d10d_ascii_decimal_probe.cpp` is a **standalone** C++17 executable (NO `src/main.cpp`) for token/record output and **4096** exact cases: 1024 distinct 10-place fractions × both signs × both spellings. A genuine negative zero case is included.
- `tools/isa07_d10d_ascii_decimal_sandbox.py` checks ASCII grammar, signed zero, exact words and nonexact rejection against literal GY62 vectors and independent Python rational arithmetic; checks record-level atomicity, whitespace, malformed tokens and four in-process CR/LF rejections; enforces a bounded subprocess timeout; checks the 4096 in-process sweep. **D10-D H1 fixture correction:** non-ASCII digit U+FF10 is constructed as literal UTF-8 bytes (`EF BC 90`) **inside** the C++ probe via `--nonascii`; the runner must not pass this character in `argv`, because Windows narrow-argv best-fit conversion can silently transliterate it into ASCII `0`. This changes only the test transport and adds an audit gate; the standalone parser and CPU are unchanged.
- D10-C's original 2048 grid and D10-B's seven source words remain separately pinned, never rewritten. Baseline Git blobs for CPU and relevant historical sources are checked by the new auditor.
- **OPEN:** nonexact conversion, rounding, underflow-sign handling, out-of-range numbers, malformed historical punch codes, mixed line/zone handling, integration with IO20, and register-M control effects. No physical-device oracle and no CPU modification in D10-D.

**Do not use the old D10-B `HOST_OBS` tests as correctness oracles after future IO20 integration.** They intentionally pin a known-bad octal ASCII parser.
