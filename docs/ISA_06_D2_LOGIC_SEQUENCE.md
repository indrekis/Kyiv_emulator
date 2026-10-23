# ISA-06 D2 — logical instruction sequencing and self-modifying RAM

> **D15/B1-H3 correction:** opcode 17 now performs masked 41-bit **XNOR**.
> The historic D2 run characterized the then-current XOR implementation;
> its assertions for opcode 17 were updated in H3 without changing the
> instruction-fetch or self-modifying-code contract. See H2 source ledger.


**Base:** `e1143b4` (`main`, successful ISA-06 D1: 38/38 STRICT, 2 OBS).
**Changes:** add only this audit note and `tests/isa/isa06_d2_logic_sequence_probe.cpp`.
No CPU, `ROM.txt`, existing tests, or root README changes. Numeric C++ literals
with leading zeroes are octal. Shift counts in prose are decimal.

## Decision after ISA-06 D1

User-run D1: **38/38 STRICT PASS; 0 DOC-MISMATCH; 2 OBS**.
Both OBS results are unqualified historical cases: a ROM write throws
`Writing to ROM`; an effective address in `2000`–`2777` reads 0. Neither is
an acceptable basis for inventing a hardware rule or patching the CPU.
ISA-05 D5 (9/9 STRICT, 1/1 POLICY, 7 OBS) and D6 (6/6 historical steps,
1 failure-branch PASS, 1 OBS) also passed. D1 was committed and pushed as
`e1143b4` and no changes to CPU were necessary.

## Historical evidence and limits (printed page numbers)

- **GY62**: Glushkov–Yushchenko, *Vychislitel'naya mashina «Kiev»*
  (1962), **p. 10**: each cycle starts by moving a command from memory to the
  instruction register K; the counter then normally advances to the next
  command. **p. 12**: opcodes 13, 14, 15, 17 use three independently
  modifiable addresses, store the result through field III, and continue
  to the next command. **pp. 163–164**, control-console description:
  a machine instruction has four sequential phases (fetch command, fetch
  field I, fetch field II, result delivery), including an explicit description
  of the separate command-by-command and phase-by-phase stepping modes.
- **DPS64**: Dashevsky–Pogrebinsky–Shkabara (1964), **pp. 18–19**:
  source/result fields for the logical instructions and bitwise treatment of
  the sign bit; **pp. 160–163, especially Fig. 76 (p. 161)**:
  general command execution/fetch logic in the control unit. The printed
  figure numbers are cited as additional hardware context, **not** as a
  proof of a particular gate propagation delay or electrical hazard.

**Deduction from described instruction sequencing:** if the *current* RAM
instruction is overwritten through its III address, the already fetched
K register still contains the executing command. The modified RAM code
can be observed by a subsequent fetch. If field III is the *next* RAM
instruction, the next fetch observes the written word. All tests stay in
valid RAM and use 41-bit words; no cycle-exact or asynchronous analog
simulation is claimed.

## Scope of tests

The 17 STRICT cases exercise:

1. All-field aliasing and shared constant/source for `13`, plus identical
   source fields for OR/AND/XNOR (including the sign bit).
2. Fetching the current instruction as either logical input (and as a
   shift operand), and overwriting the executing RAM instruction.
3. Effective-address modification which makes an operand/destination
   equal to the current instruction address.
4. Construction of the **next** instruction word by OR or by a zero-count
   shift, followed by actual execution of that new instruction.
5. Preservation of the A, P and cycle registers and sequential C progression.

`DOC-MISMATCH` means an observed deviation from this documentary model,
not authorization to update the CPU. Tests use a single normal instruction
fetch for each step, explicitly verifying `K_reg` where it matters.
`POLICY=0`, `OBS=0` in this targeted package; the two unresolved D1
OBS remain documented, and are not repeated just to increase coverage.
No authentic historical test program is claimed to be transferred.

## What D2 does not establish

- Electrical/micro-timing of simultaneous memory reads and writes.
- How writes to real ROM behave.
- How actual hardware decoded the undocumented `2000`–`2777` addresses.
- Whether host-side attempts to inject 42–64-bit words into emulator memory
  should be rejected or truncated; real machine words are 41 bits.
- ISA-04 `07` carry interpretation, ISA-05 equality, `30`, and register
  width uncertainties.

If all D2 tests pass, prefer documentation/qualification over changing the
CPU. Review the actual user-run log before selecting D3.
