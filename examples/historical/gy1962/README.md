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

## AU test I, subtraction to zero at 0155–0162 (D15/B1-H11)

- `au1_subtraction_0155_0162.k41` contains eight verbatim source records:
  operands `0002` and `0003` (GY1962 printed p. 172), and the six original
  instructions `0155..0162` (printed p. 173), with exact per-word provenance.
- The printed p.172 diagnostics predict **negative zero** (`1(0)`, full
  code `20000000000000`) for both `02 0002 0002 0347` at `0155`
  and `06 0003 0003 0347` at `0160`; both JE commands compare against
  pinned ROM `3026=20000000000000` and skip their historical STOPs.
- `02` has an existing signed-zero special case in the emulator; `06` currently
  appears to produce positive zero. H11 observes both cases *without changing*
  CPU, ROM, H9 or H10, and reports historical agreement **per operation**.
- The first fallback STOP is tested using a private JE retarget (historical
  ADD/SUB and STOP unmodified); the second original STOP is observed without
  mutation only if the emulator really mismatches its negative-zero reference.
- The bounded runner starts at `0155` and `0160` independently; maximum three
  steps. It does not execute `0154` (operator NK cell `3000`) or `0163`.
  See `docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md`.
- First-pass visual transcription and software-only evidence; a second human
  witness and historical physical-hardware oracle remain unavailable.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h11_kyivemu.exe
python -B tools/isa07_d15b1_h11_native.py --cli-exe tempkyiv/d15b1h11_kyivemu.exe --timeout 20
```

## AU test I, command addition at 0163–0165 (D15/B1-H12)

- `au1_addcmd_0163_0165.k41` is a five-word bounded HISTORICAL source
  transcription: positive word `0002`, negative word `0003` (GY1962 printed
  p. 172), and commands `0163..0165` (printed p. 173). Provenance and a
  separate CPU-independent sign-magnitude oracle accompany the image.
- Source operation `03 0002 0003 0347` adds the magnitudes, then uses
  **the sign of the second operand**. The expected result is the full negative
  41-bit value `37777777777777`, compared by opcode `16` with pinned ROM
  `3036=37777777777777`. Successful comparison branches to `0166`.
- The original STOP at `0165` is checked only on a temporary HOST copy with
  JE retargeted away from ROM `3036`. Original ADD and STOP are unchanged.
- The test is strictly bounded to one or two instructions for the original
  program, or three for the private STOP profile: **do not execute `0166`**
  (historical opcode `13`, independently scoped to a future milestone).
- H9 printed-prose conflict, H10 cyclic carry and H11 opcode06 signed-zero
  discrepancy stay OPEN and unchanged. This software check is not a physical
  hardware oracle; independent human transcription remains pending.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h12_kyivemu.exe
python -B tools/isa07_d15b1_h12_native.py --cli-exe tempkyiv/d15b1h12_kyivemu.exe --timeout 20
```

## AU test I, zero-distance logical shift at 0166–0170 (D15/B1-H13)

- `au1_shift_zero_0166_0170.k41` contains **four verbatim source words**:
  the input at octal `0261` (GY1962 printed p. 174) and the three original
  instructions at `0166`, `0167`, `0170` (p. 173). The source image does
  not invent a historical initializer at address `0000`.
- Opcode `13` uses the shift constant in the **low six bits of RAM[0000]**.
  The source listing does not print a word for `0000`; the runner *observes*
  its initialized value and requires exactly `00000000000000` before treating
  this as a valid zero-shift case. This zero-initialization is a HOST runtime
  premise, not a transcribed historical source word.
- The 41-bit shift is by zero, so the expected exact output is the input
  `0261=02525252525252`. Successful opcode `16` compares `0347` and `0261`
  and branches to `0171`; `0171` is deliberately **not executed**. Private
  retargeting of JE alone checks the original STOP at `0170`.
- **Source-label issue (OPEN):** GY1962 printed p.172 describes the
  `0166–0170` range using `СлК`, although the literal instruction on
  p.173 has opcode `13` (logical shift). The zero-shift result is identical
  and cannot resolve the label mismatch. Preserve both forms; no CPU edit.
