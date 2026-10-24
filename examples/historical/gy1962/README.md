# Historical Kyiv machine-code examples — Glushkov & Yushchenko (1962)

Canonical historical machine images are stored **here**, under `examples/historical/gy1962/`.
The test harness consumes these same `.k41` files, with **no second copy** in `tests/`.
These are verbatim source transcriptions, *not automatically passing reference programs*.

## AU test no. 1, section I (logical operations)

- `au1_logic.k41` — 39 raw 41-bit octal records: addresses `0002`, `0003` and 37 instructions `0043..0107`.
- `au1_logic_provenance.tsv` — original first-pass source record for each word.
- A fresh visual cross-check against printed pp. 172–173 matched all 39/39 words; see `docs/ISA_07_D15B1_H4_SECOND_PASS.md`.
- Printed pp. 172–173, *Vychislitelnaya mashina «Kiev»* (1962).
- The `KYIV41-OCT1` file syntax is a modern HOST container, not historical media encoding.

Build the main emulator and run from the repository root (Windows/MSYS2 example):

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/kyivemu.exe
tempkyiv/kyivemu.exe image examples/historical/gy1962/au1_logic.k41 0043 22 --watch 0347
```

**Original H1 observation on the XOR-era CPU (preserved evidence):**
`CPU_STOP STEPS=19 C=0076`, after running the historical STOP at address `0075`.
This documents a discrepancy, not a successful historical diagnostic.

**Current D15/B1-H3 correction:** opcode `17` now executes 41-bit **XNOR**.
The unchanged image is expected to reach `LIMIT STEPS=22 C=0107` with a
22-instruction budget when the updated CPU passes native qualification.
Do **not** execute `0107` as part of this bounded qualification: that command
uses the operator-settable NK cell `3000`. The original 1962 p. 11 XOR
truth table remains contrary primary evidence; DPS1964 printed p. 18 and the
1962 AU test pp. 172-173 support XNOR. This software behavior is not a
physical-hardware oracle. The 39-word second visual read matched the source image
(2026-10-24); it was performed by the same assistant, so independent
verification by a second researcher remains outstanding.

For independent reproduction of the bounded observations and two work directories:

```sh
python tools/isa07_d15b1_h2_opcode17_probe.py --cli-exe tempkyiv/kyivemu.exe --expect xnor --timeout 20
```

Other historical examples will use their own source images and per-word provenance here. See
`docs/ISA_07_D15B1_H1_GY1962_AU1_LOGIC.md` for unresolved evidence and gate definitions.

## AU test no. 1, addition: first two checks (D15/B1-H5)

- `au1_addition_0110_0115.k41` — self-contained **9-word** modern HOST image:
  three source data words `0002..0004` (printed p. 172), followed by the
  two original addition/compare/STOP triplets `0110..0115` (printed p. 173).
- `au1_addition_0110_0115_provenance.tsv` — one **visual first-pass** source
  record per word. Another reader's independent verification remains pending.
- Each group is executed from its own entry for **two instructions only**:
  `0110` should reach `C=0113` with expected `0347=12525252525252`, while
  `0113` should reach `C=0116` with expected `0347=05252525252525`.
  These are **historical predictions, not observed passes** until the H5
  native runner has executed successfully.
- The next source instruction `0116` is **not** included. This bounded test
  must not advance into it. The original failure STOPs remain verbatim.
- `python -B tools/isa07_d15b1_h5_native.py --cli-exe tempkyiv/kyivemu.exe --timeout 20`
  runs both entry points from two working directories and preserves observations.

See `docs/ISA_07_D15B1_H5_FIRST_TWO_ADDITIONS.md` for scope and source uncertainties.

## AU test I, addition checks III–V (H6)

- `au1_addition_0116_0126.k41` contains 15 historically sourced words: six
  constants at `0002..0007` and nine instructions (`0116..0126`, octal).
- The three independent additions are described on GY1962 printed p. 172,
  with machine codes printed p. 173. Provenance is adjacent to the `.k41`.
- The check at `0116` doubles a positive word; `0121` yields a negative result;
  `0124` yields a positive result. All 41 bits and exact octal expected codes
  are checked by `tools/isa07_d15b1_h6_native.py`.
- Each group includes its historical STOP fallback, but a normal run is bounded
  to the first two instructions; a **synthetic, private changed-expectation copy**
  independently checks that the historical STOP fallback is reached. This
  artificial mismatch file is never stored among canonical examples.
- The result is a software qualification only; independent human transcription
  and physical hardware oracle remain PENDING. CPU, ROM, and H1–H5 examples
  are unaffected.

Usage (MSYS2 MINGW64):

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h6_kyivemu.exe
python -B tools/isa07_d15b1_h6_native.py --cli-exe tempkyiv/d15b1h6_kyivemu.exe --timeout 20
```

## AU test I, addition checks VI–VII (H7)

- `au1_addition_0127_0134.k41` contains twelve GY1962 source words:
  six operands/expected constants (`0010`, `0011`, `0012`, `0013`, `0014`, `0017`)
  and six commands at octal `0127`, `0130`, `0131`, `0132`, `0133`, `0134`.
