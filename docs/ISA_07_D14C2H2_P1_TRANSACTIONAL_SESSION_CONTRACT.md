# ISA-07 D14-C2-H2/P1 — explicit `.kdr` transaction session

**Pinned baseline:** `8ad1a33210dc1c32f49390fca4fc0d1ff666b7cf` (D14-C2-H1).
**Scope:** standalone C++17 HOST_POLICY transaction controller; **no `Kyiv_t` mutation, no opcode dispatch changes**. Historical track encoding and geometry are **OPEN**. `HARDWARE_ORACLE=0`.

## Public component / lifecycle

`inc/kyiv_drum_transaction_v1.h`, `kyiv_drum_transaction_v1::session`:

1. **Explicit attach only.** Caller provides an **existing** `KYIVDRM1` `.kdr` path, explicit `geometry` including `profile_id`, `host_address::policy::a3_linear_v1`, and the 1-based pinned drum number (1..3). `persist::load` validates the entire image before any session exists; requested geometry/profile must match exactly. Invalid/missing image, unsupported policy, wrong lock or geometry fail. This class **never silently creates** an image. A separate explicit provisioning action must call B3 `save_atomic(logical_media(explicit_geometry),path)` before attachment. No default device selection or path.
2. **Preparation (`25`).** `prepare(raw_41_bit_instruction)` delegates to the unchanged C1b decoder and C2-H1 mapper. `raw_a2` is restricted to exact octal `0100/0200/0300`, the selected drum must match the explicit pin, `raw_a3` is 0-based linear position, and address-modification marks are rejected as unqualified HOST cases. Validation precedes mutation. Distinct read/write preparation states begin invalid and remain until replaced; a rejected `25` changes neither. No C/K/A, RAM or file side effects.
3. **Read (`24` backend).** `read_words(count)` requires successful read preparation. B2 validates the complete same-drum span and all slots; an `UNWRITTEN` cell rejects the whole read. Returns a newly allocated vector of **raw 41-bit words**, preserving `+0`/`-0`; has no side effects on session/file. Future CPU integration must validate all destination RAM cells and target branch/prefetch **before** the first RAM write.
4. **Write (`23` backend).** `write_words(words)` requires write preparation; creates a staged copy of the logical image, then B2 `write_group` validates entire span and all 41-bit words and applies the group to the copy. B3 `save_atomic(staged,path)` must return successfully **before** committing the new in-memory image via `noexcept` move assignment. Exceptions leave the previous session media and preparation states untouched; before rename they leave the old file unchanged, and B3 attempts temp cleanup. The whole-image copy is an **intentional HOST transaction staging cost**; it does not alter B2's allocation-free commit contract. The caller must serialize access (no multiprocess locks).
5. **Persistence.** There is exactly one authoritative `.kdr` image per attached session. Every successful `23` backend transaction attempts file replacement; `25/24` never save. Disk path is immutable while attached. Crash durability (fsync/parent directory), concurrent writers, symlink/race protections and cross-process atomicity **are not claimed**. `save_atomic()` success followed by a process crash before the in-memory move does not establish a durable two-phase transaction. In ordinary single-process execution the in-memory move cannot throw.
6. **Errors.** `UNPREPARED_READ`, `UNPREPARED_WRITE`, `UNWRITTEN`, `END_OF_DRUM`, `INVALID_WORD`, `GEOMETRY_MISMATCH`, and C1b/H1/B3 validation error codes are observable HOST errors. No automatic fallback to the legacy text adapters, no conversion to decimal and no silent drum switching.

## CPU integration gate (H2/P2; NOT implemented here)

- Attach must be **opt-in** before CPU execution; an unattached `Kyiv_t` must not auto-select an image or a geometry. A fresh mode distinguishes the new session from unqualified historical behavior. Existing text paths remain unchanged *until* the real CPU gates pass; then deprecate/remove them as mere placeholders.
- `25` must consume **raw** II/III fields (GY62 p.15) and commit preparation only on complete validation; on success `C←C+1`, `K←memory[C]` according to the currently established convention. Source ambiguity about address modifier register `A` and historical invalid-state behavior stays explicitly `OPEN`.
- `23/24` use the existing effective RAM interval interpretation pending a source-qualified change. For the first proof, **reject RAM address 0000** as an explicit conservative HOST restriction; require bounds within `0001..01777`, and reject any ROM/overwide input before a file or RAM commit. This avoids silently deciding the ROM-source ambiguity or the documented hardwired-zero cell semantics. Branch target/prefetch must be readable before mutation. Successful transfers branch to the command's III address; tests record C/K/A.
- `execute_opcode()` refreshes `K_reg` on entry. Thus a fault after dispatch can promise no additional K mutation only **relative to the freshly fetched instruction**, not to an arbitrary K supplied before stepping. Test both checkpoints. Reject any unintended mutation of C/A, RAM, preparations or `.kdr` on failure; host exceptions are not a historical stop-mode oracle.
- Test actual CPU `25 → 23 → 25 → 24` on a preprovisioned image with independent byte validation; simulate failure before and during replacement, failed C1b/H1 mapping, unprepared/wrong-direction, unwritten cell, last-track boundary, invalid RAM, `+0/-0` and K prefetch. Then run prior D12/D13/D14 and ISA regression gates. **No CPU commit before genuine MSYS2 CPU + regression passes.**

## Standalone P1 acceptance

`tests/isa/isa07_d14c2h2_transaction_probe.cpp` exercises the genuine C++ session with an ASCII command protocol. `tools/isa07_d14c2h2_transaction_sandbox.py` constructs the expected `.kdr` **independently** (headers, bitmap, little-endian words, CRC64-ECMA), compares the final file byte-for-byte and checks all responses. It forces an OS rename failure by temporarily replacing the target path with a directory in the test process; ensures original file restoration, session state invariance, and no leaked sibling temp files. Tests include three drum locks, track crossings, repeated preparations, invalid directions and marks, negative zero, overwide payload, wrong geometry, missing file and invalid lock. Source-controlled CPU files and all B1/B2/B3/C1b/H1 sources stay byte-identical to the pinned base.

Example build on MSYS2 MINGW64:

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tests/isa/isa07_d14c2h2_transaction_probe.cpp -o tempkyiv/d14c2h2_session.exe
python tools/isa07_d14c2h2_transaction_sandbox.py \
  --exe tempkyiv/d14c2h2_session.exe --random-cases 20 --random-steps 50 --timeout 5
```
