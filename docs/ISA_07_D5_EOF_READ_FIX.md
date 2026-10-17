# ISA-07 D5 — EOF-guarded input loops for opcodes 20 and 24

**Base:** committed `a985352` after ISA-07 D4 (two initialized `flag` variables). This is a minimal C++ host-file reading correction, **not** a certified historical peripheral behavior.

## Confirmed pre-fix failure

- The D4 one-step sandbox observed `24` reading a short input file (`1\n`) and then throwing `std::stoi` at EOF (`EXIT_3`). Empty inputs for `20` and `24` also reached an invalid numeric conversion.
- Both C++ handlers used `while(stream) { getline(stream, line); ... }`, which tests the stream *before* extraction. A failed `getline` was followed by parsing an empty/stale line.
- D4 already fixed the separate uninitialized `flag` defect. D5 does not undo or alter that change.

## Exact CPU changes

Exactly **two loop-header substitutions**, one in each of `src/main.cpp`'s handlers `20` and `24`:

```cpp
// previous
while (stream) {
    std::getline(stream, line);
    // existing processing
}

// D5
while (std::getline(stream, line)) {
    // existing processing
}
```

`stream` stands for `punch_cards` in opcode `20` and `magnetic_drum` in opcode `24`. No other C++ source lines are changed. The updated loop accepts a final nonempty record even if the file lacks a trailing newline, and does not enter the body when extraction fails at EOF. Empty/missing files cause zero iterations. This behavior is a **host input policy**, not an inference about tape/card/drum hardware.

## Bounded dynamic qualification

Reuse the **unchanged** `tests/isa/isa07_d2_io_characterization_probe.cpp` and execute only one CPU step per process. `tools/isa07_d5_io_sandbox.py` runs twelve isolated cases (six inputs for each of `20`, `24`) with an individual subprocess timeout:

- `full`, `full_noeol`: `1 2 3` => `mem[0200]=1`, `mem[0201]=2`.
- `short`, `short_noeol`: `1` => `mem[0200]=1`, `mem[0201]=0`.
- `empty` and `missing`: no input transfer => both cells remain `0`.
- Each case must end with exit 0, exactly one probe summary, and `C=0100` as the **unchanged current implementation** (not an asserted historical control-flow rule).
- File paths live in a disposable tree under `tempkyiv`; no project peripheral data files are written or read.

## Out of scope / remaining open

`C_reg` progression for `20/21/24/25`, opcode `21`'s record counter, source-range and field interpretation, empty **records** (a blank line is not an empty file), malformed numeric tokens, row offsets, and authentic device behavior remain open. We do not silently classify any of these as solved. In particular, a blank line may still raise `stol/stoi`, and D5 tests deliberately do not accept it as valid input.

Previous D1–D4 **static** auditors pin earlier CPU versions and are retained as historical evidence, not run as current-CPU gates. The D5 auditor proves that reversing only the two loop changes yields exactly the pinned Git blob of D4's CPU. The D3 dynamic sandbox (`22/23`) and ISA-06 C++ probes should be rerun before commit.

## Commands (after applying the patch)

```sh
python tools/isa07_d5_eof_audit.py --check
g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa07_d2_io_characterization_probe.cpp -o tempkyiv/isa07_d5_io_probe.exe
python tools/isa07_d5_io_sandbox.py --exe tempkyiv/isa07_d5_io_probe.exe
```

Do **not** add `src/asm_disasm.cpp` to the probe link: that file defines its own CLI `main()`. Do not commit until the user has verified the runtime tests and regression gates.
