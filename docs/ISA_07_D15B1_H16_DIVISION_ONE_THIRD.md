# D15/B1-H16 — GY1962 one-third division: source qualification

Pinned parent: `8736116b46a4b1ff111821a5fb919520a6c74276`. CPU, ROM, and earlier canonical images must remain unchanged.
Primary source: Glushkov–Yushchenko (1962), printed pp.172–173;
this is a first **visual** transcription, not independently corroborated.
HOST `KYIV41-OCT1` text is a modern container, not historical tape/cards.

## Exact source records

| Octal address | Exact 41-bit octal word | Printed page | Role |
|---|---|---|---|
| `0004` | `05252525252525` | 172 | historical_expected_one_third |
| `0026` | `01000000000000` | 173 | positive_dividend |
| `0027` | `03000000000000` | 173 | positive_divisor |
| `0205` | `12002600270347` | 173 | opcode12_division |
| `0206` | `16034700040210` | 173 | opcode16_compare_skip_STOP |
| `0207` | `33000000000000` | 173 | original_failure_STOP |


Printed p.172: `01(0) : 03(0) = 05(25)`, lines `0205–0207`.
The literal command `0205` divides RAM `0026` by `0027`, placing
result into `0347`; the `0206` comparison with `0004` jumps to `0210`
when equal; `0207` is the original source STOP.

## Independent exact integer oracle

Sign/magnitude representation has one sign bit (bit 40) and a 40-bit
fractional magnitude. Both operands are strictly positive; divisor is
nonzero. For THIS case the current CPU host policy truncates quotient:

```
numerator=0o1000000000000
denominator=0o3000000000000
q=(numerator << 40) // denominator
assert 0 <= q < (1 << 40)
assert q == 0o5252525252525
```

Full 41-bit predicted word at RAM `0347`: `05252525252525`.
The mathematical rational result is 1/3; the truncated binary fraction
has repeating `0o52` pattern. This example does NOT establish
full historic divide rounding or overflow policy, division by zero,
negative zero, or the next division case starting at `0210`.

## Strict executable qualification

- Positive runs: step 1 `C=0206`; step 2 successful branch `C=0210`.
- Private STOP: copy image to temporary directory and retarget only
  the JE second source `0206: 16034700040210` to
  `0206: 16034700260210`; original dividend/divisor and STOP stay verbatim.
  Three steps must yield `CPU_STOP STEPS=3 C=0210`.
- Watch all original data/expected cells and full 41-bit `0347`; repeat
  all runs with EXTERNAL and TEMPKYIV CWD. Never execute `0210`.
- H9/H10/H11/H13/H14 remain `OPEN_UNCHANGED`; second human witness and
  hardware oracle unavailable (`HARDWARE_ORACLE=0`). The static audit
  prints `NATIVE_GATE=PENDING`; run results are recorded separately.
