# ISA-07 D14-C2-H3/B2 — independent-process .kdr persistence qualification

Exact parent: `cf4357fe70806ed83a22e9dccd97c57bc96cff93` (H3/B1).

## Scope and provenance

This gate adds **tests and documentation only**. No tracked existing source is changed: `Kyiv_t`, CPU opcodes 25/23/24, `KYIVDRM1` B3, opt-in production CLI A2, create-new-only B1 and all historical source decisions are preserved. `HOST_POLICY=a3_linear_v1` must be selected explicitly by CLI, with exactly 3 logical drums, profile and geometry pinned. The linear third field and 2×8 test geometry are experimental; `HISTORICAL_MAPPING=OPEN`, `HARDWARE_ORACLE=0`. No crash-consistency or concurrent-writer qualification is attempted.

## Process boundaries

Each test is run by an independent Python parent which invokes external binaries (`subprocess.run`):

1. Compiled **B1 creator** `tools/isa07_d14c2h3b1_create.cpp`: `create IMAGE PROFILE TRACKS SLOTS`, rejects already occupied destination and produces a canonical all-UNWRITTEN `.kdr`.
2. Compiled **real production CLI** `src/main.cpp + src/asm_disasm.cpp`: first `expression` command stream `25(write) → 23 → 33`, explicitly attaches the *existing* image and exits. For each pin 1/2/3, writes three raw cells from RAM `0200..0202` to linear drum positions. The test parent independently constructs the **entire** expected image: header, profile, bitmap, 64-bit little-endian payload and CRC64/ECMA-182. It checks every byte after each write, including preservation of earlier drums.
3. A **different production CLI subprocess** (fresh `Kyiv_t` registers and RAM): `25(read) → 24 → 14 → 14 → 14 → 33`. Each opcode `14` performs bitwise OR with RAM `0000` (hardwired zero), copies a read-back word into RAM `0003` and prints `orr<RAW_DECIMAL>` from existing `src/main.cpp`. Check the three *raw 41-bit words* independently, **including -0 as bit 40 set**; the CLI's usual `Result:` format alone cannot distinguish +0 from -0. Check image bytes before and after read unchanged.

The fixed sequence writes to pin 1 starting at position 3, pin 2 starting at 7 (crosses a track), pin 3 at 13 (reaches final slot), then uses fresh processes to reread earlier pins. A seeded, bounded set of randomized scenarios repeats create/write/restart/read with all three executables. It preserves WRITTEN +0 and -0 as distinct from UNWRITTEN. The negative checks reject duplicate creation, missing image, wrong geometry, and CRC-corrupt copy without modifying a valid image or implicitly creating one.

## CLI and format constraints

Production `expression` arguments are decimal `(RAM_address,RAW_word)` pairs, start C is octal `0500`; raw instruction fields are constructed by an independently coded encoder. This is **not** a CPU emulator or historical oracle. Test outputs are captured with timeouts in an isolated temporary directory (including spaces in paths). Filesystem checks compare **names** only to avoid the Windows/MSYS2 `Path` identity pitfall identified in B1-H1.

The runner has `--self-test` for canonical byte structure, signed-zero/unwritten distinction, CRC64 standard vector `123456789`, and mutated CRC/bitmap. `--random-cases N` defaults to 12; `--timeout N` defaults to 15 seconds per subprocess. It never calls `git` and never modifies repo files. No generated image or test log is a release artifact.

## Acceptance

From root with clean HEAD at pinned parent, compile both normal production executable and B1 creator, then run `tools/isa07_d14c2h3b2_restart_sandbox.py --self-test` and its full real-executable gate. The expected fixed scenarios are 14, plus `--random-cases` random scenarios, so default `CASES=26/26`. Follow with audit and pre-existing A2/B1 gates as appropriate. **Do not commit** before a genuine MSYS2 production executable PASS and checks for exact four new files. Historical drum track addressing remains unqualified.
