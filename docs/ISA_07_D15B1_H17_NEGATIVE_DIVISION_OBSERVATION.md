# D15/B1-H17 — negative division with printed/host low-bit discrepancy

Pinned baseline: `a90f05a64f79ef22f12ca5ddb5a404658be87284`. Visual source: Glushkov–Yushchenko (1962),
printed pp. 172–173; **first visual reading only** (no second witness).
Modern `KYIV41-OCT1` is a host text container, not the historical medium.

## Source records

| Octal address | Exact 41-bit word | Source page | Role |
|---|---|---|---|
| `0030` | `20002000000000` | 173 | negative_dividend |
| `0031` | `00016000000000` | 173 | positive_divisor |
| `0032` | `22222222222200` | 173 | printed_expected_quotient |
| `0210` | `12003000310347` | 173 | opcode12_division |
| `0211` | `16034700320213` | 173 | opcode16_compare_skip_STOP |
| `0212` | `33000000000000` | 173 | original_failure_STOP |


Printed p.172 describes the `0210–0212` example with a negative quotient,
including a repeating group of octal 2s. The literal comparison in command
`0211` targets cell `0032`, whose printed value ends in **`00`**. The
first visual transcription has not been independently checked.

## Independent exact integer HOST oracle (not a historical ISA assertion)

The host's 41-bit representation uses a sign bit at position 40 and
40 magnitude bits. Exact binary quotient under the current CPU policy:

```python
SIGN = 1 << 40
MASK = SIGN - 1
numerator = int('20002000000000', 8)
denominator = int('00016000000000', 8)
assert numerator & SIGN and not (denominator & SIGN)
mag = ((numerator & MASK) << 40) // (denominator & MASK)
host = SIGN | (mag & MASK)
assert f'{host:014o}' == '22222222222222'
assert '22222222222200' != '22222222222222'
```

| Profile | Result (octal) | Status |
|---|---|---|
| GY1962 printed source / RAM `0032` | `22222222222200` | historical target |
| independent current-host policy | `22222222222222` | HOST prediction |
| low-magnitude delta | `00000000000022` | 18 decimal |

The source's terminal `00` could indicate a particular division-precision
or formatting convention, but that is **not established** by this one case.
Do not fix opcode `12` or retcon the printed word on that basis.

## Bounded real-CPU qualification

- Run source-exact `0210` once, watch `0347` and original RAM `0030/31/32`.
- Run `0210` and `0211` twice, inspect C. On HOST prediction, branch
  fails and `C=0212`; original `STOP` at `0212` then yields `C=0213`.
- On a HISTORICAL match, the branch gives `C=0213`; a private mutated JE
  comparison is used exclusively to witness source STOP in a three-step run.
- Repeat with EXTERNAL and TEMPKYIV CWD, both source profiles.
- Never execute address `0213`. Previous H9/H10/H11/H13/H14 conflicts
  remain OPEN_UNCHANGED. CPU/ROM and all prior source images unchanged.
- `HARDWARE_ORACLE=0`. Native results go in commit evidence, not in the
  pre-existing static audit where `NATIVE_GATE=PENDING` remains historical.
