# ISA-07 D14-C2-H3/C2 — controlled process termination at B3 publication boundaries

**Pinned parent:** `9ff476b9cf4d5a632f4af2649ff46aca918d4377` (H3/C1). **Classification:** HOST_POLICY / test-only observation. Historical magnetic drum addressing remains **OPEN**; `HARDWARE_ORACLE=0`.

## Coverage delta and scope

B3 already tests malformed binary inputs and failed rename; H2/P1 and P2 test rollback within a live process; H3/B2 verifies independent-process persistence after normal exit; H3/C1 verifies recovery after a **handled** rename failure. H3/C2 tests a different boundary: the OS externally terminates a process at a known pause *without running C++ destructors or exception handlers*.

No production code or header, CPU opcode, `KYIVDRM1` format, existing unit test, or CLI changes. The runner copies the **exact pinned** `inc/kyiv_drum_persistence.h` and `inc/kyiv_drum_transaction_v1.h` to a private temporary include directory. It injects only test-specific pause gates into the copy of B3 and splits its single output write into two equivalent halves, flushing between halves to expose a partially written candidate. The generated modified header is never placed in tracked source or shipped as production code. The test C++ executable compiles against the isolated copies; `kyivemu` create/write/read executables remain real, unmodified production binaries.

Three termination points, each in its own isolated temporary directory and independently seeded canonical image:

1. `PARTIAL_TEMP`: after flushing the first half of the candidate output to the temporary image, with the output stream still open; externally kill process. The original target must remain byte-identical; a partial sidecar may remain and MUST NOT be promoted, deleted or opened as the target by the subsequent production process.
2. `PRE_RENAME`: after closing the fully encoded candidate but before `std::filesystem::rename`; kill process. The original target must remain byte-identical, and the sidecar must match the independently computed updated image exactly. Production reattachment must still observe the original target.
3. `POST_RENAME`: after successful `std::filesystem::rename` but before the in-memory session commit; kill process. On the tested platform, the canonical target must contain exactly the new bytes and a fresh production process must read that state. This is a completed *filesystem rename boundary*, not guaranteed power-loss durability or a distributed transaction.

The runner uses `subprocess.Popen` with distinct child processes, waits for an exact marker file published from the test-only gate, then calls `Popen.kill` and verifies that the child exited nonzero and that the marker was created before termination. It does **not** use a short sleep to guess the operation phase. The private C++ probe requires an exact marker file and the literal fixture name `crash.kdr` before attaching; without the marker it must refuse all mutation. Each phase gets its own clean sandbox and the independent Python format/CRC64/ECMA-182 oracle checks canonical bytes and sidecars. Signed -0, WRITTEN +0 and UNWRITTEN remain distinguishable. The final read uses a new unmodified `kyivemu` process. Temporary directories are deleted only by the Python runner when no child is running.

## Limitations and decision policy

These are **instrumented test-only** process interruption points. Splitting the writer into half-writes is intentionally non-production behavior, so `PARTIAL_TEMP` demonstrates an adversarial incomplete candidate rather than proving the production writer naturally produces exactly those bytes at some moment. The process is killed, not the host OS and not power; there is no `fsync`, directory sync, storage write barrier, hardware oracle, or proof of durability across reboot/power loss. Multiwriter synchronization, filesystem races, anti-symlink adversarial checks and crash cleanup/GC are OPEN. A sidecar is non-authoritative and MUST NOT be auto-promoted.

`POST_RENAME` means the rename call returned success **before** the artificial pause; it does not prove a process cannot be killed *during* the rename call or that rename is atomic on all filesystems. If MSYS2/Windows exhibits different semantics or a native test fails, record the observed failure, do not weaken the oracle and do not claim an unsupported guarantee.

## MSYS2 acceptance

After strictly pinned package application from a clean `main`:

```sh
# Compile only the two unchanged production binaries, if not already available:
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
  tools/isa07_d14c2h3b1_create.cpp -o tempkyiv/h3c2_create.exe
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Iinc \
  src/main.cpp src/asm_disasm.cpp -o tempkyiv/h3c2_kyivemu.exe

python tools/isa07_d14c2h3c2_termination_sandbox.py --self-test
python tools/isa07_d14c2h3c2_termination_sandbox.py \
  --create-exe tempkyiv/h3c2_create.exe \
  --emu-exe tempkyiv/h3c2_kyivemu.exe \
  --cxx g++ --timeout 20
python tools/isa07_d14c2h3c2_audit.py --self-test
python tools/isa07_d14c2h3c2_audit.py
```

Expected `D14C2H3C2-TERMINATION PASS CASES=4/4 ...` and audit PASS, plus zero tracked changes and exactly five untracked files. The runner **must** compile the test probe dynamically against the generated private headers, never against the production header by accident. No commit/push before genuine MSYS2 results and an independent exact-file-set commit gate. A previous completed test is not rerun unless the H3/C2 results require it.
