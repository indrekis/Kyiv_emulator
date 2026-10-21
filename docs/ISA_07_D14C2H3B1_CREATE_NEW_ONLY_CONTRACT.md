# ISA-07 D14-C2-H3/B1 — explicit **create-new-only** `KYIVDRM1` provisioning

**Pinned parent:** `04be0ca3ceafa7cd10c8ef250e9425b8e435b06e` (H3/A2, production CLI attachment).

## Purpose and exact scope

The emulator can now attach an **already existing** canonical logical magnetic drum image via opt-in `--experimental-drum`. That attachment intentionally does **not** create images. B1 provides a separate executable tool for explicit empty-image creation. This stage adds **seven files only**, leaves production `src/asm_disasm.cpp`, `src/main.cpp`, `inc/kyiv.h`, B1/B2/B3, H3/A1/A2 and the CPU opcode behavior byte-identical. It has no `--force`, overwrite or automatic attach mode.

A `KYIVDRM1` file is a **HOST_POLICY binary logical image**, not a hardware-format dump. The historical encoding of tracks, the 9864 / 511 geometry discrepancy and hardware validity remain **OPEN**, `HARDWARE_ORACLE=0`. No historical geometry is inferred.

## CLI and use

Build standalone (not linked into `kyivemu`; no Boost or CPU required):

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tools/isa07_d14c2h3b1_create.cpp -o tempkyiv/kyiv-drum-create.exe
```

Explicit creation:

```sh
tempkyiv/kyiv-drum-create.exe create tempkyiv/empty.kdr experiment-137 24 137
```

Grammar: `create IMAGE PROFILE TRACKS SLOTS`. IMAGE is one argument, may contain spaces or a Windows drive letter; parent directory must already exist. PROFILE is B1 ASCII identifier (1..64, `[A-Za-z0-9_.-]`). TRACKS and SLOTS are unsigned, strictly positive decimal integers with no `+`, `-`, whitespace or suffix. **Exactly three logical drums** are created, consistent with H3/A1's explicit attach syntax. Overall B1 HOST limit is 1,000,000 slots. The resulting file contains zero *written* cells: **UNWRITTEN is not WRITTEN +0**. Separate attach requires the same PROFILE/TRACKS/SLOTS, an explicitly selected lock PIN (1..3), and an explicit existing path.

## No-clobber publication and failure behavior

B3 `save_atomic()` may **replace** its destination, therefore it must **not** be called on the requested final name. B1 prevalidates geometry, encodes expected data and checks for an existing target; it writes through B3 to a fresh, same-directory, high-entropy temporary filename. `std::filesystem::create_hard_link(temp, final)` then **atomically publishes a new directory entry or fails if that entry exists**; it does not rename/replace an existing target. The implementation removes the temporary name after publication and on failure (best effort). Race tests require exactly one winner among concurrent creators and exact byte preservation of the winner.

This conservative HOST policy **fails closed** (`ATOMIC_CREATE_UNAVAILABLE`) on file systems lacking hard-link support. In particular, no non-atomic `copy_file()` or `exists()` → replacement fallback is used. A pre-existing file, symlink or directory is rejected (`IMAGE_EXISTS`) without modification, including an invalid `.kdr`. Missing parent, invalid geometry/profile and invalid decimal arguments fail before publication.

**Limits (not claimed):** sudden-power-loss durability/fsync; adversarial pathname or directory races (including attacks on a temporary name); automatic garbage collection after abrupt process death; portable atomic publication on filesystems without hard links; multiprocess *writes* to an already attached image. B3's contents/CRC and the final image's canonical bytes are independently tested, but the historical hardware layout is not implied. Concurrent create-new publication is tested; this is **not** a concurrent image-writer lock.

## Acceptance

Test the actual standalone native C++ creator plus a separate C++ B3 loader, checked byte-for-byte by an **independent Python** format/CRC implementation. Cases: small/asymmetric, `3×24×137`, `3×24×511`, randomized geometries, strict decimal validation, malformed profile and cap, existing arbitrary file/directory, missing parent, corrupted readback, geometry mismatch, six concurrent writers to the same target and no leaked sibling temp paths. No CPU change/side effect.

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tools/isa07_d14c2h3b1_create.cpp -o tempkyiv/d14c2h3b1_create.exe
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tests/isa/isa07_d14c2h3b1_provision_probe.cpp -o tempkyiv/d14c2h3b1_inspect.exe
python tools/isa07_d14c2h3b1_provision_sandbox.py --self-test
python tools/isa07_d14c2h3b1_provision_sandbox.py \
  --create-exe tempkyiv/d14c2h3b1_create.exe \
  --inspect-exe tempkyiv/d14c2h3b1_inspect.exe \
  --random-cases 20 --timeout 12
```

**Commit gate**: exact SHA-pinned baseline, 7 new files and zero production/CPU/tracked modifications; valid package selftest; real MSYS2 native provisioner + independent bytes + no-clobber race passes; H3/A2 actual production CLI and relevant regressions where necessary. Do not declare historical geometry or a hardware oracle.

## Next stage (B2, NOT included)

Optionally expose explicit `drum-create` as a production CLI subcommand and test full end-user restart cycle `create → attach → 25/23/24 → exit → reattach → read`. Only after native B1 confirmation, and without enabling create-on-attach or implicit replacement.
