# ISA-07 D15/A2 — shared HOST image parser and bounded CLI mode

Pinned parent: `68fa06f247f3b3a70ba37a72283469b6cec6b137` (D15/A1). This stage integrates the already qualified `KYIV41-OCT1` loader and bounded execution into the actual `kyivemu` executable, without CPU changes or historical-format claims.

## End-user modes

- Previous `command`, `expression`, `removable_memory`, drum opt-in, and `--block-overflow-stop` grammar remain as-is. No default change to their unbounded execution loops.
- New opt-in syntax: `kyivemu image FILE.k41 START_OCTAL MAX_STEPS_DECIMAL [--allow-rom] [--watch ADDR_OCTAL]...`.
- The original stand-alone `tools/isa07_d15a1_run_image.cpp` uses the **same** `inc/kyiv_host_image_v1.h` parser and run control. Its `D15A1-*` labels remain stable. The production CLI uses `D15A2-*` labels, equivalent after prefix normalization.
- `--experimental-drum ...` and `--block-overflow-stop` suffixes are explicitly **rejected** in `image` mode with `IMAGE_SUFFIX_UNSUPPORTED` in this first integration, even though they remain supported in the original modes. Thus this gate makes no new claim regarding peripheral interactions or overflow policy for image mode.
- `START_OCTAL` and watch addresses are exactly four octal digits; the step bound consists only of decimal digits and is 1..100000. Image records contain four octal address digits and fourteen octal digits for the full raw 41-bit value. Images are entirely preflighted before any write.
- RAM admissions `0001..1777`; ROM `3000..3777` only if `--allow-rom`. Cell `0000` and `2000..2777` are not qualified as user image/load/start/watch addresses. Preserve `+0` and `-0` distinctions and all 41 raw bits.
- One step = one real `Kyiv_t::execute_opcode()` call; `STATUS=CPU_STOP` or `STATUS=LIMIT`. The existing CPU trace remains printed; lines prefixed `D15A2-` are the stable machine-readable HOST report. Stop causes are not fully classified as original hardware conditions.

## Staged integration and source constraints

The only changes to existing files are a replacement of the standalone A1 wrapper with a thin consumer of the shared header and an additive image-mode branch and header include in `src/asm_disasm.cpp`, *before* the original legacy-mode dispatch. The new shared header combines A1's parse, validation and execution logic without introducing a second implementation. `src/main.cpp`, `inc/kyiv.h`, the drum adapters, ROM files, and the historical source evidence must not be changed.

`Kyiv_t` still initializes `ROM.txt` relative to the working directory and silently tolerates failure to open it. This limitation is neither disguised nor addressed by the image CLI integration: `ROM_BASELINE=OPEN`. Any future history-derived tests require an explicit, verified ROM source. `KYIV41-OCT1` remains a HOST transport format, not a representation of punch cards, drum recording, or original media.

## Validation requirements

From pinned `main` with only the seven allowed files changed or added, build both **real** production `kyivemu` and the A1 standalone wrapper. Require 22 cases of exact normalized A1/A2 return/output parity with whole-image immutability, two explicit suffix rejections, two exact legacy `expression` equivalence checks against production sources obtained from pinned `git show`, plus audit PASS. The native runner creates all images and the previous-production executable in private temporary directories and uses explicit timeouts. A static audit's `REAL_NATIVE_GATE=PENDING` never means native tests were actually run.

The historical test transcription of GY62 (printed pp. 165–179), per-word provenance, ROM baseline, full STOP classification, peripheral fidelity, 9864/511 drum geometry reconciliation, crash durability and concurrent writer support are subsequent work, not achieved by D15/A2.
