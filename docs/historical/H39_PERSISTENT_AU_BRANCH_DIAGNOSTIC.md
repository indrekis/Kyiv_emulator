# H39 V2 — repeated branch 0245 and RAM[0357] provenance

**Base parent:** `f15c879a1ba1110d6c14ff7ce526397b0eadcca2` (`f15c879`) with SHA-pinned accepted H37 documentation.
**Evidence level:** `HOST_NATIVE_BOUNDED`, not a historical hardware oracle.
**FULL_AU=OPEN; HARDWARE_ORACLE=NO.**

## Why H39 V1 was rejected

The V1 probe stopped with `0245 encountered twice during probe`. That was a **probe defect**, not a CPU regression: the accepted H38 trace contains two visits to `0245` in the fresh segment `0214` (steps 18, 45), and five in the persistent segment (steps 18, 23, 28, 33, 38). H39 V2 records all visits and verifies their exact PC transitions against the already-pinned H38 source trace.

## Observed repeated branches

Historical source word: `0245: 05 0357 0000 0247`. The comparison uses the magnitude in RAM[0357] versus machine zero (RAM[0000]); a zero magnitude gives branch to `0247`, while a nonzero magnitude proceeds to `0246` in the observed scenarios.

| Trial | Visit # | Segment step (zero based) | RAM[0357] before branch | Next PC |
|---|---:|---:|---|---|
| FRESH | 1 | 18 | `00000000000000` | `0247` |
| FRESH | 2 | 45 | `00000000000000` | `0247` |
| PERSISTENT | 1 | 18 | `00374647372171` | `0246` |
| PERSISTENT | 2 | 23 | `00007633061623` | `0246` |
| PERSISTENT | 3 | 28 | `00000003634256` | `0246` |
| PERSISTENT | 4 | 33 | `00000000000001` | `0246` |
| PERSISTENT | 5 | 38 | `00000000000000` | `0247` |

The **first** control divergence is step 18, but it is not the only visit. Thus the first comparison alone is not a complete account of the loop.

## Native HOST writes to RAM[0357]

The native H39 probe took `RAM[0357]` snapshots before and after every executed instruction in the persistent preceding four segments and in the final `0214` segment, also in the fresh experiment. Recorded changes are:

| Trial | Segment | Step | Writing instruction PC | Before | After |
|---|---|---:|---|---|---|
| FRESH | PART_IV_NK_PLUS | 14 | `0241` | `00000000000000` | `20000000000000` |
| FRESH | PART_IV_NK_PLUS | 17 | `0244` | `20000000000000` | `00000000000000` |
| FRESH | PART_IV_NK_PLUS | 41 | `0241` | `00000000000000` | `20000000000000` |
| FRESH | PART_IV_NK_PLUS | 44 | `0244` | `20000000000000` | `00000000000000` |
| FRESH | PART_IV_NK_PLUS | 46 | `0247` | `00000000000000` | `37777777777771` |
| PERSISTENT | PART_IV_NK_PLUS | 14 | `0241` | `00000000000000` | `02637116040001` |
| PERSISTENT | PART_IV_NK_PLUS | 17 | `0244` | `02637116040001` | `00374647372171` |
| PERSISTENT | PART_IV_NK_PLUS | 22 | `0244` | `00374647372171` | `00007633061623` |
| PERSISTENT | PART_IV_NK_PLUS | 27 | `0244` | `00007633061623` | `00000003634256` |
| PERSISTENT | PART_IV_NK_PLUS | 32 | `0244` | `00000003634256` | `00000000000001` |
| PERSISTENT | PART_IV_NK_PLUS | 37 | `0244` | `00000000000001` | `00000000000000` |
| PERSISTENT | PART_IV_NK_PLUS | 39 | `0247` | `00000000000000` | `17175133200564` |

These identify **HOST execution provenance** only. Their interpretation still depends on unverified initial scratch RAM and artificially selected panel/PC actions.

## Diagnostics altering only initial RAM[0353]

The following interventions are *counterfactual experiments* in transient CPU objects, not reconstructed historical operator actions:

| Variant | Visits to 0245 | Steps | First exit from 0245 | Final PC | End reason |
|---|---:|---:|---|---|---|
| FRESH_WITH_0353_FROM_PRIOR | 5 | 42 | `0246` | `0252` | IO_BOUNDARY_NOT_EXECUTED |
| PERSISTENT_WITH_0353_ZERO | 2 | 49 | `0247` | `0252` | IO_BOUNDARY_NOT_EXECUTED |

The detailed evidence is in `branch_0245.tsv`, `writes_0357.tsv`, and `trial_summary.tsv`. Changes to `RAM[0353]` do not by themselves establish historical causality for `RAM[0357]` or any panel action.

## Scope and next checkpoint

H38 source authenticity (706 fresh and 699 persistent trace rows) was rechecked. All 20 canonical `.k41` files, original source words, ROM and production CPU remain unchanged. Both baseline variants end at the protected I/O boundary `0252`. Neither I/O (`020`–`025`) nor `0360` nor an unknown instruction was executed by this probe. Full AU completion remains open.

The next bounded task is to connect the observed writers of `RAM[0357]` to 1962 source words and establish a qualified I/O continuation at `0252` only with explicit device state, not an invented stop or silent bypass. `0232` and `0360` also remain guarded.

This commit contains H37's four documentation/scenario files plus this H39 report only; it changes no production CPU, ROM or historical test source.
