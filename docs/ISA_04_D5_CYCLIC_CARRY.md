# ISA-04 D5 — cyclic addition (`07`): separate hardware evidence from emulator policy

**Base:** `6f44fba` (`main`, after ISA-04 D4). **Scope:** research and probes only: no CPU, ROM, root `README.md`, or existing-test changes. The `docs/HISTORICAL_GY1962_TESTS_PLAN.md` roadmap remains in force; no historical program is transcribed in D5.

## Verified textual evidence

- **GY62**: V. M. Glushkov / E. L. Yushchenko, *Vychislitel'naya mashina «Kiev»*, 1962, **printed p. 11**, `Циклическое сложение (Ц+)`: unlike regular addition, overflow does **not** stop execution; a carry from the sign position enters the lowest bit of the summator. The description does **not** give a bit-level worked example or distinguish `|sum| == 1` from `|sum| > 1`.
- **DPS64**: L. N. Dashevsky / S. B. Pogrebinsky / K. O. Shkabara, *Vychislitel'naya mashina «Kiev»*, 1964, **printed p. 102**, `Циклическое сложение`: `a1+a2>1` yields `a1+a2-1`, and `a1+a2<-1` yields `a1+a2+1`. It explicitly says the operation's sequence is that of addition apart from overflow-signal handling. See also **printed pp. 94–98** for direct/complement code and summator value, and **pp. 100–102** for the common arithmetic microoperations and table 4.
- Both descriptions are kept **as written**; GY62 speaks about an internal carry, DPS64 about a numerically expressed memory result. They are not necessarily contradictory until exact wiring and number-code transformations are reconstructed. Neither passage explicitly settles a result for a mathematical sum **exactly** `+1` or `-1`, which is not a representable nonzero magnitude in the 40-bit fixed-point field.

## Explicit scaled comparison

Define `M = 2^40`, the code for the fixed-point magnitude `1` (which is **outside** the 40-bit magnitude range). The operand values are signed magnitudes `n/M`, with `0 <= |n| < M`. The current CPU executes an algebraic sum of operand magnitudes and, if `|sum| >= M`, computes `(|sum| + 1) mod M`, keeping the original sign of the sum. This is **POLICY**, an implementation snapshot and *not* a source-verified result.

For a sum with `|sum| > M`, the **scaled candidate** suggested by DPS64 p. 102 is `|sum| - M`, retaining the sign. For `M + k`, `k>=1`, the candidate therefore has magnitude `k`, whereas current POLICY yields `k+1` (one LSB higher). This translation presumes that the formula describes the final machine code rather than an intermediate summator state; the source does not independently prove that presumption. Such comparisons are `OBS` / `CANDIDATE`, not `STRICT`.

| Signed algebraic sum (scaled integer) | Current machine code, octal magnitude | DPS64 scaled **candidate** magnitude | Status |
|---|---|---|---|
| `M` | `1` | **undefined by strict >1 condition** | `OBS` |
| `M+1` | `2` | `1` | `OBS` |
| `2*M-2` | `M-1` | `M-2` | `OBS` |
| `-M` | `-1` | **undefined by strict <-1 condition** | `OBS` |
| `-(M+1)` | `-2` | `-1` | `OBS` |

A sign-magnitude result of `+0` versus `-0` is also **not established** by these two passages for exact cancellation, input signed zero, or wrapped zero. Do not infer a rule from standard C++ integer arithmetic.

## D5 test design and non-goals

`tests/isa/isa04_d5_cyclic_probe.cpp` runs actual opcode `007` instructions through `Kyiv_t::execute_opcode()`:

- `STRICT`: uncontroversial nonoverflow sums with nonzero output, plus the documented fact that overflow **does not halt or skip an instruction**. The numeric output of those overflow cases is **not** asserted as historical truth.
- `POLICY`: fixed expected machine words for existing code paths; changing them in a later evidence-based fix must be accompanied by an explicit test reclassification, not silent test modification.
- `OBS`: the existing machine-word output alongside the DPS64 scaled candidate (only for `|sum| > M`), the unresolved `|sum| == M` boundary, and zero-sign cases. These emit evidence but cannot fail merely because competing interpretations differ.

No machine-accuracy claim is made for the supplementary mathematical candidate. No `ROM.txt` values or historical diagnostic program codes are changed.

## To resolve D5's remaining uncertainty

1. Trace the sign-register path, two's-complement conversion and summator carry feedback in DPS64 printed pp. 94–103 and the later arithmetic-unit circuit description; distinguish the internal summator code from the converted result sent to memory.
2. If a complete worked machine-code example, control program, or diagnostic printout exists, derive the full 41-bit *output code* including the sign and least significant bit. Prefer material already identified in GY62 appendix 2, printed pp. 165–179; do **not** transcribe it in this stage.
3. Only then replace the corresponding `POLICY` test with a `STRICT` source-backed oracle and make a minimal `07` CPU change. If source evidence remains insufficient, retain the current policy explicitly as provisional and close D5 as an unresolved historical question, not a proven hardware emulation.
