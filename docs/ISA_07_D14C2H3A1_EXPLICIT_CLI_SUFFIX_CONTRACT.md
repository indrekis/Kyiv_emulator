# ISA-07 D14-C2-H3/A1 — documented opt-in CLI suffix (pure parser)

**Pinned HEAD:** `540d55dfb00a1f94271ccd91f89180d697b63797` (D14-C2-H2/P2). **Scope:** new standalone parser, standalone C++17 probe, independent Python test, audit, documentation. No edits to `Kyiv_t`, `src/main.cpp`, `src/asm_disasm.cpp`, B1/B2/B3/C1b/H1/P1/P2. **NOT a CLI integration yet.** `HARDWARE_ORACLE=0` and `HISTORICAL_MAPPING=OPEN`.

## Finding

The production `main()` in `src/asm_disasm.cpp` currently recognizes `command`, `expression`, `removable_memory` and an optional trailing `--block-overflow-stop`. It creates a `Kyiv_t`, but does not call the P2 `attach_experimental_drum(...)` API at all. Thus opt-in `.kdr` use is available programmatically and from tests, **not yet from the normal command line**. This is a real usability gap, not a CPU failure.

## H3/A1 proposed suffix

For a future H3/A2 production integration, exactly this argument tail is supported:

`<legacy mode and its arguments> [--experimental-drum EXISTING_IMAGE PROFILE TRACKS SLOTS PIN] [--block-overflow-stop]`

- `EXISTING_IMAGE` is a single argv token, so an MSYS2 Windows path including a colon, backslashes, or spaces is not parsed as colon-delimited metadata. No file is opened at the pure parser layer.
- `PROFILE` is explicit ASCII `[A-Za-z0-9_.-]` with length 1..64, as in B1.
- `TRACKS` and `SLOTS` are positive **decimal integers**, strictly unsigned, with no `+`, `-`, trailing characters, or whitespace; exactly **three** drums. B1 applies its geometry and 1,000,000-slot HOST cap.
- `PIN` is exactly decimal 1, 2, or 3 (leading zeroes accepted). It selects the independent HOST drum lock, not an inferred historical track mask.
- `--block-overflow-stop` stays last. If both suffixes are present, their order is fixed. Before these optional tails, **every legacy positional argument remains byte-for-byte unchanged and in the same position**.
- Bare/incomplete/misplaced `--experimental-drum` and misplaced/repeated `--block-overflow-stop` fail closed with named `CLI_*` errors.
- No optional historical geometry; no implicit default image, automatic creation, implicit attachment, file writes, or conversions. The suffix parser is independent of `std::filesystem` I/O.

## Release decomposition

- **H3/A1 (this change):** pure parser `inc/kyiv_drum_cli_v1.h`, independent tests, docs, SHA/Git audit. No production CLI modification.
- **H3/A2 (future):** narrowly patch `src/asm_disasm.cpp` to call the tested parser after validating mode/arguments and *before* execution; then call existing P2 `Kyiv_t::attach_experimental_drum` with the explicit policy `a3_linear_v1`. Explicit separately invoked image provisioning; never create on attach. Production CLI tests must exercise genuine `kyivemu` and verify legacy behavior, missing-file rejection, wrong geometry, active `.kdr` reads/writes, and unchanged C/K/A semantics.
- **H3/B+ (future):** bigger transfer tests, failure matrix, and eventual legacy-adapter deprecation decision. Old regression gates remain qualified; no historical oracle upgrade.

## Standalone acceptance

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tests/isa/isa07_d14c2h3a1_cli_probe.cpp -o tempkyiv/d14c2h3a1_cli.exe
python tools/isa07_d14c2h3a1_cli_sandbox.py --self-test
python tools/isa07_d14c2h3a1_cli_sandbox.py \
  --exe tempkyiv/d14c2h3a1_cli.exe --random-cases 200 --timeout 5
```

The Python reference independently validates the argument grammar, values and profile/geometry bound. A nonexistent input image path must remain nonexistent: `FILE_CREATION=0`. These results do **not** claim `Kyiv_t` or end-user CLI execution.
