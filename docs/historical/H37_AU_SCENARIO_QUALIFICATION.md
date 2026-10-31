# H37 — qualified historical AU entry, not whole-AU validation

**Baseline:** `f15c879a1ba1110d6c14ff7ce526397b0eadcca2`.
**Evidence:** H36 V2 source-only one-step PASS, five native bounded observations.
**Status:** `PASS_HISTORICAL_ENTRY_BOUNDARIES_ONLY` / `HARDWARE_ORACLE=NO` / `FULL_AU=OPEN`.

## Source qualification and scope

- The paper's printed page 173 (1962, PDF page 172 counting from 1), left column, row 0042 reads `01 3066 0000 0353`. The line was visually checked again against the **same** scan, not independently read from a second scan. The literal `01306600000353` is recorded once in the scenario manifest as `SOURCE_PRINTED`; the canonical 20 `.k41` files remain untouched.
- H36 executed 0042 through production `Kyiv_t::execute_opcode()` with pinned `ROM[3066]=14441766521042`, produced `RAM[0353]=14441766521042` and `PC=0043`. This is a strict **single-step source/native** claim, not full AU completion.
- Five paths were executed using **HOST zero-initialized RAM**, which is not an independently known historical initial state; outputs are `OBS`, never strict historical oracles.
- H36 uses `select_panel_nk(03000,true)` with sign-bit panel code for its `NK_MINUS` case. Its `NK_PLUS` labels correspond to `select_panel_nk(03000,false)`, i.e. **cabinet storage source selected**, not a verified physical +NK panel position. This distinction is essential for operator reconstruction.

## Qualified H36 trajectories

| Entry | Steps | Final PC | Why tracing stops | Status |
|---|---:|---|---|---|
| `0042` (panel negative zero at NK3000) | 97 | `0360` | External word absent from qualified AU image | OBS |
| `0043` (NK3000 cabinet source) | 256 | `0047` | Step budget; cyclic execution not automatically a defect | OBS |
| `0110` (NK3000 cabinet source) | 256 | `0121` | Step budget; cyclic execution not automatically a defect | OBS |
| `0155` (NK3000 cabinet source) | 48 | `0360` | External continuation outside source corpus | OBS |
| `0214` (NK3000 cabinet source) | 49 | `0252` | I/O opcode 022 not executed; device not emulated in this proof | OBS |

The source-only command `0042` is **not** copied into a second `.k41`, and its own `RAM[0353]` write is distinguished from an invented initial seed when entering `0214` independently. Neither historical `NK3001/NK3002` states nor scratch RAM are reconstructed by H36. `0232` is a further source-visible I/O boundary which must not be silently traversed.

## Previous completed stages not to repeat

A3/A4 produced bounded source/operator evidence, A5 characterized remaining mismatch; H23–H28 independently identified the primary shift reconstruction. H29–H32 installed, validated and committed `013` (`0b5f54f`); H33–H34 source-reconciled ISA-04 and committed `f15c879`. H35 is a source inventory (not test pass), and H36 source/native bounded evidence is now accepted. No rework of these stages is required without new evidence.

## Next open major phase: B / H38

Build **one persistent-session** historical AU runner with explicit operator events, provenance for scratch values, bounded per-epoch execution, source-only word 0042 loaded from the qualified scenario manifest, and strict I/O/external boundaries. Keep `demo`, `test`, and `diagnose` semantics distinct. First demonstrate a source-attributed `0042 -> ...` route and classify whether branches depend on unknown scratch or operator settings. Do **not** assert full AU pass, edit ROM, supply fabricated test inputs, or reroute at `0360` to make tests pass. After this, advance ROM sets, MP/PP-2, and GUI per the master roadmap.

## Files and acceptance

- `examples/historical/gy1962/scenarios/au1_h37_entry_qualification.json` — sole new source-only value 0042 and evidence-qualified entry metadata; no executable historical completion oracle.
- This report and status annotations in `ROADMAP.md` and `PROGRAM_CATALOG.md` — historical append/annotation, no deletion of previous research.
- H37 gate: verify pinned source files, H36 SHA/provenance, **all 706 trace rows**, exact five boundaries, and unchanged Git tracked files before applying these four documentation/manifest files. `git commit`/`push` are never performed.
