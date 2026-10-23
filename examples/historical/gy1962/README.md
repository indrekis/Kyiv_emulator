# Historical Kyiv machine-code examples — Glushkov & Yushchenko (1962)

Canonical historical machine images are stored **here**, under `examples/historical/gy1962/`.
The test harness consumes these same `.k41` files, with **no second copy** in `tests/`.
These are verbatim source transcriptions, *not automatically passing reference programs*.

## AU test no. 1, section I (logical operations)

- `au1_logic.k41` — 39 raw 41-bit octal records: addresses `0002`, `0003` and 37 instructions `0043..0107`.
- `au1_logic_provenance.tsv` — address, source page, original notation and single visual verification for each record.
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
physical-hardware oracle. Independent second visual transcription is pending.

For independent reproduction of the bounded observations and two work directories:

```sh
python tools/isa07_d15b1_h2_opcode17_probe.py --cli-exe tempkyiv/kyivemu.exe --expect xnor --timeout 20
```

Other historical examples will use their own source images and per-word provenance here. See
`docs/ISA_07_D15B1_H1_GY1962_AU1_LOGIC.md` for unresolved evidence and gate definitions.
