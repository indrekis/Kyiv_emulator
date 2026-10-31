# H57 — explicit replaceable ROM module 1 integration (HOST POLICY)

## Historical provenance and scope

* GY62 printed pp. 8–9: fixed ROM `3010–3277`, operator NK `3000–3007`, replaceable modules `3300–3777`; five 64-word slots. `3777` is a special random-generator connection and **is not implemented**.
* GY62 printed pp. 93–95: first physical ROM block is assigned `3300–3377` and contains square root, scalar product, matrix×vector, power and constants. The 64 exact words were transcribed and checked in H54.
* H55/H56: the module-1 square-root routine on current CPU produces `sqrt(x)/4` while the fixed-ROM routine produces `sqrt(x)`; the historical intent of this difference remains `OPEN_SOURCE_INTENT`. No numeric correction is added.

## Implementation

Only the existing **image mode** accepts the explicit pair

`--rom-module1 FILE --rom-module1-sha256 HEX`.

The complete raw file is SHA-256 verified and strictly parsed as 64 distinct 41-bit octal words at exactly `3300–3377`. All validation occurs before creating the deferred CPU. The unchanged fixed-ROM verifier separately loads its 183 verified words. The H57 module is installed only if requested, and only during this startup. A program image with `--allow-rom` that attempts to overwrite the selected module slot is rejected in full before machine construction.

The module carries `SOURCE_QUALIFIED=1` only if its digest is the pinned H54/H56 source module SHA. Other files with explicit supplied and correct SHA may be loaded but are **HOST_UNVERIFIED**, not historical source data. The default without these flags remains byte-for-byte the established legacy image-mode path, with no implicit module install. No reset, hot swap, automatic relocation, physical cabinet switch or unknown-slot substitution is implemented.

`--rom-file`, `--rom-sha256`, `--allow-rom`, `--watch` and existing modes retain their previous argument semantics. No CPU arithmetic, ROM.txt or canonical test image is changed. Console tag: `H57-ROM-MODULE1 PASS WORDS=64 SHA256=... SOURCE_QUALIFIED=... HOST_OPT_IN=1`.

## Verification and open work

H57 gate requires a **successful** H56 V2 evidence (11 paired trials). It tests the full production executable in a temporary build tree, including default baseline, selected sqrt (1/4 -> 1/8), bad checksums, truncated/duplicate/out-of-slot/overwide module files, malformed header, image overlap and CLI misuse. Only after complete verification does it apply an uncommitted four-file change to the project. The gate never pushes or commits; `git diff --check` must pass. This is still a host-emulator integration, **not a physical-hardware oracle**.

Modules 2–5, and special `3777`, remain OPEN. Do not install fake words or infer absent modules are historical zeros.
