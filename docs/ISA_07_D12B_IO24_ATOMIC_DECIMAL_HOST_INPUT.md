# ISA-07 D12-B — Atomic IO24 drum input (HOST_POLICY)

**Parent:** `afc4ad9279c75ecb2a0af7583ec6625847640dca` (D12-A committed). **CPU scope:** one include plus the existing octal `24` handler, and nine additive files. Real-user MSYS2 acceptance is mandatory before commit. Do not amend D12-A or rewrite older source-pinned observations.

## What the original sources actually support

- GY62 (Glushkov–Yushchenko, 1962), **printed p. 15**: `24` (МБЧ) transfers from the prepared magnetic drum into the **inclusive** `[a1,a2]` memory interval and then branches to `a3`. The preparation instruction `25` selects the drum/track and starting position. A physical machine-word code is 41 bits (one sign bit plus 40 magnitude bits; GY62 pp. 7–8).
- **Not established by these sources:** the host paths, UTF-8/ASCII token conventions, decimal text records, zero-based host line selection, byte offset, malformed input handling, transactionality, mechanical timing, real-drum data layout, negative-zero tape representation or exact `K` prefetch timing. These are *not* SOURCE_STRICT.
- D12-A's 20/20 genuine CPU observations (before this patch) show incomplete reads silently accepted, `std::stoi` width restriction, suffix acceptance, double-space exception and partial RAM writes. That archival observation test is **not** a post-D12-B current-code gate.

## New explicitly provisional host adapter

1. File path remains `../../mem/drum_in.txt` relative to process working directory. Open in binary mode. `drum_num_read` selects a **zero-based text line**, `drum_zone_read` selects a **byte offset within the selected first line only**. Subsequent lines start at their first byte. These positions are host policy, not a physical track or zone encoding.
2. Input tokens on the selected line and successors are **ASCII decimal sign-magnitude values** of `[-(2^40−1), +(2^40−1)]`. A leading `+` is allowed; a leading `-` sets the bit `1<<40`, even for `-0`. The decimal *magnitude* must fit 40 bits. Spaces and tabs delimit tokens. LF and CRLF are accepted; embedded CR, NUL, non-digits and suffixes are rejected. Extra tokens after the final required word are ignored, preserving the previous successful-host continuation. Whitespace-only record before the requested count is complete is rejected.
3. An entire required block is parsed and validated before the first memory write. Missing/unavailable input, selected track absent, bad zone, short block, invalid word or invalid address cause a `std::runtime_error("IO24: STATUS")`; **no memory, `C`, `h` or drum setup state is altered**. The entry instruction is already fetched to `K` by `execute_opcode()` on failure. This is an error **HOST_POLICY**, not a representation of drum failure.
4. On success, write exactly `a2−a1+1` words to physical RAM `0000..1777` inclusive. Cell `0000` stays hardwired zero. Branch `C=a3`, `K=M[C]` follows the existing emulator control path and D9-A. Addresses use the existing effective-address machinery; no revision to modifier handling.
5. The library is intentionally different from `inc/kyiv_binary_input_plan.h` (`IO21` raw octal words) and `inc/kyiv_decimal_input_plan.h` (`IO20` fractional decimal numbers). Do not equate their numeric representations.

## Evidence and acceptance

- Pure helper probe plus independent Python decimal oracle: 25 directed + 200 deterministic randomized records, `225/225`, including both zero signs, max-magnitude and error cases.
- Real `Kyiv_t::execute_opcode()` CPU probe: 30 isolated sandbox runs, with two genuine CPU steps on success and whole-RAM nonmutation plus C/K/other-register checks on error. The CPU-probe is linked against `src/main.cpp`, **not** a substitute implementation; disassembly alone is stubbed.
- Functional regressions: D8-B 10/10, D9-A valid cases only 4/4 (`full`, `track1`, `single`, `altjump`), D9-B valid cases 7/7 (exclude old `read-missing`), D10-A IO21 5/5, D10-F3 IO20 50/50, ISA06 `STRICT=89/89`, `POLICY=40/40`. Keep obsolete old `missing`, `empty`, `short` *as archival source observations*, never modify old scripts to make them pass.
- Audit pins full Git blobs of `src/main.cpp`, `inc/kyiv.h`, D12-A docs, previous D11-B regression runner; checks exact `IO24`-only+include delta, eight new files with SHA-256, portable LF/CRLF, and zero change to IO20/21/22/23/25, ROM or arithmetic. No physical hardware oracle.

## Unresolved, deferred

`IO23` output currently uses signed decimal host formatting and loses the textual sign of negative zero; full reciprocal drum roundtrip, physical sector/track addressing, transport timing and precise controls remain OPEN. Address/register destruction by peripheral group instructions also remains OPEN. Do **not** silently implement a new peripheral architecture here.
