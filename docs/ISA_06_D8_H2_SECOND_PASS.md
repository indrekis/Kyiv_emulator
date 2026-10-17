# ISA-06 D8-H2 — sign-path source reread, controlled corrections, and reproducibility

**Base:** `5b4663f` (D8-H1 merged). **Classification:** documentary investigation, not CPU qualification. This packet adds this note, a 22-entry source-linked second-pass review, a one-entry override register, and a consistency checker. It does **not** edit CPU, ROM, old tests, existing D8/H1 research records, or the historical corpus. Values `+0`/`−0` refer to the historical sign-magnitude external representation, **not** IEEE-754 floating point.

## Executive finding — a genuinely important correction

**[DIRECT TEXT, DPS64 printed p. 145]** In the description immediately following Fig. 72, the carry from the top magnitude bit (`z40`) **enters the first sign digit** of the adder; **the carry from that first sign digit generates the cyclic carry `z1`**. The second part is a *source-generation direction*, not the destination statement recorded as `TEXT_CONFIRMED` in the H1 edge **`E022: F71.Z1 -> F71.P_TZ2SM_CTRL`**.

This second reading **retracts E022 as an accepted directed electrical edge**; it does not establish the exact outgoing or feedback connections of `z1`, or a replacement gate-level netlist. In the original Fig. 71 (p. 144) `z1` is an upward output label in the region adjacent to the first summator sign trigger. The combination of textual direction and the arrow makes it unsafe to use E022 as the input into the other sign-trigger control. Whether some untraced feedback path exists remains **OPEN**. See `R002` / `R022` and override `O001`.

**Research rule:** keep H1 files as a *dated first-pass snapshot*. Every downstream consumer of `ISA_06_D8_H1_EDGES.tsv` must apply the override in `ISA_06_D8_H2_EDGE_OVERRIDES.tsv`, rejecting `RETRACT_AS_DIRECTED_EDGE` records when constructing a physical directed graph. H1 structural PASS alone is no longer enough to certify a derived graph. The H2 checker actively requires the override and its citation. Do not silently edit E022 in historical H1 and erase why it was proposed.

## Provenance and independent-review limitations

This is a **second reading by the same research assistant**, from actual original scans, and **is not an independent second researcher/reader sign-off**. H1 entries were consulted for comparison only after reviewing the figures and their textual descriptions. The two passes share an interpreter; agreement is therefore not independent corroboration. The next truly independent reread remains a future task.

Primary material: Dashevsky–Pogrebinsky–Shkabara, *Вычислительная машина «Киев»* (1964), printed **pp. 137, 144–147** and corresponding original spread images `kiev0069.png` (right p. 137), `kiev0073.png` (left p. 144 and right p. 145), `kiev0074.png` (left p. 146, right p. 147). Images are the actual historical page scans. SHA-256 of source PNGs was checked against `docs/ISA_06_D8_SOURCE_MANIFEST.tsv`; no scans or cropped images are committed to Git.

`SECOND_PASS.tsv` cites coordinates as `x1,y1,x2,y2` **in the original 3510×2550 scanned spread**, not coordinates in resized screenshots or the two-page PDF viewer. These broad bounding rectangles are navigation aids to the relevant diagram/paragraph, **not pixel-perfect bounding boxes around a wire or junction**. A coordinate matching a printed page does not independently verify the interpretation in the row. P. 144 is the left half of `kiev0073.png`; p. 145 the right half.

## Conventions: observation is not a circuit truth table

The second-pass table distinguishes the following states:

| Assessment | Meaning | Permitted inference |
|---|---|---|
| `LABEL_VISIBLE` | A glyph/number is legible on the scan | Identifies the printed symbol, not its switching function |
| `CONFIRMS_LIMITED` | Diagram or prose backs a narrow claim | Keep only the specifically described interface/functional dependency |
| `CONTRADICTS_H1` | Original source opposes a previous confident direction | Retract/demote that asserted edge via override; do not invent replacement |
| `OPEN` | Polarity, direction, state, proof independence or geometry unresolved | No promoted edge or machine-result oracle |

