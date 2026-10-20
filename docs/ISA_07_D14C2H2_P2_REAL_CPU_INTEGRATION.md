# ISA-07 D14-C2-H2/P2 — opt-in CPU link to a transactional `.kdr` drum

**Pinned baseline:** `eeef38e8ceccc17effb0f9aa4b09bd10ecf2f8c4` (D14-C2-H2/P1). **Scope:** `inc/kyiv.h`, `src/main.cpp`, one actual-CPU probe, Python `.kdr` byte oracle, docs/audit. This is **HOST_POLICY** integration and **not** hardware reconstruction (`HARDWARE_ORACLE=0`). `HISTORICAL_MAPPING=OPEN`.

## Mode and lifecycle

`Kyiv_t::experimental_drum` initially null. The caller must invoke:

```cpp
cpu.attach_experimental_drum(existing_path,
    kyiv_drum_media::geometry{"cpu-optin-2x4",3,2,4},
    kyiv_drum_host_address::policy::a3_linear_v1,
    1 /* pinned drum number */);
```

This checks the **existing** `.kdr` and strict geometry/profile; it never creates one. A failed attach does not discard an existing valid attachment. `detach_experimental_drum()` explicitly restores the legacy opcode behavior; no implicit fallback while attached. Old `23/24` text host adapters and their tests remain exactly as before when unattached. The attached session is owned by `Kyiv_t` (the class becomes non-copyable due to the `unique_ptr`, to avoid accidentally sharing a writable image session; audit existing usages before committing).

## Opt-in CPU semantics

- **`25`:** use `K_reg`, i.e., the actual raw fetched 41-bit instruction. C1b + H1 reject marked/unqualified II fields, illegal mode, wrong drum pin and invalid `a3`. Separately retained read and write preparation states. Validate the next instruction's physical address/prefetch **before** committing preparation, then `C=C+1; K=memory[C]`. Do **not** apply `A_reg` to II or III. No modification to `A` on this HOST path; the historical modifier effect remains OPEN.
- **`23`:** use effective (already A-adjusted when marked) RAM fields `a1/a2`, inclusive; in this first experiment require `0001 <= a1 <= a2 <= 01777` (reject both cell `0000` and ROM; ROM-source possibility in GY62 is OPEN). Validate branch target `a3` is readable and cache the fetched target word *before* file mutation. Stage all raw 41-bit words; an overwide word is an error. `session::write_words` performs B1/B2 validation, stages image, B3 replacement, then no-throw in-memory commit. Only on success branch to target and set prefetched `K`. Any failure leaves `C/A`, RAM and session preparations unchanged; `K` remains the already-fetched instruction, NOT the pre-step arbitrary K value.
- **`24`:** require same conservative RAM interval and a valid read preparation. Prevalidate target before any RAM mutation, retrieve the entire B2 group (reject partial reads and `UNWRITTEN`), then commit verified RAM writes. If branch destination is *inside* the new RAM interval, derive the prefetched `K` from **newly read data** rather than stale RAM; otherwise fetch the existing target before commit. Successful branch sets `C=a3` and `K` to the corresponding word. Failure leaves RAM, `C/A`, preparation and file unchanged (aside from `execute_opcode`'s initial `K` fetch).
- No async timing, hardware execution overlap, DMA or historical stop conventions. In this experiment CPU exceptions communicate HOST errors. No decoder track masking, no other drum selection, no silent geometry inference.

## Persistence boundary

The authoritative binary file is `KYIVDRM1`. Every successful `23` persists via P1/B3. Successful `24/25` never persist. Testing on MSYS2 must verify replacement and the absence of transient leftovers, not just successful decode. Transactional guarantees concern normal **single-process** execution; neither durability across sudden power loss nor interprocess locking is claimed.

## Acceptance gate

The actual probe calls `Kyiv_t::execute_opcode()` for `25 → 23 → 25 → 24` and checks RAM, `C/K/A`, preparation states, overwritten-prefetch case, raw sign bit and negative zero. Negative cases include unprepared direction, invalid II, drum lock, modification flag, direction, unwritten cell, out-of-span group, overwide RAM cell, invalid RAM, last-address opcode-25 next-fetch failure and forced failed file replacement. A 12-bit literal `04000` in the third field is NOT an out-of-range address: it sets the a3 modification mark; the genuine negative boundary uses opcode `25` at ROM cell `03777`, whose next fetch attempts `04000`. The probe supplies a diagnostic-only `disassembly()` stub, so it links with `src/main.cpp` without linking the production `src/asm_disasm.cpp` (which contains a separate `main()`). The Python oracle independently constructs and checks exact `.kdr` bytes, including CRC64/ECMA-182, bitmap, raw 41-bit payloads, and no residue. The default (unattached) `25` legacy route is also checked. A pinned source audit restricts modified tracked files to exactly `inc/kyiv.h` and `src/main.cpp` and enumerates new artifacts.

**NO COMMIT** until this actual CPU test on MSYS2 and the existing ISA arithmetic, IO21/23/24, and all D14-B1/B2/B3/C1b/C2-H1/P1 regression gates pass; paste regression receipts. If one regression fails, report and repair *only* the narrow cause before a commit. Do not call this a historical drum oracle.
