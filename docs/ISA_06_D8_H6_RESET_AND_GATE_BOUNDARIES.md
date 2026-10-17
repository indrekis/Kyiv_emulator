# ISA-06 D8-H6 — reset state and the unresolved operation-group qualifiers of Fig. 71

**Base:** `bd5703d` (D8-H5). **Scope:** historical source audit and reproducible evidence records. **No** CPU, ROM, existing tests, already-published H1–H5 evidence, or root README modifications. **No** new `STRICT` result for arithmetic opcode `01`; its exact-zero sign remains **OPEN**.

## 1. Question and principal result

After D8-H5 we know which first/second operand *transfer* pulses are selected under opcode `01`; we do not know whether the pulse goes through the correction gates `F71.C16/C18` or whether `F71.C17` contributes. We also lacked an authenticated initial condition of the two sign triggers in the *summator* (`ТЗн1См`, `ТЗн2См`), not to be confused with the two **operand-sign** triggers `ТЗн1`, `ТЗн2`.

**New source-supported finding:** DPS64 **printed p. 142** explicitly states that the initialization signal received after `ИВА1` sets the summator to zero; the list of initialization signals includes `У«0»См`. On **printed p. 144, Fig. 71**, `У«0»См` appears at the reset (`0`) control paths of **both summator-sign triggers**. Therefore their state **immediately after an effective normal reset, prior to subsequent state-changing signals, is `0/0`**. This is a scoped **DERIVED** statement obtained by combining the prose and the diagram. It is **NOT** the sign state at the later `И1`, `И2`, `И3`, `И4`, or `ИВА3` checkpoints. No physical timing margin, edge polarity, or power-on default is inferred.

This closes only the *initial-value* component of H4-O07. Full subsequent state evolution still requires gate admission, count input semantics, carry interaction, and output sampling. The distinction matters: a zero initial state plus an unknown sequence of count/carry pulses does **not** yield a unique terminal sign.

## 2. Exact source and reproducible reading procedure

**Primary:** L. N. Dashevsky, S. B. Pogrebinsky, K. A. Shkabara, *Вычислительная машина «Киев»: проектирование и эксплуатация* (1964). Cite **printed** book pages, *not* PDF indexes or cropped-image names:

1. **Printed p. 101** (original `kiev0051.png`, right page): prose specifies receiving each operand by `±Ч1/±Ч2`; `ИВА1` initiates AU zero setup. Relevant p. 102–103, Table 4 (original `kiev0052.png`), row **01**, specifies transfer selects, not correction-gate admission.
2. **Printed p. 142** (`kiev0072.png`, left page): paragraph immediately after heading «ВЫПОЛНЕНИЕ ОПЕРАЦИЙ В АРИФМЕТИЧЕСКОМ УСТРОЙСТВЕ» explicitly describes starting any arithmetic operation with AU initial zero setup following `ИВА1`, and lists `У«0»АУ`, `У«0»Р1`, `У«0»Р2`, `У«0»См`. The cited **2 µs** is relative to receiving the operation code; it is *not* a universal reset-to-summator gate delay.
3. **Printed p. 143**, Fig. 69/70 (`kiev0072.png`, right page): traces the high-level operation and temporary-control blocks; do **not** infer unshown physical wiring from similar names in different diagrams.
4. **Printed p. 144**, Fig. 71 (`kiev0073.png`, left page): locate `ТЗн1См` and `ТЗн2См`; check the printed `У«0»См` near their reset/`0` control inputs. Independently transcribe **C16**, **C17**, **C18** and the associated grouped labels. Labels are transcribed first; functional decoding is a separate claim.
5. **Printed p. 145** (`kiev0073.png`, right page), first prose after Fig. 72: the negative transfer impulses through C16/C18 generate `+1 ЗнСм` directed to both count inputs. The same page describes `z40` entering the first sign position, whose outgoing carry generates cyclic `z1`. Keep H2's **E022 RETRACTED**; do not read a new `z1 -> TZn2Sm` direct edge into the text.
6. **Printed p. 146**, Fig. 73/result-issue prose (`kiev0074.png`, outside this H6 manifest): result sign is issued from `ТЗн2См` at `ИВА3`—not simply from the mathematical sign of a host-language integer.

