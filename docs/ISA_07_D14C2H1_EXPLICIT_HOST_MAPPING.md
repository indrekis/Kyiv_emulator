# ISA-07 D14-C2-H1 — explicit, limited experimental drum mapping

**Pinned baseline:** `2a8bae35ee347edef6a957a6ce5002d926cb5e6d`.
**Kind:** `HOST_POLICY` proof-of-integration contract. **NOT hardware decoding.**
`Kyiv_t`, opcodes `23/24/25`, text adapters, C1b and B1/B2/B3 are unchanged.

## Source boundary

GY62 (1962), printed pp. 15, 59, 124, 177–179, supports the
qualified selector codes `0100/0200/0300` (octal) and read/write
selection by address I. It does **not** give a complete mapping of the
other bits of II onto physical tracks. The original magnetic-drum test
arithmetically adjusts II; after carry, the same final command word
may have different programmatic origins (D14-C1f). DPS64 (1964),
printed pp. 230–233, describes **internal** counters but not their
complete conversion from the instruction's visible address fields.

## Named host policy — `a3_linear_v1`

All of these are explicit **HOST** decisions, not SOURCE_STRICT ISA:

1. Caller must opt into `policy::a3_linear_v1`. No default policy.
2. The media object is preconstructed with an explicit B1 `geometry`
   and valid `profile_id`. Exactly **three logical drums** required.
   `slots_per_track` and `tracks_per_drum` remain parameters, never
   fixed to historical 137, 256, or 511. `experiment-137/511` are test
   geometries only, not hardware claims.
3. Parse a raw 41-bit opcode-`025` word using C1b. Only `a1=0/1`,
   only II **exactly** `0100`, `0200` or `0300` (octal), and only
   **unmarked** fields are accepted. All other II field values,
   including `0101`, `0177`, `1100`, are
   `UNQUALIFIED_TRACK_MAPPING`. Marked commands are
   `UNQUALIFIED_MODIFICATION_MARK`; this is conservative host policy,
   **not** a claim that historical command 25 forbids modification flags.
4. The caller must separately **pin the intended drum number** (1..3)
   from explicit experiment configuration, not from the command word.
   `HOST_DRUM_LOCK_MISMATCH` rejects a selector that disagrees with this
   lock. Thus if `0100 + 0100` produces `0200`, a run locked to drum 1
   **rejects** it rather than silently switching to drum 2. A run locked
   to drum 2 may accept `0200`, because provenance of an identical final
   command is fundamentally unknowable (C1f). This policy supports only
   a single configured drum per proof-of-integration run. Invalid locks
   are `HOST_INVALID_DRUM_LOCK`.
5. The selected logical drum index is `((a2 >> 6) & 7) - 1`.
   The **raw third address `a3` is a 0-based linear slot index** within
   the selected drum, *not* the historical physical slot numbering:
   `track = a3 / slots_per_track`, `slot = a3 % slots_per_track`.
   If `a3 >= tracks_per_drum * slots_per_track`, reject
   `HOST_POSITION_OUT_OF_RANGE`. This cannot address more than the
   first 2048 slots of a drum: **known HOST limitation**.
6. The preparation mapper is **read-only**: it returns `direction`
   and a validated B1 starting coordinate, not `prepared=true`.
   This is NOT yet attached to CPU. H2 must provide distinct read and
   write preparation state, with explicit initialization and errors for
   unprepared or wrong-direction `23/24` transfers.
7. For groups, use B2 `validate_span` and B2 atomic `write_group` /
   all-or-nothing `read_group`; a span may wrap to subsequent tracks
   but must **never** cross into another drum. Invalid count, overwide
   word, `UNWRITTEN` and `END_OF_DRUM` are rejected. No fallback to
   another drum or reinterpretation of the raw II field.
8. B3 `KYIVDRM1` / `.kdr` is the sole planned persistence format for
   the opt-in integration. H2 must load/validate geometry before CPU
   execution and save via B3's replacement path at an explicit point.
   B3 guarantees against tested failures, not crash-safe durability or
   multi-process transaction isolation. H1 performs no file operations.
9. In H2/H3 only, choose and test CPU-visible `C/K/A` and failure
   behavior, including RAM/ROM source ambiguity and cell `0000`.
   Do not silently carry over previous text-adapter semantics.
   Any policy decision remains labeled `HOST_POLICY`.
10. Historical coding/geometry, 9864 vs 511, final-track behavior,
   address-marker admissibility and physical KShP mapping all remain
   `OPEN`. `HARDWARE_ORACLE=0`.

## H1 artifacts / proof

- `inc/kyiv_drum_host_address_v1.h`: opt-in pure mapping adapter.
- `tests/isa/isa07_d14c2h1_host_address_probe.cpp`: actual C1b+B1+B2 API.
- `tools/isa07_d14c2h1_host_address_sandbox.py`: independent Python
  reference, including rejection and atomicity test cases.
- `docs/ISA_07_D14C2H1_DECISION_LEDGER.tsv`: scope/evidence ledger.
- `tools/isa07_d14c2h1_audit.py`: pinned file and mutation scope audit.

A correct H1 result is **NOT** a test of a real magnetic drum or CPU.
The next release gate is `D14-C2-H2`, with explicitly enabled opt-in
mode and real-CPU C/K/A + RAM + `.kdr` tests. No commit until MSYS2
sandbox and audit pass.
