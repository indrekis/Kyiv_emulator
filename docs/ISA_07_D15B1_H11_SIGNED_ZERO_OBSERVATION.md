# D15/B1-H11 — GY1962 two zero-producing subtractions (0155–0162)

Pinned baseline `e5df6e27d2bccd7f0bf97fab3f9ec41a4c7d6abf` (H10 publicly pushed).

## Verbatim historical source, not reconstructed from CPU

Glushkov & Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), printed **p.172** contains the operand words and asserts two equal-operand subtraction results `1(0)` (negative zero). Printed **p.173** lists the precise machine commands. The modern `.k41` HOST file is a first-pass visual transcription of **eight** original 41-bit octal words; original card-media representation is not claimed.

| Address | Verbatim 14-digit octal word | Source | Purpose |
|---|---|---|---|
| `0002` | `12525252525252` | p.172 | equal source operands for 02 |
| `0003` | `25252525252525` | p.172 | equal source operands for 06 |
| `0155` | `02000200020347` | p.173 | `02 0002 0002 0347` |
| `0156` | `16034730260160` | p.173 | `16 0347 3026 0160` |
| `0157` | `33000000000000` | p.173 | fallback STOP |
| `0160` | `06000300030347` | p.173 | `06 0003 0003 0347` |
| `0161` | `16034730260163` | p.173 | `16 0347 3026 0163` |
| `0162` | `33000000000000` | p.173 | fallback STOP |

The canonical current ROM word at `3026=20000000000000` is 41-bit sign-magnitude `−0`, pinned by byte-exact default ROM SHA. This is a software ROM reconstruction, not a machine-hardware witness.

## Two distinct source expectations and a possible emulator discrepancy

| Source command | Mathematical result | Historical expected 41-bit *code* | Current CPU code path prediction |
|---|---|---|---|
| `0155` opcode `02`: `0002-0002` | zero | `20000000000000` (−0) | −0, special case in `src/main.cpp` |
| `0160` opcode `06`: `abs(0003)-abs(0003)` | zero | `20000000000000` (−0) | +0 `00000000000000` (no zero sign override) |

**The arithmetic equality to zero alone is insufficient:** `+0` and `−0` are distinct 41-bit codes. The printed p.172 test requires the negative zero code for both. The current source suggests a discrepancy for opcode `06`; it is an observation hypothesis pending native measurement, not automatically a historical pass. No CPU change is part of H11.

## Bounded native experiment

Start independently at `0155` and `0160` with a 1-instruction and a 2-instruction budget in external and `tempkyiv` CWDs. The runner checks the exact destination `0347`, input data and `3026`, and the ensuing C address. The first successful two-step branch ends at `0160`; the second successful branch ends at `0163`, which **must not be executed**.

The original fallback STOP at `0157` is exercised on a **private image** with **only the comparison command `0156` retargeted** to data address `0002` (nonzero). The original `0155` arithmetic command and `0157` STOP remain verbatim. If the second group yields `+0`, its **unmodified original image** naturally executes the `0162` STOP in 3 steps, ending at `0163`. If it yields `−0`, no 3-step run is permitted because it would execute out-of-scope `0163`. Observed success of the runner means qualified measurements, not necessarily both historical checks pass.

Possible H11 decision labels: `SUB_NEGZERO_MATCH=1`, `SUBABS_NEGZERO_MATCH=0`, `SUBABS_HOST_POSZERO_MATCH=1`, `ORIGINAL_SECOND_STOP_OBSERVED=1`. Hist source alignment must be recorded separately for each opcode. H9 and H10 source conflicts stay `OPEN_UNCHANGED`; no transitive assumptions, no changes to CPU/ROM or prior historical files. Independent human verification and hardware oracle both remain PENDING/UNAVAILABLE.
