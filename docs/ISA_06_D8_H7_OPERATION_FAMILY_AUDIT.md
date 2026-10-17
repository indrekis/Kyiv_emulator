# ISA-06 D8-H7 — operation-family qualification of F71.C16–C18

**Base:** `b4fc20e` (D8-H6). **Research stage:** additive documents and a consistency checker only. **No** edits to CPU, ROM, existing tests, H1–H6 historical registers, or README. **No new historical sign oracle for arithmetic opcode `01`.**

## Question and result

Can the companion labels at Fig. 71's correction gates be assigned unambiguously to ordinary arithmetic addition? H6 recorded tentative labels near `F71.C16/C18` (`П₁, П₂, Ср3`) and a distinct label near `F71.C17` (`Л+, Л×, Р`), but the corresponding control potentials had not been mapped to the operation decoder.

**New direct-source evidence:** DPS64 **printed p. 147**, subsection *«Логическое сложение (Л+)»*, explicitly reports an `И1` pulse **through `С17` (Fig. 71)** to form `+1 ЗнСм` and set the two summator sign triggers to `1`. That corroborates the **logical** role of `F71.C17`; its visible group is consistent with `Л+`, `Л×`, `Р`. Page 147 describes logical multiplication and `Р` (continued at p.148) as distinct from arithmetic addition, and printed **p. 102, Table 4** lists them on separate instruction rows `14`, `15`, `17`. Fig. 71's `С17` is therefore **no longer simply “unknown function”**: at least one *documented* logical-operation route is identified.

**Crucial limitation:** these sources still do **not** prove the complete electrical **exclusivity** of `F71.C17` for arithmetic opcode `01`, so its event and enable in `01` remain `OPEN`, not zero. Nor do they resolve `F71.C16/C18` qualification: printed **p. 145** explicitly says negative transfers `−Ч1/−Ч2` pass through `С16/С18` in the discussion of ordinary addition; the printed companion groups near these gates remain only *tentatively transcribed*. Do **not** force agreement between label and prose by silently changing a glyph or assuming a decoder. This is an **unresolved source-to-netlist tension**, not a historical `DOC-MISMATCH` in the emulator.

## Source-based reading procedure (preserve for future reviewers)

1. First verify **unmodified original two-page spreads** listed in `ISA_06_D8_H7_SOURCE_MANIFEST.tsv`. For example, `kiev0073.png` contains printed **144 on the left / 145 on the right**, `kiev0074.png` **146 / 147**, `kiev0075.png` **148 / 149**, `kiev0080.png` **158 / 159**. Scan hashes bind claims to the particular source bytes, not to an independent reviewer.
2. On **p.144, Fig.71**, locate *figure-local* `F71.C16/C17/C18`, separately copy **pulse inputs** `−Ч1`, `И1`, `−Ч2`, then copy tentative **potential/group labels**. Do **not** confuse `F71.C17` with the `C17` of Fig.72 or the other diagrams, which renumber gates locally. Note that `С` denotes coincidence (AND) and `Р` separation (OR) in the book's potential logic convention (p.41, Fig.6); pulse threshold/timing is not established by this legend.
3. Read **p.145**, first paragraphs after Fig.72, in context of arithmetic addition on pp.144–145. Record direct prose about `С16/С18` correction and `z40` entering the first sign position and subsequently producing `z1`. Retain H2 `E022` **RETRACTED**. A *path named in prose* is not a complete event/enable truth table.
4. Read **p.147**, *«Логическое сложение (Л+)»*, for the unusually explicit `И1 → С17 → +1 ЗнСм` route for logical addition. Read the adjacent *«Логическое умножение (Л×)»* and *«Равнозначно (Р)»* passages; the label group is corroborative but the book does not write a complete three-operation Boolean decoder equation here. Read **p.148**, *«Точное сравнение (Ср3)»*, which is separate from that logical-operation group. Keep `Ср3` and `Р` distinct.
5. Check **p.102–103, Table 4** rows `01`, `14`, `15`, `16`, `17`: transfer sources by opcode. The ordinary arithmetic `01` selects ±Ч1 at И1, ±Ч2 at И2 (as H5 already established). The table does **not** directly specify `F71.C16/C17/C18` companion potential values.
6. Finally read **p.159**, *«Коммутатор операций»*. It describes production of both individual and combined operation potentials, but does not provide a visually demonstrated wire-level mapping from those control outputs to the three Fig.71 gates in the reviewed material. Treat mnemonic similarity as a **lead for future tracing**, never as decoded hardware.

