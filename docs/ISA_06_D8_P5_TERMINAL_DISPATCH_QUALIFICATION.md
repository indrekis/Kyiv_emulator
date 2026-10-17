# ISA-06 D8-P5 — bounded terminal-dispatch and STOP entry qualification

**Base:** `289e623` (P4 PASS on user MSYS2). **Additive only:** one C++ probe, one structural checker, two TSV records and this document. No changes to CPU, ROM, historical corpus or previous tests.

## Original source and literal words

Glushkov–Yushchenko (1962), Appendix 2, **printed p. 171** (scan in `Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf`, printed p.171; **not** `kiev0086.png`, which belongs to the 1964 monograph): `0157 = 16 0017 3042 0161`; `0161 = 31 0014 0162 0164`; `0164 = 31 3000 0022 0177`; `0165 = 33 0000 0001 0077`; `0166 = 33 0000 0003 0177`. The C++ probe copies these exact octal words, independently checked against the prior P4 transcript and pinned Git blobs. No new historical instruction is inferred.

## Interpretation and controlled cases

1. Under the already characterized sign branch `31`, original `0164` inspects the sign of **ROM `[3000]`**, *not* the sign of RAM `[0014]`; that RAM sign is inspected by original `0161` to select `0164`. With fixture `[0014]=-0`, `[0017]=2^39`, ROM `[3042]=2^39`, `C=0157`, run exactly three original commands: `0157`, `0161`, `0164`.
2. Supply **three explicitly injected ROM `[3000]` codes**: `+0` (expected target `0022`), `-0` (expected `0177`), negative nonzero (`SIGN|1`, expected `0177`). Do **not** execute `0022` or `0177`; their contents and role in this test's control flow are not authenticated by P5. No claim is made about which ROM `[3000]` value was installed in a real Kyiv machine.
3. In **fresh, independent CPU fixtures**, enter original `0165` and `0166` directly. Verify that opcode `33` sets the emulator's stop condition, fetching the literal documented word. **These direct-entry tests do not establish reachability from `0164` or the meaning of STOP's address fields.** Do not pin post-STOP `C` since the exact historical increment remains disputed.

## Evidence discipline

All **five** new scenarios are `POLICY`: independent runtime consistency checks subject to explicit ROM and register fixtures. **STRICT=0**. The source supports the five literal words; it does **not** establish the contents of ROM `[3000]` or that `0165`/`0166` can be reached from the `0164` path. Both `0022` and `0177` remain `UNEXECUTED`, and terminal program completion remains `OPEN`. The prior H2 netlist E022 remains `RETRACTED`; no historical sign-of-zero addition oracle is created.

P4's regression tests remain the integration qualification for consecutive 896-cell RAM sweeps. P5 is only a bounded study of the *terminal dispatcher*, not a surrogate full memory test or authenticated boot trace.

## Tooling and QA

`python tools/isa06_d8_p5_terminal_dispatch_audit.py --check --show-gates` validates the five original octal words against the committed P4 arrays, verifies Git object IDs (independent of Windows LF/CRLF), checks the scan digest literal and gate-table constraints, and rejects trailing whitespace. `--show-gates` uses `next_pc=...` rather than a shell-redirection-like arrow in output.

C++ probe: `g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa06_d8_p5_terminal_dispatch_probe.cpp -o tempkyiv/isa06_d8_p5_terminal_dispatch_probe.exe`. Run the executable and preserve its complete result. On any discrepancy, do not change CPU to satisfy test policy without further source evidence; report the first failing PC and decoded word.

## Source-attribution erratum (D8-P6)

The previous P5 manifest incorrectly assigned `kiev0086.png` to GY62. It actually depicts DPS64 (1964) printed pp.170–171 (control-unit schematics). GY62 (1962), printed pp.170–171, in the dedicated 1962 PDF is the historical authority for the original program words. D8-P6 replaces the manifest hash and corrects the auditor. This changes **source metadata only**; historical K words, P5 test logic, all POLICY gates, and the CPU are unchanged.
