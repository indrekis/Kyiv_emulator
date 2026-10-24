# D15/B1-H6 — three additional GY1962 arithmetic-unit checks

Pinned parent: `ab046eb99e6c7fa43fda35bf287f1e0ffa6052fe` (H5). This stage only imports original historical
code from Glushkov/Yushchenko 1962, **printed pp. 172–173**. It does not alter
CPU semantics, ROM, or earlier historical images. The `.k41` header is a modern
HOST format, not a claim about actual historical punched media.

## Source interpretation (all codes are octal)

| Group | Printed arithmetic example (p.172) | Historical instructions (p.173) | Expected 41-bit machine word |
|---|---|---|---|
| `0116–0120` | `07 5736 7573 6745 + 07 5736 7573 6745` | `0116` add; `0117` compare with `0007`; `0120` STOP | `17 3675 7367 5712` at `0347`, next `C=0121` |
| `0121–0123` | `05(25) + 32(52)` | `0121` add; `0122` compare with `0003`; `0123` STOP | `(25)`, encoded `25 2525 2525 2525` (negative), next `C=0124` |
| `0124–0126` | `12(52) + (25)` | `0124` add; `0125` compare with `0004`; `0126` STOP | `05 2525 2525 2525` (positive), next `C=0127` |

The input cells `0002–0004` are present in H5 and reproduced verbatim in this
standalone image. New constants `0005–0007` are directly transcribed from p.172.

## Independent reference arithmetic

Let `M=(1<<40)-1`, `S=(1<<40)`. Interpret a word as `-(word & M)` if
`word & S`, else `word & M`. Direct integer calculations give:

- `0006 + 0006 = 17367573675712` (`0007`).
- `0004 + 0005 = 25252525252525` (`0003`, negative result).
- `0002 + 0003 = 05252525252525` (`0004`, positive result).

The historical group enters at `0116`, `0121`, or `0124` independently. No
execution from previous H5 groups or historical `0107` (NK selector) is needed.
For each group, the ordinary image is run with step budgets 1 and 2 in two
working directories, checking exact destination `0347`, unchanged data cells,
and the next counter. A synthetic private test replaces only the **expected
constant** by zero, proving that the real historical fallback STOP instruction
is reached after three steps; that synthetic file is never checked in.

## Source and qualification limits

- `SOURCE_VISUAL_FIRST_PASS=1`; no independent second human transcription.
- `HISTORICAL_EXPECTATION_MATCH` must be determined by native Windows/MSYS2 CPU
  execution, not by the static audit or a Python arithmetic oracle alone.
- `ROM_DEFAULT_PIN=1` is checked by the native runner's use of the normal image
  CLI without overriding the pinned ROM.
- `HARDWARE_ORACLE=0`. No original machine hardware measurements.
- No invented logic for overflow; these source examples do not exercise a
  deliberately overflowing result. No historical-code corrections permitted.
