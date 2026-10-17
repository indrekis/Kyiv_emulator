# ISA-06 D8-P9 — independently selected operator NK3000–3002 in memory

**Base:** `bbfb995` (P8 user-confirmed PASS). This adds a small software NK panel source model and integrates the selected read path into `Kyiv_memory_t`. `src/main.cpp`, arithmetic, ROM.txt, and previous tests are unchanged. No assertion of authentic 1960 operator-switch startup positions or cabinet contents.

## Documentary scope

Glushkov–Yushchenko (1962), **printed pp. 8, 120–121, 161**; source evidence already qualified in P7 and reference model in P8. `3000–3007` are operator-settable codes; **only `3000–3002`** have documented individual panel/cabinet source switches (p. 161). The sign of `3000` controls RAM-test chaining (p. 120); the sign of `3001` controls the first test's custom-pattern selection (p. 121). No particular initial code, switch position, or automatic ROM loading from the front panel is documented for our emulator.

## New software contract

`Kyiv_NK_panel_t` (`inc/kyiv_nk_panel.h`) stores three independent 41-bit panel codes, configured flags and selection flags. All selectors default to **cabinet**: `Kyiv_memory_t::read_memory(03000..03002)` reads the existing `mem_array_m` cabinet storage, preserving existing repo semantics.

- `kmem.set_panel_nk_word(addr, value)` explicitly configures the panel 41-bit code at only `03000..03002`; values exceeding 41 bits are rejected (not truncated).
- `kmem.select_panel_nk(addr, bool)` selects panel or cabinet independently. Selecting a panel word before explicit configuration throws; no fabricated implicit `+0` is returned. Selecting cabinet needs no panel configuration.
- `kmem.is_panel_nk_selected(addr)` reports current source. Invalid addresses reject.
- `kmem.write_rom(addr, value)` remains the cabinet programming path. It does **not** overwrite a selected panel word. `write_memory()` continues to reject writes at ROM addresses, including NK words.
- Other ROM addresses, `0000` RAM-zero rules, and CPU arithmetic/control code are unchanged. CPU fetch and operand reads automatically use `read_memory` and therefore the selected NK word.

`Kyiv_NK_panel_t` does not implement cabinet hardware, switch signals, contact timing, persistence, or operator UI. Source selection is a **POLICY** implementation of a documented interface, not a certified circuit implementation. Both signed zeros retain their exact 41-bit codes. No `STRICT` claims are promoted.

## Test plan and boundaries

A fresh `Kyiv_memory_t` verifies all 8 combinations of three independent selectors, different panel/cabinet words, full-width 41-bit codes, non-overwriting cabinet updates, rejection of unconfigured panel selection, out-of-range words and unsupported addresses. An actual `Kyiv_t` executes original `31 3000 0022 0177` from a controlled RAM instruction with cabinet `+0` and panel `−0`, checking the two targets under source toggling. This is a *bounded POLICY experiment*; `0022`/`0177` are not fetched or executed by this test.

Run prior D1–P8 suites plus the P9 unit/integration probe. Original RAM diagnostic from documented `0117` and historical sign-0 behavior remain independently qualified as in P8. P9 does not claim authentic default ROM contents, historical electrical accuracy, or natural final STOP reachability.
