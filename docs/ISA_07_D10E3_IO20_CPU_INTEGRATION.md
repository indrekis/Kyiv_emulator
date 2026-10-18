# ISA-07 D10-E3 — narrowly scoped IO20 integration

Status: **proposed, not committed; requires user MSYS2 evidence**.

Pinned baseline: `7803a002fd979cd91e3a22e40955beb944067a53` (`main` after D10-E2 / Windows H1). Main CPU blob unchanged relative to the older revision: `bc9331b178333d2e3ef32789972bc16bc70c39ea`.

## Historical evidence / qualification

- `SOURCE_STRICT` GY62 (Glushkov / Yushchenko, 1962), printed p. 16: opcode `20` (В1) transfers decimal numbers into an **inclusive** memory interval `[a1,a2]`, converting into machine binary codes; punched-card `a3` selects a zone. Printed p. 58: `C <- C+1`, `K <- M[C]` on successful IO20. Printed pp. 7, 17: 41-bit sign/magnitude fractional representation; hardwired address `0000` is documented on p. 8. The physical RAM address range is `0000–1777` octal, unlike the current permissive `Kyiv_memory_t::write_memory` host implementation (`0000–2777`).
- `SOURCE_STRICT` DPS64 (Dashevskii / Pogrebinskii / Shkabara, 1964), printed pp. 15–16: 10 BCD nibbles and a separate sign for decimal I/O.
- GY62 PDF SHA256: `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`.
- DPS64 PDF SHA256: `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`.
- Earlier D10-C / D10-D / D10-E2 fixed or independently tested the exact BCD converter, ASCII adapter, and whole-command input plan; **do not modify these components**.

## D10-E3 host policy, not physical peripheral semantics

1. The existing path `../../mem/punch_cards_in.txt` is preserved, relative to the *process cwd*; missing/inaccessible stream is an explicit error. File opened in binary mode, normalization of LF/CRLF by E2 plan.
2. `perfo_num >= 0` is the zero-based physical text line to select. Effective `a3` is the **byte offset within only that first selected line**, NOT a historically valid encoding of punched-card zones. Subsequent lines are fully consumed, with exact selection from E2 plan. `perfo_num` is not automatically incremented. Future card/zone adapter is OPEN.
3. Fail closed on negative `perfo_num`, descending `[a1,a2]`, or addresses outside physical RAM `0000–1777`. The max number of writable words is 1024. Address `0000` retains the documented hardwired-zero behavior (discard any input assigned there).
4. Invoke `kyiv_decimal_input_plan::collect()` to prevalidate **all consumed tokens and records**, including extras on the last record, and collect *all* necessary words before performing **any memory writes**. If `status != exact`, throw `std::runtime_error("IO20: STATUS_CODE")`; all destination memory remains unchanged. No fabricated historical HALT or rounding.
5. On failure before commit, `C_reg` remains at the opcode address and `K_reg` may have been updated by the initial `execute_opcode()` instruction fetch. No assertion of register rollback. `A_reg`, `h`, and other registers are not speculatively mutated. No historic physical error-state claim.
6. On success, write exactly `a2-a1+1` converted 41-bit words in the inclusive interval, then preserve GY62 documented `++C_reg` and `K_reg=M[C_reg]`. No change to opcodes `21–25`.

## Known boundaries and openly unresolved questions

- Rounding and nonexact input: OPEN historically. D10-C currently returns `NONEXACT`; this integration rejects it as HOST_POLICY, rather than rounding.
- Signed input `-0`: representable by D10-C; physical device preservation of the negative-zero sign OPEN.
- True punched cards' zone addressing / repeat IO20 selection / physical error signaling / exact post-I/O `A_reg` destruction remain OPEN. No attempt to model electronics, timing or mechanics.
- GY62's RAM `0000–1777` versus existing `write_memory` permissive range beyond `1777`: D10-E3 adds a local IO20 validation only, not a refactor of memory.
- Transactionality concerns partial RAM writes from invalid data; the prevalidation guarantees no partial writes on parsing, EOF, invalid address or missing file. Allocation failures and asynchronous process termination during commit are not promised to be transactional.

## Evidence gates

1. `D10E3-AUDIT`: compares exact `src/main.cpp` include + IO20-only delta against pinned `7803a00`, pins D10-C/D10-D/E2 and `inc/kyiv.h`, checks no mutation of `IO21–25` or any other tracked CPU sections.
2. Compile and execute `tests/isa/isa07_d10e3_io20_cpu_probe.cpp` linked with **real `src/main.cpp`**, not a CPU mock. Python runner: 31 cases (14 positive/2 real CPU steps each; 17 negative/atomicity cases). Separate cwd and `../../mem/punch_cards_in.txt` per case, timeouts, independent exact `fractions.Fraction` oracle and seven source-calibrated octal words. For failure check all 1024 RAM cells are unchanged, C unchanged, K fetched-current and registers preserved. For success check all guards, inclusive writes, sequential PC/prefetch, and executing XOR in step #2. The probe uses a stub for **disassembly output only**, not a substitute CPU.
3. Run D10-E2's 26/26 functional tests again (do **not** run the pinned old D10-E2 structural auditor after `7803a00`), and perform applicable post-D10-E3 ISA-06, D8-B, D9-A, D9-B regressions. Old D10-A/D10-B IO20 octal-`HOST_OBS` and pre-fix D7/D8-A/D3 gates are archival evidence, not valid new expectations. Old structural auditors that pin `src/main.cpp` cannot be used as post-E3 gates.
4. User MSYS2 `PASS` results, compile and regression logs **before** commit/push. If failure, isolate H1, do not broaden the patch.

No SIMH work or nonessential refactors in this stage.
