# ISA-07 D14-C2-H3/A2 — production CLI opt-in attachment

**Exact parent:** `d75f38cbbc946545d5feb5e6fddae0cf6759f09e` (H3/A1).
**Scope:** one tracked production CLI source `src/asm_disasm.cpp` plus documentation and tests. `inc/kyiv.h`, `src/main.cpp`, the A1 parser and B1/B2/B3/C1b/H1/P1/P2 logic **must be unchanged**.

## Historical boundary

This is **HOST_POLICY** for experiments with a logical image, not a historically certified drum decoder. `HARDWARE_ORACLE=0`, `HISTORICAL_MAPPING=OPEN`, geometry 9864/511 unresolved. It neither changes the CPU instructions nor replaces legacy decimal text adapters when the experimental session is not attached.

## Exact end-user grammar

`kyivemu <legacy mode + legacy arguments> [--experimental-drum EXISTING_IMAGE PROFILE TRACKS SLOTS PIN] [--block-overflow-stop]`

`command`, `expression`, `removable_memory` retain their pre-existing positional grammar. The A1 `kyiv_drum_cli_v1::parse` strips only qualified optional suffixes; it rejects incomplete, misplaced or repeated markers before executing the CPU. `TRACKS`/`SLOTS` are positive decimal integers; exactly three logical drums; the profile name must be B1-valid; `PIN` is 1..3. `EXISTING_IMAGE` is one path token and may contain spaces or Windows drive letters. Existing overflow flag must remain **last**; all old positionals stay in their original positions after stripping.

The CLI passes `kyiv_drum_host_address::policy::a3_linear_v1` explicitly, with no default image, path, geometry, drum lock or automatic new-media provisioning. If attachment fails (missing/corrupt image, geometry mismatch), CPU execution does not begin, a named attach error is emitted and the process returns nonzero. The C++ session first validates an existing complete `KYIVDRM1` image. There is no best-effort format conversion or fallback to text on failed explicit attachment.

## Placement and compatibility

`src/asm_disasm.cpp` parses suffixes after `argc < 2` help and reading `mode`, replacing only its original trailing `--block-overflow-stop` logic. Parsing and optional attach occur before branching to any mode's CPU execution; `Kyiv_t` construction retains the existing ROM initialization behavior. No new image is opened on a legacy no-suffix CLI invocation. Existing mode argument interpretation otherwise remains unchanged. CLI errors and attach errors are host diagnostics, not a historical stop mode.

## Independent production acceptance

Build the actual normal CLI executable, **including `src/asm_disasm.cpp` which contains `main()`**; unlike P2 probes, no `disassembly()` stub is used:

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Iinc \
  src/main.cpp src/asm_disasm.cpp -o tempkyiv/d14c2h3a2_kyivemu.exe
python tools/isa07_d14c2h3a2_cli_sandbox.py --self-test
python tools/isa07_d14c2h3a2_cli_sandbox.py \
  --exe tempkyiv/d14c2h3a2_kyivemu.exe --timeout 15
```

The independent Python oracle explicitly provisions a fresh `KYIVDRM1` file before positive tests; that is **test provisioning**, never auto-create-on-attach. It runs genuine `kyivemu expression` sequences containing `25→23→25→24`, checks all image bytes (CRC64-ECMA-182, bitmap, 41-bit raw words and negative zero), tests pin 1, 2, and 3, and tests both old CLI invocation and the old overflow flag without the new suffix. It also checks malformed suffixes and missing, corrupt and geometry-mismatched images without file mutation. Images in isolated temporary directories, no retained test fixtures.

**Release gates:** A2 audit exact file scope, genuine Windows/MSYS2 CLI test, P2 CPU 35/35, D13B 23/23 (+ ISA06 89/89 and 40/40), other relevant component gates as needed. No commit or deprecation decision until the genuine executable passes. Not verified for concurrent `.kdr` writers or crash durability.
