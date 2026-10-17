# ISA-06 D8-H4 — `+1 ЗнСм` correction-pulse fan-in and event boundaries

**Base:** `1619bb7` (D8-H3). **Documentary research, NOT an emulator or historical-ISA correction.** This stage adds four documents and a reproducible checker; it changes neither CPU, ROM, previous evidence tables, nor existing tests. H2's retraction of `E022` continues to apply.

## Question and exact scope

Which printed conditions feed the correction pulse `+1 ЗнСм` in Fig. 71, and how much of its *event history* can be inferred without inventing the initial states or switching rules of `ТЗн1См` and `ТЗн2См`? The aim is to separate the visible **C16/C17/C18 -> Р** network from (a) the sign-trigger transfer and (b) `z40 -> first sign digit -> cyclic z1`. Do not conflate all three.

This packet deliberately **does not** solve the terminal sign of `01` for `±0` or opposite equal nonzero operands, does not promote any D6/D7 `OBS` to `STRICT`, and does not endorse a netlist suitable for gate-level simulation.

## Primary evidence and imaging protocol

- Dashevsky–Pogrebinsky–Shkabara, *Вычислительная машина «Киев»* (1964), **printed p. 144, Fig. 71** (left side of original `kiev0073.png`): at bottom-right are separate numbered **C16, C17, C18** feeding a combining **Р** glyph with the labelled output **`+1 ЗнСм`**. The visually legible pulse inputs at C16 and C18 are **`−Ч1`** and **`−Ч2`**. Each also has a *different* accompanying enable input which appears to carry a grouped mnemonic (`П1, П2, Ср3`), but that mnemonic's electrical assertion under opcode `01` has not been established. C17 has a separately labelled input `И1` and another operation-mnemonic group; neither may be silently ignored or assigned a truth value from its appearance alone. A small short dash near the C18-to-Р connection must not be interpreted as a confirmed inverter or polarity control without a source-based legend.
- **Printed p. 145**, first paragraphs (right side of *the same original* `kiev0073.png`): the narrative explicitly says negative number-transfer pulses **`−Ч1` and `−Ч2`**, through **C16** and **C18**, create the **`+1 ЗнСм`** correction signal, delivered to the **count inputs of both summator sign triggers**. This is a **documented functional interface**. It does **not** assert that `C17=0` in opcode `01`, that a given pulse is always admitted, that pulses are of the same sign/polarity, or that two such events necessarily survive OR-combination as two distinct clock edges.
- **Printed p. 144**, prose surrounding Fig. 71: the first number is admitted using `И1`, then the second using `И2`; sign determines whether the value is transferred via `+Ч1/−Ч1` or `+Ч2/−Ч2`. **P. 145** describes a first addition stage modulo two and a subsequent carry stage; separate delayed `±Ч3` pulses are offset 1.6 µs relative to `±Ч2`. This gives broad *ordering*, not a complete pulse waveform/timetable.
- **Printed p. 41, Fig. 6**: explicitly defines `С` as coincidence (AND) and `Р` as separation (OR) for its potential and pulse/potential examples, subject to the limitations already documented in D8-H3. Thus a Boolean **envelope** is possible; actual enabled pulse arrivals, timing and state changes are separate matters.
- **Printed p. 52, Fig. 14**: a dedicated binary counter stage toggles on an accepted count pulse, but there is still no proof that the Fig. 71 sign-trigger count ports use precisely its reset/hold/toggle semantics in every phase.
- **Printed p. 145**: `z40` enters the first sign position; carry *from that sign position* forms cyclic `z1`. **Printed p. 146, Fig. 73**: the output sign at `ИВА3` comes from `ТЗн2См`, after unknown intermediate states.

Source image `kiev0073.png`: original 3510 × 2550 two-page spread, left p.144 and right p.145, **SHA-256 `60d672ceb4eac0fa6079b13817b05a80224e51d08ff5b9908f0919fb5c794773`**, pinned in D8/H3 source manifests. The broad locator for the correction group is `x=1180..1740,y=1000..1610` **on the original spread**; p.145 relevant prose on the right has `x=1780..3400,y=0..600` and `y≈1400..2090`. These are deliberately broad locators, not pixel-accurate pin boxes. Use full-size images; do not infer source fidelity from derived enlarged crops. Scan hashes certify identity, not accuracy of transcription.

## Fan-in transcription and epistemic types

