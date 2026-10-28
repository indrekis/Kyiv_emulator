# D15/B1-H10 — GY1962 cyclic addition, carry into the LSB

Pinned baseline: `cc688d3298eae645624b99195e28a5c6fe8012c4` (H9 pushed and source-prose discrepancy preserved OPEN).

## Primary source (not inferred from the emulator)

- Glushkov & Yushchenko (1962), **printed p. 172**: operand `0007` (`17 3675 7367 5712`) and the stated expected word `0020` (`16 7573 6757 3624`), explanatory row for `0151–0154`.
- **Printed p. 173**: verbatim commands `0151` cyclic addition (07), `0152` exact equality (16), `0153` fallback STOP (33), `0154` operator-dependent negative-conditional command (31).
- Source image `examples/historical/gy1962/au1_addcyc_0151_0154.k41` is the modern HOST-only 41-bit format, not original physical media. The source word at `0154` is included in the image for documentation **but must never be executed by this bounded test**.
- One visual transcription only; a second human witness remains **PENDING**.

| Octal address | Raw 14-digit 41-bit word | Printed page | Meaning |
|---|---|---|---|
| `0007` | `17367573675712` | 172 | source operand (twice) |
| `0020` | `16757367573624` | 172 | historical expected result |
| `0151` | `07000700070347` | 173 | `07 0007 0007 0347` |
| `0152` | `16034700200154` | 173 | `16 0347 0020 0154` |
| `0153` | `33000000000000` | 173 | failure STOP |
| `0154` | `31300001100155` | 173 | operator-dependent command; OUT OF BOUND |

## Independent arithmetic discriminator

Use `SIGN = 1 << 40` (sign bit) and `MASK = SIGN - 1` (40-bit magnitude). The positive operand at `0007` equals `0o17367573675712` and doubling it produces `0o36757367573624`. Therefore a carry from magnitude bit 40 occurs:

| Candidate | 40-bit result (14-digit octal) | Relation to printed `0020` |
|---|---|---|
| `2*x mod 2**40` (discard carry) | `16757367573624` | EXACT MATCH |
| `(2*x + 1) mod 2**40` (end-around carry +1) | `16757367573625` | MISMATCH by 1 LSB |

**Original H10 baseline:** opcode `07` used the second candidate as a provisional software policy. GY1962 printed p. 11 speaks of carrying back to the low bit; DPS1964 printed p. 102 describes a related reduction by one unit. The source-text tension remains historically **OPEN**.

**Follow-up, 2026-10-28:** private CPU candidate removes the additional low-bit `+1` on carry, keeping `magnitude & ((1ULL << 40) - 1)`. Native observation: H10 result `16757367573624` matches printed cell `0020`; ten-case historical batch 10/10 (8 source matches, 2 independently documented discrepancies), D5 strict tests 7/7. The five D5 policy failures reflected the earlier implementation, not historical ISA requirements. The updated D5 suite includes a bounded exact-word two-step JE check and revised explicitly provisional boundary expectations. This is a **source-aligned software decision**, not independent verification of physical hardware. In particular, exact `+1`/`-1` signed-zero results remain policy, not historical oracle. No source image or ROM is modified.

## Safe native observations (not a source-success regression)

Run the original image at `C=0151` with 1 and 2 steps, watching `0347`, `0007`, and `0020`. On the original printed result, the `0152` JE would branch to `0154` after two steps. With the current host candidate result (+1), JE falls through to `0153`. **Only in the fallthrough case** execute a third instruction and check original STOP with `CPU_STOP STEPS=3 C=0154`. Never execute `0154`: it reads operator-settable cell `3000` and its behavior cannot be qualified by this source fragment.

The original H10 runner reports `HISTORICAL_ORACLE_MATCH` and `HOST_POLICY_PLUS1_MATCH` separately; its OLD-POLICY assertions describe its original baseline and are not post-change regression criteria. The follow-up qualification uses the ten-case checkpoint batch (one historical H10 step), the D5 probe with two bounded historical steps, and Qt GUI native smoke. Source image, ROM and other historical fixtures remain unchanged.

`H9_SOURCE_PROSE_CONFLICT=OPEN_UNCHANGED`; `HUMAN_INDEPENDENT_WITNESS=PENDING`; `HARDWARE_ORACLE=0`.
