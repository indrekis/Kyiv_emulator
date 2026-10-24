# D15/B1-H4 — fresh visual cross-check of GY1962 machine words

Pinned parent: `8857d97361fce920990c5ebf6b2584bd68dc58de` (H3 XNOR CPU correction already committed/pushed).

## Source and method

- Glushkov & Yushchenko (1962), original printed **pp. 172–173**; scanned PDF indexed pp. **171–172**.
- The two data records `0002`, `0003` are at the lower left of printed p. 172.
- The complete logical subsection `0043..0107` is in the left column of printed p. 173.
- On 2026-10-24, a **fresh manual visual reading** was entered from page images without extracting the canonical `.k41` file first. Only after completing all 39 rows were the readings compared mechanically with `examples/historical/gy1962/au1_logic.k41`.
- **Result: 39/39 word-for-word equal, 0 differences.** Breakdown: 2 DATA and 37 COMMAND records.
- This fresh pass was performed by **the same assistant involved in the earlier transcription**. It is a second visual pass, **not** an independent second *person*. A separate human witness remains pending.
- This is a transcription comparison, **not** a hardware-level oracle and **not** a claim about the correctness of the historical printed program's control flow.

## Canonical data and immutable evidence

- The sole executable historical image is `examples/historical/gy1962/au1_logic.k41`, retained byte-for-byte (SHA-256 `56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c`).
- Original one-pass provenance `au1_logic_provenance.tsv` remains an unchanged historical evidence record. The new `ISA_07_D15B1_H4_SECOND_VISUAL_READ.tsv` is an evidence transcript, not a second executable image.
- The audit reconstructs all raw 41-bit octal codes from five original print groups and checks the complete address set/order, first-pass TSV provenance and pinned SHA.
- `src/main.cpp`, ROM, H2 conflicting-source evidence, H3 CPU regression and `.k41` are not modified.

## Unresolved limitations

- `HUMAN_INDEPENDENT_WITNESS=PENDING`: independent researcher has not reread the scan.
- `HARDWARE_ORACLE=0`: physical Kyiv hardware behavior cannot be inferred from matching text alone.
- The GY1962 p. 11 XOR/XNOR discrepancy is preserved in D15/B1-H2. H3 made a source-grounded emulator decision in favor of 41-bit XNOR.
- The bounded historical diagnostic intentionally ends before executing `0107`, whose NK selector at `3000` depends on operator input.

## Reproduction

```sh
python -B tools/isa07_d15b1_h4_audit.py --self-test
python -B tools/isa07_d15b1_h4_audit.py
```

Do not silently change the historical words to make any test pass.
