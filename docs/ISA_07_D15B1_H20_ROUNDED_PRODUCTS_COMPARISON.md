# D15/B1-H20 — paired rounded products, comparison and bounded failure path

Pinned baseline `2e4fb8eb27707ca95ca698424545af2476fbad27`. Glushkov–Yushchenko (1962), printed p.174.
Transcription is **first visual pass**; not a claim of a second independent
human reading or of original machine observations.

## Five literal source words (octal)

| Address | 41-bit machine word | Instruction role |
|---|---|---|
| `0227` | `11035303540355` | Rounded multiplication |
| `0230` | `11035403530356` | Rounded multiplication |
| `0231` | `16035503560234` | Exact signed-code comparison |
| `0232` | `22035303560233` | FAIL perforator output; NOT EXECUTED |
| `0233` | `33000000000000` | FAIL stop; NOT EXECUTED |


### Program intent versus native observations

`0227` multiplies scratch words RAM[0353] × RAM[0354] with rounding into
RAM[0355]; `0230` swaps the operands into RAM[0356]. `0231` uses opcode 16
and branches to **0234** if the two full machine words coincide. If they
are not equal it falls through to `0232` (opcode 22 perforator output),
followed by `0233` STOP. This H20 stage stops at the **entry** to either
0234 or 0232, after at most three instructions. No side-effecting I/O is
performed. H21 may start at 0234 as a separate stage.

The printed source does NOT specify a standalone initial state for scratch
RAM[0353]/[0354]. H19 documented an unknown historical generator seed;
no H20 output is claimed to be a hardware-derived expected word.

### Profiles (HOST exact integer oracle, not historical hardware oracle)

| Profile | PRIVATE input 0353 | PRIVATE input 0354 | Expected both products | C after 3 instructions |
|---|---|---|---|---|
| SOURCE_ZERO_INIT | unspecified, host zero | unspecified, host zero | `00000000000000` | `0234` |
| PRIVATE_POSITIVE | `14000000000000` | `10000000000000` | `06000000000000` | `0234` |
| PRIVATE_MIXED_SIGN | `14000000000000` | `24000000000000` | `23000000000000` | `0234` |
| PRIVATE_MISMATCH_COMPARE | same private positive pair | same | both `06000000000000` | `0232` |

The last row uses a **private replacement** `0231=16035503540234` to
compare RAM[0355] against RAM[0354], thereby forcing false and
explicitly demonstrating the failure branch. Original source remains
byte-identical. For each profile and both workdirs, run at step bounds 1,
2, 3 (24 native cases); watch RAM 0353–0356 and confirm exact PC. No
command at 0232/0233/0234 executed. No host I/O or ROM write.

Earlier H14 historical rounded-product discrepancy remains OPEN;
this H20 probe does not resolve that conflict. All H9/H10/H11/H13/H14/H17
conflicts remain OPEN_UNCHANGED; H19 seed UNKNOWN; CPU/ROM/prior images
unchanged; HARDWARE_ORACLE=0.