`docs/ISA_06_D8_H4_CORRECTION_GATES.tsv` contains five figure-local records: `F71.C16`, `F71.C17`, `F71.C18`, `F71.P_CORR` (H1's *editorial alias*, not a printed gate number), and the count-output interface. The columns separate a **visible connection** from **source prose** and **unverified gate conditions**. The `F71.P_CORR` record describes visually drawn combination of all three C outputs; generic `С`/`Р` functions from p.41 are the justification for a *symbolic envelope*, not a validated physical circuit or its timing.

Let `n1` denote **occurrence of the printed `−Ч1` transfer pulse**, `n2` the similarly qualified `−Ч2` pulse; let `g16`, `g18` stand for **unverified, contemporaneous enables** on the companion C inputs. Let `u17` be the entirely unqualified contribution from C17. Then only as an idealized pulse/potential abstraction:

```
C16_event = n1 AND g16                  [conditional abstraction]
C18_event = n2 AND g18                  [conditional abstraction]
P_correction_event = OR(C16_event, C17_event, C18_event)
```

This is **NOT an equation for the electrical pulse waveform**, and especially not a proof that `C17_event` is absent or that a correction count is simply the number of negative operands. The sign of `+1 ЗнСм` in its printed name is an operation label, **not an independently measured active-high pulse polarity**. The small printed `−` near the C18 leg is logged as an **OPEN graphic/polarity issue**, not a NOT operator. Without verified timing, `OR` of two events cannot tell whether the downstream trigger sees one or two countable impulses.

The `--show-envelope` tool uses the **explicit hypothetical assumptions** `C17_event=0`, `−Ч1/−Ч2` separate in time, and each accompanying gate enable independently 0/1. It prints a **range** of possible *C16/C18* admitted events. This range does not constrain the actual machine beyond the narrow model's assumptions. The machine's correction count, sign-trigger states, `z1` output and sign bit at `ИВА3` all remain **OPEN**.

## Six exact-zero cases (D8/D6/D7 regression of the *question*, not predictions)

| `01` input pair | `−Ч1` if enabled | `−Ч2` if enabled | C16/C18-only envelope with C17 suppressed | Historical sign |
|---|---|---|---|---|
| `+0, +0` | no | no | `[0,0]` events | **OPEN** |
| `+0, −0` | no | yes | `[0,1]` events | **OPEN** |
| `−0, +0` | yes | no | `[0,1]` events | **OPEN** |
| `−0, −0` | yes | yes | `[0,2]` events | **OPEN** |
| `+5, −5` | no | yes | `[0,1]` events | **OPEN** |
| `−5, +5` | yes | no | `[0,1]` events | **OPEN** |

Even when `[0,0]` under this envelope, an unknown C17 contribution and other control pathways remain. The table is a **model-coverage map**, not a table of resulting `ТЗн2См` states.

## Independent claims ledger, blockers, and correction discipline

`docs/ISA_06_D8_H4_EVIDENCE.tsv` records 16 statements as `SOURCE_TEXT`, `SOURCE_FIGURE`, `SCOPED_INFERENCE` or `OPEN`. `docs/ISA_06_D8_H4_OPEN_ITEMS.tsv` lists actionable blockers, each with the source that would be needed to close it. An `OPEN` item stays open even if the model checker passes; an independent blind second-reader review is still missing. H1/H2/H3 snapshots are not modified retroactively. **H2 `E022` stays retracted** and must not be resurrected as `z1 -> ТЗн2См` by applying an OR-gate legend.

For independent future use, follow this protocol:

1. Verify the **exact source image hash**, printed page, figure and full-resolution coordinate system; confirm the same source edition. Keep image crops only as navigation aids, never the sole evidence.
2. Record each figure-local gate label, its count of drawn inputs, every printed mnemonic and any small `+`/`−` mark *as separate objects*. Mark a crossing or unreadable glyph `OPEN` before assigning electrical semantics.
3. Extract the **textual functional claims** separately from diagram connectivity. Tag observations `SOURCE_TEXT` or `SOURCE_FIGURE` and hypotheses `SCOPED_INFERENCE`; log disagreements without overwriting prior H1/H2/H3 claims.
4. Trace **control qualifies and their opcode decode**: determine when the other C16/C18 enable inputs become true under `01`, and when C17 contributes. Search control-unit tables and timing descriptions, not only this one figure.
5. Recover trigger **initial states**, pulse polarity and accepted-edge semantics for both count inputs. Reconstruct carry generation including `z40` and cyclic `z1` with H2's corrected direction.
6. Only then model chronological arrival of transfer pulses, correction, carry, state toggles and `ИВА3` sampling for **each** six exact-zero cases. Cross-check against GY62 (1962), printed p.13 documented `02` equal subtraction `−0` without confusing it with `01`.
7. Promote any historical `STRICT` test or CPU patch only after a **complete provenance-linked state trace** excludes alternative terminal signs. Re-run D1–D7 and downstream historical RAM diagnostics after any future change.

**H4 exit:** a source-bound, reproducible *partial fan-in + event-envelope* qualification, **not** a complete gate-level description and **not** a signed-zero ISA result. Do not edit `src/main.cpp` or `mem/ROM.txt` in this stage.

## Reproduction

From repository root after applying the D8-H4 patch:

```sh
python tools/isa06_d8_h4_correction_audit.py --check --show-envelope
python tools/isa06_d8_h3_convention_audit.py --check
python tools/isa06_d8_h2_review_audit.py --check
python tools/isa06_d8_h1_netlist_audit.py --check
python tools/isa06_d8_sign_models.py --check
```

`CORRECTION-CHECK PASS` certifies **table integrity, scoped model invariants, explicit preservation of H2 `E022` retraction and open status**; it is not a hardware simulation or independent historical sign oracle.