Source hashes for the four selected unmodified two-page spreads are in `docs/ISA_06_D8_H6_SOURCE_MANIFEST.tsv`. The original scans are *not added to Git*. To reproduce: obtain the scans, verify hashes with the checker, compare the figure labels visually, then verify the tabular claims. The source order **p.142 prose → Fig.69/70 → Fig.71 → p.145 prose** is essential: a text reference can confirm a functional interface without authenticating every physical edge.

## 3. Re-read of the C16–C18 input groups

The high-resolution Fig. 71 crop shows the following; Cyrillic mnemonic spelling remains an image transcription, **not** proof of corresponding asserted operation-control potentials:

| Figure-local node | First printed input | Companion printed group (visual reading) | What follows | What does **not** follow |
|---|---|---|---|---|
| `F71.C16` | `−Ч1` | `П₁, П₂, Ср3` (exact subscript/glyph reading tentative) | a *selected* negative first transfer is a candidate contribution | `g16=1` under opcode `01` is not established |
| `F71.C17` | `И1` | `П+, П×, Р` (glyphs tentative) | this **additional** gate can potentially add a correction event | `C17=0` on opcode `01` is not established |
| `F71.C18` | `−Ч2` | `П₁, П₂, Ср3` (same visible group text) | a selected negative second transfer is a candidate contribution | `g18=1` under opcode `01` is not established |
| `F71.P_CORR` | three C outputs | `+1 ЗнСм` | output pathway fans into both sign-trigger count inputs | a numeric pulse count or active-high edge is not established |

**Important:** Printed `С` (“совпадение”, AND) and `Р` (“разделение”, OR) are documented at DPS64 **p. 41, Fig. 6**, as confirmed in H3. A graphical control-group label such as `П₁, П₂, Ср3` is **not** by itself a logic function or a complete opcode selector. Similarly, the same symbol string at two inputs does not independently prove an electrically shared wire. Node IDs are scoped to their figure: `F71.C16` is **not** `F72.C16`. The dash next to the C18 output remains OPEN (H4-O04); it may not be treated as a NOT gate.

This pass deliberately makes **no new claim** that these group names mean particular instructions; no explicit opcode-to-qualifier definition or verified interconnect was found in the consulted source ranges. Resolving that mapping remains the first objective of H7.

## 4. Phase/state reconstruction with evidence grades

`ISA_06_D8_H6_RESET_PHASE_TRACE.tsv` is the auditable phase model:

- **P00 → P01 (DOC + DERIVED):** operation code accepted; `ИВА1` triggers AU setup, including `У«0»См` and zero state of both summator sign triggers **immediately after reset**.
- **P02–P03 (DOC/OPEN):** first sign `ТЗн1` is latched, transfer `±Ч1` selected at `И1`. The actual acceptance of `−Ч1` through C16 **and** additional C17 action are unknown; the sign-trigger state after the phase is OPEN.
- **P04–P05 (DOC/OPEN):** second sign `ТЗн2` latched, `±Ч2` selected at `И2`; admission through C18 and the count-input response are unknown.
- **P06 (DOC/OPEN):** delayed `И3`/carry path; `z40` acts on first sign position, whose outgoing carry generates `z1`. The actual carry inputs and produced events for all-zero magnitude data are **not** derived by this document.
- **P07 (DOC/OPEN):** `И4`, result output at `ИВА3`, and reading of `ТЗн2См`. State at this output point is still OPEN.

This is a **logical sequence**, not a numerical waveform. The source-supported post-reset state is a **checkpoint**, not an assumption that it persists until `ИВА3`.

## 5. Six cases: separately known reset, source transfers and admission

