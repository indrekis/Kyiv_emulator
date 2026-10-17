# ISA-06 D8-H3 — logic-symbol convention and count-input semantics, with historical provenance

**Target base:** `e3e23bb` (D8-H2 committed). **This is a documentary research stage only.** Add five files; do not edit the emulator, ROM, older evidence/override snapshots, tests, or root README. This stage supersedes the prior claim that no source-defined meaning for symbols **С / Р** had been authenticated. It does not undo the H2 retraction of H1 edge **E022** and does not establish any arithmetic `01` zero-sign oracle.

## Executive finding (source-based, not conjectural)

**DPS64 printed p. 41, Fig. 6** (*Реализация операций формальной логики*):

1. A **potential coincidence** device `С` implements the Boolean operation **AND**, `X = X1 ∧ X2` for the two-input circuit drawn. A **potential separation** device `Р` implements **OR**, `X = X1 ∨ X2`. The prose expressly says that a high level represents logic **1** for these chosen potential levels. These are contemporary definitions from the authors, not modern gate-label guesses.
2. The same p. 41, Fig. 6в, represents an **impulse-potential** network with coincidence elements feeding a combining separation element. The book's explicit formula is an OR of AND terms, combining potential signals `X_i` with pulse signals `x_i`. **Footnote on p. 41:** uppercase notation for potential signals, lowercase for pulse signals *in this chapter*.
3. **DPS64 printed p. 43, Fig. 7** shows serial coincidence (combining potentials with pulses) and cautions against treating the entire historic impulse/potential circuit as a modern instantaneous Boolean evaluator: a static truth function does not define pulse width, order, or latch action.

These discoveries **partially resolve H1-007 / H2 R009**. They justify a gate-family meaning in the same book, while still requiring verification that *each* numbered `F71.Cnn`, `F72.Cnn`, `F67.Cnn`, etc. has the exact assumed fan-in and pulse-gating function. They DO NOT convert the H1 `DIAGRAM_GROUP` edges into proven physical wires. Figure-local numbering remains compulsory (`F71.C16` ≠ `F72.C16`). Our historical prose citations here refer to the **printed** pages, not PDF viewer page indices.

## Trigger and count-input evidence (restricted application)

**DPS64 printed pp. 49–52, Figs. 12–14:** The authors explicitly describe pulse-conditioned trigger state changes. Fig. 13 distinguishes `0` and `1` set pins and shows gates selected by a previous register bit. On printed **p. 51**, the register-shift example routes a pulse through one of two gates to set the next stage to 0 or 1, conditional on the predecessor state. On printed **p. 52, Fig. 14**, the dedicated binary **counter** works as follows:

| Counter stage **before** a single accepted count pulse | Coincidence path in Fig. 14 | Stage **after** | Carry pulse to next stage | Source classification |
|---|---|---|---|---|
| `0` | `C1` | `1` | no | **DOC** p. 52 |
| `1` | `C2` | `0` | yes | **DOC** p. 52 |

Thus for that explicitly described counter stage a controlled, accepted incoming event gives `new_bit = 1−old_bit`, `carry = old_bit` (**DERIVED**, not a generic flip-flop electrical specification). This is *not* proof that either sign trigger in **Fig. 71** has the exact same wiring, reset state or edge convention. It is possible to use count inputs for toggling, but the sign-trigger circuit must be traced explicitly before claiming a transition.

**DPS64 printed p. 145, Fig. 71** independently says negative transfer pulses `−Ч1` / `−Ч2` through **C16 / C18** form a correction `+1 ЗнСм` reaching count inputs of **both** sign triggers `ТЗн1См` and `ТЗн2См`. The architecture requires a state-/event-based model, not `res < 0`. Yet the actual states when the correction and carry signals arrive, plus their event ordering, remain **OPEN**.

## Evidence table, sources, and revisions

New files:

