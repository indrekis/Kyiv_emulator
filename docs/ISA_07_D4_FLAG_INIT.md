# ISA-07 D4 — initialize input-handler termination flags (20, 24)

**Baseline:** `75312d0`, after the D3 opcode-22 break fix. This stage repairs two definite C++ uninitialized-local reads, not historical I/O behavior. The *only* CPU changes are two `bool flag;` declarations to `bool flag = false;` in handlers 20 and 24. No changes to `C_reg`, file formats, parsing, device model, loop iteration, ROM, or other commands.

## Evidence and limitations

- D1 and D2 explicitly identified uninitialized `flag` in `20` and `24`; D2 recorded one-step host-file observations before the fix. The flag is read after the line-processing branches, including paths that never assign it. Initialization to `false` is the minimal well-defined C++ correction.
- The handlers still use `while(stream)` and do not check `getline` before processing. An empty or malformed line can cause `std::stol`/`std::stoi` to throw; malformed input behavior is **not fixed** by D4. In particular, an input containing **one value** for opcode `24` when two are requested reaches EOF and reproducibly throws `std::stoi` (`EXIT_3` in the existing driver). This is **HOST_INPUT_OPEN**, not `CODE_FIX` or a successful one-value read.
- The unchanged `C_reg` in opcode 20 and 24 is a distinct `CODE_ANOMALY` whose historical correctness remains unresolved. The D4 executable deliberately performs **exactly one CPU instruction** and discards the machine.
- Historical audits D1/D2 pin an old CPU; D3 pins exactly one added `break`. They must not be rewritten to accept the D4 CPU or run as *current* static regression gates. The D4 auditor instead derives the permitted CPU source by applying precisely two substitutions to the original committed D3 CPU blob and checks the entire result.

## Qualification

1. Apply the ZIP patch on clean `75312d0` and run `python tools/isa07_d4_flag_audit.py --check`.
2. Compile the **unchanged** D2 driver: `g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa07_d2_io_characterization_probe.cpp -o tempkyiv/isa07_d4_io_probe.exe`. Do **not** add `src/asm_disasm.cpp`, which provides another `main()`.
3. Run `python tools/isa07_d4_io_sandbox.py --exe tempkyiv/isa07_d4_io_probe.exe` in ephemeral directories. For each of `20` and `24`, it tests full, short, empty, and absent input files. Full files for both opcodes and the short file for opcode `20` must finish one CPU step and preserve known input values (**three CODE_FIX cases**). Short input for opcode `24` is a separate, explicitly checked *known* `stoi` exception at EOF, not a success oracle. Empty-file exceptions are recorded as unresolved input parsing behavior; all runs must terminate within their time budgets.
4. Run full historical CPU/ROM probes D1 through D8-P10, and the D3 corrected-output sandbox. Do not run D1/D2 or D3 **static CPU-pin auditors** against the new CPU: D4 replaces them as the current exact-change gate. Preserve them unchanged as historical records.
5. Commit only after user runtime evidence and regressions. Keep every new behavioral assertion classified as `CODE-FIX`, `CODE-OBS`, or `HOST_INPUT_OPEN`, **not STRICT hardware ISA**.
