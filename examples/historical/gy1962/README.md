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
