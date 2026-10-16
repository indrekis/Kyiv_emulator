# ISA-06 D3 — historical shift words from GY62 fourth RAM test

**Base:** `c194d04` (`main`, ISA-06 D2). Characterization-only: no CPU/ROM/old tests modified.

## Evidence

- Glushkov–Yushchenko (1962), **printed p. 170**: fourth RAM test is described as recording a traveling one or zero (commands 0122–0136), followed by RAM reading and verification (0140–0155).
- Same book, **printed p. 171**, fourth RAM test listing:
  - `0131: 13 3012 0021 0021`
  - `0150: 13 3012 0021 0021`
  - `0156: 13 3012 0017 0017`
- Same book, **printed p. 12**: opcode 13 uses six low bits of the first-address cell as the count; its sign selects left/right, all 41 bits shift, discarded bits vanish; effective addresses may be modified.
- Dashevsky–Pogrebinsky–Shkabara (1964), **printed p. 18**, shift description and command encoding, corroborating the three-address structure.
- Emulator `mem/ROM.txt`, line for `3012`, currently reads `00 0000 0000 0001` (one-bit positive shift). **This is a human transcription, not an independently verified original ROM word.**

## Qualification boundary

`tests/isa/isa06_d3_historical_shift_probe.cpp` executes the **three authentic instruction words** at their authentic addresses. It supplies a controlled input at `0021` or `0017`, rather than reconstructing the full historical fourth RAM test. The tests verify left shift by one, in-place writing, sequential C, fetched K, and unchanged A/P/Cy, using the documented logical-shift rule. Tests therefore qualify instruction behavior **in a synthetic operand context**, not the historical program's checkpoints or outcome.

The emulator's transcription of ROM 3012 is reported separately as OBS. The STRICT cases inject `1` into ROM 3012 as an explicit test fixture, justified by the documented positive one-bit shift semantics, **not** by treating the transcription as historical ground truth.

**ROM loading caveat (D3 diagnostic correction).** `Kyiv_t` currently opens `../mem/ROM.txt` relative to the process working directory (`inc/kyiv.h`, constructor); it does not check whether the open succeeded. Tests are normally invoked from the repository root, where the transcription instead resides at `mem/ROM.txt`. Therefore a default-constructed CPU reporting `ROM[3012] = 0` does **not** imply that the transcribed file contains zero. The OBS line now reports the constructor value, whether the constructor input path is available, and the independently read transcription value from `mem/ROM.txt`. This diagnostic is about file resolution/loading, not independent evidence of the historical ROM. No constructor or CPU behavior is changed in this package.

This packet does not resolve hardware timing, undocumented address ranges, ROM transcription errors, or full historical RAM-test behavior. No CPU correction is justified by these tests alone.
