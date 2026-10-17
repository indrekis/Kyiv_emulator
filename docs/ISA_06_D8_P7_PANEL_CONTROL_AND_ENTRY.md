# ISA-06 D8-P7 — operator-settable NK, RAM-test selection and true entry 0117

**Base:** `6fe5999` (P6 committed, 89/89 STRICT and 24/24 POLICY on user's MSYS2). This is a **source qualification and one bounded POLICY probe**, not a full panel implementation. One P6 auditor pin is repaired to remain valid after P6 was committed. CPU, ROM, original machine words, P5/P6 probes and prior docs are unchanged.

## Primary evidence: Glushkov–Yushchenko 1962 (GY62)

- **Printed p. 8:** addresses `3000–3007` are eight manually settable **41-bit NK** (`наборные коды`). They differ from permanently wired `3010–3277` and replaceable wired `3300–3777` code regions. Thus `3000` and `3001` are not globally constant factory ROM words.
- **Printed p. 161:** NK `3000`, `3001`, `3002` appear both on the operator console and in the ROM cabinet. Each has a separate switch: **up selects the console code**, **down selects the corresponding cabinet NK**. This is a source-selection mechanism, not a simple immutable memory array. The source does not state an identical console switch configuration for NK `3003–3007`; retain their general 41-bit NK status without inventing panel overrides.
- **Printed p. 120, RAM tests:** sign of NK `[3000]` controls whether **all four RAM tests run cyclically (`+`)** or **just the panel-selected test runs (`−`)**. First-test entry `0022`; second `0045`; third `0100`; **fourth `0117`**. The documented `0164 = 31 3000 0022 0177` on printed p. 171 thus corresponds to two meaningful *modes*; `[3000]` remains operator-configurable and P6 did not execute that word.
- **Printed p. 121, first RAM test:** negative sign in NK `[3001]` instructs use of a manually entered code from NK `[3007]`; other settings select the listed standard code patterns. This is **first-test**, not fourth-test, control.
- **Printed p. 122:** the fourth RAM test writes and checks walking-bit patterns, then repeats with complementary codes; this matches the *intended structure* of P6's two epochs, but P6's initial conditions and comparison semantics remain POLICY.
- **Printed p. 170, actual fourth-test entry:** `0117 = 01 0000 0000 0014`, `0120 = 01 3012 0000 0017`, `0121 = 01 0017 0000 0021`. Previous P6 began at `0120` with RAM `[0014]=+0` injected, bypassing **the documented** `0117` initialization. P7's new bounded probe executes all three exact words, preloading `[0014]=-0` and confirming that `0117` clears it to `+0` in the **current emulator POLICY**.

## Post-0164 interpretation — precise limits

- **NK3000 positive:** by p. 120, intended to cycle through all tests; opcode `0164` branches to `0022`, first-test entry. The combination of source description and branch operands is a strong historical *control-flow intent*; no real-hardware execution is thereby authenticated.
- **NK3000 negative:** opcode `0164` branches to `0177`, outside the reproduced fourth-test listing. The source specifies execution of only a panel-selected test, but **does not give the exact executable word at `0177`**. Do not describe `0177` as STOP and do not fabricate its content.
- **NK3001:** independent manual choice affects how first RAM test at `0022` supplies patterns; values are not established by the shipped `mem/ROM.txt`.
- **OPEN:** actual machine cabinet and panel settings, the content at `0177`, and the natural post-fourth-test terminal route.
- **Repo observation:** `[3000]` and `[3001]` absent from `mem/ROM.txt` is consistent with operator-supplied NK and is **not evidence that a factory ROM dump is missing**. Constructor defaults of zero are implementation behavior, **not historical operator setup**.

## Preventing errors in subsequent stages

Before modeling the console, specify (a) separate 41-bit **cabinet** NK values for `3000–3007`; (b) independent 41-bit **panel** values for `3000–3002`; (c) per-address panel/cabinet source selection for those three; (d) explicit initial configuration required by each historical diagnostic. Not yet implemented; no CPU mutations allowed in P7. It must remain possible to distinguish selecting the positive and negative *sign* of zero.

### Repair to the P6 source checker

P6 edited `tools/isa06_d8_p5_terminal_dispatch_audit.py` as a documentary erratum. Original P6 checker incorrectly required the *pre-P6* P5 auditor blob at `HEAD`. At base `6fe5999`, `HEAD` correctly contains the *post-P6* blob. The revised checker requires the original Git blob at **exact historical commit `92f5352`** and the corrected blob at **current HEAD**; it does not weaken the pin or silently update the expected source.

## Verification and epistemic boundary

P7 adds one bounded C++ test for original `0117→0120→0121→0122`, with injected `ROM[3012]=+1`, no external serial input, and no claim of historical front-panel initialization. It remains **POLICY** and does not re-run 1,181,826 P6 instructions. Prior historical 89 STRICT and P1–P6 POLICY invariants remain unchanged; P7 has no signed-zero oracle and no new proof for opcode `01` negative-zero addition. In particular **H2 E022 stays RETRACTED**. Publicly accessible digital GY62 PDF is represented by the pinned SHA-256 and precise printed-page citations; P7 audit validates the ledger and Git source (optional external PDF hash check when supplied), not page-image recognition by OCR.
