# ISA-06 D8-H9 — decoder-potential vocabulary, bounded search, and stop/go decision

**Base:** `2010cd0` (D8-H8). **Read-only source research.** New files only; no CPU, ROM, former docs, tests, or prior audit edits. All six opcode-`01` exact-zero results remain **OPEN**. This phase deliberately avoids reproducing an unsupported gate-enable truth table.

## Research question and result

The missing H8 link is a **specific electrical equation/wire** from a decoded operation or combined control potential to the *other* input of F71.C16 / C17 / C18. We re-examined the operation names and signal classes at DPS64 (Dashevsky–Pogrebinsky–Shkabara, 1964), printed **pp. 144–149 and 158–165**, together with AU transfer-control table 4 on pp. 102–103, to distinguish documented potential types from speculative terminal identification.

**Positive finding:** p.159 describes **three different kinds** of operation potentials: (i) individual operation selectors; (ii) negations of some operation selectors; (iii) combined selectors representing multiple operations. It further states that **fifteen arithmetic operations are handled uniformly in the **control unit (УУ)** and encoded with one common potential**, typographically printed **`«О»`**, with a reference to `Т₅АОп (Т₄₁РК)`. The glyph should not be silently substituted with the arithmetic numeral zero, the hardwired `+0`, or an identified gate input. Opcode `01` is described as ordinary addition at p.144, and so it belongs to the arithmetic-device operation family; the presence of this *УУ control-unit classification* does **not** identify the second input of any of F71.C16–C18.

**Control-unit boundary:** `УУ` in the p.159 statement means the control unit, whereas the Fig.71 sign triggers belong to the arithmetic unit (`АУ`). The shared control potential is **not** a demonstrated physical input to the Fig.71 gates.

**Additional disambiguation:** p.148 names **`Ср3`** as the exact-comparison operation and describes its control procedure. That is a documented name; it is **not** independent proof that a similarly looking glyph next to Fig.71 is electrically identical to the more generic commutator potential `Ср` on p.159. H6/H7's `П₁, П₂, Ср3` reading remains **tentative**, and H2's `E022` retraction remains binding.

**Stop/go finding:** the reviewed original-source spans substantiate decoder *architecture and vocabulary*, not a traceable commutator-output → Fig.71 companion-terminal map. Do **not** invent those wires, infer `C17=0`, infer unconditional acceptance at C16/C18, or generate a historical sign for `−0 + +0`. A continued loop of prose restating these same pages without an independent schematic or new source cannot close this blocker.

## Reproducible source-reading procedure

All page numbers are **printed book numbers**, not PDF page indices. The original scans are the bytes in `ISA_06_D8_H9_SOURCE_MANIFEST.tsv` (eight spread images, SHA-256). Enlargements and transcription notes are *reading aids*, not separate original evidence.

1. Cross-check p.144 Fig.71 **gate-local labels** with p.145 direct narrative: for ordinary addition `−Ч1` and `−Ч2` enter the sign-correction group through C16/C18. Record **pulse path** separately from **operation-family qualifier** and **accepted count event**. This narrative does not fix all additional AND inputs for every zero case.
2. Read p.147 for `Л+`'s `И1 → C17` route; do not infer that an arithmetic operation is impossible on that gate without the group decoder's actual Boolean membership.
3. Read p.148 exact comparison `Ср3` separately from p.159 `Ср` selector; treat similar lettering as a *candidate alias requiring physical confirmation*, not a connection.
4. At pp.158–159, separately transcribe the **first five opcode triggers**, individual outputs, negated outputs, combined potentials, and shared AU `«О»` control. Record explicitly that a **common potential** is not by itself an equation for Fig.71.
5. Cross-check pp.160–165 timing diagrams and table 6 for control architecture only. Their negative finding is **limited to these reviewed pages**. They cannot justify an absolute claim that a schematic exists nowhere, or replace the missing wire diagram.
6. Reconcile with pp.102–103 table 4: the sign of the operand selects `±Ч1/±Ч2`. These signals are *necessary source-pulse opportunities*; downstream AND admissions and the final sign-trigger state remain independent unknowns.
7. Run H9 and inherited H1–H8 auditors; retain all six `OPEN` case outcomes and H2 `E022=RETRACTED`. An audit PASS demonstrates ledger invariants, **not correctness of the hardware**.

## Evidence grades, future-proof claims, and no-go rule

- `DOC` — a bounded statement directly supported by the printed page (e.g. the existence of combined potentials).
- `DOC_SCOPED` — a specified flow stated for an operation family, without its full electrical preconditions.
- `DERIVED_LIMITED` — restricted cross-page inference (e.g. opcode `01` is an AU addition operation).
- `OPEN` — physically unproven connection, event, polarity, or clock-dependent result.
- `NEGATIVE_SCOPE` — **only the checked pages** lack the required complete net; not proof of absence in other archives.

For each future candidate connection require (a) an original source or independently recorded waveform; (b) figure-local **terminal and name** verification, without conflating C17 across figures; (c) active level/polarity and exact opcode `01` Boolean group membership; (d) timing relative to `И1/И2`, `z40/z1`, reset and `ИВА3`; (e) a complete stable 41-bit result prediction. The `PROOF_OBLIGATIONS.tsv` preserves these as separately testable blockers.

**Decision gate:** this documentary pass is **NO-GO** for a new opcode-01 historical `STRICT` assertion or CPU patch. The next productive material is the original **commutator/diode matrix**, a wiring drawing, independent contemporaneous technical report explicitly naming the operation groups, or an authenticated hardware/diagnostic trace. Until such evidence appears, use an alternative research branch (bounded historical program integration with distinct `OBS` and `POLICY`), and do not repeatedly convert the same unknown into nominal progress.

### Where to seek additional evidence

Prioritize archival design documentation of the Kyiv **operation selector / `коммутатор операций` / `дешифратор операций`**, working drawings for the AU sign block, or maintenance material listing control potentials. Public summaries of Kyiv's architecture (without drawings) and a biography about MESM are background context, **not** electrical oracles. If an artifact arrives, hash the *unaltered original*, preserve figure/page and provenance, and add an overlay rather than rewriting H1–H8 evidence history.

## Constrained six-case status

For `+0 + +0`, `+0 + −0`, `−0 + +0`, `−0 + −0`, `+5 + −5` and `−5 + +5`: the published input transfer selection and post-reset sign-trigger pair `(0,0)` remain qualified by earlier stages. Actual C16/C17/C18 admitted events, `z40/z1` case traces, `ТЗн2См` at `ИВА3` and historical output sign remain **OPEN**. H9 deliberately contains **no speculative gate-level executable hardware model**.

## Verification

```sh
python tools/isa06_d8_h9_potential_audit.py --check --show-obligations
python tools/isa06_d8_h8_commutator_audit.py --check
python tools/isa06_d8_h7_operation_family_audit.py --check
python tools/isa06_d8_h6_reset_decode_audit.py --check
python tools/isa06_d8_h5_transfer_audit.py --check
python tools/isa06_d8_h4_correction_audit.py --check
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```

Optional: H9 `--verify-source DIR` reads original unaltered `kiev*.png` spreads from `DIR` (all eight are required) and verifies SHA-256. **A checker PASS cannot settle the sign of the historical zero.**
