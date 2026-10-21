# ISA-07 D14-C2-H3/C1 — failure → reopen → resume qualification

Pinned baseline: `59e3fd25b8655ca869f7510b8c4e5cd3598d897e` (H3/B2).
This C1 stage is **tests/docs only**, no production C++, CPU, B1/B2/B3/H1/H2/P1/P2/A1/A2/B1/B2 changes.

## Why this gate exists

Earlier B3 and H2/P2 already validated deterministic rename failures, in-memory transaction rollback and temporary-file cleanup. H3/B2 validated the ordinary independent-process persistence cycle. C1 covers the **composed lifecycle** not asserted by either alone: data successfully committed by a production process, a later failed overwrite, a *new production process* that reopens the prior committed data, and an independently verified successful update after recovery. It does not repeat all H3/B2 random, multi-drum and signed-zero cases.

## Exact scenario and trust boundary

The Python runner creates a marked, exclusive temporary directory and invokes three independent native executables (production B1 creator, production `kyivemu`, test-only C++ fault probe), each with a timeout. The test-only probe **refuses** any directory without an exact `.h3c1-isolated-sandbox` marker and must never be run against a real user image. The runner uses the HOST 3-drum, 2-track, 8-slot geometry, profile `h3c1-recovery`, and pinned drum 1. It provisions a fresh image and writes a raw 3-word group starting at logical position 3. The independent Python oracle checks each byte of the full canonical file (header, 3×2×8 bitmap, raw 41-bit words, written count, CRC64/ECMA-182).

The C++ probe first attaches the already-valid image and prepares a different write through the *real* `kyiv_drum_transaction_v1::session`. It then temporarily moves the image to a sibling backup and occupies the final path with an **empty directory**, forcing `std::filesystem::rename(temp, final)` to fail with `REPLACE_FAILED`. Regardless of whether that expected failure occurs, it restores the original target **before reporting the result**, checks session snapshot/preparation and independent B3 reload, and exits. The parent verifies exact original file bytes and that no temporary file or backup remains. Recovery verification uses a **new** production CLI process, not that probe's session.

Next, another production CLI process writes a different 3-word group to the same cells. A subsequent fresh process must read those exact raw words. Sidecars with names matching plausible interrupted B3 and B1 temporary artifacts are then planted **by the test**, not by a simulated crash. Production attachment must use only the specified final `.kdr`, neither promoting nor garbage-collecting these sidecars. Finally, a deliberately CRC-corrupt final image must be rejected without silently selecting an orphan; the test restores the valid fixture explicitly and checks readback again.

## Explicitly **NOT** proven

- There is no process kill, power failure, `fsync`, parent-directory synchronization, sector tear or durability claim. Orphans are synthetic; this does not prove which artifacts a real crash would leave.
- No multiwriter lock, stale attached-session detection, cross-process serializability or conflict resolution. Uncoordinated writers remain out of scope and unsafe; B1's concurrent *creation* qualification is unrelated.
- The `.kdr` format, `a3_linear_v1` address mapping and sidecar naming are HOST policies; `HISTORICAL_MAPPING=OPEN`, `TRACK_MAPPING=OPEN`, `HARDWARE_ORACLE=0`.
- Error signalling is tested for this deterministic filesystem obstruction, not every possible disk/filesystem/ACL failure. Replacing arbitrary, user-owned directories, hardlinks or symlinks is neither implemented nor tested.

## Build and acceptance (MSYS2 MINGW64)

From repository root, **after** a strictly pinned package apply and with a clean tracked tree:

```bash
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tools/isa07_d14c2h3b1_create.cpp -o tempkyiv/h3c1_create.exe
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Iinc \
  src/main.cpp src/asm_disasm.cpp -o tempkyiv/h3c1_kyivemu.exe
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tests/isa/isa07_d14c2h3c1_failed_replace_probe.cpp -o tempkyiv/h3c1_fault.exe
python tools/isa07_d14c2h3c1_recovery_sandbox.py --self-test
python tools/isa07_d14c2h3c1_recovery_sandbox.py \
  --create-exe tempkyiv/h3c1_create.exe \
  --emu-exe tempkyiv/h3c1_kyivemu.exe \
  --fault-exe tempkyiv/h3c1_fault.exe --timeout 15
python tools/isa07_d14c2h3c1_audit.py --self-test
python tools/isa07_d14c2h3c1_audit.py
```

The acceptance line is `D14C2H3C1-RECOVERY PASS CASES=8/8 ...` (plus auditor PASS). If filesystem behavior differs, report FAIL; do **not** weaken the assertion or reinterpret errors as success. Check previous B3/P1/P2 and H3/B2 evidence before deciding whether a particular regression needs rerun. **No commit or push** before genuine MSYS2 results and a separate exact-set commit/postcommit gate.
