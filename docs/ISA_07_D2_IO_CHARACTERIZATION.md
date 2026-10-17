# ISA-07 D2 — Characterization of IO opcode paths 20–25

**Base:** `b4ed64a`. **Scope:** documentation, read-only audit and a one-step C++ probe with a process-level Python sandbox. Do **not** change CPU, ROM, device state, source input files or historical oracles in D2. This is NOT evidence that the historical I/O commands acted this way.

## Sources and classification

- GY62 (Glushkov–Yushchenko 1962), **printed pp. 15–16**, describes peripheral command roles and control-transfer conventions; does not establish this emulator's host paths, EOF treatment or the UB of a C++ local variable.
- Repo `src/main.cpp`, blob `f84acfb22fa3e00f598f3cdb05d4ed2a6618f893`: exact current C++ control flow.
- ISA-07 D1 issue registry, blob `013549da8348b0575f960387715fb1cc5ec95121`.

`CODE_DEFECT` means a C++ defect independent of hardware; `CODE_ANOMALY` means observed CPU control-state behavior with no settled historical oracle; `CODE_SUSPECT` requires comparing documented semantics; `OBS` is intentionally not promoted to STRICT/POLICY. See the TSV for a machine-checkable register.

## Characterized behavior and its limits

1. `22` writes `../punc_cards_out.txt` and, **without break**, falls through `23` and writes `../magnetic_drum.txt`. The sandbox checks both files appeared; this is a reproducible C++ defect, not hardware semantics. `23` by itself writes only the drum file.
2. `20` and `24` declare `bool flag;` and can read it without initialization on some input paths. With a complete fixture (`01 02 03` and `1 2 3` respectively), the loop assigns it before testing it. The ordinary sandbox run probes **only this constrained path**. Empty, missing or malformed inputs have **no qualified behavior** and are not used to produce deterministic test expectations.
3. `21` initializes a local record `counter=0` but never increments it. The sandbox checks two one-step modes, `h=0` and `h=1`. This is **not** an exhaustive proof of punch-tape record behavior.
4. `20`, `21`, `24`, `25` contain no assignment/increment to `C_reg`. One-step observations intentionally capture that `C` remains at the original command; they **do not** infer that historical hardware should automatically increment it.
5. `22/23` use `for (i=0; i<=source_2; ++i)` while fetching `mem[source_1+i]`. Here source_2 acts as a *count-like last offset*, which requires independent comparison with GY62's endpoint semantics. Short controlled data prevent broad reads and writes. No claim of definite historical mismatch yet.
6. Paths inside C++ are relative to `cwd`. Python runs each command in a **new TemporaryDirectory under `tempkyiv/`**, with fixtures for `../../mem/` and `../`. It removes those test files after each child. It does not alter the repository's `mem/`, punched tape or drum files. Each child executes **one opcode step**, so stalled command counters cannot create an infinite execution loop.

## Harness acceptance

`python tools/isa07_d2_io_audit.py --check` checks all six handlers, exact Git blobs at HEAD, and the six-row D2 ledger. The source file and header are unmodified; do not bypass these pins. No reliance on the historical commit object is required.

Build with `g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa07_d2_io_characterization_probe.cpp -o tempkyiv/isa07_d2_io_characterization_probe.exe`. The probe defines a no-op `disassembly` and **must not link** `src/asm_disasm.cpp` (it has a CLI `main()`). Then run `python tools/isa07_d2_io_sandbox.py --exe tempkyiv/isa07_d2_io_characterization_probe.exe`.

The eight sandbox observations and their results are **CODE-OBS**, not `STRICT` or `POLICY` assertions about the Kyiv hardware. If the C++ implementation changes in D3, its corresponding observations and manifest must be deliberately updated. Execution timeouts/failures are reported with a failing exit code for controlled modes.

## Next phase

D3: smallest CPU-only fixes for `22` fallthrough and uninitialized flags; compare `20–25` control transfers and I/O range definitions with GY62 before modifying `C_reg` and loops. Do not investigate analog/electrical timing unless it is needed to establish digital instruction semantics.
