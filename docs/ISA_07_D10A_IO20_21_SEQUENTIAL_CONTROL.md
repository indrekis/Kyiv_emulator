# ISA-07 D10-A — sequential control after IO20 and IO21

**Baseline:** `da84dee` (D9-B). **Primary historical source:** V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), **printed p. 58** (PDF page 58), SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`. The detailed operation descriptions supplement printed pp. 15–17. They explicitly give **C+1→C** and **memory[C]→K** for BOTH opcode 20 (В1) and 21 (В2). The old D7 document examined pp. 15–16 only and classified IO20/21 PC semantics as OPEN; this is a **new source resolution**, not a retroactive change to D7 evidence or pins.

## Historical digital contract vs host policy

- `SOURCE_STRICT` (**p.58**): 20 and 21 execute an inclusive destination group and then continue at the **next sequential instruction**; source explicitly depicts loading the instruction register from that next location.
- `HOST_CODE_FIX` (exactly FOUR CPU statements): append `++C_reg; K_reg = kmem.read_memory(C_reg);` to each of IO20 and IO21 after finishing the existing input loop. Do not change file parsing, `h`, memory addressing, drum setup, or opcode 24/25 PC semantics.
- `SOURCE_STRICT` (**p.58**): instruction-register reload (`M[C]→K`) is explicitly documented, not merely inferred by analogy. `HOST_CODE_FIX`: `K_reg = kmem.read_memory(C_reg)` is the implementation choice; `execute_opcode()` fetches again at the beginning of the next step. Tests check **both** the documented immediate `K_reg` state and a genuine second-step XOR.
- `HOST_POLICY`: missing files, short records, head selection, card zones and file paths belong to the emulator adapter; the source does not assign error behavior for those fixtures. No hardware device-model assertions.
- `OPEN`: **numeric conversion in IO20 is NOT repaired here**. Printed pp. 16–17 specify decimal input converted into a binary **fixed-point** format with 40 fractional bits and separate sign, and up to ten BCD decimal digits per input word. Today's `std::stol(...,8)` text parser/host word storage is not historically faithful. D10-A fixtures intentionally use single octal digits to prevent that known disagreement from obscuring the PC test. `21` text input representation, EOF/malformed handling, register-M destruction, and inverted intervals remain separately unqualified.

## Two genuine CPU-step witnesses

- Twelve independent sandbox scenarios: 20 × {range, single, offset, short, missing, zone1}; 21 × {range, single, offset, h1, a3, missing}.
- IO command resides at 0100; after step one PC **0101**, `K_reg` contains the actual XOR opcode at 0101, and the input destination cells and `h` match the existing host policy. A STOP decoy at 0120 demonstrates that IO21's nonzero `a3` does **not** redirect the PC; IO20's `a3=1` remains a card-zone byte offset, not a branch target.
- The second CPU step executes real XOR 5 XOR 3 = 6 (destination 0302), gives PC **0102**, and leaves the fetched XOR word in `K_reg`.
- Every test runs in a separate temporary directory and uses only host mock files; no analog/peripheral/hardware oracle.
- **Legacy D8-A full runner is obsolete as a current PC oracle**: its IO20/21 cases expected C=0100 before this source-supported fix. Preserve its pinned historical files unchanged, and use this two-step D10-A runner for these opcodes. ISA-06 and D8-B/D9-A/D9-B remain applicable.

## Source provenance

GY62 printed p.58 uses the operation names **В1** (`20`) and **В2** (`21`) and separately writes the sequential `C+1→C` and instruction-register update for each. Printed p.17 describes sign-magnitude fractional coding and BCD input capacity. These are documentary digital facts, not proof of physical timing or a generic host `int` representation.
