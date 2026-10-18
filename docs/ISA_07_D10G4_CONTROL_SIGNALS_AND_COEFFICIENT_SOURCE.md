# ISA-07 D10-G4 — opcode 20: control signals, coefficient provenance, disposition

**Decision:** retain D10-F2/F3's ideal rational conversion followed by truncation as the emulator's **INFERRED / PROVISIONAL** IO20 value. G4 found **no source-supported, bit-exact replacement**. The most probable *method* remains the shortened-multiplier, shifted-multiplicand family established in G2/G3; its physical coefficient loading and low-bit treatment are **OPEN**. This is a deliberate outcome, not a declaration that the machine truly used ideal truncation.

**Pinned baseline:** `75a401107b03e9fb535d9aaf97b56c85a434293f` (D10-G3, committed, postcommit PASS and pushed). This stage adds read-only research files only: no `src/main.cpp`, no decimal converter, no `IO20` policy, no existing code or gates modified.

## Sources and verification standard

- **DPS64**: Л. Н. Дашевский, С. Б. Погребинский, Е. А. Шкабара, *Электронная вычислительная машина «Киев»* (1964), project `Kiev_1964_scan.pdf`, SHA256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5`.
- **GY62**: В. М. Глушков, Е. Л. Ющенко, *Вычислительная машина «Киев»* (1962), project PDF SHA256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`.
- **All references below use PRINTED pages**. In DPS64, PDF page index (zero based) 43 = pp.86–87; 52 = pp.104–105; 54 = pp.108–109; 59 = pp.118–119; 60 = pp.120–121; 61 = pp.122–123; 62 = pp.124–125. These particular spreads were examined as high-resolution images, not OCR. No independent electrical or numeric hardware trace was available.
- The `TABLE5_SIGNAL_MATRIX.tsv` is a **selected manual reading** of the p.124–125 table, not a transcription of the whole table. `READING_QUALIFIED` means symbol/subscript/condition should be rechecked against a better facsimile before it is ever used as gate logic. The table is NOT machine-parsed by the auditor and cannot independently authenticate its own transcription.

## 1. Control pulses: what Table 5 actually distinguishes

DPS64 p.124, figure 63, is a **common temporal diagram for multi-cycle operations**, not a full IO20 pulse recording. The accompanying explanatory text on p.125 identifies `ИВА₄` as machine control clocking and `ИВА₁` as arithmetic-device control clocking, and notes `ВЗ₁`/`ВЗ₂` as the respective starts of temporary signal sequences. In the table, distinct operation rows are provided for `20` («Ввод чисел») and `21` («Ввод команд»), separate from `10`/`11` multiplication.

Selected *directly readable* cells:

- For both `20` and `21`, `ПЧ₁` and `ПЧ₂` are **dashes**. Do **not** assume the generic two-operand memory read pattern for IO20, and do not interpret a dash as proof that an electrical gate is off in every microcycle.
- Both rows show `У«0»Р₁` associated with `ИВА₁`, an `У«0»См` entry associated with `ИВА₁`, `+Ч₂,+Ч₃` under `ИКЛ`, and `У«1»Р₁` under `ИК`. These are **listed signal conditions**, not assertions about the meaning of `ИКЛ` or the width of `Р₁`.
- The `У«0»Р₂` and `УЭ` cells in row `20` have extra conditional terms involving `НИ₁/НИ₃` and `П_s` relative to row `21`. Some glyphs/subscripts are not perfectly legible. Their exact Boolean expansion remains **READING_QUALIFIED**. In particular, `П_s` has not been proven to mean a decimal *position counter* or coefficient-source selector.
- `ИКОп` in row `21` explicitly refers back to the row `20` entry ("То же"). No unique `IO20` shift count can be extracted from that cell alone.

The general discussion on p.125 says ordinary arithmetic operand acceptance uses `ПЧ₁` and `ПЧ₂`; `20` and `21` instead show dashes there. **This is evidence of a different control entry path**, not the complete 40-bit BCD loop. The shift/no-shift decision cannot be settled by counting figure-63 pulses: the figure gives only the representative common scheme.

## 2. Where did the equivalent codes `Э_s` come from?

- **SOURCE_STRICT_TEXT (DPS64 p.121):** the prose introduces an algorithm *given a set of equivalent codes* (`При наличии набора кодов Э_s ...`), then instructs loading an equivalent into the multiplicand register, conditionally adding it to the adder, shifting, and replacing it for the next decimal position. This **states a logical input dependency**, not a storage technology.
- **SOURCE_STRICT (DPS64 pp.86–87, fig.61):** registers `Р₁`, `Р₂`, adder `См`, and common control apparatus are depicted. The figure **does not show a dedicated `Э_s` ROM, coefficient width, or a table of encoded equivalents**.
- **SOURCE_STRICT (DPS64 pp.105, 121–122):** Kyiv uses shortened multiplication with *shifted multiplicand*, and the decimal conversion description specifically reuses multiplier micro-operations. This favors using the existing arithmetic datapath rather than hypothesizing an unrelated converter.
- **SOURCE_STRICT_CONTEXT (DPS64 p.109):** five additional low bits (`m=5`) of the multiplication adder are chosen in the derivation for `q=2,n=40`. This is **not** evidence for a 45-bit ROM or for coefficient representation of `Э_s`.

