# ISA-07 D15/A1 — deterministic HOST octal image and bounded CPU run

Pinned parent: `a361ff744befbd76062133a488b00ddcba9565ff` (D14-C2-H3/C2). Scope: the *already exercised* standalone `tools/isa07_d15a1_run_image.cpp`, one narrow parser guard, an independent Python regression runner, and documentation/audit. Neither `src/main.cpp` nor `src/asm_disasm.cpp`, the production `Kyiv_t` CPU, any ISA or drum headers, `.kdr`, nor ROM contents are modified. This is **not** the native media format of historical Kyiv.

## The first deliberately small functional contract

Executable: `tempkyiv/d15a1_run_image.exe IMAGE.k41 START_OCTAL MAX_STEPS_DECIMAL [--allow-rom] [--watch ADDR_OCTAL]...`.

`KYIV41-OCT1` is an ASCII *HOST* textual format, with one literal header line (comments/whitespace allowed) and one or more records `AAAA WWWWWWWWWWWWWW`, where the address is exactly four octal digits and the raw word exactly fourteen octal digits (zero-padded), at most 41 significant bits. Empty lines and trailing `#` comments are accepted. Values are **raw** machine words; the 41st sign bit is preserved, so positive and negative zero are distinct. No conversion from decimal to fixed point or assembly language is performed. Duplicate addresses and malformed headers, fields, digits, overwide words, unreadable/empty files are errors. The **complete file** is parsed and validated before the first write to the newly created `Kyiv_t`.

The first provisional address admission policy is `0001..1777` for RAM, and `3000..3777` for ROM only with `--allow-rom`. Address `0000` is hardwired zero, `2000..2777` is not qualified; both are refused for load/watch/start. This is a limited HOST admission policy and **not** a definitive statement about the original hardware address bus, ROM overlay or operator initialization.

`START_OCTAL` is exactly four octal digits. `MAX_STEPS_DECIMAL` is strictly 1..100000 with decimal digits only (leading zeros allowed). A very long decimal digit sequence must be rejected **before** integer multiplication, preventing modular overflow and acceptance of a wrapped value. One step means one call of the *actual existing* `Kyiv_t::execute_opcode()`; output `STATUS=CPU_STOP` if it reports false, else `STATUS=LIMIT` if the budget expires. Diagnostic `C/K/A/P/LOOP/T` and repeated `--watch` raw words are printed in a stable labeled text report. This is a process-local execution budget, **not** an emulated historical clock or a classification of every physical stop cause.

CLI memory input is read-only: opening the image must never overwrite it. Ordinary CPU stdout (diagnostic and trace lines) is intentionally unchanged. CPU errors may be reported separately; `D15A1-ERROR` is a HOST tool error and does not establish a historical machine-stop mode.

## Evidence and out-of-scope limitations

Initial independent native smoke: 5/5 (add/STOP/negative zero, budget, duplicate address, hardwired zero, ROM opt-in). Initial independent extended native run: 20/20 (zero opcode, equal loop, 41-bit limit, sign-sensitive branch, file syntax and strict failures), confirmed in user's MSYS2 logs **before** integration of the narrow decimal-overflow guard. A fresh 21-case runner gate is required before committing this package. Audit `REAL_NATIVE_GATE=PENDING` is intentionally static; do not rewrite it to PASS based on a source scan.

`Kyiv_t` constructor currently obtains `../mem/ROM.txt` relative to the process working directory and does not turn inability to open the file into a fatal error. Therefore D15/A1 does **not** yet offer a qualified/reproducible historical ROM baseline. The historical test corpus (GY62 printed pp. 165–179), per-word provenance, test-control cycle expectations, explicit ROM selection and verification remain D15/A2+ work. The stub `disassembly()` in the standalone driver suppresses only the separate CLI disassembler; execution uses real production `Kyiv_t`. Future CLI integration needs explicit image and ROM policy and may require a reusable run-control API instead of duplicating `main`.

Do **not** claim full ISA equivalence, historical timing, historical image format, complete ROM or peripheral fidelity, crash durability, safe simultaneous `.kdr` writers, resolved drum/track mapping, or hardware-oracle validation.

## Acceptance (MSYS2 MINGW64)

From repository root after pinned apply:

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  src/main.cpp tools/isa07_d15a1_run_image.cpp -o tempkyiv/d15a1_run_image.exe
python tools/isa07_d15a1_extended_regression.py
python tools/isa07_d15a1_audit.py --self-test
python tools/isa07_d15a1_audit.py
```

Require `D15A1-EXTENDED PASS CASES=21/21 SOURCE_IMMUTABLE=1` and audit PASS. Do not commit/push before real native evidence, exact-set staging, clean postcommit state and a verified remote baseline. The existing 5 smoke cases are preserved evidence and need no rerun unless source changes outside the pinned parser guard.
