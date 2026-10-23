# ISA-06 D1 — logical instructions: documentary audit and CPU characterization

> **Current opcode 17 correction (D15/B1-H3):** Execution is 41-bit **XNOR**
> (`~(a ^ b) & MASK41`), not XOR. The 1962 pp. 172-173 diagnostic and
> 1964 p. 18 truth table agree; the 1962 p. 11 XOR table is contrary
> evidence retained in `docs/ISA_07_D15B1_H2_OPCODE17_SOURCE_ADJUDICATION.md`.
> Historical D1 38/38 results below characterize the *former* XOR implementation.
> The D1 regression values have been updated for the corrected semantics.


**Base:** `62a5c413ff70c97c7ca87bcd2a43f5087d5e640c` (`main`, ISA-05 D6).
**Scope:** add this note and `tests/isa/isa06_d1_logic_probe.cpp` only. No CPU, ROM,
existing tests, root README, or historical corpus changes. Values beginning with
`0` in C++ examples are **octal**; bit counts in prose are decimal.

## Historical primary sources (printed pages, not PDF page numbers)

1. **GY62** — V. M. Glushkov and E. L. Yushchenko, *Vychislitel'naya mashina
   "Kiev": matematicheskoe opisanie* (1962), **p. 12**: definitions of `13`,
   `14`, `15`, `17`, address modification, sequential control flow, treatment
   of all 41 bits including the sign. For the memory layout/zero location,
   see **pp. 7–9**, especially p. 8; for address modification see **p. 9**.
2. **DPS64** — L. N. Dashevsky, S. B. Pogrebinsky and K. A. Shkabara,
   *Vychislitel'naya mashina "Kiev": proektirovanie i ekspluatatsiya* (1964),
   **pp. 18–19**: truth tables for logical OR, AND, **XNOR**, and `13` shift
   addressing/direction/count; explicitly states the sign digit participates
   in logical operations like other digits. For the sequencing of one-cycle
   logic operations see **pp. 100–103**, particularly **Fig. 62** (p. 100)
   and **Table 4** (pp. 102–103). The transfer of the result after processing
   both operands supports ordinary in-place operation for the bitwise group;
   exact timing of arbitrary overlaps remains a possible hardware follow-up.

### Documented behavior

| Opcode (oct) | Historical term | Result written to address III |
|---|---|---|
| `13` | logical shift | shift the **entire 41-bit code** at address II by `mem[I] & 077` bit positions; use the **sign bit of `mem[I]`** for direction (positive: left; negative: right) |
| `14` | logical addition | bitwise OR of full 41-bit codes at I, II |
| `15` | logical multiplication | bitwise AND of full 41-bit codes at I, II |
| `17` | equivalence (1964 p. 18; 1962 test pp. 172-173) | bitwise XNOR of full 41-bit codes at I, II, sign included; result masked to 41 bits |

`13`: bits lost outside the 41-bit word are discarded; zeros enter from the
opposite side. Shifts of **41 or more** positions produce **positive zero**
(`00000000000000` as a full machine word, including the sign). The amount is
held in the **six low bits of the memory word at I**, not directly in the I
address field and not in all 40 magnitude bits. The constant's sign is used
for direction, not shifted together with the operand. The operand's sign **is**
shifted: e.g. shifting the code for `-0` right by one creates a positive code
with the highest magnitude bit set; shifting it left by one gives `+0`.
Shifting either sign of a zero amount preserves the 41-bit operand code.
These are consequences of GY62 p. 12, not floating-point or signed integer
arithmetic. There is no arithmetic right shift or automatic sign restoration.

All four operations advance the command counter to the next instruction and
allow **independent A-register modification of each of the three fields**
(GY62 pp. 9 and 12). The permanently zero memory word at address `0000`
is a discard destination (GY62 p. 8); only its postcondition is asserted.

### Current code reviewed (not a historical authority)

`src/main.cpp` on the stated base, `Kyiv_t::execute_opcode()`:

- `opcode_log_shift`: first reads `mem[effective I]`, masks `0b111111`,
  checks the sign of `mem[effective I]`, then shifts `mem[effective II]`
  left or right and writes `mem[effective III]`; left result is masked to
  41 bits. It agrees with **the textual descriptions** of GY62 p. 12 and
  DPS64 pp. 18–19 for valid 41-bit operands and 0..63 shift amounts.
  This is a static code review, not yet a runtime qualification.
- `opcode_log_or`, `opcode_log_and`, `opcode_log_xor` operate on the raw
  memory codes with native bitwise operations; no conversion through signed
  magnitude is performed. For valid 41-bit inputs, all bits participate.
- `shift_addr3_byA()` is invoked before dispatch and performs address addition
  modulo `04000` for each field that has its modification flag set.
- `Kyiv_memory_t::write_memory()` ignores writes to `0000`.

**Unresolved / not normalized by D1:** handling of memory codes with bits
above bit 40 set (the real machine has 41-bit words); physical decode for
address space `2000`–`2777`; writing to ROM; precise internal microstates
and overlapping-address timing for the shift instruction. No interpretation
of these cases is made normative.

## Test strategy and confidence

`tests/isa/isa06_d1_logic_probe.cpp` builds a fresh `Kyiv_t` for every test,
places one machine instruction at `0100`, executes one **real CPU** step and
compares the full output word plus sequential `C=0101`, continuation and no
stop. The fixture sets memory data explicitly; it does not depend on ROM
contents. The test provides the same no-op `disassembly()` stub as earlier
ISA probes; it does **not** test the assembler/disassembler.

- **STRICT** (38 cases): six-bit count from addressed memory, shifts 0/1/39/
  40/41/63 in both directions where relevant, the sign bit and signed-zero
  behavior, ignored higher bits in shift constants, the three bitwise
  operations' 41-bit truth tables, operand/destination overlap, address
  modification, address wrapping and destination `0000`. The overlap
  tests are functional postconditions; the `14/15/17` sequencing has further
  support in DPS64 pp. 100–103 (Fig. 62, Table 4).
- **DOC-MISMATCH**: emitted for any *failed* STRICT case. A mismatch is a
  reason to investigate, not permission to patch the CPU automatically.
- **POLICY** (0 cases in D1): there is no new emulator semantic choice to
  freeze as historical fact. Prior ISA policy remains unchanged.
- **OBS** (2 cases): attempt to write a logical result to ROM, and an
  A-modified source address entering the `2000`–`2777` range. Exceptions or
  values are printed **without** a pass/fail oracle. These do not affect the
  process exit code.

No historical test program is claimed to be incorporated. This package does
not yet test noncanonical >41-bit data as valid input or provide an electrical
model of the shift unit. It leaves the ISA-04 `07` cyclic-carry and ISA-05
`30`, A/Cy and equality questions untouched.

## Qualification procedure

From repository root (MSYS2 MinGW64), after applying the supplied patch:

```bash
g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa06_d1_logic_probe.cpp -o tempkyiv/isa06_d1_logic_probe.exe
./tempkyiv/isa06_d1_logic_probe.exe
```

The expected terminal summary, **if the documented cases agree**, is:

```
ISA-06 D1 STRICT=38/38 DOC-MISMATCH=0 POLICY=0 OBS=2
```

This expected string is **not** a claim that the actual emulator has passed.
Run `tests/isa/isa05_d6_historical_f_probe.cpp` and
`tests/isa/isa05_d5_width_probe.cpp` as regressions; only the user execution
log can qualify the real checkout. After the log, decide whether D2 should
address a confirmed mismatch or continue characterizing machine-specific
hardware edge cases. Do not modify the CPU on the strength of OBS alone.
