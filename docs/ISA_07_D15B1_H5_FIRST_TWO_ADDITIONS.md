# D15/B1-H5 — first two addition checks from GY1962

Parent pinned at `29011c27a5ae64afe75442de13cafea95871d42c` (D15/B1-H4 verified transcription of logic example).
This is the **initial six-command subset** of the following historical arithmetic
block, **not** the complete addition section or complete arithmetic-device test.

## Primary source, exactly delineated

- Glushkov & Yushchenko, *Vychislitel'naya mashina «Kiev»* (1962),
  printed **p. 172** / PDF **p. 171**: data `0002`, `0003`, `0004` and
  historical calculation/expected results for `0110–0112`, `0113–0115`.
- Same monograph, printed **p. 173** / PDF **p. 172**, first column:
  exact six instructions at octal addresses `0110..0115`.
- Each word is transcribed **once** by the assistant and recorded in the
  adjacent source-provenance TSV. No independent second visual reader yet.
- The image uses modern `KYIV41-OCT1` HOST format, not historical card or drum media.

## Source predictions, distinct from emulator observations

| Start (octal) | Instructions executed | Historical result at `0347` | Branch destination after 2 steps |
|---|---|---|---|
| `0110` | `01 0004 0004 0347`; `16 0347 0002 0113` | `12 5252 5252 5252` | `0113` |
| `0113` | `01 0003 0002 0347`; `16 0347 0004 0116` | `05 2525 2525 2525` | `0116` |

Opcode `33` at `0112`, `0115` is a printed failure-stop instruction.
The bounded success-route runner never deliberately executes either STOP.
Do not expand the instruction budget or jump to `0116` until those next words
have been transferred with provenance; this image contains no `0116`.

## Qualification contract

- No CPU, ROM, logic-section `.k41` or earlier evidence is changed.
- Exact 9/9 image/provenance/source verification, with deliberately mutated
  byte rejected by the audit's self-test.
- Run the *real* production `kyivemu image` against the SHA-pinned default ROM
  from two different CWDs, for both starting points and one/two-step budgets.
- 1 step checks raw result at `0347`; 2 steps check historical conditional
  branch destination and same raw result. Each scenario also watches the three
  unchanged input data words.
- A `PASS` in the native runner means both the independent historical prediction
  and observed emulator execution agreed. A mismatch must retain the printed
  words and report the observed route; no automatic CPU fix.
- `HUMAN_INDEPENDENT_WITNESS=PENDING`, `HARDWARE_ORACLE=0`.

## Replication

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1_h5_kyivemu.exe
python -B tools/isa07_d15b1_h5_native.py --cli-exe tempkyiv/d15b1_h5_kyivemu.exe --timeout 20
python -B tools/isa07_d15b1_h5_audit.py --self-test
python -B tools/isa07_d15b1_h5_audit.py
```
