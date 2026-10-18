# ISA-07 D8-A — inclusive destination intervals for input commands 20, 21, 24

**Baseline:** `6abccb5` (D7, read-only characterization). **Digital source:** GY62 — Glushkov & Yushchenko (1962), printed pp. 15–16, SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`; see `docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md`. This source supports destination addresses **a₁…a₂ inclusive** for commands 20/21/24. The document does not specify all host file adapter conventions.

## Exact CPU patch (six comparisons; no other CPU changes)

- `20`, two input-token branch guards: `num_counter == (a₂ - a₁)` → `num_counter > (a₂ - a₁)`.
- `21`, two input-record branch guards: `com_counter < (a₂ - a₁)` → `com_counter <= (a₂ - a₁)`.
- `24`, two drum-input-token guards: `num_counter == (a₂ - a₁)` → `num_counter > (a₂ - a₁)`.

The source says inclusive; the *host file fixture* is a chosen policy. For the qualified **nondecreasing intervals** a₁ ≤ a₂, input now fills a₂, including the single-cell interval a₁=a₂. The tape host text is parsed as **octal** (`22`, `33`, `44` in the fixture therefore become decimal `18`, `27`, `36` in RAM). Short input may still leave destination cells unmodified; do not invent a peripheral error convention.

## Evidence gates

- 12 isolated cases (`20/21/24` × range, single destination, nonzero start; plus `20/24` short file and `21` with h=1). The C++ probe executes ONE opcode step, and Python uses temporary trees so no actual peripheral files are touched.
- All tests preserve C=0100 as an observation, NOT a historical control-transfer oracle. `21` updates h by the number of accepted tape records under the existing host policy.
- **reversed** address interval a₂ < a₁ is OPEN: unsigned subtraction in the current emulator can wrap. Do not silently assert empty interval, reordering, wraparound, or historical machine behavior. D8-A does not test/use this interval and does not claim it safe.
- D8-A does NOT fix the output endpoints for 22/23 (D8-B), decimal conversion for 20, 21 EOF/parsing, malformed/blank records, C_reg progression, or modification register behavior. No analog/electrical timing is simulated.
- The prior D7 tests *must not* be run as current-CPU pass conditions once an old mismatch is fixed. D7's old blob stays pinned; D8-A audit pins D7 and checks the exact current CPU delta.

Classifications: `SOURCE_STRICT_INTERVAL` describes the book's digital inclusive boundary, `HOST_CODE_FIX` describes the C++ delta, `HOST_POLICY` describes text records and EOF, and `OPEN` marks unresolved source semantics. Not a historical peripheral hardware oracle.
