# ISA-06 D6 — sign of an exact-zero sum: documentary audit and characterization

**Base:** `9e2e4d3` (`main`, ISA-06 D5). This stage adds only this note and `tests/isa/isa06_d6_zero_sum_probe.cpp`. No CPU, ROM, existing tests, historical corpus, or root README changes. This is **not** an ISA fix.

## Question

When arithmetic instruction `01` adds 41-bit sign-magnitude machine codes whose mathematical sum is zero, does a genuine Kyiv machine output `+0` (`00 0000 0000 0000`) or `-0` (`20 0000 0000 0000`)? In particular, `(-0)+(+0)` occurs at original instructions `0123` and `0141` of the fourth RAM diagnostic and is an input to the exact-code comparison `16` later in that diagnostic.

## Source statements (printed pages)

1. **GY62** — V. M. Glushkov, E. L. Yushchenko (1962), **p. 7, fig. 1**, defines the 40 magnitude bits and the separate sign bit. **P. 11** describes ordinary addition of algebraic numbers. **P. 13** explicitly states that subtraction of equal numbers produces a **negative zero**; this is *not* a statement about the sign of arbitrary zero sums produced by `01`. **P. 17** distinguishes `-0` and `+0` in representation and comparison. **Appendix 2, pp. 170–171** contains the fourth RAM test: original words `0123 = 01 0021 0000 0020`, `0141 = 01 0021 0000 0020`, and exact-code comparisons including `0144 = 16 4000 0020 0146`. These are historical words; injected operand values remain test fixtures.
2. **DPS64** — L. N. Dashevsky, S. B. Pogrebinsky, K. A. Shkabara (1964), **pp. 96–97**, describes negative operands in the arithmetic summator as *bitwise complements* rather than a conventional modern signed integer, including carry/overflow logic. **Pp. 100–103, fig. 62 and table 4** document the two-pass adder and its operation-control signals. **Pp. 136–139, fig. 67** show the structure of an adder bit. **Pp. 144–146, figs. 71–73** describe the sign flip-flops and output: the sign digit is issued from the summator sign trigger (`ТЗн2См`) via the result-sign path, rather than being determined simply by the sign of a mathematical integer computed in software.

## Inference, not yet historical oracle

A *possible* gate-level reconstruction is that a negative-zero operand is complemented to an all-ones internal code, which may leave a negative-zero sign after adding `+0`. This gives `(-0)+(+0) -> -0` as a **candidate**, reinforced by the RAM diagnostic's intent to exercise a travelling zero and exact-code comparison. But the cited descriptions do not, by themselves, resolve **all** details of normalization, carries, inverting the result back into direct code, or sign-trigger timing for an *exactly zero* sum. The original RAM diagnostic is not yet a fully qualified ROM+RAM execution oracle. **Do not promote this hypothesis to STRICT or alter opcode 01 in this stage.**

Alternative models to distinguish in future work:

| Model | `(+0)+(-0)` | `(-0)+(+0)` | `(-0)+(-0)` | Equal nonzero opposite signs |
|---|---|---|---|---|
| M0: mathematical integer then sign of result (current general add path) | +0 | +0 | +0 | +0 |
| M1: bitwise-complement adder with preserved negative-zero pattern (candidate; needs gate/timing validation) | -0 | -0 | -0 | may yield -0 |
| M2: operand-order-dependent sign resolution | depends on order | depends on order | -0 or +0 | depends on order |

The table is a **hypothesis register**, not an assertion of historical behavior. This probe can record current results but cannot by itself discriminate hardware models: independent logic/circuit analysis is required.

## Test classification and scope

- **STRICT (5 cases):** four nonzero sums of positive/negative operands according to algebraic addition (GY62 p. 11), and equal-number subtraction yielding negative zero (GY62 p. 13). The subtract case is a narrow previously established regression, *not* evidence that addition behaves the same. Assert exact 41-bit value, original instruction `K`, sequential `C`, no stop, preservation of A/P/Cy.
- **OBS (8 cases):** the four signed-zero pairs under `01`, exact cancellation of two nonzero operands in both orders, and original RAM-test `01` words at `0123` and `0141` with an explicitly injected `-0` in `0021` and the hardwired `+0` at `0000`. Record `K`, operand/result bits, `C`, stop and register state, with **no sign oracle**. The two historical samples are contextual observations, not full historical-program successes.
- **No POLICY** assertions introduced: the purpose is to avoid canonizing current zero-sign semantics.

## Current CPU implementation (not a historical source)

At `src/main.cpp`, `Kyiv_t::opcode_arythm` turns each signed-magnitude operand into an `int64_t` algebraic quantity, sums as an integer, and, for ordinary `01`, uses `res < 0` to set the sign bit. The integer result zero therefore loses the distinction between `-0` and `+0`. That is an identifiable **emulator policy/implementation mechanism**; it is not yet a documented CPU defect. The explicitly special subtraction-equal case is treated differently and produces `-0`.

## Next gate

After the real run of D6: retain OBS and carry out a dedicated sign-trigger/carry microoperation reconstruction from DPS64 figs. 67, 71–73 (pp. 136–139, 144–146) and the original RAM diagnostic. Only after a defensible historical oracle is established should CPU behavior change with a matching regression test. Separately, the known CWD-dependent ROM constructor path is not part of this stage.
