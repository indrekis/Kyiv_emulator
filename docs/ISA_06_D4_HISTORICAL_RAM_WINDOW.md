# ISA-06 D4 — bounded sequences from the historical fourth RAM test

**Base:** `3c9b8bc` (`main`, ISA-06 D3/H1). Scope: **two new files only**. No changes to CPU, ROM, existing tests, root README, or historical-test plan.

## Documentary basis, with printed page numbers

- **GY62**, Glushkov and Yushchenko (1962), **p. 170**, Appendix 2, *Tests of storage devices (ЗУ)*: fourth RAM test (`Четвертый тест ОЗУ`) uses instructions **0122–0136** to write a traveling one/zero, **0140–0155** to read/verify it. The appendix is a published diagnostic program, not a general mathematical example.
- **GY62, p. 171:** original full octal instruction words for this diagnostic at their real octal addresses. The D4 source contains **16 complete historical machine words**. It does not reconstruct these words from the current emulator's assembler.
- **GY62, p. 12:** logical shift `13` shifts all 41 bits; positive shift constant means left, negative means right, count from six least-significant bits in the first-address cell.
- **GY62, p. 13:** exact comparison `16` compares magnitude and sign; `+0` and `-0` are distinguishable.
- **DPS64**, Dashevsky, Pogrebinsky and Shkabara (1964), **pp. 18–19**, corroborates logical instructions and 41-bit behavior; the control-unit description **pp. 160–163** describes instruction-fetch and execution flow (Fig. 76 is the control-device functional scheme, not independent proof of particular ROM values).

## Executed windows (authentic instruction words; controlled operands)

| Test | Real instruction addresses (octal) | Characteristic | Expected end |
|---|---|---|---|
| setup | 0120, 0121, 0122, 0123 | Copy initial one to cells 0017, 0021, 0020; group-register initialization | PC 0124, A 0200, Cy 0000 |
| write regular | 0127, 0130, 0131 | Two unsuccessful exact comparisons; 41-bit shift | 0021=2, PC 0132 |
| write high bit | 0127 | Exact match to upper magnitude bit | 0021 unchanged, PC 0133 |
| write -0 | 0130, 0135 | Exact match to negative zero; reset to one | 0021=1, PC 0136 |
| write +0 | 0130, 0131 | +0 not equal to -0; left shift of zero | 0021=+0, PC 0132 |
| read regular | 0146, 0147, 0150 | Exact comparisons followed by shift | 0021=2, PC 0151 |
| read high bit | 0146 | Special branch for high-bit pattern | 0021 unchanged, PC 0152 |
| read -0 | 0147, 0154 | Special branch for negative-zero pattern | 0021=1, PC 0155 |
| tail | 0156, 0157 | Shift cell 0017, then exact comparison/branch | 0017=upper magnitude bit, PC 0161 |

All nine cases are `STRICT` **for documented instruction semantics and control flow given the explicit fixture**. The high-bit branches stop at 0133/0152: they intentionally do **not** assert what happens when the next arithmetic instruction adds `-0` and `+0`. Two separate `OBS` execute the authentic 0133 and 0152 words with explicit `ROM[3026] = -0` and record the sign-of-zero result without normative expected value. In the current source `opcode_add` derives the result sign from a signed host-integer sum, which cannot preserve the sign of an exact zero; this is a characterization opportunity, **not** a proved historical CPU defect. The test checks every executed machine word in `K`, every PC transition, the final operand, P/A/Cy, and absence of unexpected stop. It never infers historical truth from a repeated emulator result.

### ROM fixture provenance and limitation

The current human-transcribed `mem/ROM.txt` has `3012 = 00 0000 0000 0001`, `3026 = 20 0000 0000 0000` and `3042 = 10 0000 0000 0000`. D4 **sets these exact values explicitly with `write_rom`** before each test, so that the test does not depend on the working directory or on successful loading of the transcription. These are **controlled assumptions**, not independently proven historical ROM contents. In particular, branch behavior involving `3026`/`3042` cannot yet be asserted as the historical machine's complete RAM-test path without independent confirmation of the original constants.

The previous D3 OBS established that `Kyiv_t` currently tries to open `../mem/ROM.txt` relative to the process working directory. D4 **does not change this constructor** or `ROM.txt`; it does not mistake a failed file open for an all-zero historical ROM.

### Scope deliberately excluded

- The two `OBS` for `01` and `(-0)+(+0)` are **not** counted as `STRICT`; the documentary zero-sign rule for this arithmetic combination remains unresolved.
- This is **not a full execution or PASS of the fourth RAM test**. It does not execute the write/read iteration, arithmetic update (`0124–0126`, `0132`, `0134`, `0136`, `0140–0145`, `0151`, `0153`, `0155`), global initialization, or error exits.
- Exact `04/05` equality remains an existing `POLICY` and is not tested here. Any future end-to-end historical test must resolve or explicitly model such branches.
- Does not resolve ROM transcription, pseudo-RAM `2000–2777`, ROM destination writes, hardware timings, or control-panel specifics.

## Decision gate

If all nine `STRICT` cases pass: do not edit CPU automatically; examine the two `OBS` separately. Next stage may investigate **full loop topology and printed RAM-test invariants** (with source/fixture separation), or address the documented constructor path defect in a dedicated non-ISA reliability patch after agreement. If an assertion fails, inspect the first PC transition and independent documentary basis before changing behavior.