- H9 printed explanation, H10 cyclic carry, H11 opcode06 negative-zero and
  this new p.172 label mismatch remain OPEN. Original machine execution,
  second human transcription and a hardware oracle have not been established.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h13_kyivemu.exe
python -B tools/isa07_d15b1_h13_native.py --cli-exe tempkyiv/d15b1h13_kyivemu.exe --timeout 20
```

## AU test I, three rounded multiplications at 0171–0201 (D15/B1-H14)

- `au1_rounded_multiplication_0171_0201.k41` contains **14 exact first-visual-source words**:
  five RAM data/expected records (`0015`, `0021`–`0024`, printed p. 172)
  and nine literal commands at `0171`–`0201` (printed p. 173).
  They form three opcode `11` rounded-multiplication tests, each followed by
  an opcode `16` comparison and original opcode `33` failure STOP.
- ROM `3035=17777777777777` is a pinned emulator software-ROM value;
  no extra HOST replacement for this ROM cell is included in the image.
- Groups `0171` and `0174` are predicted to match p.172 exactly with results
  `00000000000001` and `30000000000000`; their original STOPs are
  exercised on private comparison-mutant files only.
- **Potential conflict:** p.172 expects `17777777777775` for `0177`, whereas
  independent integer rounded multiplication of `ROM[3035]` by itself,
  using the current CPU rounding rule, predicts `17777777777776`.
  Native tests record both outcomes as separate profiles; if the CPU yields
  `17777777777776`, its literal historical comparison falls through to the
  **original STOP at `0201`**. This is an observation, not a hardware truth.
- Neither canonical source words, CPU, ROM nor prior H1–H13 examples change.
  Original H9, H10, H11, H13 source/behavior conflicts remain OPEN_UNCHANGED.
  Second independent human source reading and real Kyiv hardware oracle remain
  PENDING. Never execute beyond boundary `0202`.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h14_kyivemu.exe
python -B tools/isa07_d15b1_h14_native.py --cli-exe tempkyiv/d15b1h14_kyivemu.exe --timeout 20
```

## AU test I, negative rounded multiplication at 0202–0204 (D15/B1-H15)

- `au1_rounded_multiply_negative_0202_0204.k41` contains six verbatim
  first-visual-source words: RAM operands `0004`, `0005`, expected code
  `0025` (GY1962 printed p. 172), and instructions `0202`, `0203`,
  `0204` (printed p. 173). These are *octal* addresses and raw 41-bit words.
- Original opcode `11`: `0004 × 0005 → 0347`. Sign is negative, and
  the independent sign-magnitude rounded prediction matches source
  `0025=23434343434343` exactly. Opcode `16` jumps to `0205` on equality.
  **Never execute the command at `0205`** in this H15 stage.
- Historical failure STOP `0204` is verified on a private copy with
  retargeted JE source operand `0025→0004`; neither source multiplication
  nor the STOP is modified; private images must not be committed.
- Two separate working-directory runs check exact input cells, all 41
  result bits, control-flow and STOP: six native cases total. This is
  software qualification, not physical machine evidence.
- CPU, ROM, H1–H14 canonical images and prior issues H9/H10/H11/H13/H14
  remain unchanged. A second independent human transcription and a
  real-hardware oracle remain pending.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h15_kyivemu.exe
python -B tools/isa07_d15b1_h15_native.py --cli-exe tempkyiv/d15b1h15_kyivemu.exe --timeout 20
```

## AU test I, one-third division at 0205–0207 (D15/B1-H16)

- `au1_division_one_third_0205_0207.k41` contains six exact first-visual-source
  41-bit octal words: the expected RAM `0004` on printed p.172,
  operands `0026`, `0027` and commands `0205`, `0206`, `0207`
  on printed p.173 of Glushkov–Yushchenko (1962).
- Opcode `12` divides positive `0026=01000000000000` by
  `0027=03000000000000` into `0347`. Opcode `16` compares
  `0347` with historical `0004=05252525252525` and jumps to `0210`.
  In this 40-bit fractional case, independent integer division
  `(numerator<<40)//denominator` predicts the historical code exactly.
