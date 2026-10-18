# ISA-07 D12-A — IO24 (МБЧ): bounded host-input characterization

**Baseline:** `c67c1e5b4840b36202d94894f3eb59de8a879b81` (W1 committed and pushed). **This is a read-only, no-CPU-edit characterization stage.** The observed failures and missing-file behavior must not become historical-device oracles. The GY62 primary source establishes only the explicitly noted digital semantics.

## Documented scope and earlier qualifications

- **GY62**, В. М. Глушков / Е. Л. Ющенко, *Вычислительная машина «Киев»* (1962), **printed p. 15**: after preceding command **25** prepares drum coordinates, command **24** transfers machine codes to RAM in the inclusive interval `[a1,a2]` and transfers control to **a3**. The printed description discusses continuation to the next track when necessary; it does **not** document the emulator's host pathname, ASCII decimals, LF/CRLF, failure exceptions, or `std::stoi`. See `docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md`.
- **D9-A** already established a **seven-case real two-step CPU** witness for opcode 24's branch and emulator K prefetch; **D9-B** checked command 25's sequential setup followed by 23/24 (eight cases). Do not reclassify D9-A/B's host policy as historical behavior; do not duplicate source-pinned old auditors after W1.
- **D8-A** qualified inclusive input intervals. **W1** only changed `num_counter` from `int` to `addr_t` inside IO24; it did not repair host errors, code parsing, or address validation. An unchanged CPU at baseline has Git blob `80de2590770966cc80cb812d5cc6e3c0afa6e8ea`.

## Exact current C++ path (CODE_OBS before any D12-B fix)

`src/main.cpp`, `case IO_operations_t::opcode_read_magnetic_drum`, opens `../../mem/drum_in.txt`, skips `drum_num_read` lines, applies `line.substr(drum_zone_read, line.size())` to the first selected line, splits tokens with `boost::split(..., " ", token_compress_off)`, converts with **`std::stoi` (signed 32-bit `int` in current MinGW)** and immediately writes each value to `kmem.write_memory`. Negative host decimals are encoded as sign-magnitude using `to_negative(abs(number))`. For later lines it takes their entire text. The loop stops after it has visited more tokens than the inclusive target count, or after EOF. On normal completion it branches to `a3` and prefetches K.

This is a *host textual adapter*, not the historic drum coding. Specific risk classes:

1. **PARTIAL_WRITE:** a bad later token or overrange `std::stoi` throws after earlier destination cells were modified. C and K then remain at the current command (after initial fetch); target memory is not rolled back.
2. **SILENT_SUCCESS:** a missing, empty, short or never-selected host stream can complete normally, transfer to `a3`, and leave zero or only part of the requested interval written.
3. **PARSER_ACCEPTANCE:** `std::stoi("5xyz")` accepts its valid prefix; `-0` becomes `+0`. 41-bit binary raw code (`2^40` decimal) and even `2^31` cannot pass 32-bit `stoi`.
4. **TOKENIZATION:** `token_compress_off` creates empty tokens from doubled spaces, yielding a failure after any previously written words.
5. **ADDRESS_GUARDS MISSING:** no explicit check for nondecreasing `[a1,a2]` or for the physical RAM limit `01777`. A single input word can reach host address `02000` under the existing permissive memory API, although it is not documented RAM. **Reversed intervals are STATIC_ONLY in D12-A**, not run through an unbounded write loop.
6. **TRACK/ZONE HOST_POLICY:** `drum_num_read` selects a **text-file line**, and `drum_zone_read` a **byte offset** into its text, not a verified historical cylinder/track/zone encoding. A negative or excessively large offset is outside this qualification.

## Genuine CPU observation experiment

`tests/isa/isa07_d12a_io24_host_observation_probe.cpp` links the actual `src/main.cpp` and defines a stub for **disassembly output only**. Each process executes one IO24 step, records three target words and all **physical RAM** cells (plus demonstrative address `02000`) relative to its pre-step snapshot; a successful IO24 executes a second **real XOR instruction** at `a3` (`5 xor 3 = 6`), while a caught conversion exception stops after one step. C, K, drum setup and unchanged unrelated physical RAM are checked. Test files live in per-process disposable directories under ignored `tempkyiv/`; never touch `mem/` in the repository.

The Python sandbox freezes **20 current-code observations**: basic/single-cell/selected line/byte zone/multiline; missing/empty/short/selected-track exhaustion; malformed first and later input, suffix, negative and `-0`, too-large 32-/41-bit integers, doubled spaces, CRLF; a safe single-word write at nonphysical `02000`; alternate a3 branch. Dangerous reversed intervals and out-of-bounds I/O are deliberately omitted from runtime probes and remain **STATIC_RISK**.

**Classification of observations:** `CODE_OBS` for code behavior, `HOST_POLICY` for text/token selection, `SOURCE_STRICT` *only* for successful `[a1,a2]` and transfer to `a3` specified by GY62. A successful test of a current-code defect is not approval of that behavior for D12-B. D12-A never asserts physical tape/drum timing, rotation, error handling or full hardware bit identity.

## Exact gate and next step

1. `D12A-AUDIT` must see exactly five untracked files, pristine tracked files, expected `c67c1e5` HEAD and pinned `src/main.cpp`, `inc/kyiv.h`, D9-A/B probe blobs. It checks normalized LF/CRLF and all content hashes except itself; no CPU changes.
2. Compile the new probe with `g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc src/main.cpp tests/isa/isa07_d12a_io24_host_observation_probe.cpp -o tempkyiv/isa07_d12a_cpu.exe` (never link `src/asm_disasm.cpp`). Run `tools/isa07_d12a_io24_host_sandbox.py --exe ... --timeout 5`, expecting 20/20, with host defects reported as **observations**.
3. Run D9-A 7/7 and D9-B 8/8 under current CPU if helpful; their functional probes are still valid. Do not run their historical Git-SHA auditors.
4. Only after actual MSYS2 PASS and source-only audit may the five new files be committed. **D12-B** can then introduce *independently decided* host input grammar, staged/atomic writes, physical RAM checks, and qualified errors. Do **not** silently transplant IO21's octal raw-word format: current IO24 uses signed decimal tokens and the drum setup/zone protocol differs.

No revised claim about hardware-rounding or IO20/21 is involved in this stage.
