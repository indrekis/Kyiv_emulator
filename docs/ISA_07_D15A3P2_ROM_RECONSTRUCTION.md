# D15/A3-P2 — two source-confirmed ROM word restorations

Pinned parent: `56e7cc1d2dce558fa1f98d1f7df96e923fe464fd` (D15/A3-P1).

Scope: update two entries only in `mem/ROM.txt`: octal `3121 = 01 0005 3011 0005` and `3123 = 12 3011 0005 0004`. Source: V. Glushkov and E. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), **printed page 91**, Program 6 (`ln x`), direct review of the scanned original table (not OCR-only). No correction to any other source code or RAM/ISA semantics; no other ROM word may be changed.

Original Git ROM source: blob `bb6224e130c59564a8ccc4b224c55e41e50784a3`, raw SHA256 `6d26b37262262fd110fffb493f38d512d8d2fe36f322695829951c7ae8de0dd5`; 4396 bytes, 183 lines, 181 syntactically valid rows, malformed 3121 and 3123, absent 3200. Recovered source: 183 valid records; octal `3200` remains absent. Do not infer unknown 3200 is historical zero.

The same book (printed page 8) explicitly defines `3000–3007` as operator-settable **наборные** codes and `3010–3277` as **постоянно-спаянные** codes, the latter range including `3200`. The user reports a prior finding that `3200` is settable; the evidence reviewed for this package does not establish that and the apparent disagreement is **OPEN**, not silently adjudicated. Confirm via original source before assigning an image or user-selectable historical value to 3200. This does not block practical use of the 183 recovered words with explicit limitations.

The existing `Kyiv_t` constructor loads `../mem/ROM.txt` relative to the process working directory and silently leaves missing or malformed cells zero. This package intentionally DOES NOT change that behavior. Runtime deterministic explicit ROM selection, SHA check, unknown-cell provenance and missing-ROM fail-closed handling are future D15/A3-P3 work. The real native probe runs from `tempkyiv/`, where `../mem/ROM.txt` resolves to repository ROM, checks the two actual loaded words using `kyivemu image ... --watch` and also verifies independent byte-exact source reconstruction. This checks the *current* constructor, not a qualified portable ROM loader.

No hardware oracle, complete historical PZU, replacement policy for 3200, or claims of full program correctness. Source changes should not be committed until package audit and native probe pass. No silent fallback to no-ROM as a historical mode.


## D15/A3-P2 Windows native ROM-loader qualification correction

The first Windows native run of P2 **failed** with `D15A2-ERROR stol`, before any
watch evidence. This exposed a pre-existing bug in `inc/kyiv.h`'s `Kyiv_t()`:
`std::stol(data, 0, 8)` is a 32-bit `long` conversion under Windows x64
(LLP64) and cannot represent the full 41-bit unsigned Kyoto machine word.
When the ROM file was actually present (`cwd=tempkyiv/`), a large, valid
word triggered `std::out_of_range`. Earlier tests with different working
directories could silently construct a machine with missing ROM.

The narrowly expanded P2 change set includes one replacement in the ROM
constructor only: `std::stol(data, 0, 8)` -> `std::stoull(data, 0, 8)`.
This matches the existing `word_t=uint64_t` storage. It does not modify
instruction decoding, arithmetic, memory address policy, peripheral models,
or the still-unresolved ROM file path. This **is** a change to `inc/kyiv.h`,
so the scope must be reported as `CORE_HEADER_MOD=1`, not `CPU_MUTATION=0`.

Real Windows gate: compile the actual `kyivemu`, execute one STOP from
`tempkyiv/` where legacy `../mem/ROM.txt` resolves to the actual ROM, and
watch `3121`, `3123`, **and `3036=37 7777 7777 7777`**, whose value
exceeds 32-bit `long`. Distinguish this observed, implementation-specific
success from a verified historical image. Retain unknown `3200` and the
separate need for explicit, checked ROM selection in D15/A3-P3.
