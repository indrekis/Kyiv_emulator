# ISA-06 D8-H5 — opcode 01 transfer-pulse decode and timing constraints

**Working base:** actual upstream `e6ce079` (D8-H4). This is an **additive documentary qualification**. No edits to CPU, ROM, H1–H4 tables, existing tests or the root README. All octal machine addresses below are octal. The sign of an exact-zero result of `01` is still **OPEN**.

## 1. Narrow problem and approach

D8-H4 identified three Fig. 71 coincidence gates, `F71.C16`, `F71.C17`, `F71.C18`, converging on the `+1 ЗнСм` correction output. H4 explicitly left the companion enables `g16/g18`, `C17` and pulse chronology unknown. Here we **do not decode those enables by analogy**. We identify instead the *upstream* operation-specific production of `+Ч1`, `−Ч1`, `+Ч2`, `−Ч2` from the original **Table 4, operation 01**, compare the order to Fig. 62 and to the arithmetic-unit narrative, and state exactly what remains missing between that decode and the sign-register count inputs.

Method: inspect the native-resolution two-page PNG spreads `kiev0051.png`, `kiev0052.png`, `kiev0073.png` (source hashes in `SOURCE_MANIFEST.tsv`). Read **printed** p.100 Fig.62 and prose, p.101 addition narrative, pp.102–103 Table 4, p.144 Fig.71, p.145 Fig.72 and transfer/carry text **as separate evidence**. Record the printed mnemonics before translating them to logical formulas; use previously documented Fig. 6 `С=AND`, `Р=OR` convention only within its stated limits. Trace Table 4 horizontally across the page boundary: its row `01` begins on printed p.102 and continues on p.103. Do not substitute the similarly named signals in other operations' rows.

## 2. Direct documentary evidence

- **DPS64 printed p.101 (one-tact addition narrative):** `И1` transfers the first number in direct or inverse code depending on its sign, and `И2` does the same for the second. The original text explicitly gives `+Ч1` for sign `0` and `−Ч1` for sign `1`, likewise `+Ч2` and `−Ч2`. At `И2` the modulo-two sum is formed; delayed `±Ч3` signals initiate the carry phase.
- **DPS64 p.102, Table 4 row `01`:** the `+Ч1` column reads `И1 ∧ «0»Зн1`; `−Ч1` reads `И1 ∧ «1»Зн1`; `+Ч2` reads `И2 ∧ «0»Зн2`. **P.103**, continuation of the same row, `−Ч2` reads `И2 ∧ «1»Зн2`; the `±Ч3` columns use delayed `±Ч2*`. The little star refers to a **1.6 microsecond shift**, not to a Boolean complement. Thus the four-way *transfer selection* for opcode `01` is documentarily determined, assuming the signs have been correctly latched as described.
- **DPS64 printed p.100, Fig.62 and its text**, and **p.101**: `И1` occurs after first-code preparation, `И2` after second-code preparation, `И3` follows `И2` by 1.6 µs, and `И4` terminates or initiates overflow handling. Source p.100 gives a 6 µs interval from `И2` to `И4` and 7.6 µs total one-tact operation after both numbers accepted; these are **published nominal relations**, not a recovered per-gate pulse-width or actual trigger toggle count.
- **DPS64 printed p.144 Fig.71, p.145 prose**: `−Ч1` is shown at the `C16` input and `−Ч2` at `C18`; negative transfer pulses through these gates form correction `+1 ЗнСм`, delivered to the counting inputs of **both** sign triggers. The **other** input of each gate has a separate group label (tentatively `П1, П2, Ср3` in H4); the drawing does NOT establish a complete operation-01 enable decoding. `C17` also enters the combining `Р`, with its own `И1` and another operation-group label; its enabled state on opcode `01` is **not proven**.
- **DPS64 p.145**: `z40` is fed to the first sign position; the carry emerging from that position produces cyclic `z1`. H2 **retracted H1 E022** as a directed `z1 -> ТЗн2См` edge. This packet does not restore it. The sign finally issued at `ИВА3` comes from `ТЗн2См` (p.146), after intermediary events that are not yet fully decoded.

## 3. Typed symbolic reconstruction (NOT a gate-level netlist)

Let `s1,s2 ∈ {0,1}` be **already latched sign codes** (`0` positive, `1` negative), `i1,i2` occurrences of the respective transfer pulses, and `n1,n2` the *selected negative transfer pulse occurrence* under opcode `01`.

```
+Ч1 = И1 AND (s1=0)          −Ч1 = И1 AND (s1=1)
+Ч2 = И2 AND (s2=0)          −Ч2 = И2 AND (s2=1)
+Ч3 = delayed(+Ч2, 1.6 µs)   −Ч3 = delayed(−Ч2, 1.6 µs)
```

Here `AND` means **logical qualification**, not instantaneous electrical voltage addition; `delayed` is documentary timing notation, not a measured transfer function. The above applies to **operation 01**, not all opcodes. In particular, the labels at the bottom of Fig.71 are not established merely by the fact that Table 4 uses `И1`/`И2`.

