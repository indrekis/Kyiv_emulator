# ISA-07 D8-B — absolute inclusive output intervals for opcodes 22/23

**Base:** `2c4a3da` (ISA-07 D8-A). **Digital documentary source:** V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), printed pp. 15–16, PDF SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`. See committed `docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md`.

The book describes output of codes stored at addresses **a₁ through a₂ inclusive**, and control transfer to a₃, for both `22` (perforated output) and `23` (drum write). The current implementation at D8-A instead reads `a₁+i` for `i` from 0 through a₂, interpreting **absolute endpoint a₂ as a count-like offset**. With a₁=0200, a₂=0202 it emits 131 host text fields rather than 3.

## Exact CPU change

For each of the two output handlers only:

- `for(uint64_t i = 0; i <= addr3_shifted.source_2; i++)` becomes `for(uint64_t i = addr3_shifted.source_1; i <= addr3_shifted.source_2; i++)`.
- `kmem.read_memory(addr3_shifted.source_1 + i)` becomes `kmem.read_memory(i)`.

Thus output covers absolute addresses `[a₁,a₂]` for **a₁ <= a₂**. No change to `C_reg=a₃`, `K_reg`, host file paths/format, `word_to_number`, address modifiers, or other opcodes. Previous D3 `break;` after 22 is preserved.

## Qualification and limits

- 10 single-step process-isolated cases: both `22`/`23` × (`range` 0200..0202, `single` 0201..0201, `offset` 0201..0203, `legacy` 0001..0002, `fromzero` 0000..0002).
- `fromzero` expects the values `0 5 7` (not `3 5 7`). In the current `Kyiv_memory_t`, `write_memory(0000, ...)` is a no-op because address 0000 is hardwired to zero (`inc/kyiv.h`). This is a **host memory model invariant** for the fixture, not new evidence about peripheral hardware. The former fixture incorrectly attempted `write_memory(0000, 3)` and the runner's expectation was therefore impossible.
- Temporary directories isolate actual host output files. Both exact word sequences and the **absence of output to the other device** are checked. `C=0120` and `running=1` are checked. The host integer text encoding and peripheral physical behavior are NOT a historical device oracle.
- A **reversed interval** a₂ < a₁ is not source-qualified. The proposed positive-direction loop performs no iterations in that case, but **that incidental host behavior is not asserted as historical semantics or tested**. Do not invent wraparound, address reversal, or a hardware error.
- D3's historical output test uses a₁=0001, a₂=0002 and expects *three* words under the old offset interpretation; after this fix the correct count is **two**. Do NOT use the old D3 runner as a current-CPU pass gate. The new `legacy` case preserves its no-fallthrough property with a qualified two-word expectation.
- D7 remains a pinned **pre-fix mismatch record**, and D8-A remains a pinned **previous-CPU change gate**. Do not rewrite those auditors or expected old output lengths to force them to pass on newer CPU.
- D8-B does NOT address decimal interpretation in opcode 20; next PC of 20/21/24/25; reversed input intervals; malformed records; output mode switches; drum track selection/rollover; address-modification register destruction; physical device timing.

`SOURCE_STRICT_INTERVAL` refers only to the documented digital endpoints, `HOST_CODE_FIX` to exact C++ changes, `HOST_POLICY` to test file presentation, and `OPEN` to unsettled machine behavior.
