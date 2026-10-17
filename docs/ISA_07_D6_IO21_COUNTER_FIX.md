# ISA-07 D6 — opcode 21: advancing the punched-tape record counter

**Base:** `464f6d3` (D5, CPU blob `8beb18801926fbd40fa5680b7490124fedeeead7`). The **only** CPU edit adds `++counter;` at the end of opcode `21`'s input loop. Other CPU handlers, all existing probes, ROM, `inc/kyiv.h` and earlier audits remain unchanged. This is an emulator host-file fix, **not** evidence of the historical punch-tape protocol.

## Evidence and scope

- GY62 (Glushkov and Yushchenko, 1962), **printed p. 16**, defines the purpose of binary/code input but does **not** prescribe the emulator's host text-file line numbering, `h` counter, or `heads.txt` format.
- Current `src/main.cpp` (base blob above): opcode `21` initializes `counter=0`, compares it against `num=h`, and calls `getline` repeatedly without incrementing `counter`. Any initial `h>0` therefore cannot select the requested record. After reading, existing code performs `h += com_counter`.
- `docs/ISA_07_D1_OPEN_ISSUES.tsv` issue `IO_COUNTER` and ISA-07 D2 one-step characterizations established this as a C++ code defect, not a machine oracle.

## Exact change and qualified behavior

Add **one** line `++counter;` immediately after `if(flag) { break; }` inside the opcode-21 loop, before its closing brace. It counts each successfully iterated file line under the **current** C++ model. The D6 C++ probe uses source address `0200`, second address `0202` (thus **two** imported words under the existing `source_2-source_1` bound) and a sandbox tape with six octal lines `11`, `22`, `33`, `44`, `55`, `66`. Expected outcomes under controlled host policy:

| Initial `h` (decimal) | RAM `[0200]` | RAM `[0201]` | Final `h` (decimal) |
|---:|---|---|---:|
| 0 | `0011` | `0022` | 2 |
| 1 | `0022` | `0033` | 3 |
| 2 | `0033` | `0044` | 4 |
| 4 | `0055` | `0066` | 6 |

An additional **two-step, bounded** run reuses one `Kyiv_t` and reads from `h=0` to `h=2` to `h=4`; each call still executes a single opcode. All file I/O happens inside a fresh temporary directory under `tempkyiv/`; `../punched_tape.txt` and `../heads.txt` resolve to test files, never repository files. Timeouts and exceptions fail the tests. These are **HOST_CODE_FIX** assertions, not `STRICT` historical test claims.

## Deliberately not changed

1. The word count `source_2 - source_1` remains *exclusive* rather than an inclusive address interval. The GY62 interval contract for opcode `21` is not independently qualified here.
2. `h` remains the host-position policy (`h += com_counter`). The currently ignored `heads.txt` contents are not interpreted as a historical record format.
3. `C_reg` still does **not** advance on opcode `21`. Its historical transition remains `OPEN` (ISA-07 D1 issue `IO_PC`).
4. The loop still uses `while(punch_cards)` with `getline` inside; this can process stale/empty input at EOF, particularly for truncated or malformed records. D6 fixtures provide enough valid lines and do **not** claim EOF robustness for opcode `21`.
5. No changes to `20`, `22`, `23`, `24`, `25`, analog timing, or device emulation.

## Acceptance

- `python tools/isa07_d6_io21_counter_audit.py --check`: reverse the one-line CPU change and compare the **entire** normalized source to the pinned original Git blob; verify four other unchanged blobs and the D6 contracts. It does **not** require local presence of a historical commit object.
- Build `src/main.cpp` plus `tests/isa/isa07_d6_io21_counter_probe.cpp`, **not** `src/asm_disasm.cpp` (contains another `main`). Run `tools/isa07_d6_io21_sandbox.py --exe ...`, expecting `PASS=5/5 TOTAL_STEPS=6`.
- Keep D1/D2/D3/D4/D5 source-pinned audits as **historical-version evidence**. They are not expected to pass against this newer CPU. Run ISA-06 functional probes and D3/D5 I/O runtime regressions before committing.
