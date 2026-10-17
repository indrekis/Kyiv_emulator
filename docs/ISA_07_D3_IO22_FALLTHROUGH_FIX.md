# ISA-07 D3 — isolate the missing `break` between opcodes 22 and 23

**Baseline:** `a311c22` (D2 committed and pushed). **Scope:** one inserted `break;` in `src/main.cpp` and new D3 read-only qualifications. No changes to the historical input/output rules, other opcode handlers, ROM, headers, or existing tests.

## Evidence and scope

- **CODE-DEFECT:** D2 documented and dynamically reproduced opcode `22`'s unintended fallthrough to opcode `23`; this creates *both* `punc_cards_out.txt` and `magnetic_drum.txt` when only `22` executes. The `22` handler ends by setting `C_reg` to field III; its compound statement is closed before the separate `23` case label, but there is no intervening `break;`.
- **Target:** insert **one** `break;` after the closing brace for `22` and before the case for `23`. No other CPU edit.
- **Expected corrected CODE semantics:** opcode `22` writes only the punch output, opcode `23` writes only the drum output; each transfers to field III, `0120` in the existing D2 one-step fixture. These assertions concern isolation of distinct C++ handlers, not a complete historical device model.
- **Still OPEN:** input `20/24` uninitialized flags; input `21` nonadvancing record counter; `20,21,24,25` control flow; address-range/count handling for `22/23`; host-specific file I/O and devices. D3 does not alter or reclassify these questions.

## Retaining historical evidence

D1/D2 scripts deliberately pin the *pre-fix CPU* and classify the fallthrough as present. They are historical, version-specific audits: do **not** rewrite their conclusions to pretend the defect remains in the current implementation. Their normal `--check` against the changed CPU is expected to fail. D3 instead checks the historical pinned Git blob `f84acfb22fa3e00f598f3cdb05d4ed2a6618f893` and requires that the entire present working-tree `src/main.cpp` be exactly the historical content **plus this single `break;`**. Existing D2 probe and its Python sandbox remain unmodified; the D2 sandbox expects the old two-output defect for mode `22`, so it is not a post-fix success oracle. D3 uses the D2 one-step C++ probe in its own sandbox runner with corrected expectations.

## Verification and acceptance

1. Audit exact source transformation and original Git blob: `python tools/isa07_d3_io22_fix_audit.py --check`.
2. Compile the **existing** one-step D2 probe:
   `g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa07_d2_io_characterization_probe.cpp -o tempkyiv/isa07_d3_io22_probe.exe`
   (`src/asm_disasm.cpp` must **not** be linked; it contains another `main()`.)
3. `python tools/isa07_d3_io22_sandbox.py --exe tempkyiv/isa07_d3_io22_probe.exe`; the D3 runner creates a fresh temporary test tree for **each one-step execution**, checks file absence/presence **and numeric output contents**, checks `C=0120` and no STOP, uses an execution timeout, and deletes its fixtures.
4. Run all earlier **CPU/ROM** probes D1–D8-P10 (including the two 78-cycle P10 paths). The old D1/D2 **I/O characterization scripts** remain archived pre-fix baseline; do not run their `--check` as current-version regressions.
5. After all PASS, commit five D3 files and the single-line change to `src/main.cpp`; rerun D3 audit after commit. No rebaseline of D1/D2 Git blob pins.

**Classification:** D3 test verdicts `CODE-FIX`, not independent historical I/O ISA oracles. For specific device-level historical semantics use GY62 printed pp. 15–16 with a separate source audit; this stage makes no additional claim about peripheral simulation.
