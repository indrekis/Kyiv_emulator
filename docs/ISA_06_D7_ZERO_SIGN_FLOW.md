# ISA-06 D7 — adder sign-path audit: zero result, exact compare, and sign branch

**Base:** `49ccd7a` (ISA-06 D6). Adds this note and `tests/isa/isa06_d7_zero_sign_flow_probe.cpp` only. **No CPU, ROM, existing tests, README, or historical corpus edits.** The objective is a narrowly instrumented *consequence test*, not a historical adjudication of `01`'s zero sign.

## Sources and levels of evidence

**GY62:** V. M. Glushkov and E. L. Yushchenko, *Vychislitel'naya mashina "Kiev"* (1962), **printed pp. 11, 13, 17, 170–171**. Page 11 defines arithmetic addition `01`; p. 13 explicitly states that subtracting two equal numbers yields a **negative zero** and defines exact comparison (`16`) as equality of *both sign and magnitude*, while sign branch (`31`) uses the sign of the first operand. Page 17 explicitly distinguishes positive/negative zero. The fourth RAM test in appendix 2 (pp. 170–171) contains the original **`0123 = 01 0021 0000 0020`** and **`0141 = 01 0021 0000 0020`** words and later code-exact comparisons. These original machine words are historical; their test operands below are injected, not authenticated historical initial memory.

**DPS64:** L. N. Dashevsky, S. B. Pogrebinsky, K. A. Shkabara, *Vychislitel'naya mashina "Kiev": proektirovanie i ekspluatatsiya* (1964), **printed pp. 94–98, 100–103, 136–139, 144–146**.

- **P. 94:** machine numbers have distinct `+0` and `-0` under the documented external representation. The exposition also distinguishes their order for comparisons; this is not a zero-sum sign rule.
- **Pp. 96–98:** the adder is based on per-bit inversion / complementary internal codes and has a carry/overflow path; a sign-magnitude integer sum alone does not reproduce all internal states. This description does **not** uniquely fix the output sign of all exact-zero sums.
- **Pp. 100–103, fig. 62, table 4:** reception of the first and second numbers, modular accumulation, carry propagation, operation-end and sign-output control are separately timed. The documented `01` sign-dependent reception signals must be distinguished from any conjectured “prefer sign of first operand” software rule.
- **Pp. 136–139, fig. 67:** the bit-slice summator has two input registers, a summator trigger and a carry chain, rather than an atomic mathematical-int add.
- **Pp. 144–146, figs. 71–73:** the sign bits are latched in sign triggers. On result issue, the sign is taken from the summator's second sign trigger (`ТЗн2См`), separately from the magnitude-code output path. This alone does **not** disclose a complete state table of those triggers for exact zero, including all carries.

**Deduction vs source:** the *hypothesis* that `(-0)+(+0)` should preserve a `-0` code is supported indirectly by the intended RAM-diagnostic use of a travelling zero and the hardware sign-path architecture. It remains a **candidate, not a proven historical ISA oracle**. In particular, converting external negative zero to an internal complementary representation does not by itself establish the final sign without the carry/micro-timing details. The `−0` result of **equal-value subtraction `02`** is a different case: it is explicit in GY62 p. 13 and is `STRICT`.

## D7 scope and method

This probe checks two distinct layers:

1. **Historical STRICT control semantics** (8 cases). Four direct `16` comparisons exercise `+0 == +0`, `-0 == -0`, and both different-sign pairs; two direct `31` branches use preloaded `+0` / `-0`. Two three-step chains execute **equal-value subtraction `02`** (positive equal numbers, negative equal numbers), then `16` against injected `-0`, then `31`, and assert exact 41-bit `-0`, the fetched instructions, next PCs, sign branch, selected preserved registers, and no stop. These expectations follow GY62, *not* the current C++ addition implementation.
2. **Zero-sum OBS consequences** (8 cases). Six synthetic `01` sums cover all four signed-zero pairs plus opposite-signed cancellation of equal nonzero magnitudes, in both operand orders. Two more use the **historical first word** at actual PC `0123` or `0141` with injected `RAM[0021] = -0`. After executing `01`, an **instrumented, synthetic** `16` checks equality of the result code to `-0`, and a synthetic `31` branches based on the resulting sign. The observed code, comparison decision and sign branch destination are logged without normative assertions. **The synthetic continuation is not an original historical RAM-test trace.** The pair of diagnostic branch words is placed at both possible comparator continuation PCs so every test takes three steps regardless of the observed sign.

All fixtures are explicit and in octal: `ROM[3026] = 20 0000 0000 0000` (`-0`) is written using `write_rom`, bypassing the separately known CWD-dependent ROM loader. `ROM[3026]` is **not** considered independent historical ground truth. Cell `0000` remains the hardwired `+0`. In a normal test chain, operands are at `0002` and `0003`, destination `0004`; comparator and sign branch follow at `PC+1` and `PC+2`/`PC+3`. The genuine instructions at `0123`/`0141` use `0021`, `0000`, `0020` exactly as published; only their *successor* commands are diagnostic.

## Interpretation and decision gate

- Success of all eight STRICT checks confirms sign-sensitive downstream control and equal-subtraction `-0` independently of any conjecture for `01`.
- Whatever eight OBS cases report for `01` is a **characterization** of the emulator and how its output controls `16` and `31`, not a historical adjudication.
- If a future, explicit reconstruction of fig. 71 and table 4 uniquely predicts a different sign, prepare a **separate** candidate CPU change and re-run D1–D7 plus D5's full-loop observations. Until then, **no CPU change**.
- No proof is claimed for full fourth-RAM-test correctness, undocumented addresses, ROM provenance or CWD-independent loading, hardware faults, or an exact physical timing model.
