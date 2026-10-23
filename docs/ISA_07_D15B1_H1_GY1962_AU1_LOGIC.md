# D15/B1-H1 — historical arithmetic-device test no. 1, logical section (OBSERVED)

Pinned parent: `1b187d944d63ef0961e019e35de4a6374346e504` (D15/A3-P3).
No changes to existing tracked code, CPU, ROM, or HOST loader.

## Canonical example and provenance

The one canonical image is `examples/historical/gy1962/au1_logic.k41`; its adjacent
`au1_logic_provenance.tsv` records all 39 words, each `VISUAL_SINGLE_PASS` (independent
second transcription remains PENDING). The image is **identical byte for byte** to the
previously installed file in `tests/historical/gy1962/` (SHA-256
`56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c`).
The earlier file is moved, not copied, so regressions run the same visible example.

Source: V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»*
(1962), printed pp. **172–173**: input data `0002`, `0003` (p. 172), and exact
command listing `0043..0107` (p. 173). 37 instructions, 12 fallback STOPs.
`0043` is the entry point for the isolated logic section; `0107` uses the
operator-settable NK selector `3000`, so bounded runs avoid executing it.

## Native evidence versus original expectation

First genuine Windows/MSYS2 run after the initial H1 package:

```
D15B1H1-CASE 01 PROFILE=HISTORICAL_ENTRY CWD=EXTERNAL RC=0
D15A2-RUN STATUS=CPU_STOP STEPS=19 C=0076
D15A2-WATCH ADDR=0347 RAW=37777777777777
```

The live program reaches `0073 = 17 0002 0003 0347` and, with the current
bitwise XOR semantics, gets all 41 ones from the complementary input words.
`0074 = 16 0347 0000 0076` therefore does not branch and `0075 = 33 ...`
executes STOP; after that the emulator reports C=`0076`.

**Two source claims conflict:** the 1962 instruction description (printed p. 11)
specifies operation `17` as *inequivalence* with the XOR truth table. Yet the
arithmetic-test examples (printed p. 172) label `0073..0075` and `0076..0100`
as expecting zero for complementary operands, and `0101..0103`, `0104..0106`
as expecting all ones for identical operands: an XNOR truth table.
The actual machine's intended behavior for this discrepancy is **OPEN**.
Neither source page can be erased by forcing the runner to expect the other.

The printed command `0102 = 16 0347 3036 0107` also jumps directly to
`0107` when satisfied, skipping `0104..0106`. Preserve it **as printed**;
this is another source-level observation, not a license to readdress it.
`3200` is an unestablished ROM cell but not touched by the bounded logic tests.

## Narrow qualification gates

- Pin all 39 unchanged transcribed words and the original ROM blob.
- Run actual production `kyivemu image` with default SHA-pinned ROM in two working directories.
- Record and assert **observed emulator behavior** (`HISTORICAL_ENTRY` early STOP),
  plus bounded direct probes of 0073, 0101, and 0104 explaining the discrepancy.
- Count an OBSERVATION PASS as reproducibility **only**, not a historically passing diagnostic.
- `HISTORICAL_EXPECTATION_MATCH=0`, `ISA_ADJUDICATION=OPEN`,
  `INDEPENDENT_SECOND_PASS=PENDING`, `HARDWARE_ORACLE=0` remain explicit.

No CPU changes. The earlier 22-step successful-route assertion was falsified by the
native gate and is superseded, not silently rewritten as a successful execution.
