# D15/B1-H8 — GY1962 negative-zero addition checks VIII–IX

Pinned baseline: `e795f1959d97bf3f34251fc2131447e86d51c611` (`main`, H7 pushed).

## Source boundaries and notation

- V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962):
  **printed p. 172** gives two data words and predicted results; **printed p. 173**
  prints the six machine instructions `0135..0142`. Transcription is one visual
  read, not an independent second researcher (`HUMAN_INDEPENDENT_WITNESS=PENDING`).
- The standalone HOST `KYIV41-OCT1` image has eight source records. It is NOT a
  reconstruction of physical punched-card encoding. All codes are **octal**;
  data words are full 41-bit sign-magnitude values (bit 40 = sign).
- Printed p. 172 equations are `1 (0) + (0) 1 = (0) 1` for `0135–0137`
  and `1 (0) + (0) 20 = (0) 20` for `0140–0142`; parentheses indicate
  recurring digits. The exact source codes below are the primary oracle.
- Both ADD instructions use `3026`, *not encoded as a word in this image*.
  The pinned currently reconstructed ROM stores **`20 0000 0000 0000`** there,
  or `20000000000000` as a 14-digit octal word. This decodes to **−0**.
  Provenance of the ROM remains independent of this printed excerpt:
  a pinned ROM value is a source prerequisite, not a hardware truth claim.

## Source words (first visual read)

| Address | Octal 41-bit word | Printed page | Role |
|---|---|---|---|
| `0015` | `00000000000001` | 172 | positive_one_data |
| `0016` | `00000000000040` | 172 | positive_0040_data |
| `0135` | `01302600150347` | 173 | add_negative_zero_plus_0001 |
| `0136` | `16034700150140` | 173 | compare_then_skip_stop |
| `0137` | `33000000000000` | 173 | historical_failure_stop |
| `0140` | `01302600160347` | 173 | add_negative_zero_plus_0040 |
| `0141` | `16034700160143` | 173 | compare_then_skip_stop |
| `0142` | `33000000000000` | 173 | historical_failure_stop |

## Source-independent arithmetic oracle

Let `SIGN=1<<40` and `MAG=SIGN-1`; decode a word as signed magnitude.
ROM `3026=20000000000000` has sign set and zero magnitude.

| Start | Signed operation | Expected word at `0347` | 1 step | 2 steps |
|---|---|---|---|---|
| `0135` | −0 + 1 | `00000000000001` | `C=0136` | `C=0140` |
| `0140` | −0 + 040 (octal) | `00000000000040` | `C=0141` | `C=0143` |

The 41-bit **sign bit must be zero** in both results, and neither result
is an overflow. The source uses compare-equal opcode `16` at `0136`, `0141`.
Original STOPs `0137`, `0142` are reached only when equality fails.

## Native qualification and safety boundaries

Run `tools/isa07_d15b1_h8_native.py` on a compiled **real** emulator executable.
For each start, two working directories run 1 and 2 instruction budgets;
private mutants retarget *only the ADD operand address*, keeping the historical
JE and STOP instructions unchanged, then run 3 steps to
verify original fallback STOP. Total: **12 cases = 8 positive + 4 STOP**.
The runner separately watches pinned ROM cell `3026`, expected data cells,
result `0347`, final `C`, and canonical SHA. It must not execute `0143`.

Neither CPU nor ROM nor previous historical examples may be modified.
`HARDWARE_ORACLE=0`; success is a software qualification, not a physical-machine
measurement. A second human transcription remains pending. Do not silently
change original machine words to match the emulator.
