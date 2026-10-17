# ISA-06 D8-H1 — sign-block circuit transcription: evidence-first working netlist

**Repository base:** `b14f4cf` (`main`, ISA-06 D8). **Scope:** documentation plus a structural checker; **no** modification of CPU, ROM, ISA tests, existing files, or root README. **Status:** **PARTIAL TRANSCRIPTION, NOT AN EXECUTABLE HISTORICAL GATE MODEL.**

## Why this stage exists

D6/D7 showed that the current opcode `01` returns `+0` for all six tested exact-zero sums. That is a reproducible emulator observation, *not* an independently established Kyiv ISA result. D8 recorded that the true adder outputs the sign through its dedicated second summator sign trigger (`ТЗн2См`) after internal conversions/carries. D8-H1 creates an auditable circuit inventory with evidence at gate/signal level. It deliberately refuses to manufacture missing input polarities, wire junctions or trigger states. The key question `01(−0,+0) -> ?` stays **OPEN**.

## Frozen sources and numbering convention

- DPS64: L. N. Dashevsky, S. B. Pogrebinsky, K. A. Shkabara, *Вычислительная машина «Киев»* (1964), **printed p. 137 Fig. 67**, p. 138 explanation, **p. 144 Fig. 71**, **p. 145 Fig. 72**, **p. 146 Fig. 73**, with p. 101 and table 4 (pp. 102–103) for controls. Images: `kiev0069.png` **right** = p.137; `kiev0070.png` **left** = p.138; `kiev0073.png` **left/right** = pp.144/145; `kiev0074.png` **left** = p.146. Original image and PDF SHA-256 are already pinned in `docs/ISA_06_D8_SOURCE_MANIFEST.tsv`; D8-H1 does not copy source scans into Git or silently update source hashes.
- GY62 (1962), printed p. 13: `02` subtracting equal numbers yields negative zero; this **does not** establish the zero sign of `01` addition.
- **Gate namespaces are figure-local.** `С1` in Fig. 71 is *not* `С1` in Fig. 72 or Fig. 73. IDs `F71.C01` and `F72.C01` are intentionally different.
- `C_GLYPH` in our TSV denotes the printed **«С»** symbol, and `P_GLYPH_GROUP` our explicit junction/grouping alias for a printed **«Р»** circle. Their electrical functions and active polarities are **NOT** declared to be Boolean AND/OR until separately verified against the historical circuit-symbol convention.
- Source `DOC`: directly visible label or clear narrative. `PHOTO_CLEAR`: direct diagram connection with no material ambiguity at current scan resolution. `TEXT_CONFIRMED`: prose directly identifies a connection. `DIAGRAM_GROUP`: grouping appears in diagram but polarity/fan-in remains unqualified. `OPEN`: not yet interpreted. None of these labels is equivalent to a complete gate truth table.

## Files and their meaning

| File | Meaning | Invariants |
|---|---|---|
| `ISA_06_D8_H1_NODES.tsv` | figure-qualified inventory: numbered `С` glyphs, triggers, interface ports, **synthetic alias** groups | all IDs distinct; original symbol versus analyst alias explicit |
| `ISA_06_D8_H1_EDGES.tsv` | *selected* visible/documented connections with evidence label and page for every row | all endpoints exist; no invented electrical polarity |
| `ISA_06_D8_H1_OPEN_ITEMS.tsv` | unresolved crossings, missing labels, timing, second-read requirements | no OPEN item silently converted to a historical oracle |
| `tools/isa06_d8_h1_netlist_audit.py` | static completeness/referential checker; no circuit simulation | prints `STRUCTURE-CHECK PASS` only for a well-formed research record |

**Caution:** The `EDGES` file is NOT an exhaustive gate-by-gate netlist. An apparent line crossing must not be upgraded to an electrical junction without a second source reading. The grouped `P_*` nodes are notation introduced by this audit, not historically numbered elements.

## Step-by-step transcription: source claim, bounded inference, missing data

### A. Fig. 71 — sign block (printed p. 144)