In particular, numbered `С` and combining `Р` symbols are figure-local. H2 has **not** located and authenticated a circuit-notation legend that would license treating every `С` as a specific modern AND gate, every `Р` as OR, or a printed `0`/`1` trigger pin as an active-high voltage. `F71.C16` and `F72.C16` are different elements. Graph arrows depict flow in a diagram but are **not automatically equivalent** to a positive-level Boolean implication or an edge-trigger condition.

## Results, ordered by the actual signals

### 1. Operand receipt and correction — pp. 144–145

**[TEXT]** For arithmetic addition `01`, the sign controls whether the corresponding magnitude passes in direct or inverse code via `+Ч1`/`−Ч1` and `+Ч2`/`−Ч2` (p. 144). **[TEXT]** Negative transfer pulses through `С16` and `С18` generate the `+1 ЗнСм` correction pulse, which goes to **count inputs of both summator sign triggers** (p. 145). Fig. 71 visibly includes both `ТЗн1См` and `ТЗн2См`, each distinct from its operand-sign counterpart `ТЗн1`/`ТЗн2`.

**[UNRESOLVED]** The content of either trigger immediately before the correction pulse, edge/pulse polarity, exact per-input gate functions, and timing of `z40` can alter the terminal sign. Thus “the correction pulse exists” **does not** mean “negative zero must survive” or that both triggers toggle identically. Fig. 71's `С17` is visibly in the correction combining group, but the prose singles out `С16`/`С18` for negative operands; `С17` must not be assigned their meaning without further evidence.

### 2. Transfer delays — p. 145, Fig. 72

Two separate rectangles marked **1.6 μs** lie in the paths to `+Ч3` and `−Ч3`. The text specifies the delay relative to the second-number transfer pulses `+Ч2`/`−Ч2`. This supports an ordering constraint for the later transfer phase, **not** a fixed 1.6 μs machine-cycle length, nor a measured output pulse width. The horizontal link around `С4`, `С5`, `С6` is visually present but does not define a Boolean equation by itself.

### 3. Magnitude carry and sign carry — pp. 137, 144–145

Fig. 67 includes `z(k−1)` and `z(k)` through a multi-stage transfer network. There is not yet a verified truth table for `С13`, `С14` and the summator state that would generate a specific `z40` for every zero sum. The p. 145 prose confirms **`z40 -> first sign digit`** and **`first sign digit carry -> cyclic z1`**. It does **not** confirm H1's presumed `z1 -> second sign trigger` directed edge. Do not join the diagrams at the same-named graphical label without following the real physical path and distinguishing “source of carry” from “recipient of carry”.

### 4. Result selection and output — p. 146, Fig. 73

The p. 146 narrative reports that at `ИВА3` code output is in **inverse form via `С11` when `ТЗн2См=1`** and **direct form via `С12` when `ТЗн2См=0`**. The sign is separately issued from `ТЗн2См` through the 41st output-sign path. Coincident states of the two sign triggers permit ordinary completion; different states indicate overflow (p. 145). Neither fact supplies the prior two-trigger transition trace or the historical sign of exact-zero arithmetic addition.

P. 147's discussion of **logical addition** (`Л+`) explicitly changes sign-trigger state under its own operation controls. It is valuable as a *separate-opcode control*, **not** an oracle for arithmetic `01`. Likewise, the GY62 p. 13 equal-subtraction `−0` result is a valid independent check for `02`, not a license to infer all zero sums under `01`.

## Six exact-zero cases: current gate of proof

