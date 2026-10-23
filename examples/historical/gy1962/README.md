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

**Current observed result:** `CPU_STOP STEPS=19 C=0076`, at historical STOP command `0075`.
This is reproducible evidence of an unresolved disagreement in the 1962 book: printed p. 11 defines
opcode `17` as bitwise *inequivalence* (XOR), whereas the test's expected-value table on printed
p. 172 is for bitwise *equivalence* (XNOR). The emulator currently implements XOR. The observed
stop **does not prove** a defect in the CPU and **does not qualify** this test as historically passing.
Do not silently change the source listing, expected results, or ISA to force a PASS.

For independent reproduction of the bounded observations and two work directories:

```sh
python tools/isa07_d15b1_h1_native.py --cli-exe tempkyiv/kyivemu.exe --timeout 20
```

Other historical examples will use their own source images and per-word provenance here. See
`docs/ISA_07_D15B1_H1_GY1962_AU1_LOGIC.md` for unresolved evidence and gate definitions.
