# ISA-06 D8-P6 — terminal provenance, source erratum and natural reachability

**Base:** `92f5352` (P5 committed). Scope: source-attribution correction to three P5 documentary/audit files plus one new C++ POLICY probe, one source-origin ledger, one manifest, a new checker and this document. **No CPU, ROM, existing test implementation, or original octal word changes.**

## Verified source distinction — GY62 vs DPS64

GY62 means *Vychislitelnaya mashina «Kiev»* (Glushkov–Yushchenko, **1962**) and is distributed here as `Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf`. Its **printed pp.170–171** contain the RAM-test source words, including `0022`, `0120–0166`. Printed pp.172–173 introduce separate examples for the arithmetic unit.

The earlier P5 manifest erroneously named `kiev0086.png` as the 1962 RAM-test scan. **It is instead a scan of printed pp.170–171 from DPS64 (Dashevsky–Pogrebinsky–Shkabara, 1964)** and shows *control-unit circuitry*, not the 1962 diagnostic listing. We correct the P5 document, manifest and corresponding P5 auditor hash. This is a metadata-only erratum.

## The two destinations are not a final-stop proof

- **`0022` is documented.** GY62 printed p.170 explicitly classifies instructions `0022–0027` as selecting write codes for the **first RAM test**, not as the end of the fourth test. The original instruction at `0022` is `31 3001 0025 0023`. Both its execution and interpretation require other program and ROM state.
- **`0177` is not a listed instruction of the fourth RAM test** in GY62 pp.170–171, where the reproduced fourth-test instructions terminate at `0166`. Later GY62 pages use address `0177` in **separate arithmetic-unit example programs**. This does not authenticate RAM-test memory `[0177]` nor a reachable STOP.
- `0164 = 31 3000 0022 0177` is documented; its branches depend on ROM `[3000]` (P5). It jumps to neither `0165` nor `0166`. P5's directly entered STOP tests cannot be described as a natural stop of the fourth diagnostic.

## Repo ROM census, distinct from real-machine ROM

At baseline `92f5352`, `mem/ROM.txt` has **no entries** `[3000]` or `[3001]`. It **does** contain `[3012]=+1`, `[3026]=-0`, `[3042]=2^39` in the emulator's current 41-bit coding. These match the P4 test fixtures but do **not** independently certify historically installed ROM. The C++ CPU constructor opens `../mem/ROM.txt` relative to the **current working directory**; the regression probes inject ROM values explicitly and therefore do not depend on this loader. The source checker pins the original Git blob and reads ASCII-only target lines in binary mode, avoiding Windows LF/CRLF and unrelated legacy encoding issues.

Without documentary evidence for ROM `[3000]`, `[3001]` and test entry state, running onward through `0022` or `0177` would introduce another arbitrary fixture. No new control-flow `STRICT` or historical zero-sign oracle is claimed.

## P6 experiment: two complete natural pattern epochs, no intervention after initialization

We reuse all 39 exact P4 original octal instruction words (27 HIST, 6 BRIDGE, 6 TAIL), pinned by the P4 Git blob and compared token-for-token. Start with the explicit **P4** fixtures and `C=0120`; then execute the original program without further writes by the test harness. It should sweep RAM `0200–1777` with moving **one** patterns, reach the first terminal condition, execute `0162` (equal subtraction yields `−0` in RAM `[0014]`), restart via `0163` to `0120`, sweep the moving **zero** patterns, and reach the next `0161` whose negative branch sets `C=0164`.

**Hard stop at `C=0164` before fetching/executing `0164`.** We do *not* inject ROM `[3000]` or `[3001]`, or execute the uncertain destinations `0022`/`0177`. A fixed upper bound of 1,350,000 instructions prevents infinite loops.

For every sweep, the C++ probe verifies 896 consecutive 41-bit writes and 896 reads against its **write-phase RAM snapshot**, exact branch-to-`0146` for the original compare, the `0137→0140` handoff, counters of `−0`, and unchanged memory after reading. It checks the first positive-pattern epoch, the true `0014:+0→−0` transition at original `0162`, and the final negative-pattern epoch. It emits a *compact per-cycle* TSV, not a million-row trace.

**The `POLICY` test is provisional**, because startup/ROM constants and opcode-05 equality remain POLICY. A success establishes internal consistency and natural reachability of `0164` **under the selected fixture**, not real-hardware execution. Unexpected first divergence is printed with first_bad_pc and fetched_K. C++ full execution must pass on user's MSYS2 before staging or committing.

## Acceptance and source classes

- **Source/documentation:** exact GY62 PDF SHA-256, corrected P5 manifest and auditor, original P4/P5 C++ Git blobs, repo ROM Git blob; no mixing of the 1962 and 1964 books.
- **POLICY:** complete natural reachability to `0164`, no manual second-epoch entry, program never fetches `0164`, two valid 41-bit RAM sweep epochs.
- **OPEN:** historical ROM `[3000]`, `[3001]`; `[0177]` fourth-test content; whether first RAM test eventually reaches either STOP; actual hardware adder signed-zero semantics. H2 E022 remains RETRACTED.

The P5 auditor **must still pass** after the source-attribution correction; P4 and previous source records remain otherwise unchanged.
