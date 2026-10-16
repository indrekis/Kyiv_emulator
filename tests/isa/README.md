# ISA-01 characterization probe

This deliberately small suite checks the **existing implementation** and does **not** modify it. It compares key properties with the 1962 description of Kyiv; it is **not a replacement for the historical program corpus**.

Baseline: `indrekis/Kyiv_emulator` `main`, `0e2a06f544712c48b53323492fcfdc578de90473` (the revision inspected).

Copy `first_pass_probe.cpp` to `tests/isa/` in the checkout. From the repo root:

```bash
g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/first_pass_probe.cpp -o isa_first_pass_probe
./isa_first_pass_probe
./isa_first_pass_probe --strict    # only when fixing code; nonzero exit on mismatches
```

This standalone executable supplies a **no-op stub** for `disassembly()` to avoid linking the existing `src/asm_disasm.cpp` (which contains the project's CLI `main()`). Thus this is a CPU/memory probe and does **not** test the assembler/disassembler. If your tree has since refactored `main()` or disassembly, adapt the build instructions.

Some failures are **expected** in the original revision: opcode `00`, subtraction `−0`, negative intermediate result in `03`, overflow for `03`, modified address wrap and immutability of `0000`. Do not require a green CI run before correcting those defects. Cases labelled PASS are still only smoke checks; they do not establish correctness for all 41-bit operands.

All numeric instruction/address values in the tests are octal C++ literals (with leading `0`); emitted results are also octal. `kSign=1<<40` encodes `−0`.

The book's printed example `2667 + 1323 − 4000 = 213` on printed p. 9 is an arithmetic error: the correct octal result is `0212`. The probe intentionally expects `0212`.

The test for writes to address `0000` checks the **postcondition** (cell reads as 0); both ignoring the write and rejecting the write are accepted for now, because the precise electrical behaviour is not yet resolved.

Known limitations:
- The noop opcode `00` next-address behaviour is inferred from normal sequential execution; it should be validated again against relevant machine-level tests.
- A failure involving a thrown exception is reported, not silently treated as a result.
- The suite does not yet cover all of `07`, sign-of-zero propagation outside `02`, physical memory timing, I/O, or exact stop microstate.
