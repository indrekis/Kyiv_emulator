# ISA-06 D8-P2 — bounded real historical RAM diagnostic with provisional signed-zero policy

**Target baseline:** `468a4ef` (ISA-06 D8-P1, following H9). **Only new** documentation, C++ probe and Python auditor. No changes to CPU, ROM, previous probes, original corpus or root README. This stage tests the engineering policy chosen in D8-P1, not newly authenticated behavior of 1959–1964 hardware.

## Source and provenance

- **GY62** (Glushkov–Yushchenko, *Vychislitel'naya mashina «Kiev»*, 1962), **printed pp. 170–171**: fourth RAM diagnostic, original code at octal `0122–0136` (write/travel) and `0140–0155` (read/compare); exact octal machine words transcribed in D5 and independently cross-checked by this stage. Printed p. 13 explicitly specifies `-0` for equal-operand subtraction **02**, but **does not** specify the sign of zero for all **01** sums.
- **D5** (`tests/isa/isa06_d5_historical_ram_iterations_probe.cpp`): authoritative *project transcription* used for 27 original test words. This is not independent ROM authentication. P2 duplicates those words to keep the probe self-contained and the Python auditor requires byte-for-byte identical entry text.
- **DPS64** (Dashevsky–Pogrebinsky–Shkabara, 1964), printed pp. 96–103 and 142–146: complement arithmetic, sign-trigger pathway and timing; incomplete schematic-to-code recovery still prevents historical certification of opcode **01** zero sign.
- **D8-P1** (`468a4ef`): proposed ones'-complement-inspired policy for **01** gives `-0` on an exact zero sum if either operand has negative sign; output from opcode **02** remains independently **STRICT**. `-0 + +0 -> -0` is **POLICY**, not historical `STRICT`.
- **H2 E022 retraction** remains in force. H1–H9 fail to prove gate admission / final `ТЗн2См` for opcode **01**.

**Fixtures, NOT historical facts:** ROM `[3012]=1` (left-shift count), `[3026]=-0`, `[3042]=highest positive magnitude bit`; RAM `[0014]=+0` (select sign branch), `[0021]=-0`, beginning data RAM `[0020]`, `[0200]`, `[0201]` set to `077` unless a scenario explicitly preloads them. `P=0371`, `A=0`, `Cy=077`. ROM is populated using `write_rom` and is **not** loaded through the known CWD-sensitive constructor; no original ROM dump or authenticated full initial memory is claimed.

## Original-code walkthrough, with separate confidence levels

`docs/ISA_06_D8_P2_EXPECTED_WALK.tsv` gives **32 individual PC→next-PC transitions**, eight for each bounded pass. `K` at each transition must equal the *original* 14-octal-digit word at that PC. `A`, `Cy`, `P`, stop state and exact 41-bit stored words are also checked.

| Scenario | Source PC range and expected result | Assertion |
|---|---|---|
| First write pass `-0` | Starts `0122`; `0123` copies `0021=-0` to `0020`; indexed `0126` stores `-0` at RAM `0200`; branches at `0130` and `0135`; returns `0123` | **POLICY** (opcode 01 zero-copy sign) |
| Second write pass `+1` | `0123` stores `+1` at `0201`; `0131` shifts travel pattern; `0132` uses unresolved opcode **05 equality**; returns `0123` | **POLICY** (ISA-05 equality rule) |
| First read pass `-0` | Start `0140`; `0141` copies `0021=-0` into `0020`; `0144` compares indexed RAM `0200` against `0020`, succeeds; `0147` recognizes `-0`; returns `0141` | **POLICY** (signed-zero copying) |
| Second read pass `+1` | `0141` copies `+1`; code-exact compare `0144` succeeds for RAM `0201`; `0150` shifts; `0151` uses opcode **05 equality**; returns `0141` | **POLICY** (ISA-05 equality rule) |
| Counterfactual read | Original `0140→0141→0142→0144` executes; **test harness then overwrites RAM `[0020]` with `+0`**, leaving RAM `[0200]=-0`; actual `0144` rejects it and original `0145` executes STOP | **POLICY-sensitivity**, not a historical trace of model M0 or observed hardware |
| Preloaded mismatch | RAM `[0200]=-0` and `[0020]=+0` are injected **before** `0144`; original exact comparison `016` falls through to original STOP `033` at `0145`; post-STOP C is **not** asserted | **STRICT** on compare/STOP only; no opcode 01 |

**Four POLICY cases and one STRICT control case**. The integrated write→read case uses the *same* `Kyiv_t` and preserves the just-written RAM `[0200]=-0`, `[0201]=+1`, but the harness explicitly switches phases by loading `A=0`, `Cy=077`, `C=0140`, `RAM[0021]=-0`, `RAM[0020]=077`. This is a **controlled intervention**, **not the original natural progression** from `0137` into `0140` and not a certified end-to-end historical RAM test.

## Interpretation and counterfactual

Model M0 (old integer addition) would copy an injected `-0` as `+0` at `0141`. With RAM `[0200]=-0`, original `0144` is a code-exact comparison and distinguishes those machine codes. The counterfactual fixture changes the cell explicitly at the boundary to show the genuine error STOP path; it is **not** an actual execution of the pre-P1 CPU implementation, and it is not evidence that initial diagnostic RAM truly contained `-0`.

These conditional executions provide a useful *program-level consistency test* for the P1 policy and demonstrate why the choice matters operationally. They do **not** distinguish P1's `+5 + -5 -> -0` model from alternatives or independently validate unknown signed-zero microarchitecture. A circuit-level proof or authenticated machine trace is still required to upgrade any `01` zero-sign case to `STRICT`.

## What checks actually establish

- **C++ probe**: exact original words at every executed instruction; expected historical control transitions **under explicit fixture and POLICY assumptions**; stored full 41-bit values; preservation of `P`, terminal A/Cy states; conditional STOP sensitivity.
- **Python audit**: expected-walk TSV matches exactly four literal trace arrays and there are 27 octal instruction words in D5 and P2 which match. Verifies the baseline historical-program transcription is unchanged. It cannot prove chip or machine behavior.
- **Existing suites**: D1–D7 plus P1; H1–H9 document audits and D8 conceptual model. Existing D4–D7 `OBS` still stay `OBS` even if they now print `-0` as expected.

**Do not** change `01` semantics, classify its zero-sign as `STRICT`, or claim the complete fourth RAM diagnostic passes at this stage. Full read/write diagnostics, RAM fault simulation, ROM provenance and exact behavior of `05` on equality remain future work.