- The original failure STOP at `0207` is exercised only on a private
  test image with a **single JE operand** retargeted from `0004` to
  `0026`. Source words and the original STOP remain unchanged.
- Strict boundary: **do not execute `0210`**. The following division
  group `0210–0212`, division rounding, overflow and hardware semantics
  require separate qualification.
- Source Git pins 38/38; CPU, ROM and earlier source examples are unchanged.
  The independent second human transcription and real hardware oracle
  remain pending. All H9/H10/H11/H13/H14 conflicts remain OPEN_UNCHANGED.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h16_kyivemu.exe
python -B tools/isa07_d15b1_h16_native.py --cli-exe tempkyiv/d15b1h16_kyivemu.exe --timeout 20
```

## AU test I, negative fractional division at 0210–0212 (D15/B1-H17)

- `au1_division_negative_0210_0212.k41` contains six first-visual-source
  words, printed p.173: negative numerator `0030=20002000000000`,
  positive divisor `0031=00016000000000`, expected RAM word
  `0032=22222222222200`, and commands `0210` (opcode `12`),
  `0211` (opcode `16` comparison), `0212` (original STOP).
- This printed 41-bit negative result is **NOT** predicted by the current
  host truncating division: exact sign/magnitude integer division predicts
  `22222222222222`; the observed discrepancy must be recorded, not
  interpreted as a confirmed historical rounding rule or silently corrected.
  Magnitude discrepancy is `0o22` (18 decimal) in low-order bits.
- Test source-exact commands; on a host mismatch the original STOP at `0212`
  is expected and the step counter becomes `C=0213`. Runner also recognizes
  the historic-match profile, using a private mutant comparison as a STOP
  witness. **Never execute `0213`.** No changes to the source image or CPU.
- Both CWD profiles, full 41-bit result, three original source cells, and
  exact 44 source Git pins are verified. H9/H10/H11/H13/H14 conflicts remain
  OPEN_UNCHANGED; independent human witness and hardware oracle unavailable.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h17_kyivemu.exe
python -B tools/isa07_d15b1_h17_native.py --cli-exe tempkyiv/d15b1h17_kyivemu.exe --timeout 20
```

## AU test I, control transfer at 0213 (D15/B1-H18)

- `au1_control_transfer_0213.k41` contains **one exact first-visual-source
  word** at address `0213` (GY1962 printed p.174): `05 0000 0000 0263`.
  Opcode `05` compares the absolute values at addresses `0000` and `0000`.
  Self-comparison must take the branch to octal **`0263`** regardless of
  RAM `0000` content. Run only **one instruction**; `0263` is never executed.
- The prose on printed p.172 assigns `0214–0226` to pseudorandom-number
  generation and `0256–0345` to constants. The printed target `0263`
  lies in that latter interval, where printed p.174 shows a word beginning
  with opcode `35`. This is **source-layout context**, not evidence that
  `0263` should be executed in H18 or that the prose has an error.
- The native runner uses two explicitly **PRIVATE**, nonhistorical images
  with data `0001=1`, `0002=2` and opcode `05`: true comparison `1<=2`
  must branch to `0263`; reversed comparison `2<=1` must fall through
  to `0214`. All cases are bounded to **one CPU instruction** and the
  source-exact historical image remains byte-immutable. No extra RAM/ROM
  words are claimed to be printed at the chosen addresses.
- Six scenarios across EXTERNAL/TEMPKYIV CWD; run with verified HOST ROM
  and unchanged CPU. H9/H10/H11/H13/H14/H17 source and behavior conflicts
  remain OPEN_UNCHANGED; no independent human or hardware oracle.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h18_kyivemu.exe
