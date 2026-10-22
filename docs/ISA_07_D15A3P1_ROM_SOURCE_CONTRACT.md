# D15/A3-P1 — byte-exact ROM source census and provisional export

Pinned parent: `846c450a9f84334169e8f00a1f1b285fffb6c20c` (D15/A2). This stage is **read-only source characterization** plus an optional *private* HOST `KYIV41-OCT1` export. It is not a runtime ROM fix, a historical reconstruction, or a ROM upgrade. No tracked CPU, CLI, ROM, drum, or D15/A1/A2 source is edited.

## Why a strict ROM source gate is necessary

`Kyiv_t` currently tries `../mem/ROM.txt`, relative to the process working directory. If opening the file fails, it silently proceeds with zero-initialized ROM. It strips whitespace before interpreting address and word and silently discards lines with unrecognized field lengths. The current `mem/ROM.txt` (pinned Git blob `bb6224e130c59564a8ccc4b224c55e41e50784a3`) is thus neither an explicit reproducible baseline nor a fully qualified historical image.

In the 184-address octal interval `3010..3277`, the exact Git object contains **183 nonempty physical lines**: 181 strictly valid octal records; 2 records with literal UTF-8 replacement-character bytes `ef bf bd` in their machine words (address `3121`, line 74; address `3123`, line 76); no record for `3200`. The set of unresolved addresses is exactly `{3121,3123,3200}`. Those words are not silently assigned any value and there is no attempt to infer their contents from mathematical routines or other sources. The original source file remains unchanged.

This is **syntactic** classification only. A correctly formed octal record can still be a wrong historical transcription. All historical comparisons remain `HARDWARE_ORACLE=0` pending per-word cross-check with the 1962 and 1964 sources.

## Tool behavior

`python tools/isa07_d15a3p1_rom_census.py --self-test` verifies its own strict parser and mutation witnesses.

`python tools/isa07_d15a3p1_rom_census.py` opens **only** the byte-exact Git object `846c450:mem/ROM.txt`, requiring the repository on clean, pinned `main`. It does not interpret the worktree copy (which can be CRLF-translated). It checks physical line count, raw byte length, strict octal-record structure, out-of-range words, duplicates, malformed byte sequences, and exact unresolved-address set. Its runtime output includes the raw source SHA-256.

`python tools/isa07_d15a3p1_rom_census.py --strict-complete` deliberately returns nonzero (`STRICT_ROM_INCOMPLETE`), documenting that the current source **cannot** be considered a complete qualified ROM. Do not convert that deliberate expected failure into a passing gate by weakening the check.

`python tools/isa07_d15a3p1_rom_census.py --export-private tempkyiv/rom_p1_fixture` creates exactly two files in a previously nonexistent private folder: `ROM-provisional.k41` holding **only** the 181 syntactically valid source records (none of the three unresolved locations), and `ROM-provisional-manifest.json` declaring the three unresolved addresses, raw file SHA-256, Git provenance, and provisional status. Output is **not** added to the tracked repository, not automatically loaded, and not a qualified baseline. It is a reproducible diagnostic aid for the next step, not a validated historical ROM image.

## Follow-up function work

D15/A3-P2 will introduce explicit choice and verification of a ROM source for `image` mode; legacy modes retain their existing behavior. Require byte-exact fingerprint of the selected source, validation before changes to the machine, clear reporting of omitted/unresolved cells, and CWD independence. Do not silently fill unresolved historical codes with zero, repair them, or claim historical completeness. We may support an explicitly labeled HOST-provisional policy for isolated experiments only. The GY62 historical corpus is still pending.

## Acceptance

The package must apply only at the pinned HEAD with an otherwise clean tree, yielding exactly four new files. Static audit pins the ROM blob plus source files; source mutation is forbidden. The ROM source test must report `D15A3P1-ROM-CENSUS PASS ... VALID=181 INVALID=2 MISSING=1` and `D15A3P1-EXPORT PASS ... OMITTED=3` from real MSYS2 Git. No commit/push without native Python source test and final audit.
