# D15/B1-H13 — zero-distance 41-bit logical shift (opcode 13)

Pinned parent: `f9b5d7c088093041be01aceb427a61168f2ec95a`. This H13 package does not modify CPU, ROM or
historical images committed before H13.

## Literal first source reading

GY1962 printed p.173 gives the machine words at `0166`, `0167`, `0170`.
GY1962 printed p.174 gives memory data at `0261`. The data are *not*
on p.172, unlike earlier cases.

| Address | Full word (14 octal digits) | Source |
|---|---|---|
| `0261` | `02525252525252` | p.174, data |
| `0166` | `13000002610347` | p.173, opcode `13` shift |
| `0167` | `16034702610171` | p.173, opcode `16` exact compare |
| `0170` | `33000000000000` | p.173, original STOP |

All addresses and machine words above are octal. First visual transcription
only; an independent human witness is **PENDING**.

## Instruction and initialization boundary

The 1962 GY instruction definition on **printed p.12** specifies shifting
all 41 bits of the second source according to the six least-significant
bits of the first source (`a1`); a positive constant shifts left,
negative shifts right. At address `0166`, `a1=0000`, `a2=0261`, `a3=0347`.
The printed AU source data list begins at `0001`, so `0000=0` is **not**
a historical word transcription. The unmodified native emulator is asked
to observe RAM `0000` at runtime and this particular test qualifies
only when it reports exact 41-bit `00000000000000`.

Under this **explicit HOST startup premise**, a zero-distance shift must
preserve the complete input word, including its sign bit. The 41-bit
CPU-independent bit-vector result is therefore
`0347=02525252525252` (not an arithmetic approximation).
After 1 step expect `LIMIT STEPS=1 C=0167`, after 2 a successful
exact compare with RAM `0261` sends control to `C=0171`.
**Do not execute `0171`.** The original STOP at `0170` is tested only
on a private temporary copy with the JE second operand retargeted
from `0261` to `0000` (unaltered original shift and STOP). A three-step
private execution must yield `CPU_STOP STEPS=3 C=0171`.
Test in two working directories: **6 cases**, 4 historical-path plus
2 private STOP. Before and after the run, verify the source image SHA.

## Source-description discrepancy — OPEN, independent of shift result

Printed p.172 characterizes the range `0166–0170` as
`(0) СлК 02(52) = 02(52)` using the `СлК` abbreviation that elsewhere
names command addition (opcode `03`), whereas the actual p.173 machine
instruction is opcode `13` (logical shift). This is a discrepancy
between the **text label** and the **literal machine operation**.
A zero-distance shift can generate the same output as an identity-like
command addition, so the observed arithmetic value does not adjudicate
which printed description is in error. No instruction replacement,
retroactive source rewrite, or CPU semantic change is authorized.
H9 prose/code discrepancy, H10 opcode07 carry and H11 opcode06 signed
zero remain OPEN_UNCHANGED as three separate prior matters.

## Evidence limits

Native PASS means bounded software-emulator agreement with machine-code
semantics and *observed* RAM startup zero, **not** proof of hardware
behavior or resolution of the p.172 label. `HARDWARE_ORACLE=0`;
`HUMAN_INDEPENDENT_WITNESS=PENDING`. The historical source image
contains only the four documented verbatim words.
