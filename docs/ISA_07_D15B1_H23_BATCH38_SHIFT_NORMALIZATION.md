# H23 — 38-word continuation, evidence layers and stop-gated probes

**Historical source:** Glushkov / Yushchenko, *Вычислительная машина «Киев»* (1962), printed p.174; words 0300–0345 inclusive. 29 program words 0300–0334 and 9 constants/data 0335–0345. Provenance `VISUAL_FIRST_PASS`; visual proofreading remains separate from native observation.

## Functional checkpoints

| Subgroup | Entry | Checkpoints | Scope |
|---|---|---|---|
| A normalization | 0300,0302 | source HOST-zero and PRIVATE negative-zero entry; compare ROM[3177]=-1 normalization outputs 0347 and 0350 to printed data 0335 and 0336 | 0307 boundary |
| B shift arithmetic | 0307 and 0315 | left vs right shift using sign of count, 12-bit distance; left40 vs right40; altered PRIVATE count off-by-one rejected | 0326 boundary |
| C sign/shift loop exit | 0326,0334 | count low-six-bit mask for -64,-65, conditional STOP and self-comparison branch to 0360 | 0360 boundary |
| D source data | 0335–0345 | Nine exact 41-bit historical words: expected normalizer result/order, shift counts and reference words | Never executed |

## Source != host != hardware

- `RAM[0335] = 30000000000000` is the **printed** expected negative normalized half; `RAM[0336] = 20000000000047` is the **printed** negative order word. Both remain unmodified in the canonical source image.
- The current HOST `opcode_norm` stores the unsigned magnitude of normalization power (e.g. `00000000000047` for ROM[3177]) rather than signed order. A PRIVATE entry with `RAM[0350]=-0` reaches the normalization and probes that difference. No historical-initial-state claim follows from such a private entry.
- Exact matching of a simulated 41-bit HOST policy does not establish correctness against physical EOM Kyiv, even when all native cases PASS. The source comparison `0305` provides a **discriminator** that must not be silently reclassified as a historical PASS.
- Step-limited CLI checks PC, stop/limit, four watched words `0003,0347,0350,0351` after individual prefixes, in both CWDs. Canonical historical code has **no** private seeds or mutated commands. Private 0332 comparison is optional runner-only evidence to reach 0334; it never changes historical data.
- No execution of 0360; no execution of data 0335–0345. CPU, ROM, earlier images unchanged; H9/H10/H11/H13/H14/H17 OPEN_UNCHANGED.

**Expected status before native:** `SOURCE=VISUAL_FIRST_PASS; HOST_PROBE=MODEL_ONLY; NORMALIZER_ORDER_SIGN_ORACLE=OPEN; HISTORICAL_RAM=UNKNOWN; HARDWARE_ORACLE=0`.
