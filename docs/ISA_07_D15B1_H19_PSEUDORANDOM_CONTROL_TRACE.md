# D15/B1-H19 — source-exact pseudorandom control-flow block, 0214–0226

Pinned baseline: `47d53096deac3dab0a8ada1d88b388b5da032df7`. Glushkov–Yushchenko (1962), printed pp.172,174.
First visual source reading, **not yet independently transcribed or hardware witnessed**.

## Exact source records

Eleven source command words (octal addresses) and one source RAM constant:

| Address (octal) | 14-digit word | Reading |
|---|---|---|
| `0214` | `01035300000354` | Opcode `01` |
| `0215` | `10035430420353` | Opcode `10` |
| `0216` | `31035302210217` | Opcode `31` |
| `0217` | `02000003530353` | Opcode `02` |
| `0220` | `01035330420353` | Opcode `01` |
| `0221` | `15035402600352` | Opcode `15` |
| `0222` | `12035230440352` | Opcode `12` |
| `0223` | `15035430440351` | Opcode `15` |
| `0224` | `05000003510226` | Opcode `05` |
| `0225` | `02000003520352` | Opcode `02` |
| `0226` | `17035203530353` | Opcode `17` |
| `0260` | `01777777777777` | Printed RAM constant |


The printed description on p.172 labels **0214–0226** generation of a
pseudorandom number. The historical listing does **not** print the initial
seed or final expected generated word for this block. Scratch RAM cells
0351–0354 are used. Do not attribute HOST zero initialization or test seeds
to the original Kyiv hardware or to the 1962 book.

## Control-flow map and source context

- `0214`: opcode 01, `0353+0000→0354`.
- `0215`: opcode 10 (non-rounded multiplication), `0354×ROM[3042]→0353`.
- `0216`: opcode 31 sign branch: negative `0353→0217`, nonnegative `→0221`.
- Negative path `0217→0220→0221`; nonnegative skips those two commands.
- `0221`: opcode 15 AND with printed `0260` low-37-bit mask; `0222`: opcode 12
  division by ROM `3044`; `0223`: opcode 15 AND with ROM `3044`.
- `0224`: opcode 05 absolute comparison against cell zero, destination
  `0226`; fallthrough `0225` remains a source word, not a proven executed
  instruction for any tested seed. `0226`: opcode 17 41-bit equivalence
  (XNOR) into cell `0353`; next `0227` is outside this test.
- ROM `3042=10000000000000`, ROM `3044=02000000000000` (pinned HOST ROM).
- Previous H18 source `0213` reaches `0263`, not `0214`. This is a fresh,
  explicitly chosen entrypoint and is **not** end-to-end historical proof.

## Independent host-policy oracles and bounded scenarios

The independent reference is an exact integer/sign-magnitude emulator for
**the commands exercised**, not a claim of original 1962 machine semantics.
Both working directories (EXTERNAL and TEMPKYIV) must agree.

| Test state | Initial cell `0353` | Path | Steps | Next C |
|---|---|---|---:|---|
| Canonical HOST zero-init | unprinted / defaults to 0 on this HOST | 0214,0215,0216,0221,0222,0223,0224,0226 | 8 | 0227 |
| PRIVATE +LSB | `00000000000001` | nonnegative path | 8 | 0227 |
| PRIVATE −LSB | `20000000000001` | negative path via 0217,0220 | 10 | 0227 |

For each profile the native runner performs **two step-limited independent
runs**, first 3 steps to discriminate opcode 31, then the full 8/10 steps.
It checks the register/watch snapshots (`0351–0354`) against the integer
oracle, plus source and private-image byte hashes. No instruction `0227`
or any untested fallthrough of `0225` is executed.

Do not infer statistical randomness, historical seeding rules, genuine
hardware timing or complete generator output sequence from this evidence.
H9/H10/H11/H13/H14/H17 questions remain OPEN_UNCHANGED. CPU, ROM and
prior source images unchanged. HARDWARE_ORACLE=0.