- GY1962 printed p. 172 gives the data and two arithmetic predictions;
  p. 173 prints the actual instruction words. The accompanying provenance
  distinguishes an initial visual transcription from independent human verification.
- First check: `0010 + 0011 -> 0017 = 27773775776777` (negative sign bit).
  Second check: `0012 + 0013 -> 0014 = 00200100040020` (positive sign bit).
- The source's `STOP` fallbacks at `0131` and `0134` are preserved. Real
  qualification executes each successful fragment within a two-instruction
  bound; a temporary HOST-only image with one altered expected constant
  exercises each STOP path. No private image is committed.
- The next instruction `0135` is not in this image. The historical `.k41`
  file is intentionally standalone; `0347` comes from the emulator's ROM.
- Native tests use the same `image` runner in two working directories.
  No CPU, ROM, or prior example modifications are part of this H7 package.
  This is a reproducible emulator test, **not a hardware oracle**.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h7_kyivemu.exe
python -B tools/isa07_d15b1_h7_native.py --cli-exe tempkyiv/d15b1h7_kyivemu.exe --timeout 20
```

## AU test I, negative-zero additions VIII–IX (H8)

- `au1_addition_0135_0142.k41` contains eight verbatim source records:
  two positive data words at `0015`, `0016` (printed GY1962 p. 172) and
  six commands at `0135..0142` (printed p. 173).
- Both additions use ROM address `3026` as their first operand. In the **pinned
  current ROM** `3026=20 0000 0000 0000` (41-bit sign-magnitude negative zero).
  This is a pinned software reconstruction, **not** independent hardware evidence.
- The historically predicted results are the exact positive codes at `0015`
  and `0016`; both are tested, including the sign bit and successful JE branches.
- The original fallback STOPs `0137` and `0142` are tested on temporary copies
  with a retargeted ADD operand address (JE and STOP stay verbatim). The canonical historical image is immutable.
- Native commands, evidence and limitations: `docs/ISA_07_D15B1_H8_NEGATIVE_ZERO_ADDITIONS.md`.
- This software qualification leaves both an independent human source witness
  and a physical-machine oracle **PENDING**. No CPU or ROM changes are admitted.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h8_kyivemu.exe
python -B tools/isa07_d15b1_h8_native.py --cli-exe tempkyiv/d15b1h8_kyivemu.exe --timeout 20
```

## AU test I, subsequent negative-zero additions X–XI (H9)

- `au1_addition_0143_0150.k41` preserves eight original machine words:
  data at `0010`, `0013` (GY1962 printed p.172), and instructions
  `0143..0150` (p.173). It is a HOST image, not physical card encoding.
- Both ADD instructions use pinned ROM `3026=20000000000000` (−0).
  Their machine-code operands predict the unchanged **positive** results
  `0010=00010004002001` and `0013=00400200100040`.
- **Source discrepancy**: printed p.172's commentary assigns `0143..0145`
  a `(0)20` result and assigns `0146..0150` the `0010` result, while the
  literal instructions at these addresses reference `0010` and `0013`,
  respectively. Record this mismatch; do NOT repair the source or assert
  unqualified historical-explanation agreement.
- The `tools/isa07_d15b1_h9_native.py` runner tests *machine-code-derived*
  expectations and the original STOP fallbacks on temporary private mutants.
  See `docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md` for exact source and limits.
- CPU/ROM and all previous canonical examples remain immutable. Independent
  human transcription and a physical Kyiv hardware oracle remain PENDING.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h9_kyivemu.exe
python -B tools/isa07_d15b1_h9_native.py --cli-exe tempkyiv/d15b1h9_kyivemu.exe --timeout 20
```

## AU test I, cyclic addition at 0151 (D15/B1-H10)

- `au1_addcyc_0151_0154.k41` contains six verbatim 1962 machine words:
  operands `0007` and `0020` (printed p. 172) and instructions `0151..0154`
  (printed p. 173), with per-word first-visual-pass provenance.
- Source opcode `07` at `0151` adds `0007+0007` cyclically and compares the
  result with `0020=16757367573624` at `0152`; the original fallback STOP
  is `0153`. Address `0154` is included for provenance ONLY, not executed.
- Independent 40-bit arithmetic shows a distinction: truncating the carry
  gives the printed `16757367573624`, while adding an end-around carry unit
  gives `16757367573625`. The current CPU uses the latter as an explicit
  provisional *emulator policy*. No hardware conclusion follows.
- The H10 bounded **observation** runner measures 1-, 2- and (only if
  the check fails) 3-step behavior. It must not execute command `0154`,
  which refers to operator-settable `3000`. A mismatch to the printed
  result is retained as evidence, **not silently converted into PASS**.
- See `docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md`. H9's printed
  prose discrepancy remains OPEN and entirely separate from this question.
  No CPU, ROM, or previously committed historical image is modified.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h10_kyivemu.exe
python -B tools/isa07_d15b1_h10_native.py --cli-exe tempkyiv/d15b1h10_kyivemu.exe --timeout 20
```