**Ranked coefficient-source hypotheses:**

1. **Preferred / INFERRED:** a *set of pre-established equivalents* supplied to the existing multiplier register, with the scale compensated somewhere in the input/accumulation path. This respects p.121's conditional "given the set" formulation without inventing the physical location. The mechanism might use memory, wiring or externally supplied codes; **which one remains OPEN**.
2. **Plausible / OPEN:** coefficients generated by sequential arithmetic from a smaller seed plus decimal scaling. The text neither requires nor excludes this, and no actual generation routine has been established.
3. **Unsupported / DO NOT ASSERT:** a dedicated 45-bit or 80-bit ROM specifically for decimal equivalents. No such hardware was identified in the reviewed figures/pages.

## 3. Reconciling decimal weights and time

DPS64 p.120 unambiguously gives BCD weights `8,4,2,1`, and p.121 gives `Э_(s,1)=10^-s` followed by halving. The **uncompensated** MSB-first interpretation gives one eighth of the true input. Our preferred working normalization is an *8× effective preload*, or an algebraically equivalent compensation at another stage. The scale's physical location and per-digit bit scan direction are not proven by the block diagram or Table 5.

D10-G3's abstract model has ten equivalent loads, 40 BCD tests and either 30 useful shifts or 40 shifts including terminal shifts. In the model, the output is **identical** for both counts because the equivalent is unconditionally reloaded for each digit. DPS64 p.122 states about **270 µs** maximum conversion time; table 2 around p.88–90 lists **264 µs** for the arithmetic-device input interval. Neither figure assigns microsecond/clock costs to all 40 bit operations and load/terminal steps. No justified cycle count can be reverse-solved.

## 4. Competing low-bit behaviors and practical decision

| Candidate | Evidence | Current disposition |
|---|---|---|
| Ideal rational `floor(N·2^40/10^10)` with separate sign | Mathematically exact source input and no documented IO20 round-up | **Retain as existing `PROVISIONAL` emulator policy**, not a bit-level hardware oracle |
| Shifted-multiplicand converter with pre-established coefficient codes | DPS64 pp.105, 121–122; compatible with Fig.61 | **Preferred hardware-method hypothesis**; register precision, preload scaling and coefficient bits OPEN |
| Guarded (hypothetical P=45) coefficients with round-to-nearest on load | p.109 m=5 only for multiplication; D10-G2/G3 counterfactual -1 ULP at 0.625 | **Sensitivity test only**, not an implementation change |
| Naive unscaled `10^-s`, scan 8→4→2→1, then halving | Contradicts p.120 by a factor 8 | **Reject this combination**; not a refutation of printed `Э_s` or other bit orderings |
| Automatic IO20 round-to-nearest (by analogy to multiplication opcode 11) | GY62 pp.10–11 distinguishes rounded multiply | **Do not infer**; no qualifying input-specific instruction found |

**Stop decision:** the reviewed sources do not provide the binary coefficient values, their location/precision, a complete opcode-20 timing trace, or a historical hardware result for nonexact decimals. Accordingly **DO NOT MODIFY `IO20`** at this gate. Record low-bit hardware identity as `OPEN`; use the best-supported shifted-multiplicand architecture as the historical explanation and retain ideal truncation as a predictable emulator policy. Further reconstruction should be evidence-triggered (original controller schematics, punched-input tests, ROM/constant listings, or machine-generated output), rather than inventing a pulse-accurate model from incomplete tables.

## 5. Reproducible evidence gate

- `tools/isa07_d10g4_evidence.py`: manually curated, source-qualified signal subset and exact-arithmetic diagnostics; TSV regenerated from code. It does not infer electronic semantics from terse symbol names.
- `tests/isa/isa07_d10g4_evidence_test.py`: independent `Fraction` oracle, deterministic 1000 random ten-digit inputs plus 14 fixed cases, bit-order/signed-zero-independent magnitude checks, 30-vs-40 shift-model output identity, optional parity with committed D10-G3 code, and negative input cases.
- `tools/isa07_d10g4_audit.py`: Git baseline/pins, absence of edits to existing code/docs, normalized LF SHA for new files, TSV regeneration, source decision markers. No PDF OCR / machine-specific historical word oracle.

**New sources only; user MSYS2 PASS required before committing.** D10-G4 cannot certify that the physical machine's LSB matched any mathematical model.
