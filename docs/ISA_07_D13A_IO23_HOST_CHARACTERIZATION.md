# ISA-07 D13-A — IO23 host-output characterization (no CPU changes)

**Baseline:** `f7c2b405a49fc6956628ed4e94bd3380e9726a43`, following committed D12-B. **Stage:** observation, not a fix. D12-B's strict `IO24` input contract and all earlier gates remain untouched. New files only. No physical-drum oracle.

## Historically qualified vs host-specific

- GY62 (Glushkov–Yushchenko, 1962), printed p. 15: `23` (МБЗ) sends the inclusive RAM interval `[a1,a2]` to the drum and passes control to `a3`. This is **SOURCE_STRICT** for the memory interval and successful branch, not for the host serialization format or physical write-error response. The established two-step D8-B and D9-B probes qualify the digital branch.
- `K <- M[C]` immediately after `C <- a3` is an **EMULATOR_CONVENTION**. `execute_opcode()` fetches again at the next step; this is not independent historical evidence of exact prefetch timing.
- Physical RAM `0000..1777` (octal) and 41-bit sign/magnitude are source-qualified machine bounds (GY62 printed pp. 7–8). Current C++ memory permits reading addresses beyond physical RAM; this is an observable **host-code risk**.
- The filenames, decimal text representation, trailing spaces, truncate-on-open behavior, and lack of durability guarantees are **HOST_POLICY**/**CODE_OBS**, not historical drum format.

## Current `src/main.cpp` behavior at the pinned base

`opcode_write_magnetic_drum` opens `../magnetic_drum.txt` with default `std::ofstream` truncation. On a successful open it iterates inclusively from `addr3_shifted.source_1` to `source_2`, writing `word_to_number(kmem.read_memory(i))` followed by one ASCII space per word. An unsuccessful open prints `Unable to open file` and still branches to `a3` and prefetches `K`; the stream's later write/flush/close failures are not checked. There are no guards for a reversed interval, physical RAM bounds, or representable raw 41-bit words.

`word_to_number` uses the sign bit and the low 40 magnitude bits. A negative zero word is serialized as `0`; an overwide host word is silently projected onto a 41-bit sign/magnitude interpretation. For the reversed interval, unsigned `for (i=a1; i<=a2; ++i)` executes zero times, producing an empty truncated file, then branches; this is safe to characterize but not qualified hardware behavior. A one-cell source at octal `02000` or within host ROM also serializes, despite being outside physical RAM.

**Important asymmetric paths:** `IO23` writes `../magnetic_drum.txt`; D12-B `IO24` reads `../../mem/drum_in.txt`. Even with a compatible decimal token, these commands do **not** share persistent media. `IO23` ignores the configured `drum_num_write` and `drum_zone_write` parameters (even after a genuine `IO25` write setup). `IO24` consumes a selected host line and byte offset. Do not claim a `23 -> 24` roundtrip works without new shared-media policy.

## Evidence and acceptance matrix

`tests/isa/isa07_d13a_io23_host_observation_probe.cpp` executes genuine CPU instruction steps and snapshots the entire emulator memory (`0000..3777` octal) before `23`, verifying that output is non-mutating. Successful IO23 must prefetch a genuine XOR at `a3`; the next CPU step executes `5 XOR 3 = 6`. The `io25-setup` case executes three real CPU steps (`25`, `23`, XOR) and checks the write configuration. Input and output fixtures are sandboxed per case; no repository media files are mutated.

`tools/isa07_d13a_io23_host_sandbox.py` checks **20 exact current-code observations**: range, single, offset, legacy, fromzero, overwrite, open-error, negative, negative-zero, max-positive, max-negative, sign-only, reversed, beyond-physical, rom-source, drum-params, modified-addresses, alternate-branch, io25-setup, highbits-masked. Checks include exact *bytes* (including trailing spaces), `C/K`, RAM integrity, unrelated registers, selected drum registers and real next opcode, as well as absence of extra host files.

The successful preflight of 7/7 `IO23` cases from D8-B on MSYS2 is already established. The new 20/20 suite **must be executed on actual `src/main.cpp`** before committing D13-A. Cases such as open-error, reversed, sign-only and outside-physical intentionally reproduce undesirable host behavior; they cannot be retained as acceptance gates after future fixes.

## Next steps (not part of D13-A)

- **D13-B:** design robust output prevalidation, sign-preserving lossless textual representation if chosen, physical RAM interval validation, explicit write/flush/close errors, and a defined host-side atomic-write policy. Keep source-qualified `C=a3` on success; do not assume the historical machine's error path.
- **D13-C / separate architecture decision:** a logical drum image indexed by track/zone/word, shared by `23` and `24`, with a versioned lossless 41-bit representation, deterministic address mapping and explicit persistence/failure policy. Keep legacy `../magnetic_drum.txt` and `../../mem/drum_in.txt` adapters separate during migration. Prove `25 -> 23 -> 25 -> 24` using genuinely executed instructions. This is **HOST_POLICY**, not reconstructed drum-media encoding or latency.
- Output `22` (printer/perforator) shares a similar unvalidated loop; handle that later rather than silently modifying it here.

No hardware emulator, timings, device-status specification, SIMH port, source repairs or CPU mutation are authorized by this observation stage.
