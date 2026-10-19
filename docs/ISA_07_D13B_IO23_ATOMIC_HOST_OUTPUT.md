# ISA-07 D13-B — checked, staged IO23 host output

**Exact Git baseline:** `506cfec97bfbedc6da6e9a0717ca4eb525edb067` (D13-A). D13-A's 20 genuine-CPU cases characterized the former adapter. **Scope:** IO23 handler and one include in `src/main.cpp`; nine new files; IO20/21/22/24/25 and arithmetic unchanged.

## Evidence classes

* **SOURCE_STRICT:** the documented IO23 reads an inclusive `[a1,a2]` RAM interval and transfers control to `a3` on successful transfer; Glushkov–Yushchenko 1962, printed p.15. A Kyiv machine word has 41 bits in sign/magnitude form, with bit 40 the sign; printed pp.7–8. These source facts do **not** establish a digital file format or OS-level error behavior.
* **EMULATOR_CONVENTION:** after success, `C=a3; K=memory[C]`. K prefetch timing is not an independent device hardware oracle.
* **HOST_POLICY:** strict range `0000..1777` octal, reject reversed intervals and overwide 41-bit RAM values, stage the complete output, serialize signed decimal text with a trailing ASCII space for every word. `-0` is spelled `-0` to retain its sign. Cell 0 reads as zero.
* **HOST_POLICY:** write bytes to a temporary file in the destination directory, `flush` and `close`, then `std::filesystem::rename` to the original path; on failure, remove the temporary file and leave existing destination data untouched. Errors throw `IO23: REASON` before `C/K` transfer. The host output path remains `../magnetic_drum.txt`.
* **OPEN:** multithreaded/multiprocess writer races, OS/filesystem crash durability (`fsync`/directory barriers), physical magnetic-drum track/zone format and fault response. **Do not call the file update power-loss durable or multi-writer atomic.**

## Changes from D13-A observations

Old `open-error` continued with `C=a3` despite no output. Old `negative-zero`/`sign-only` lost the sign; old `reversed` wrote empty output; old `beyond-physical` and `rom-source` read outside the documented RAM; old `highbits-masked` silently masked a non-machine-width source word. All six kinds of behavior are intentionally superseded by checked host policy. The archived D13-A probes and audit remain byte-for-byte unchanged.

## Gates before commit

1. Exact HEAD and `HEAD:src/main.cpp` blob, exact normalized handler replacement and include; nine new-file SHA checks; no other tracked mutations.
2. Host formatter: 225 independently computed cases, signed zero, sign/magnitude max, overwidth and empty inputs. File replacement test with preexisting file, invalid output target, preservation of old bytes and no leftover temporary files.
3. Real `Kyiv_t`: successful `IO23 -> XOR`, `IO25 -> IO23 -> XOR`, whole-memory/state check, and rejects leaving C/K and RAM unchanged; replacement/no-temp-leak check in isolated host cwd.
4. Functional regression: D12-B's 22 groups (`D8B 10`, `D9A 4`, `D9B 7`, `IO21 5`, `IO20 50`, `ISA06 STRICT 89`, `POLICY 40`) with only its HEAD pin adjusted in the NEW D13-B runner, plus current D13-A positives; obsolete D13-A policy cases remain archival.

No source-qualified assertion of actual drum media encoding. Later shared-drummodel project will connect IO23/24 through a common logical image as a separately reviewed HOST_POLICY feature.
