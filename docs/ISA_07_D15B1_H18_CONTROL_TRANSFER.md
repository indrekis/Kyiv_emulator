# D15/B1-H18 — source-exact opcode 05 control transfer at 0213

Baseline: `f811c480ef193868cd1a8880d055a5d1f8556be2`. Glushkov–Yushchenko (1962), printed pp.172 and 174.
**First visual transcription only; no independent human witness.**

| Octal address | Source-exact word | Printed page | Role |
|---|---|---|---|
| `0213` | `05000000000263` | 174 | opcode `05`, operands `0000/0000`, destination `0263` |

The single input word is neither a full program nor a continuation of
`0210–0212`: that preceding historical comparison failed under the HOST
profile (H17), and its original `STOP` at `0212` was observed. H18 uses
an **explicit fresh entrypoint** at `0213`, without claiming the continuous
historical AU test reached this instruction.

## Independent conditional-branch oracle

Opcode `05` is absolute less-than-or-equal. Therefore:

- Original source `|RAM[0000]| <= |RAM[0000]|` is a tautology. Its result
  does **not** depend on whether the unprinted initial RAM cell `0000`
  happens to contain zero, positive or negative zero. After one instruction
  `C=0263`, with no second step.
- PRIVATE case T: `RAM[0001]=1`, `RAM[0002]=2`, instruction
  `05 0001 0002 0263`: `1<=2` true, `C=0263`.
- PRIVATE case F: the same data, instruction `05 0002 0001 0263`:
  `2<=1` false, `C=0214`.

The two private comparisons demonstrate the branch is conditional rather
than a disguised unconditional jump; the private operands are synthetic
and are **not** attributed to the 1962 listing. No instruction at `0214`
or `0263` is ever executed in these tests.

## Source-map caveat

Printed p.172 labels `0214–0226` pseudorandom-number generation and
`0256–0345` constants. Printed p.174 gives the branch target `0263`,
which lies in that *latter* range; the entry `0263` visually begins with
opcode `35`. This is recorded without inferring what subsequent historical
execution would do, and without relabeling either source range.

## Native qualification gates

- EXACT source image includes only `0213`; source Git blobs pinned 50/50.
- EXTERNAL and TEMPKYIV CWD both run original/T/F, **one step each**.
- Canonical `0213` source bytes and private synthetic operand words are
  checked before and after execution; no `--watch 0000` (unsupported CLI).
- Execution boundary: `0263` and `0214` both NOT_EXECUTED; audit preserves
  CPU, ROM, and all previous images.
- H9/H10/H11/H13/H14/H17 conflicts remain OPEN_UNCHANGED.
- Hardware and independent second-human oracles remain unavailable.