## Ledger status and machine-state boundary

- `F71.C17` is **DOC_LOGICAL_PATH**: at least `Л+` uses it as explicitly reported on p.147. **It is not certified to be absent during arithmetic `01`.**
- `F71.C16` / `F71.C18` are **TEXT_SUPPORT_PATH** for ordinary addition on p.145. Their per-case companion enable, pulse acceptance, polarity and physical pin mapping are **OPEN**.
- H6's **derived reset-only** `(ТЗн1См,ТЗн2См)=(0,0)` stays valid immediately after effective `У«0»См`. H5's ±Ч1/±Ч2 source selection stays valid. **No later sign-trigger value is inferred.**
- The end-of-operation output sign is taken from `ТЗн2См` on `ИВА3` (DPS64 p.146), but every six-case result stays `OPEN`. `M0/M1/M2a/M2b` remain toy hypotheses, not emulated schematic results.

### Operation-group evidence versus inferred enable

| Gate | Pulse | Supported operation evidence | Opcode `01` admission | Remaining task |
|---|---|---|---|---|
| `F71.C16` | `−Ч1` | Arithmetic addition via C16, p.145; grouped Fig.71 label *not yet decoded* | `OPEN` | Decode `П₁,П₂,Ср3` and identify its actual source net |
| `F71.C17` | `И1` | Logical addition via C17, p.147; group `Л+,Л×,Р` | `OPEN` | Prove/deny its activation in arithmetic 01 via control potential, not assumption |
| `F71.C18` | `−Ч2` | Arithmetic addition via C18, p.145; grouped Fig.71 label *not yet decoded* | `OPEN` | Decode second transfer qualifier and timing |

The six signed-zero/cancellation cases in `ISA_06_D8_H7_OPCODE01_BOUNDARIES.tsv` preserve these unknowns. A status of `OPEN` is **not** a failure; all output signs are intentionally undetermined.

## Reproducibility, contradiction handling and next gate (H8)

New files: operation-family evidence ledger, three-gate table, six-case matrix, delta from H4's twelve open questions, source-hash manifest, and `tools/isa06_d8_h7_operation_family_audit.py`. The checker validates schema, case consistency with H6, the inherited H2 E022 retraction, and prohibitions against turning the new `Л+→C17` source finding into an arithmetic `01` sign oracle. Optional `--verify-source DIR` verifies original scan SHA-256. It checks **documentation integrity**, not hardware timing or correctness of historical transcriptions.

**H8 decision:** obtain a *traceable* operation-commutator net/equation linking opcode `01` and the printed Fig.71 group potentials, then independently determine whether `F71.C17` is excluded for `01` and when `C16/C18` admit the negative transfer impulses. Correlate those events with the reset condition, `z40`, `z1`, and `ИВА3`. Require a second reader for unresolved glyphs. Do not modify the CPU, relabel old H1 edges, restore E022, or promote D6/D7 observations to `STRICT` without a complete source-supported transition sequence.

## Run

From repository root after installing this additive patch:

```sh
python tools/isa06_d8_h7_operation_family_audit.py --check --show-gates
python tools/isa06_d8_h6_reset_decode_audit.py --check
python tools/isa06_d8_h5_transfer_audit.py --check
python tools/isa06_d8_h4_correction_audit.py --check
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```
