# ISA-06 D8-H8 — operation commutator versus Fig. 71 sign-gate admission

**Base:** `f94e552` (D8-H7). **Source-limited investigation, NOT a decoded electrical netlist or an ISA fix.** This patch is **additive**: no CPU, ROM, pre-existing test or D8–H7 register is edited. The six opcode `01` zero-sum signs remain **OPEN**.

## Research question and outcome

**Question:** Can the *operation commutator* described by Dashevsky–Pogrebinsky–Shkabara (1964), printed p.159, independently supply the values on the companion potential inputs of Fig.71 gates `F71.C16`, `F71.C17`, `F71.C18` for octal opcode `01`?

**Result:** The *existence and architecture* of the decoding are directly documented. Printed p.158 says that the first five flip-flops of the instruction register store the opcode and drive a decoder. Printed p.159 describes a commutator of decoding circuits which produces individual **and combined** operation potentials according to those five flip-flops. However, the inspected Fig.71 and pp.158–165 do **not** provide a traceable one-to-one wire, terminal map or Boolean term connecting **one named output** of that decoder to **the companion terminal** of each of `C16–C18`. Thus the local admission of those gates, even for `01`, is **OPEN**. A decoder's existence is **not** a proof of a particular decoded gate's state.

This stage adds a new positive source finding (the instruction-decode and control architecture), but does **not** falsely close the prior blocking unknown. This is an evidence gap, not an emulator DOC-MISMATCH.

## Original-source reading procedure (preserve as reproducible protocol)

Use the original two-page spread PNGs and verify bytes against `ISA_06_D8_H8_SOURCE_MANIFEST.tsv`. Page numbers below are the **printed** book pages, not PDF indices, file indices or OCR page numbers.

1. **p.158, original `kiev0080.png` left:** first five command-register triggers hold the operation code; their outputs lead to a *дешифратор операций*. The statement refers to a register and decoder, not directly to the AU sign triggers. Identify the *first five* specifically rather than extrapolating all 41 command-register bits.
2. **p.159, same spread right:** *«Коммутатор операций»* consists of decoding schemes selected by the **five** opcode triggers. It generates individual, negated and **combined operation potentials**. Record these three output classes separately. The book lists numerous operation names and combined examples. Similarity of an abbreviation in the commutator text and a printed Fig.71 gate input does **not** establish an electrical link. Also note the statement that **fifteen AU operations** are encoded with one common potential at the AU-control level; do not extrapolate this potential to `C16–C18`.
3. **pp.160–161, `kiev0081.png`:** Fig.75 is a timing diagram for the central control system. Its pulses `ИВА1–ИВА4` and other start/read/write intervals refer to the global control path; they do not directly depict the Fig.71 correction-gate enables. Avoid interpreting a whole machine cycle as the AU `И1 → И2` interval.
4. **pp.162–163, `kiev0082.png`:** Fig.76/77 and surrounding prose show where central-control signals are formed and routed to memory/AU; some routes depend on operation type or grouped addressing. This corroborates that not every operation shares identical control timing. These drawings are *not* a circuit netlist of the commutator-to-`F71.C16/C17/C18` wiring.
5. **pp.164–165, `kiev0083.png`, Table 6:** identify the distinct columns for arithmetic, `УП`, `УПП`, comparisons, group operations and the emitted `ИВА`/reset/control signals. Footnotes condition many entries on group signs and mode. This is an **operation-to-control schedule**, not a direct Boolean equation for the second input of a gate in Fig.71. Do not silently translate a dash in the table to `C17=0`.
6. **p.144, `kiev0073.png` left, Fig.71:** figure-local inputs of `C16` (`−Ч1`), `C17` (`И1`) and `C18` (`−Ч2`); the grouped companion labels still require a verified net name/connection. H6 transcription is tentative (especially `П₁, П₂, Ср3`); H7's documented logical `Л+` C17 path is independent of that tentative glyph reading.
7. **p.145, same spread right:** text explicitly describes the `−Ч1/−Ч2` correction path through `C16/C18` when explaining arithmetic addition, and the `z40` → first sign place → `z1` relation. **H2 E022 remains RETRACTED**; do not reinterpret it as a known `z1 → ТЗн2См` net.
8. **p.147, `kiev0074.png` right; p.148, `kiev0075.png` left:** logical addition `Л+` explicitly uses `И1 → C17` and `+1 ЗнСм` (p.147); exact comparison `Ср3` has its own stated control procedure (p.148). Presence of a C17 route for `Л+` **does not prove electrical exclusivity**, nor whether its group could accidentally or deliberately overlap `01`.
9. **Review H6/H7 matrices** after reading the physical sources. Only **published** transfer selection (`±Ч1/±Ч2`), the reset checkpoint `(0,0)`, and the explicitly documented logical route are retained. All three opcode-01 gate admissions, all accepted count pulses, `ТЗн2См` at `ИВА3`, and the historical sign for every six-case sample remain `OPEN`.

