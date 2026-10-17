# ISA-06 D8-P1 — provisional signed-zero addition policy

**Target source baseline:** `src/main.cpp` byte-identical to Git commit `2010cd0` (D8-H8); later H9 *documentation-only* commits are compatible. This package changes **only opcode `01`'s exact-zero sign policy**, adds a narrow policy probe and an independent mathematical candidate model. It does **not** alter opcode `02`, ROM, historical instructions, existing tests, or historical corpus.

## Decision and evidence hierarchy

- **GY62 (1962), printed pp. 11, 13, 17:** `01` adds algebraic machine numbers; `02` applied to equal numbers produces `−0` **explicitly**; the machine distinguishes `+0` from `−0`. Only the equal-subtraction statement is a `STRICT` zero-sign rule.
- **GY62, appendix 2, printed pp. 170–171:** original instructions `0123` and `0141` are `01 0021 0000 0020`; they add hardware `+0` to cell `0021`. Sign-dependent and code-exact tests follow. These are useful architectural clues, **not** a proof that initial `0021` is `-0` or that a full diagnostic historically passes under the candidate.
- **DPS64 (1964), printed pp. 95–97, 100–103, 142, 144–146, figs. 62, 71–73, table 4:** sign-magnitude external format, negative operand bit-complements, carry paths, sign-trigger correction, and direct/inverse result issue. These provide a credible mechanism for distinct zero signs; the unresolved correction/trigger timing **does not determine a unique output**.
- **D8-H2:** proposed directed link E022 is **retracted**. H3–H8 establish the gates, transfer-decode and reset boundaries, but do not prove opcode `01`'s gate enables and final `TЗн2См`.
- **External context (not independent machine-circuit proof):** historical accounts at icfcst.kiev.ua and generic one's-complement architectures. Neither supplies a verified `01` sign table for Kyiv.

## Engineering decision: model M1, with POLICY—not STRICT—status

The candidate uses **41-bit one's-complement addition with end-around carry**, interpreted back to the documented external sign-and-40-magnitude-bit code. In this abstract model, an exact zero sum is `+0` **only if both external operands have nonnegative sign**; otherwise it is `-0`. This rule also naturally yields `-0` from equal-operand subtraction, whereas the previous integer model needs a special `02` condition. It preserves the additive identity for **machine codes**: `-0 + +0 = -0`.

The 41-bit one's-complement model is a *candidate semantics*, not a faithful reconstruction of the actual two-trigger sign path. Its strong explanatory economy motivates changing the emulator policy now, but is not a historical correctness claim. Other gate/timing models can remain compatible with presently verified facts.

### The six discriminating cases

| Operands (`01`) | Prior integer M0 | Adopted candidate M1 | Historical oracle |
|---|---|---|---|
| `+0 + +0` | `+0` | `+0` | OPEN |
| `+0 + -0` | `+0` | `-0` | OPEN |
| `-0 + +0` | `+0` | `-0` | OPEN |
| `-0 + -0` | `+0` | `-0` | OPEN |
| `+5 + -5` | `+0` | `-0` | OPEN |
| `-5 + +5` | `+0` | `-0` | OPEN |

**Asymmetric positive/negative nonzero sums remain unchanged.** This *deliberately does not* transfer the candidate rule to other arithmetic opcodes.

### How to interpret probabilities

The texts supply qualitative evidence but not measured frequencies or independent observations of physical hardware at this edge case. Consequently there is **no identifiable empirical likelihood** for competing models. A useful *subjective engineering ranking* under explicit assumptions (ordinary end-around-carry datapath, no extra zero-normalizer, no unrecorded input-order special case) is:

| Model | Judgmental weight (illustrative, not a posterior) | Reason |
|---|---|---|
| M1, one's complement preserving `−0` | 0.75 | Bit-complements, cyclic carry, dual zero and natural subtraction `−0`, plus additive identity in diagnostics |
| M0, integer result with sign canonicalization | 0.15 | Current emulator mechanism, but no independent evidence of a hardware zero-normalization circuit |
| M2, operand-order-dependent zero sign | 0.10 | Plausible only if partially unresolved gate/timing pathways break order symmetry |

These weights **are assumptions**, not measured or computed historical probabilities. Reweighting the missing zero-normalization/trigger behavior can reverse the ranking. Do not cite `0.75` as an empirical certainty. M1 is preferred because it makes the fewest additional ad hoc exceptions; it is not forced logically.

## Implementation scope

`src/main.cpp`: in the existing `opcode_add/sub/subabs` result packing block, keep the integer arithmetic and existing overflow behavior. Only when `opcode == opcode_add && res == 0` and at least one original operand has a negative sign, set the outgoing sign flag. Do not normalize `-0` input codes before checking sign. Keep `opcode_sub`'s explicit `-0` result and other opcodes unchanged.

This deliberately **does not** claim cycle accuracy or fix any ROM loader, opcode `05`, or fourth-RAM-test qualification.

## Verification and rollback criteria

- `tools/isa06_d8_p1_ones_complement_model.py --check`: six signed-zero cases, 10 equal-subtractions, deterministic random non-overflow integer consistency. The Python model validates M1's mathematical self-consistency only.
- `tests/isa/isa06_d8_p1_signed_zero_policy_probe.cpp`: **POLICY 8 cases** for zero sign, including original first instructions at PCs `0123`/`0141` with *injected* `-0`; **STRICT 4 cases** for prior historically documented nonzero `01` and equal `02`. A policy mismatch is *not* a DOC-MISMATCH.
- Re-run ISA-06 D1–D7; zero-addition `OBS` prints will deliberately change. D5's `STRICT` cases should remain unaffected but must be re-run. Never change their classifications to make failures disappear.
- An independently authenticated machine trace, complete original ROM/RAM fixture, or a complete sign-trigger electrical reconstruction that conflicts with M1 warrants reverting or refining this policy. A passing emulator test alone does not validate history.

## Source availability / next step

An online search identified contextual museum pages and an independent 1981 memoir, but **no new primary original commutator netlist or verified signed-zero addition trace**. Continue documentary work only when additional schematics / diagnostics become accessible. In the meantime exercise the fourth-RAM-test with explicit initial RAM and ROM provenance, and preserve `STRICT`/`POLICY`/`OBS` separation.