**[DOC]** The diagram visibly separates `ТЗн1` and `ТЗн2` (operand signs) from `ТЗн1См` and `ТЗн2См` (summator signs). It identifies the numbered `С1..С18` devices in the sign-control networks. Each of `ТЗн1`/`ТЗн2` has `0` and `1` control inputs in the schematic, and Fig. 71 labels outputs as `«0»Зн1`, `«1»Зн1`, etc. Distinguish **0/1 input pin** from **the potential representing stored zero/one**; the same numeral occurs in two places with different meanings.

The selected edges give a topological grouping for the left/right operand-sign trigger inputs (`C1..C8`), a `C14/C15` group for `ТЗн2`, and a `C16..C18` correction group. **[DOC/TEXT]** p. 145 says negative input transfer pulses `−Ч1`, `−Ч2`, through `С16`, `С18`, generate a correction signal `+1 ЗнСм` that reaches the count inputs of the two summator sign triggers (Fig. 71). **[DOC/TEXT]** Carry from the 40th summator magnitude digit (`z40`) enters the first sign position; carry out of the first sign position (`z1`) affects the second. **[DOC/TEXT]** p. 146 explicitly says final sign output is from `ТЗн2См` along `КШЗ41` at `ИВА3`.

**[OPEN]** A correction signal being present says nothing yet about whether a given `−0` produces `ТЗн2См=0` or `1` after carries. The exact mapping of C9/C10, both trigger reset conditions and every wire contact around the two sign triggers is unfinished. Do not handcraft a signed-zero truth table from these qualitative dependencies.

### B. Fig. 72 — code transfer controls (printed p. 145)

**[DOC]** Transfer paths are explicitly called `+Ч1`, `−Ч1`, `+Ч2`, `−Ч2`. For `01`, p. 144 says the sign of operand 1 chooses `+Ч1` for positive and `−Ч1` for negative; operand 2 likewise chooses `+Ч2`/`−Ч2`. Fig. 72 displays `С1..С23` with outgoing groups for those four transfers. Two further visible outputs `+Ч3`, `−Ч3` each have an indicated 1.6-microsecond delay element in their drawing. The p.145 narrative relates these delayed signals to the carry phase, not an independent arithmetic opcode.

The table records only plainly discernible top-level fan-in: `C1..C4` group to `+Ч1`, `C6..C9` to `−Ч1`, `C12/C13/C15` to `−Ч2`, and `C17/C18/C20..C23` to `+Ч2`, with shared subnodes `C5/C16/C19`. **[OPEN]** Do not infer a full input truth function for any group from this shape. The leaf labels and exact shared junctions require careful independent re-reading.

### C. Fig. 67 — magnitude bit and carry (p. 137, explanation p. 138)

**[DOC]** A typical stage contains first/second operand bit registers `ТР1`, `ТР2`, a summator trigger `ТСм` and a carry chain. The p.137 text identifies `С3` and `С6` for operand-bit reception. `+Ч1/−Ч1`, `+Ч2/−Ч2` control direct/complement code transfer. The p.138 text describes formation of local carry `z_k` via the bit state and gate `С13`, and a previous-bit carry `z_{k−1}` through `С14`. Its timing caveat says transfer/carry pulses must not violate storage stability; the carry has an actual **separate** time phase.

**[DERIVED / interface only]** The 40th magnitude stage interfaces with the first sign position via `z40`, but the per-bit subdiagram is not a complete sign-block truth table. The `F67.TCMk` bit trigger must not be confused with `F71.TZ2SM` sign trigger: their inverted/direct output controls need separate namespaces.

### D. Fig. 73 — end-of-operation and output controls (p. 146)

**[DOC]** The diagram shows `С1..С7` feeding an `ИКОП` group and `С8..С10` feeding an `ИПр` group; the book's p.145 text says equal summator sign triggers permit normal completion while differing ones signal exceeding the number range. Under the relevant panel setting that can cause skipping a command or stopping; those mode details are outside D8-H1. The p.146 text explicitly states `ТЗн2См=0` selects direct code `ВПК` through `С12`, and `ТЗн2См=1` selects inverse code `ВОК` through `С11`, at `ИВА3`; the sign is then issued separately from that same trigger.