`ISA_06_D8_H6_OPCODE01_GATE_BOUNDARIES.tsv` carries forward H5's six published input cases *without modifying them*. It adds the two independently evidenced **after-reset `0` states**, leaving the three gates' accepted events, `ТЗн2См` at `ИВА3`, and historical opcode-01 zero-sign **OPEN**. A negative transfer source is not an accepted correction impulse. Even with `(0,0)` after reset, both pulse chronology and carry path are necessary to compute the end state.

D8 reference models M0/M1/M2a/M2b remain **toy hypotheses**, not circuit models. The present stage does not distinguish which model matches the historical hardware. Observed `+0` output of the emulator under D6/D7 is not upgraded to a DOC-MISMATCH.

## 6. Permanent evidence and supersession rules

The H6 tables each have a single role: `...EVIDENCE.tsv` records exact source-scoped assertions and exclusions; `...RESET_PHASE_TRACE.tsv` records phase ordering; `...F71_GATE_LABEL_REVIEW.tsv` separates read glyphs from decoded control values; `...OPCODE01_GATE_BOUNDARIES.tsv` copies H5's upstream transfer selection and adds reset-only states; `...OPEN_DELTA.tsv` tracks H4 blockers without changing old ledgers; `...SOURCE_MANIFEST.tsv` fixes scan bytes. `tools/isa06_d8_h6_reset_decode_audit.py` checks schema, cross-stage compatibility, H2 E022 retraction, no arbitrary gate enable, and that every terminal sign remains OPEN. It can verify original scan hashes if supplied; the default run requires **no** bundled images.

**Evidence grades:** `DOC_SCOPED` (text), `PHOTO_CLEAR_LABEL`/`FIGURE` (label, geometry), `DERIVED_SCOPED` (deduction from multiple direct sources with explicit preconditions), `OPEN` (missing proof). A tool PASS is a consistency result, **not** historical hardware validation. A future reviewer must preserve the raw H1/H2/H3/H4/H5 rows; corrections are recorded as overlays/new stages. H2's retraction of edge **E022** remains active.

## 7. H7 decision gate (do not patch CPU before passing)

1. Independently locate the operation-group controls `П₁, П₂, Ср3` and `П+, П×, Р` in source control schematics or a textual decoder table; map to opcode `01` with printed page/figure and actual connectivity, not visual analogy. In particular test the possibility `C17` operates at `И1` for `01`—do not assume absent.
2. Resolve accepted event semantics, including the polarity of `+1 ЗнСм`, the dash near C18, and temporal relation of `C16/C17` at `И1` and `C18` at `И2`.
3. Reconstruct full sign/carry transitions from the **known reset condition** through `z40`, the first-sign-position carry `z1`, and output `ИВА3`, using F67/F71/F72/F73; compare with the original 1964 microoperation table. Record state values *at every event*, not only final answer.
4. Obtain a blinded independent second reading for disputed figures; otherwise retain explicit confidence limits.
5. Only when a complete independent source-attributed trace uniquely fixes a signed-zero output of `01`, promote that particular case to `STRICT` and consider a **separate** CPU patch with D1–D7 regression suite. Do not silently rewrite D6/D7 OBS.

**Exit verdict H6:** `У«0»См` provides a documented summator reset and a **derived, conditional `(ТЗн1См, ТЗн2См)=(0,0)` immediately after reset**. Visible C16–C18 input labels are recorded with their remaining uncertainty. Admission of those gates for opcode `01`, complete trigger trajectory and final signed-zero code remain **OPEN**. No CPU change.

## 8. Reproduce

From repository root, after installing the additive H6 patch:

```sh
python tools/isa06_d8_h6_reset_decode_audit.py --check --show-boundaries
python tools/isa06_d8_h5_transfer_audit.py --check
python tools/isa06_d8_h4_correction_audit.py --check
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```

Optional hash check: `python tools/isa06_d8_h6_reset_decode_audit.py --check --verify-source /path/containing/kiev0051.png-etc` (pass **directory**). This packet carries no synthetic historic RAM/ROM execution.
