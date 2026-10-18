# W1 — Compiler warning cleanup (ISA-07, no behavioral modernization)

Pinned parent: `d6d435b3147053e65a7f6d0f7c2c0f4d6d4a7095` (D11-B accepted, 225/225 plan, 28/28 actual CPU, 22/22 regression groups). This stage is restricted to five tiny edits across `src/main.cpp` and `inc/kyiv.h`; **all existing tests, source-qualified behavior and CPU policies remain frozen**.

## Warning-to-delta map

| Flag | Site | Narrow delta | Qualification |
|---|---|---|---|
| `-Wreorder` | `aproxy` constructor, `inc/kyiv.h` | initialize `ref` before `mPtr` in textual initializer list | C++ always initializes members in declaration order; behavior preserving |
| `-Wunused-variable` | `word_to_addr3` | remove unused `Addr_3_mask_shift` | no observable use |
| `-Wunused-function` | `parse_kyiv_number` | remove unused file-local function | no callers in pinned translation unit; no runtime effect |
| `-Wsign-compare` (2 sites) | opcode `24`, magnetic drum input | change nonnegative counter type from `int` to `addr_t` | same comparisons for representable nonnegative counts, no change to guards or branch |
| `-Wunused-variable` | opcode `10/11` multiplication | remove dead invocation of pure `leftmost_one(res_mul)`; retain both helper overloads | unused return, no state effects; does not validate historical rounding |

## Explicit non-goals / unresolved defects

- `IO24` retains current `std::stoi`, file paths, selection, EOF, partial-write, branch/prefetch, and reversed-interval behavior. `source_2-source_1` still uses unsigned arithmetic and may underflow for a reversed interval: **OPEN**, not fixed here. The wider nonnegative counter prevents `int` overflow in exceptionally long host inputs but this stage does not add a new input policy.
- No changes to actual multiplication data flow or number of shifts; the vacuous dead helper call is not evidence that a missing normalization step is correct.
- No warning suppression, no `-Wno-*`, no library/API/CLI refactoring, no new history assertions.
- Old SHA-pinned auditors must remain archival; apply current **functional** regression gates. W1's source pin is based on real complete Git blobs, not fragments.

## Reproducibility and acceptance

Archive `apply_w1.py` accepts `--self-test`, `--prepare`, and `--apply`; it reconstructs `W1.patch` against the **entire** `HEAD:<path>` content, pins exact old Git blobs, checks the clean checkout, and handles LF/CRLF on Windows without relying on fuzzy `git apply`. `--prepare` does not edit repository files. `--apply` writes two source files and installs this document and `tools/w1_warning_audit.py` only after all checks pass. It validates the resulting content and runs the read-only auditor, rolling back on failure when its output files are unchanged by external activity.

Precommit: `python tools/w1_warning_audit.py`; compile a real Kyiv_t probe with `g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc src/main.cpp tests/isa/isa07_d11b_io21_cpu_probe.cpp`; run `tools/isa07_d11b_io21_cpu_sandbox.py` (28/28), `tools/isa07_d11b_input_plan_sandbox.py` (225/225, unchanged plan executable), and a current-HEAD functional regression gate for `IO20=50/50`, `IO22-25=25/25`, `IO21=5/5`, `ISA06=89/89+40/40`. The archived `tools/isa07_d11b_regression_gate.py` pins its own old HEAD (`707cdf7`): it MUST NOT be run unchanged at W1 HEAD `d6d435b`; The ZIP supplies `run_w1_regressions.py`, a temporary driver that reuses the *functional* D11-B runner with the W1 HEAD requirement (without editing its archived source).

PASS on the developer's actual MSYS2 is mandatory before commit. Expected proposed diff: exactly `src/main.cpp`, `inc/kyiv.h`, this document, and `tools/w1_warning_audit.py`. No commit/push until user pastes actual PASS logs.
