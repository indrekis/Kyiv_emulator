# ISA-07 D14-C1e — actual CPU execution of magnetic-drum test arithmetic

**Git baseline:** `dbd045dab0b40dd834e21fb1ed3c4c8f75478331` (D14-C1d).  **Scope:** observational, read-only with respect to the repository; **no production code change**, `HARDWARE_ORACLE=0`.

## Historical input and limits

GY62 (Glushkov–Yushchenko, 1962), **printed pp. 83, 124, 177–179**: `3040` contains +`2^-12`, which is raw `1 << 28` in the fixed-point 40-fraction-bit representation. The magnetic-drum test forms and adjusts commands using:

| Octal location | Octal instruction | Test action |
|---|---|---|
| `0003` | `01 0052 0000 0024` | Copy prepared **write** opcode-25 template |
| `0005` | `01 0054 0000 0026` | Copy prepared **read** opcode-25 template |
| `0011` | `10 3000 3040 0060` | Multiply NK `3000` by `2^-12` into `0060` |
| `0016` | `03 3002 0024 0024` | Add NK `3002` to write template |
| `0017` | `03 3002 0026 0026` | Add NK `3002` to read template |
| `0035` | `03 0060 0024 0024` | Add computed increment to write preparation |
| `0036` | `03 0060 0026 0026` | Add computed increment to read preparation |

The test executes those seven **genuine** `Kyiv_t::execute_opcode()` steps in **dependency order** by explicitly assigning the next PC. It does **not** claim this is an uninterrupted reproduction of the complete original test program (other commands and branches are omitted). We do not execute any drum IO operation `23/24/25` here.

### Controlled NK inputs

`NK3000` is assigned the *synthetic but historically motivated* raw word `n << 24` (`0 <= n <= 500`), with all other bits zero. `NK3002` is assigned `(drum << 18) | start`, where `drum in {1,2}` and `0 <= start <= 03777` (octal). Both **cabinet** and explicitly selected **panel** sources are covered: no claim is made about historical switch power-on states. Program instructions use their original opcode and address fields; the CPU's current sign-magnitude arithmetic decides the result.

The independent oracle predicts:

- `raw(0060) = ((n << 24) * (1 << 28)) >> 40 = n << 12` (without rounding in opcode `10`);
- after `0016/0017`: `word(0024)=ins(025,1,0,0)+raw(3002)` and `word(0026)=ins(025,0,0,0)+raw(3002)`;
- after `0035/0036`: both words additionally receive `raw(0060)`, preserving their respective direction bit;
- after each isolated arithmetic instruction: `C=executed_pc+1`, `K=executed_instruction`, `T=0`, and `A` is unchanged — *expected current-code observations*, not hardware oracle claims.

The Python oracle uses exact integer arithmetic and never calls the C++ implementation or reads its output to derive expectations. The C++ probe links directly with `src/main.cpp`, uses the actual `Kyiv_t`, and prints state after **each** executed step. Staged results are verified independently by Python.

## Status and decision rule

- `SOURCE_STRICT`: opcodes and constants as printed in GY62.
- `SOURCE_DERIVED`: the arithmetic expectations **conditional on the selected NK words**, full 41-bit command encoding and source-prescribed grouping.
- `CODE_OBS`: concrete `Kyiv_t` output at the pinned revision.
- `OPEN`: interpretation of the increased II address as track/drum/position, source meaning of other NK bits, transfer end-of-track and any hardware timing.
- `HOST_POLICY`: probe's input validation, panel/cabinet controls, and error reporting.

A mismatch is reported as `CODE_OBS_MISMATCH` with expected and observed values. **Do not change multiplication or the drum decoder as part of this step.** Archive observations for a separately qualified ISA correction if needed. Even if all observations match, do **not** promote the C1b drum-digit extraction to a historical track decoder: `n=64/137/256/500` deliberately crosses that naive boundary.

## Build and run in Windows 11 / MSYS2 MINGW64

```sh
export PYTHONDONTWRITEBYTECODE=1
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  src/main.cpp tests/isa/isa07_d14c1e_nk3000_cpu_probe.cpp \
  -o tempkyiv/d14c1e_cpu.exe
python tools/isa07_d14c1e_nk3000_cpu_sandbox.py \
  --exe tempkyiv/d14c1e_cpu.exe --random-cases 20 --timeout 45
```

The `src/main.cpp` executable is expected to log other messages; the sandbox parses only records with the unambiguous `D14C1E-BEGIN` / `D14C1E-STEP` prefixes. This is a **native CPU** test, not a behavioral mock or a PDF/hash oracle.

The baseline remains unchanged. The only commit candidates for this stage are this documentation, evidence ledger, probe, sandbox and audit. Commit **only after** genuine MSYS2 execution, evidence review and passing Git audit; follow the project's separate commit/postcommit gate.
