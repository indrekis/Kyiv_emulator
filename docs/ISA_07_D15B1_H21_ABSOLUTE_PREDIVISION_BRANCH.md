# D15/B1-H21 — GY1962 AU test I: magnitude pre-division branch (0234–0240)

## Evidence boundary

Primary source: Glushkov / Yushchenko, *Vychislitelnaya mashina "Kiev"*, 1962, **printed p.174** (left column, consecutive rows marked 0234–0240). Octal addresses. The five source words in the `.k41` and provenance TSV are literal visual transcription, not invented examples.

| Addr (oct) | 41-bit code (14 octal digits) | Source semantics |
|---|---|---|
| 0234 | `06035300000355` | opcode 06, absolute-magnitude subtraction `|0353| - |0000| -> 0355` |
| 0235 | `05035403550240` | opcode 05, if `|0354| <= |0355|` then `C=0240`, else `C=0236` |
| 0236 | `06035400000355` | opcode 06, `|0354| - |0000| -> 0355` |
| 0237 | `01035300000354` | opcode 01, signed `0353 + 0000 -> 0354` |
| 0240 | `01035400000356` | opcode 01, signed `0354 + 0000 -> 0356` |

`0000` is zero **only under the independent standalone host-image initialization** used here. This historical fragment does **not** print a complete entry RAM state. In a preceding test chain the meaning of any scratch state must be justified separately. We do not declare a machine-hardware oracle.

## Native observation strategy

Canonical historical words, starting at `0234`; do not execute `0241`. Bound the program to either 3 (TRUE branch) or 5 (FALSE branch) instructions. Observe all four RAM locations `0353`, `0354`, `0355`, `0356` *after each executable step*. Use the two established CWD modes and compare the complete results (not just C). Three PRIVATE explicit seeds also exercise positive and negative operands without changing the canonical `.k41` or CPU. The source file does not set a seed.

- `SOURCE_ZERO_INIT`: host zero-initialized RAM; TRUE, visit `0234 0235 0240`.
- `PRIVATE_TRUE_NONZERO`: `0353=04000000000000`, `0354=02000000000000`; TRUE, visit `0234 0235 0240`.
- `PRIVATE_FALSE_POSITIVE`: `0353=02000000000000`, `0354=04000000000000`; FALSE, visit `0234 0235 0236 0237 0240`.
- `PRIVATE_FALSE_NEGATIVE`: `0353=22000000000000`, `0354=24000000000000`; FALSE, visit `0234 0235 0236 0237 0240`. The negative signs must remain visible in the additions and output `0356`.

The independent numerical comparator uses exact 40-bit sign-magnitude arithmetic, not floating-point. It mirrors *documented HOST implementation behavior* for opcode 06, opcode 01, and opcode 05. H11 signed-zero semantics are **not settled** by these cases. No source-side oracle for initial scratch contents is claimed.

## Safety / scope

- Entry `0234`; strictly bounded. No execution of `0241` or subsequent iterative division, nor any I/O or STOP beyond the fragment.
- `PINS` protect 68 baseline Git blobs; one README append; exactly six new files. `src/main.cpp`, `mem/ROM.txt`, previous source examples remain immutable.
- Preserve OPEN_UNCHANGED: H9, H10, H11, H13, H14, H17. Separately H19_SEED=UNKNOWN and H20_SCRATCH_INPUTS=UNKNOWN. Hardware confirmation not provided.
- `NATIVE_GATE=PENDING` until independently executed on the user's actual MSYS2 MINGW64 build.