- `docs/ISA_06_D8_H3_CONVENTION_EVIDENCE.tsv`: 20 scoped claims, with `DIRECT_TEXT`, `DERIVED_FROM_TEXT`, `LIMITED_INFERENCE` or `OPEN`; assertions explicitly distinguish `CONFIRMED_SCOPED` from historical arithmetic oracles.
- `docs/ISA_06_D8_H3_DECISION_OVERLAY.tsv`: six precise updates to H1/H2 unresolved questions. The **H2 retraction of E022 is unchanged**. The H1 and H2 TSVs remain immutable snapshots.
- `docs/ISA_06_D8_H3_SOURCE_MANIFEST.tsv`: original 3510×2550 spreads, per-entry SHA-256 from the source ZIP/PDF set, page mappings and localators. New scans `kiev0021.png`, `kiev0022.png`, `kiev0025.png`, `kiev0026.png`, `kiev0027.png` are NOT committed. The already authenticated `kiev0073.png`/`kiev0074.png` are included for continuity.
- `tools/isa06_d8_h3_convention_audit.py`: deterministic schema/provenance/transition-table checker, not a machine-model validation.
- This note, containing the scope of the original interpretation and the instructions for rechecking it independently.

**Provenance:** `DPS64` denotes Dashevsky–Pogrebinsky–Shkabara, *Вычислительная машина «Киев» (Проектирование и эксплуатация)* (1964). Original scanned images are the authority. Scan `kiev0021.png` contains **printed p. 40 on the left, 41 on the right**; `kiev0027.png` contains printed 52 on the left and 53 on the right. The scan hash record is a *content-integrity fingerprint*, not an independent second-reader certificate. The previous review and this H3 reading share the same research assistant; neither is an independent expert sign-off.

## Status after H3 — **do not overpromote**

| Question | Before | After H3 | Can infer historical arithmetic `01` zero sign? |
|---|---|---|---|
| Generic `С` and `Р` logical functions | OPEN (H1/H2) | Direct book definition: **AND and OR** for described potentials | **No** |
| Pulse-potential combination | OPEN | Book's AND-of-potential+impulse then OR, with case notation | **No** |
| A binary count stage transition | OPEN | Documented **Fig. 14 counter** toggles on accepted pulse; carry from prior `1` | **No** |
| F71 summator sign-trigger `count` transition | OPEN | Known correction pulse interface; actual gate wiring and state **OPEN** | **No** |
| Direction of H1 E022 | Retracted by H2 | Remains **RETRACTED**; not repaired by generic gate definition | **No** |
| `+0+−0`, `−0++0` and other exact-zero sums | OPEN | **OPEN** | **No** |

### Why the new gate legend does not prove a result

A gate-level simulation of a pulse-potential machine requires source-specific **pin connectivity, current trigger state, arrival order, pulse acceptance and carry generation**, not just an AND/OR legend. The `С`/`Р` symbols are necessary evidence and now qualified, but the 50 H1 `DIAGRAM_GROUP` records and the 16 H1 open items still require electrical tracing. One cannot use the desired behaviour of the fourth historical RAM test as a prior for the sign-trigger truth table, or treat typed `ROM.txt` as an independent hardware ground truth.

### Next bounded stage (D8-H4)

1. Independently transcribe exact fan-in, *pulse versus potential*, and output for `F71.C16`, `F71.C17`, `F71.C18` and the sign correction group, using printed **p. 144 Fig. 71** and p. 145 prose. Avoid using H1 line groups as already proved.
2. Document two paths separately: negative pulse `−Ч1/−Ч2 → +1ЗнСм` and `z40 → first sign position → generated z1`. **E022 stays excluded.**
3. Search for explicit reset/initialization of `ТЗн1См` and `ТЗн2См` (p. 144 and table 4 pp. 102–103); record every still-unreadable junction as OPEN rather than choosing a modern synchronous `T` flip-flop model.
4. Only after event-ordering proof, build a **symbolic state-transition model** for six exact-zero sums; reconcile independently against the GY62 printed p. 13 documented `02` equal-subtraction `−0`, not by automatically copying subtraction rule to addition.
5. If a historical `01` sign oracle becomes defensible, introduce separate STRICT tests and CPU modifications **in a later independent stage** with full D1–D7 regressions. No CPU edits now.

## Running and interpreting the checker

From repository root: `python tools/isa06_d8_h3_convention_audit.py --check`; optionally `--show-truth` for explicitly scoped 2-input Boolean and Fig. 14 counter tables. Also rerun `python tools/isa06_d8_h2_review_audit.py --check` and `python tools/isa06_d8_sign_models.py --check`. `CONVENTION-CHECK PASS` means valid records + correct miniature logic examples, **not** historic signed-zero ISA verification.
