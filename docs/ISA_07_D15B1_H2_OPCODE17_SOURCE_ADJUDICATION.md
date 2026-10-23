# D15/B1-H2 — evidence for operation 17 (octal), 41-bit equivalence

Baseline: `b2e498bfa7715c645708c7c143a80deeb5ce65e9` (H1 observation only). This stage records **source evidence and testable hypotheses**; it does **not** modify CPU semantics or the original historical .k41 image.

## Source comparison, preserving conflicting evidence

| Direct source | Printed / PDF page | Machine opcode | Actual semantics supported | Evidence |
|---|---|---|---|---|
| V. M. Glushkov, E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), command-description chapter | printed p. 11 / PDF p. 12 | octal 17 | XOR, *neravnoznachnost* | Explicit truth table: 00→0, 01→1, 10→1, 11→0. |
| Same volume, historical arithmetic-unit test I (logical operations) | printed pp. 172–173 / PDF pp. 171–172 | octal 17 | XNOR, *equivalence* | Printed check rows 0073–0106 expect complementary source words to yield all zeroes and identical source words to yield all ones. |
| L. N. Dashevskii, S. B. Pogrebinskii, E. A. Shkabara, *Vychislitelnaya mashina «Kiev» (proektirovanie i ekspluatatsiya)* (1964), 'Logicheskie operatsii' | printed p. 18 / PDF spread p. 10 (left) | octal 17 | XNOR, *ravnoznachno* | Explicit truth table: 00→1, 01→0, 10→0, 11→1. |

The 1962 text's XOR truth table is **genuine contrary primary evidence**, not a transcription error that we are authorized to silently correct. The 1964 table and the 1962 operational diagnostic agree on XNOR. The latter pair supports an **engineering decision in favor of XNOR**, but does not constitute observation of the original physical machine. `HARDWARE_ORACLE=0`.

### Historical machine-word cross-check (octal)

- `0002 = 12525252525252`, `0003 = 25252525252525` are bitwise complements within 41 bits; both are copied unchanged from GY1962 printed p. 172.
- `0073 17 0002 0003 0347` and `0074 16 0347 0000 0076`: test expects **0000...0** for complementary words, consistent with XNOR and inconsistent with XOR.
- `0076 17 0003 0002 0347` and `0077 16 0347 0000 0101` repeat that test with reversed operands.
- `0101 17 0002 0002 0347`, `0102 16 0347 3036 0107`: test expects **all 41 bits set** for identical operands, consistent with XNOR.
- `0104 17 0003 0003 0347`, `0105 16 0347 3036 0107`: similar check, but 0104–0105 are *not executed* on the successful main control-flow route; check separately.
- `3036 = 37777777777777` is the recovered fixed-ROM all-ones word; the value is already verified in D15/A3-P2 and D15/A3-P3.

The source is an **historical reference for the intended emulator semantics**, not a proven physical-machine result. Do not rewrite `au1_logic.k41` or replace 1962 p. 11's XOR evidence.

## 41-bit candidate functions

`MASK = (1 << 41) - 1`

- Existing emulator: `XOR(a,b) = (a ^ b) & MASK`.
- Proposed correction: `XNOR(a,b) = (~(a ^ b)) & MASK`.
- Masking is mandatory: the host word is `uint64_t`, not a 41-bit hardware type. Unmasked `~` would set 23 nonexistent high-order bits.
- The sign bit (bit 40) is included in *all 41 bits*, consistent with the logical-operations description in the 1962 chapter. The probe exercises sign-only values.

The native diagnostic `tools/isa07_d15b1_h2_opcode17_probe.py` uses **synthetic HOST-only one-instruction images**, with an independent mathematical oracle. Use `--expect xor` to qualify the current baseline *before* any CPU patch, and `--expect xnor` after a separately gated correction. Its historical-image cross-check is a second scenario, not a replacement for independent zero/sign-bit cases.

## Staging decision

`SOURCE_ADJUDICATION=XNOR_PREFERRED`, `1962_DESCRIPTION_CONFLICT=OPEN`, `HISTORICAL_PROGRAM_IMMUTABLE=1`, `CPU_MUTATION=0`, `INDEPENDENT_SECOND_SOURCE=1964`, `HARDWARE_ORACLE=0`.

Do not label the current CPU's successful XOR probe as a pass of the historical arithmetic-unit test. After a CPU fix, require passing the **same** probe in `--expect xnor` mode and the full historical image from address 0043, before updating the test's current qualification status. The H1 observation remains traceable to its original commit.