The figure-local scope matters: `F71.C17` is **not** the `C17` on Fig.72 or Fig.76; repeated Cyrillic gate letters and numerical subscripts in different figures do not establish net identity.

## Formal missing link

Let `b4..b0` denote the five documented command-register opcode triggers, `D_k(b4..b0)` an *individual* decoder output for operation `k`, and `G_j` any *combined* operation group potential. These are **notation introduced for analysis**, not printed signal equations. We would require a sourced mapping such as

```
(opcode bits) → (named decoder term or combined G_j) →
    (physically verified Fig.71 companion terminal) →
    (C16/C17/C18 AND admission + pulse chronology) →
    (+1 ЗнСм count input) → (z40, z1 interactions) →
    (ТЗн2См sampled by ИВА3)
```

Verified from historical sources: **the first arrow's existence**, NOT the Boolean truth table of a particular term and NOT the second arrow's electrical connection. For opcode `01`, `D_01=1` would be a property of an **individual** ideal decoder definition, but a *combined* potential's value cannot be deduced without its constituent set and polarity. Do not use this analytical notation to set `C16_en=1`, `C17_en=0`, or `C18_en=1`.

### Current gate-boundary table

| F71 element | Directly evidenced | New commutator evidence | Still OPEN |
|---|---|---|---|
| C16 | negative first-transfer route p.145 | p.159 confirms *classes* of operation potentials | which group drives companion terminal; value for `01`, accepted event |
| C17 | `Л+` impulse through C17 p.147 | individual / combined outputs could have different scopes | physical exclusivity against opcode `01`, admitted event |
| C18 | negative second-transfer route p.145 | group-decoder architecture p.159 | companion group net and its `01` value; timing/polarity |

**Controlled counterexample:** even if a decoder has a unique asserted individual output for `01`, a combined `G_add` containing `01` and a combined `G_logic` excluding it can exist simultaneously as different Boolean functions of the same five bits. A group glyph on the Fig.71 drawing is therefore insufficient to decide the gate enable without a documented definition **and wiring**. This illustrates why the missing link is real; it is *not* a claim that either example group exists in Kyiv hardware.

## Provenance and negative findings

`ISA_06_D8_H8_CONTROL_EVIDENCE.tsv` captures 20 bounded positive/negative claims, with a printed page and explicit exclusions. `...COMMUTATOR_INTERFACES.tsv` records six interfaces independently: opcode register, decoder, combined groups and the three F71 gates. `...OPCODE01_BOUNDARIES.tsv` preserves all six prior H7 cases; `...OPEN_DELTA.tsv` tracks all 12 inherited H4 blockers without editing their source records. `...SOURCE_MANIFEST.tsv` provides byte counts and SHA-256 for seven original unmodified scan spreads. It is not a proof that the scan itself represents every historically built revision of the computer.

Audit rules:

- `DOC` proves only what the printed page actually says; `FIGURE_LABEL` proves a glyph or topology only within its figure; `DERIVED_LIMITED` states the preconditions; `OPEN` is not an assumed zero; `NEGATIVE_SCOPE` reports the checked source's limits, not a universal claim of absence in all historical documents.
- **Never** transform absence of a gate on Fig.76/77 or Table 6 into proof of nonactivation. **Never** infer instruction-level signed-zero behavior from the host integer addition, from the toy models M0/M1/M2a/M2b, or from a manufactured test fixture.
- Preserve all source-ledger history: H2's `E022` remains retracted. No old TSV is changed; this new stage is an overlay.
- To close H8 block: obtain the original operation commutator schematic/diode matrix, decode equations, or an unambiguous textual statement that links an operation-group potential to each Fig.71 physical gate. Independently verify disputed glyphs; then trace gates and reset/carry pulse chronology through result issuance. **Only** a unique end-to-end source-supported result permits a future `STRICT` zero-sign assertion and separate candidate CPU patch.

## Reproduce

From the repo root:

```sh
python tools/isa06_d8_h8_commutator_audit.py --check --show-interfaces
python tools/isa06_d8_h7_operation_family_audit.py --check
python tools/isa06_d8_h6_reset_decode_audit.py --check
python tools/isa06_d8_h5_transfer_audit.py --check
python tools/isa06_d8_h4_correction_audit.py --check
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```

Optional: pass `--verify-source DIR` to H8 audit to compare the seven original `kiev*.png` files to the manifest. Tool PASS is a **source-ledger consistency check**, not gate-level hardware verification. No image/OCR derivatives are used as final electrical authority.
