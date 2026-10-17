# ISA-07 D7 — documentary qualification of IO 20–25, NO CPU FIX

**Baseline:** `f30644f` (D6). **Primary source:** V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»*, 1962, **printed pp. 15–16** (PDF pp. 15–16), SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`. This volume explicitly describes the machine as of January 1, 1960 (preface). This stage does not assert hardware test evidence beyond the book.

## Documentary statements (`SOURCE_STRICT`, not emulator tests)

- Printed p. 15: six peripheral opcodes: 20 number input, 21 instruction input, 22 output, 23 drum write, 24 drum read, 25 drum preparation. All are group instructions and **destroy the address-modification register**.
- Printed p. 15: `25` sets drum/track using raw II address and start location using raw III address. It passes control to the **following instruction**, required to be 23 or 24. I is 0 for reading *onto* drum, 1 for writing *from* drum in the original wording; this odd direction phrasing should be investigated independently, NOT normalized silently.
- Printed p. 15: `23` transfers codes from memory cells **a1 through a2 inclusive** to drum, then branches to a3. `24` reads the prepared drum into RAM **a1 through a2 inclusive**, then branches to a3. The remaining track is used automatically if the selected track lacks space (no wrap after track 24). This track behavior is not part of D7.
- Printed p. 16: `20` inputs **numbers** into RAM **a1 through a2 inclusive**, converting decimal to binary; card input uses III address as a zone selector. `21` differs in *not* converting decimal to binary. The description of the shared destination interval applies to 21 as well.
- Printed p. 16: `22` outputs **a1 through a2 inclusive** and branches to a3. The physical output device and decimal/octal printing mode depend on panel switches, not solely the opcode. For decimal printing, special prior code conversion is required.
- GY62 pp. 15–16 do not clearly assign the normal continuation PC for `20/21`, unlike the explicit text for `23/24/25/22`. **Do not infer it**.

## Exact observed implementation disagreements (`DOC_MISMATCH`)

| Opcode | D7 one-step fixture | Current code (pre-fix) | Documented digital contract |
|---|---|---|---|
| 20 | `a1=0200`, `a2=0202`, `1 2 3` | two values, third untouched | three inclusive destinations |
| 20 | input text `10 20` with a one-word fixture | first RAM word `8` (decimal), parsed in base 8 | the input text `10` is decimal ten; exact 41-bit machine encoding/scale remains unqualified |
| 21 | `a1=0200`, `a2=0202`, three tape lines | two values, third untouched | three inclusive destinations |
| 22 | `a1=0200`, `a2=0202` | 131 emitted fields (`a1 + [0..a2]`) | exactly three codes |
| 23 | same addresses | 131 emitted fields | exactly three codes |
| 24 | `a1=0200`, `a2=0202`, `a3=0120` | two values, `C=0100` | three values, `C=0120` |
| 25 | CPU one step at `C=0100` | `C=0100` | next sequential command (`C=0101`) |

### Precision and limitations

The numeric sample for 20 tests **only the decimal textual adapter**: GY62 also discusses BCD representation; this test does not prove how a historical fractional number should be encoded into the 41-bit word. Do not treat host `std::stol` numeric values as a hardware representation oracle. The literal 131 output fields is a **current emulator regression observation** (decimal length of octal `0202` plus one), not a historical transmission count.

For 20/21/24 the test inspects destination memory and program counter only. It does not claim the correct `h`, selection of tape records, transport delays, or input errors. No analog timing is modeled. For 25, only normal sequential PC semantics are at issue; preparation registers are outside the D7 test.

**D7 deliberately makes NO changes** to `src/main.cpp`, `inc/kyiv.h`, memory files, ROM or prior baseline tools. Existing D3–D6 regression passes are not historical I/O oracles; D7 documents the differences before any repair.

## Recommended next phases (independent patches)

- D8: inclusive `[a1,a2]` destination interval for 20/21/24; separately fix 22/23 absolute inclusive endpoint; test equal endpoints and nonzero start with hard bounds; preserve pre-fix D7 as historical observation.
- D9: PC transfer for 24 to a3 and 25 to following command; distinguish from unresolved 20/21 PC and panel-start mechanisms; verify any common post-instruction logic.
- D10: decimal-vs-octal input and representation for opcode 20, including signs, fractions and numeric encoding — do not equate host decimal integer with historical numerical format without a qualified encoding policy.
- Later: empty/malformed records, 21 EOF handling, output mode switches, drum track rollover and modification register destruction after correlating digital control logic.
