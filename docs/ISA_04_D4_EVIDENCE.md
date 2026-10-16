# ISA-04 D4 — zero detector and signed zero; cyclic carry comparison

**Baseline:** `a873546` (pushed `main`, ISA-04 D3). Supplements `ISA_04_D3_EVIDENCE.md` rather than rewriting that historical checkpoint. Historical results are distinguished from source-supported inferences and provisional emulator policy.

## 35 — normalization of -0 (schematic reconstruction; high confidence)

DPS64: Dashevsky–Pogrebinsky–Shkabara, *Vychislitelnaya mashina «Kiev»* (1964), **printed pp. 151–153**, section *«Операция сдвига и нормализации»*, specifically *«Нормализация (Нр)»* on pp. 152–153.

- The input number is accepted into `P1`; the normalization detector checks whether the most significant magnitude bit is 1, or **all bits of `P1` are zero**, in which case normalization is impossible and the normalizing-pulse generator is blocked (p. 153).
- In the blocked case the shift counter `ТД` is set to zero. Output of the order precedes output of the mantissa (p. 153).
- The result's **sign is output separately**, as in multiplication (pp. 152–153). The sign trigger is a separate element of the arithmetic unit; the condition “all P1 bits zero” refers to the magnitude register. See pp. 136–137 (structure of a summator bit) and the separate sign-trigger path of arithmetic operations.

**Source-derived inference (not an explicit sentence about `-0`):** sign-magnitude `-0` has a zero magnitude in `P1`, so the zero detector inhibits normalization regardless of its separate negative sign. Result: order 0, mantissa `-0` (octal `20000000000000`). This is a reconstructed microoperation rule, now tested as STRICT with that justification. The previous D3 `OBS` remains a historical record and will show the newly changed behavior, without itself enforcing a result.

CPU changes: (a) handle all zero magnitudes identically for shift count; (b) derive output sign from source-1 sign, *not* `res_for_norm < 0`. For nonzero values no change is expected. The `35` order/mantissa write order is unchanged.

## 07 — cyclic addition (comparison, still unresolved)

- GY62 (Glushkov–Yushchenko, 1962), printed **p. 11**, states that a carry from the sign position returns to the least significant sum bit.
- DPS64 (1964), printed **p. 102**, *«Циклическое сложение»*, gives a **real-number** correction: for `a1+a2 > 1`, output `a1+a2-1`, and for `a1+a2 < -1`, output `a1+a2+1`. Neither passage explicitly resolves the result for **exactly** `+1` or `-1`, which are not ordinary representable fractions in this 40-bit fixed-point convention.
- The current emulator implementation performs end-around carry adding **one extra LSB** after wrapping the magnitude. A concrete contrast: `(1/2)+(1/2 + 2^-40)` is `1+2^-40`. The DPS64 mathematical rule yields `2^-40` (`raw 1`), whereas the present emulator yields `raw 2`. For its negative counterpart, the emulator yields `-2` LSB versus the published real-number formula's `-1` LSB. This is a discrepancy worth investigating, not yet proof of how the actual bit-level summator behaved in every state.

D4 therefore **does not change 07**. Additional `OBS` cases print both the emulator's raw value and the integer-scaled DPS64 formula (where defined), making discrepancies visible without treating the mathematical text as a proven bit-level oracle. The D2 carry tests remain POLICY, not STRICT.

## Test classification

- `STRICT`: an implementation requirement with source-backed reasoning (including the stated schematic inference for `-0`).
- `OBS`: prints the observed current result and source-derived mathematical expectation, but **does not assert** that they must agree.
- `POLICY`: earlier D2 tests intentionally preserve the pre-existing `07` behavior.

## Remaining investigation before changing 07

1. Establish how the `07` operation gates the final summator carry at the transition between sign and magnitude, particularly exactly ±1.
2. Relate the ordinary fixed-point interpretation to the sign-magnitude and complement-code sequence shown in DPS64, pp. 94–103 and 136–141.
3. Confirm with historical arithmetic diagnostic programs, if accessible; do not infer an extra low bit solely from a generic modulo formula.

The project root `README.md` and reconstructed `ROM.txt` are untouched by D4.