**[OPEN]** A schematic of end/output selection does not retrospectively determine trigger state at that time. `ИКОП` and `ИПр` may have additional causes for other operations; D8-H1 is NOT a proof that all overflow/stop logic is covered by this inventory.

## What can be concluded for signed zero, today?

| Operands of `01` | F71 operand-sign input potentials | Candidate result models | `z40` | `z1` | Final `ТЗн1См` | Final `ТЗн2См` | Historical sign |
|---|---|---|---|---|---|---|---|
| `+0, +0` | `0,0` | M0/M1/M2a/M2b predict +0 | ? | ? | ? | ? | **OPEN** |
| `+0, −0` | `0,1` | model disagreement | ? | ? | ? | ? | **OPEN** |
| `−0, +0` | `1,0` | model disagreement | ? | ? | ? | ? | **OPEN** |
| `−0, −0` | `1,1` | model disagreement | ? | ? | ? | ? | **OPEN** |
| `+5, −5` | `0,1` | model disagreement | ? | ? | ? | ? | **OPEN** |
| `−5, +5` | `1,0` | model disagreement | ? | ? | ? | ? | **OPEN** |

*Unknowns are genuine: neither a source citation nor a passing synthetic comparator computes these states without full reset, pulse and carry transitions.* Input sign potentials are confirmed in the p.144/p.145 text; they are **not** the final state of the two summator sign triggers.

## Reproducible procedure for next researchers (D8-H2)

1. **Freeze and verify:** check `b14f4cf`, inspect original PDF/PNG digests recorded in `ISA_06_D8_SOURCE_MANIFEST.tsv`, keep printed-page mapping explicit. Never substitute an enlarged AI reconstruction for the original scan.
2. **Confirm symbols:** find the book's circuit-symbol convention for numbered `С`, `Р`, `Т`, count/set/reset, **pulse-active polarities**, inversion notation. Record source page for every legend conclusion.
3. **Second read every figure:** a second reader independently annotates each gate and junction *without consulting the edge TSV*. Compare both readings; accepted edges get a two-reader signoff and a reference to original full-resolution image. Divergent or illegible labels stay `OPEN`.
4. **Leaf-level fan-in:** assign every actual input a named port. Replace synthetic `P_*` groups with physically verified vertices only if function and connection are established; use unique local names where historical schematic lacks a number.
5. **Microsequence timing:** derive logical event ordering from Fig. 62 / Table 4 and explicit 1.6/6-microsecond delays. Do **not** treat the stages as identical oscillator ticks or infer an exact gate-delay simulator without pulse assumptions.
6. **Symbolic engine:** after electrical pin polarities are confirmed, implement source-annotated `set/reset/count` semantics for both summator sign triggers and `z_k` stages, then run six exact-zero cases plus nonzero and overflow controls.
7. **Reconcile:** require independent agreement with p.145 normal/overflow criterion, p.146 `ИВА3` code selection, GY62 equal-subtraction `−0`, and where defensible the historical RAM diagnostic without assuming typed ROM is original hardware truth.
8. **Decision gate:** only once a *complete signed-zero proof chain* exists, promote individual cases to historical `STRICT` and separately propose a CPU patch. Until then D6/D7 `OBS` remain observations, not a test failure.

### Acceptance and handoff

- Gate **inventory**: partial, versioned, reproducible; see TSV and checker.
- Gate **truth functions** and signed-zero **microstate traces**: **OPEN**.
- Actual arithmetic output bit for `−0 + +0`: **OPEN**.
- Proposed CPU change: **NONE**. Existing D1–D7 tests remain valid without updating their classification.
- Known CWD-dependent `ROM.txt` loading bug stays separate from this milestone.

**Code/use:** from the repository root run `python tools/isa06_d8_h1_netlist_audit.py --check`. This checks research-table referential integrity and source coverage, **not** hardware truth or historical CPU behavior. See also `python tools/isa06_d8_sign_models.py --check` from D8 for toy-model invariants only.
