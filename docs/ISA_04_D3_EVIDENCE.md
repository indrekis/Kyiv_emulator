# ISA-04 D3 — signed zero, normalization and cyclic carry: source audit

**Base:** `57b0c88` (`main`). Supplements `ISA_04_ARITHMETIC_AUDIT.md` and
`ISA_04_D2_EVIDENCE.md`. This phase changes only two narrow CPU behaviors:
**multiplication sign at a zero magnitude** and **normalization of +0**.
All octal codes are prefixed with `0` in explanatory text where helpful.

## Sources and evidentiary thresholds

- GY62 = Glushkov–Yushchenko, *Vychislitelnaya mashina "Kiev"*, 1962,
  printed pp. 11–12 (instructions 07, 10, 11, 35).
- DPS64 = Dashevsky–Pogrebinsky–Shkabara, *Vychislitelnaya mashina "Kiev"*,
  1964, printed pp. **102–103, 146–150, 152–153**.
- The DPS64 scan is image based. Page numbers below are **printed page
  numbers**, not PDF indices. Do not confuse descriptions of the physical
  sign trigger with the ordinary mathematical value of a signed zero.

### 10 and 11 — multiplication, including zero-valued results (HIGH evidence)

DPS64, p. 149, "Операции умножения": the sign of the product is formed by
modulo-2 addition of the operand signs in the sign trigger of register P2.
DPS64, p. 150: at the result-output pulse, the product **sign** is driven
from that sign trigger to the corresponding output bit. The described
sign path is independent of the magnitude-dependent early termination.

Consequently the emulator must compute the output sign as `sign1 XOR sign2`,
**not** `res_mul < 0`. In particular `(-0)*(+1/2)` gives `-0`, and a negative
nonzero exact product truncated to zero retains a negative sign. This phase
adds corresponding STRICT regression tests, including operation 11 rounding.
No change to magnitude computation or to rounding is proposed here.

### 35 — normalization of +0 (HIGH evidence), -0 (OPEN)

DPS64, pp. 152–153, "Нормализация": if the input is already normalized
or **cannot be normalized because all bits of register P1 are zero**, the
normalizing-pulse generator is inhibited, shift counter TD is set to zero,
and the operation proceeds to result output. The order is output first,
then the normalized number. For **+0**, this gives no shifts, order `0`,
returned mantissa `+0`. The previous emulator-produced order `047` (octal,
39 decimal) was not established by any historic source; D3 corrects `+0`
only and asserts this in a new STRICT regression test.

**-0 is not settled by the above passage.** It is a distinct full 41-bit
code, whose sign trigger is set, and the described zero detector is given
as a register-wide check without enough detail to establish whether it
excludes the separate sign position. D3 does **not** change or claim
historically correct `35(-0)`. Its output remains `OBS`, despite the
asymmetry of the temporary implementation. A subsequent microoperation
study must resolve zero detection and sign-bit transfer before changing it.

DPS64 p. 153 also states the order is output before the mantissa: if the
second and third effective addresses coincide, the final memory value
is the mantissa. The new test checks this for a nonzero input; this does
not settle all possible operand overlap or memory timing configurations.

### 07 — cyclic addition (still OPEN at disputed final LSB)

GY62 p. 11 says the carry from the sign position enters the least
significant summator position. DPS64 p. 102 gives the real-valued rule
`a+b-1` for sum > +1 and `a+b+1` for sum < -1, whereas pp. 146–147
specify the altered overflow-interlock signal. DPS64 pp. 136–139 describe
how carries form in the summator, but the available text alone does not
unambiguously establish an executable instruction-level result at all
boundary encodings (especially `|a+b|==1`). D3 therefore **does not
change 07**. The D2 POLICY tests remain POLICY, not historical oracles.

## Interpretation of the test suite

- STRICT: evidence-supported behavior; regression must pass.
- OBS: factual current output printed without historical approval.
- 07's previous POLICY tests remain in D2 unchanged.

## Future checks

1. Reconstruct zero detection in registers P1/P2 and sign-trigger transfer
   in normalization using DPS64 figs. 69–73 and timing of output pulses.
2. Reconstruct cyclic carry at the exact-one boundary from the bit-level
   transfer, not from an approximate fractional arithmetic identity.
3. Characterize a register-zero result due to shift underflow, explicitly
   distinguishing the sign of the result from the magnitude zero detector.
4. Compare the published historical arithmetic test programs with the
   revised multiplication behavior before marking an entire device tested.