| Addition `01` | External emulator D6/D7 observation | Gate-level sign `ТЗн2См` at `ИВА3` | Status |
|---|---|---|---|
| `+0 + +0` | `+0` | unknown | OPEN |
| `+0 + −0` | `+0` | unknown | OPEN |
| `−0 + +0` | `+0` | unknown | OPEN |
| `−0 + −0` | `+0` | unknown | OPEN |
| `+5 + (−5)` | `+0` | unknown | OPEN |
| `−5 + (+5)` | `+0` | unknown | OPEN |

The right answer cannot be obtained by merely comparing the first and second operand signs, nor by choosing M0/M1/M2 in D8 on plausibility grounds. The **whole pulse/state chain** is still missing. No historical `STRICT` oracle for those six cases has been established and no CPU change is proposed.

## Procedure for future work and independent checking

1. **Freeze provenance:** pin commit `5b4663f`, D8 source manifest and image SHA-256. Verify p.144/145 split in `kiev0073.png`; do not cite raw PNG page indices as printed pages.
2. **Independent blind transcription:** give a second researcher the original full-resolution images **without H1 or H2 tables**. Record each port, arrowhead and each crossing/junction *before* any comparison. Include an annotator identifier and review date in a new signed result file. H2 is explicitly not this sign-off.
3. **Adjudicate each divergence:** for every claimed edge, compare source coordinates, text description, both transcripts, and original printed labels. Mark `ACCEPTED_ELECTRICAL`, `GROUP_ONLY`, `RETRACTED` or `OPEN`. Unresolved should never be silently merged into a digital netlist.
4. **Document switching conventions:** find independent, page-cited descriptions for the printed `С`/`Р` circuits and count/set/reset trigger action (pulse polarity, edges). A symbol shape alone is insufficient.
5. **Build a source-attributed *phase* table:** initial trigger reset; first number transfer; second number transfer; complement correction `+1 ЗнСм`; magnitude carry `z40`; sign-position carry/cyclic `z1`; later `ИВА3`. Do not assign exact timestamps where the books specify only ordering or a partial delay.
6. **Run a gate/trigger symbolic model** only after the prerequisites above. Inputs: 41-bit sign-magnitude operand pairs, operation `01`, and justified reset state. Outputs: two sign-trigger states and carry events for each phase. Assert only separately documented invariants; expose all alternative outcomes for ambiguous wires.
7. **Cross-check independently:** p. 145 agreement/overflow conditions, p. 146 `ВПК`/`ВОК` sign selection, GY62 equal subtraction, D8-D7 characterizations and the original RAM test with source-certain constants. Do not use a transcribed ROM as an independent historical oracle without corroboration.
8. **Decide gate:** when **each** zero case has a complete evidence-linked trace with no unresolved direction or polarity affecting the final sign, promote that case to `STRICT` in a later standalone packet. Only then consider a minimal CPU patch plus D1–D7 regression suite.

## Reproducing and interpreting the H2 checker

From the repository root:

```bash
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_sign_models.py --check
python tools/isa06_d8_h2_review_audit.py --check --emit-filtered-edges tempkyiv/ISA06_D8_H2_filtered_edges.tsv
```

Optionally, with the original full-size PNGs already available outside Git:

```bash
python tools/isa06_d8_h2_review_audit.py --check --verify-scans /path/to/original/pngs
```

The optional `--emit-filtered-edges` writes a **research evidence table**, currently with 80 entries instead of 81 after dropping E022; it is **not** an executable electrical netlist. The first command verifies H1 issue references, H1 directed-edge provenance, legal review states, page/image coordinate bounds, source-manifest presence, and the mandatory **E022 override**. The optional second pass verifies PNG SHA-256 and dimensions against the previously pinned D8 manifest. This is **structural consistency and source integrity only**, never proof of physical circuit correctness or of a zero-sum ISA result. The toy models' check is also not a historical oracle.

**Handoff state:** H1 remains a reproducible first-pass archive; H2 retracts one improperly confirmed directed edge and records further qualified source readings. The final signed-zero truth table is **OPEN**. No patch to `src/main.cpp`.