In the H4 fan-in terminology, the unresolved downstream model remains:

```
C16 = (−Ч1) AND g16       [g16 = OPEN, diagram companion input]
C17 = u17                 [u17 = OPEN, diagram and operation decode]
C18 = (−Ч2) AND g18       [g18 = OPEN, diagram companion input]
+1 ЗнСм <- OR(C16,C17,C18) [symbolic *event pathway*, NOT pulse count]
```

Because `И1` and `И2` are sequential (Fig.62), their **nominal transfer windows** are distinguished; overlap of pulses as *seen at the correction port*, actual gate propagation, input polarity, C17 events, and downstream count-edge acceptance remain unknown. **Do not conclude** that two negative operands cause exactly two correction trigger toggles. The marker `+1` in `+1 ЗнСм` is the original name, not proof of an active-high electrical edge.

## 4. Six-case table and counterfactual controls

`ISA_06_D8_H5_OPCODE01_TRANSFER_MATRIX.tsv` enumerates the six existing D6/D7/H4 source pairs and the **selected first/second transfer pathways** (one per `И1` and `И2` for the latched sign), the two negative pulse presences, and explicit `OPEN` entries for `g16`, `g18`, `C17`, terminal `ТЗн2См`. `+5,−5` and `−5,+5` are cancellation examples; the **magnitude does not change the sign-pulse selection** for the same input signs. This matrix is a **documented upstream decode**, not a simulation of the historical zero sum.

Counterfactual gate example: a `−Ч1` source can be asserted in the table while its `C16` correction contribution is absent if `g16=0`; conversely a `C17` event could contribute even when neither negative transfer source is present. Both are **possibilities**, not descriptions of the real opcode-01 microprogram. A `CORRECTION-PULSE COUNT` or final sign inferred from just `s1,s2` is therefore unsupported.

## 5. Chronology with evidence grades

| Order | Stage | Primary support | What is **not** deduced |
|---|---|---|---|
| 0 | first operand fetch, its sign latched in `ТЗн1` | DPS64 pp.100–101,144 | instantaneous analog reset levels |
| 1 | `И1`: first transfer; `±Ч1` selected by `Зн1` | pp.101–102 Table 4, Fig.62 | C16 enable or C17 assertion |
| 2 | second operand fetch, its sign latched in `ТЗн2` | pp.100–101,144 | initial states of `ТЗн1См`,`ТЗн2См` |
| 3 | `И2`: second transfer; `±Ч2` selected by `Зн2`, modulo-two sum stage | pp.100–103 | C18 enable, accepted sign count pulse |
| 4 | `И3`: delayed `±Ч3` initiate carries | pp.100–103,145 | exact `z40`/`z1` events for each zero case |
| 5 | `И4`: completion/overflow decision, later result output | pp.100–103,145–146 | sign sampled at an independently established edge |

The positions of the correction events relative to the sign-register initialization, `z40` propagation, cyclic `z1`, and `ИВА3` cannot be ordered sufficiently to compute the sign. This is an **explicit D8-H5 stop condition**.

## 6. Non-retroactive evidence, remaining gates, and next steps

New structured files: `..._TRANSFER_EVIDENCE.tsv` (claim + source + grade), `..._OPCODE01_TRANSFER_MATRIX.tsv` (six input-sign cases), `..._OPEN_DELTA.tsv` (H4 blockers narrowed but **not closed**), and `..._SOURCE_MANIFEST.tsv` (hashes of exact page spreads). Previous H1–H4 remains untouched. New checker verifies table shape, trace compatibility, source hashes optionally, H2 `E022` retraction, and preserves the declared `OPEN` status for every terminal sign. It checks **consistency**, not historical microcircuit functionality.

For H6, examine the operation-decode generation of the figure-local control group on `C16/C18` and the group adjacent to `C17`, tracing any printed `П1,П2,Ср3` / `П+,П×,Р` (labels provisional) back to the operation-control circuits; do not equate names seen at another figure without a documented interconnect. Independently reconstruct *initialization* of both sign-triggers and the edge semantics and ordering at their counting ports. Use high-resolution full spreads; require a second unprimed reader for any newly asserted ambiguous graphical connectivity. Only a complete source-attributed state trace through `ИВА3` can promote any `01` signed-zero case to historical `STRICT` or justify a CPU change.

**D8-H5 exit:** verified operation-01 upstream transfer selection and published timing constraints, **not** an established C16/C17/C18 admission truth table, not physical pulse count, not terminal sign, not an end-to-end RAM-test pass.

## 7. Reproduction

From repository root after applying H5:

```
python tools/isa06_d8_h5_transfer_audit.py --check --show-matrix
python tools/isa06_d8_h4_correction_audit.py --check
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```

Optional source verification (not bundled in repository): `python tools/isa06_d8_h5_transfer_audit.py --check --verify-source /path/to/directory/with/kiev0051.png/kiev0052.png/kiev0073.png` (supply the directory, not a file). Hashes certify exactly which scans were consulted, not correctness of our reading.
