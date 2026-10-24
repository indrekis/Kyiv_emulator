# D15/B1-H7 — historical addition checks VI–VII, GY1962

Pinned baseline: `fa5b491a5a15fe97b9ec5f9bba5066b12f77a76d` (H6 committed/pushed).

## Scope and source fidelity

- Original: Glushkov & Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962),
  printed **p. 172** for six data/expected words, **p. 173** for six machine instructions.
- Canonical HOST-only image: `examples/historical/gy1962/au1_addition_0127_0134.k41` (12 machine words: 6 data + 6 instructions).
- Machine words in the source are octal; every data value below is **14 octal digits**,
  representing the complete **41-bit sign-magnitude** code (sign at bit 40).
- The file begins at instruction `0127` and intentionally omits instruction `0135`.
  It is not an image of historical physical media.
- The print scan was visually read once for these 12 words (`VISUAL_FIRST_PASS`).
  A separate human transcription is not available (`HUMAN_INDEPENDENT_WITNESS=PENDING`).

## Exact first-pass source records

| Address (oct) | Source code (octal word) | Printed page |
|---|---|---|
| `0010` | `00010004002001` | 172 |
| `0011` | `30004002001000` | 172 |
| `0012` | `20200100040020` | 172 |
| `0013` | `00400200100040` | 172 |
| `0014` | `00200100040020` | 172 |
| `0017` | `27773775776777` | 172 |
| `0127` | `01001000110347` | 173 |
| `0130` | `16034700170132` | 173 |
| `0131` | `33000000000000` | 173 |
| `0132` | `01001200130347` | 173 |
| `0133` | `16034700140135` | 173 |
| `0134` | `33000000000000` | 173 |

## Independent arithmetic oracle (not CPU-derived)

The historical note on printed p. 172 predicts:

| Command | Operand I | Operand II | Expected 41-bit result | Sign |
|---|---|---|---|---|
| `0127` `01 0010 0011 0347` | `00010004002001` | `30004002001000` | `27773775776777` (from `0017`) | negative |
| `0132` `01 0012 0013 0347` | `20200100040020` | `00400200100040` | `00200100040020` (from `0014`) | positive |

For each 14-digit octal word, decode the top (41st) bit as sign,
subtract/multiply/add the remaining forty magnitude bits as signed integers,
and re-encode the result as 41-bit sign-magnitude. Both independent equations
match the original references exactly. Neither operation overflows the 40-bit
magnitude field. This oracle is independent of the emulator's arithmetic.

## Control-flow qualification

- `0127` ADD: at 1 step, `0347=27773775776777`, `C=0130`.
- `0130` JE compares `0347` with `0017`: at 2 steps, successful `C=0132`.
- `0131` is the original fallback STOP; a private altered `0017` forces `CPU_STOP` in 3 steps, ending `C=0132`.
- `0132` ADD: at 1 step, `0347=00200100040020`, `C=0133`.
- `0133` JE compares `0347` with `0014`: at 2 steps, successful `C=0135`.
- `0134` is the original fallback STOP; a private altered `0014` forces `CPU_STOP` in 3 steps, ending `C=0135`.
- Four positive and two negative profiles across two CWDs = **12 native cases**.
- No execution at `0135` is admitted; avoid unknown follow-on state.

The historical source expected-value record is never modified. Any synthetic
mutation is created in a temporary directory and used solely for STOP coverage.
The source SHA-256 and the default ROM pin must remain constant.

## Qualification boundaries

This is a source transcription + documentary oracle, not a physical-machine
measurement. Native qualification is pending until the real MSYS2 run; auditor
PASS alone is not a native PASS. CPU, ROM, preceding examples, and previous
H1–H6 ledgers must not be changed. `HARDWARE_ORACLE=0`.
