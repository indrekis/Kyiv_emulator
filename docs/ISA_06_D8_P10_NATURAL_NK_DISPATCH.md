# ISA-06 D8-P10 — fourth RAM diagnostic full path through NK3000 dispatch

**Base:** `ad2bda7` (P9 user-confirmed PASS). **Additive-only:** no changes to `src/main.cpp`, `inc/kyiv.h`, `inc/kyiv_nk_panel.h`, `mem/ROM.txt`, or prior probes. Glushkov–Yushchenko (1962), printed pp. 8, 120–121, 161, 170–171.

## Goal and evidence boundary

The complete **40 original instruction words** from P8 (entry `0117`, 27 body, six bridge, six tail) are unchanged. Two **independent** `Kyiv_t` fixtures each start at `0117` with poisoned `RAM[0014]=-0`, then execute the entire 39+39 running-one / running-zero RAM diagnostic (896 writes and 896 full-width comparisons per cycle). At the naturally reached `0164`, execute **that one original instruction** `31 3000 0022 0177`. **Never fetch or execute either target** (`0022`, `0177`). The post-dispatch `C` is inspected directly.

Operator NK source is set once before entry and never touched during the running program:

- CABINET: explicitly program NK `[3000]` cabinet to `+0`, configure panel to `-0`, leave selector in CABINET. Expected after 1,181,828 total executed instructions: `C=0022`.
- PANEL: same two explicit 41-bit codes, select PANEL on NK `[3000]`. Expected after 1,181,828 total executed instructions: `C=0177`.

Both cases assert 78 complete cycles with 39 in each epoch, final `RAM[0014]=-0`, exact historical `K[0164]`, successful execution, and **target not executed**. Mode selector and effective NK3000 word must remain unchanged. Each mode is a separate `POLICY`; the 1962 manual documents operator-selectable codes and the test mode sign but **does not give an authentic position of the operator switch on power-on**. ROM `[3012]`, `[3026]`, `[3042]`, remaining registers, RAM initialization and selected NK values are **controlled fixtures**. No claim is made that ROM `[3000]` contains an immutable historical constant.

## Deliberate limits

- This is a test of integrated **digital control semantics**, not a reconstruction of contact timing, switching delays or analog circuits.
- The destination program at `0022` (first RAM test entry) and the contents/reachability of `0177` remain **outside the test**. Neither path to STOP nor full four-test orchestration is certified; both remain **OPEN**.
- Earlier `POLICY` assumptions about opcode `01` signed-zero sign and opcode `05` remain `POLICY`, even when a 2,363,656-instruction two-run test passes. Nothing here raises that behavior to `STRICT`.
- Use `--trace-prefix tempkyiv/isa06_d8_p10` for two optional 78-line TSV cycle summaries; no per-instruction megabyte logs.

## Build

```bash
python tools/isa06_d8_p10_natural_nk_audit.py --check

g++ -std=c++17 -O0 -g -Iinc src/main.cpp \
  tests/isa/isa06_d8_p10_natural_nk_dispatch_probe.cpp \
  -o tempkyiv/isa06_d8_p10_natural_nk_dispatch_probe.exe
./tempkyiv/isa06_d8_p10_natural_nk_dispatch_probe.exe --trace-prefix tempkyiv/isa06_d8_p10
```

The C++ probe provides the same test-only `disassembly` stub as P8, avoiding the `main` collision in `src/asm_disasm.cpp`. The executable **must not** link `src/asm_disasm.cpp`. No changes to production source are required.

Success means `POLICY=2/2`, `POLICY-FAIL=0`, `DOC-MISMATCH=0`, two natural branches, two times 78 cycles. Rerun all prior tests/audits before committing; commit only if the user MSYS2 test succeeds.