python -B tools/isa07_d15b1_h18_native.py --cli-exe tempkyiv/d15b1h18_kyivemu.exe --timeout 20
```

## AU test I, pseudorandom block 0214–0226 (D15/B1-H19)

- `au1_pseudorandom_0214_0226.k41` contains **12 first-visual-source words**:
  the eleven printed instruction words `0214–0226` (octal address range)
  and printed RAM constant `0260=01777777777777`, GY1962 printed p.174.
  Printed p.172 calls this range *pseudorandom-number formation*, but
  **does not specify the initial contents of RAM `0351–0354` here**.
- Original `0213` branches to `0263`. This experiment instead explicitly
  starts at `0214`, WITHOUT claiming it was reached sequentially.
- Bounded observation: current HOST zero-initialized `0353` follows the
  nonnegative path `0214,0215,0216,0221,0222,0223,0224,0226` (8 steps);
  a separate **PRIVATE** negative seed `0353=20000000000001` explores
  `0217,0220` (10 steps). A PRIVATE positive seed `0353=00000000000001`
  provides a third nonnegative control. No seed is silently added to the
  canonical historical image. Each run stops before executing `0227`.
- The generated register traces and final words are **HOST-policy
  observations**, NOT an independently witnessed historical pseudorandom
  sequence. Separate source/ROM/seed/cwd evidence; H9/H10/H11/H13/H14/H17
  unresolved conflicts remain OPEN_UNCHANGED. CPU and ROM unchanged.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h19_kyivemu.exe
python -B tools/isa07_d15b1_h19_native.py --cli-exe tempkyiv/d15b1h19_kyivemu.exe --timeout 20
```

## AU test I, paired rounded multiplication 0227–0233 (D15/B1-H20)

- `au1_rounded_products_swap_0227_0233.k41` transcribes **five historical
  instruction words** at addresses 0227–0233 (octal), GY1962 printed p.174:
  opcode 11 for both operand orders, opcode 16 comparison, and a failure
  branch containing a perforator output opcode 22 and STOP opcode 33.
- No initial values for `0353` or `0354` are printed alongside this pair.
  The canonical image deliberately leaves these scratch values unspecified.
  Source-only HOST zero-init and two PRIVATE nonzero operand-pair probes
  qualify bounded execution and exact host integer rounding, not a
  historical real-hardware sequence. Previous H19 has unknown seed and
  cannot be treated as a historical oracle for H20.
- Normal path executes at most `0227,0230,0231`, then stops **before**
  reaching `0234`. An additional PRIVATE mismatched comparison reaches
  `0232` but **never executes opcode 22** (perforator) or `0233` STOP.
- Full source/ROM/CPU prior images immutable. H9/H10/H11/H13/H14/H17
  conflicts OPEN_UNCHANGED; H19_SEED=UNKNOWN; HARDWARE_ORACLE=0.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h20_kyivemu.exe
python -B tools/isa07_d15b1_h20_native.py --cli-exe tempkyiv/d15b1h20_kyivemu.exe --timeout 20
```

## AU test I, absolute-value pre-division branch 0234–0240 (D15/B1-H21)

- `au1_absolute_predivision_0234_0240.k41` transcribes five
  historical instruction words from GY1962 printed p.174: opcode 06
  absolute-magnitude subtraction, opcode 05 magnitude comparison,
  and opcode 01 signed addition. Control may skip `0236–0237`.
- Entry `0234`, branch `0235`: when `|RAM[0354]| <= |RAM[0355]|`,
  jump directly to `0240`; otherwise execute `0236`, `0237`, then
  `0240`. Constrain each native probe to 3 or 5 instructions and
  stop **before** executing `0241` (outside this qualified fragment).
- Scratch values `0353–0356` have no independently established
  historical entry state. SOURCE_ZERO_INIT is host-initialized RAM,
  not a source-seeded historical oracle. Three labeled PRIVATE seeds
  exercise both comparison outcomes, including negative operand signs.
  Results compare against an exact sign-magnitude HOST model; signed-zero
  alternatives and prior H11 remain OPEN, not inferred as historical ISA.
- H19_SEED=UNKNOWN; H20_SCRATCH=UNKNOWN; earlier H9/H10/H11/H13/H14/H17
  conflicts OPEN_UNCHANGED; no CPU, ROM, prior-image mutation and
  HARDWARE_ORACLE=0.

```sh
g++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h21_kyivemu.exe
python -B tools/isa07_d15b1_h21_native.py --cli-exe tempkyiv/d15b1h21_kyivemu.exe --timeout 20
```
