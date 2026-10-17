# ISA-06 D8-P8 — original fourth RAM test entry across both natural epochs

**Base**: `40054e0` (D8-P7 PASS: 89/89 STRICT, 25/25 POLICY). **Additive-only** P8: one C++ probe, one static source checker, one standalone Python NK reference and four documents/tables. CPU, ROM, original transcripts, prior tests and prior audits are **unchanged**.

## Primary evidence and scope

Glushkov–Yushchenko (1962), **printed pp. 120, 170–171**: the fourth RAM test starts at `0117`, whose original word is `01 0000 0000 0014`. Original `0120` initializes a running pattern using ROM `3012`; `0121` copies the pattern into the working word. P7 verified the three-word entry in isolation. P6 traced 78 full passes from `0120` to the boundary *before execution* of `0164`. P8 combines the two **without resetting or injecting state after entry**.

P8 deliberately initializes RAM `[0014]` to `−0` *before* starting `C=0117`. Original `0117` must overwrite that marker with `+0` using hardwired RAM `[0000]=+0`. From `0117`, continue through both 39-pattern epochs, naturally executing `0162` (equal-number subtraction gives `−0`) and returning from `0163` to `0120`. Do not rewrite `[0014]`, `C`, `A`, `P`, `Cy`, `K`, ROM or swept RAM during the program. Stop before fetching `0164` and assert `0014=−0`, exactly 39 positive and 39 negative epoch cycles, no premature STOP and no code-exact mismatches.

This is a **POLICY** integration check, not independent hardware verification. Exact 41-bit data are checked in 896 RAM locations per cycle (78 cycles), with ROM `3012=+1`, `3026=−0`, `3042=2^39` still explicit initial **fixtures**. Current emulation policy for opcode `01` signed zero and opcode `05` equality remains under investigation; this test does NOT upgrade them to STRICT. `0164` and both of its targets remain unexecuted. Source of historical `0177` program word remains OPEN. The early P6 starting point `0120` and its preinjected `0014=+0` remain correctly documented; P8 does not retrospectively treat that test as starting at `0117`.

## Operator NK source selection — separate reference contract

GY62 printed **p. 8** lists eight 41-bit manually settable NK codes `3000–3007`. Printed **p. 161** describes individual panel-versus-cabinet selectors only for NK `3000`, `3001`, `3002`; do not invent equivalent console switches for `3003–3007`. Printed **p. 120** ties the sign of NK `3000` to all-four-tests versus selected-test control, and p. 121 ties the sign of NK `3001` to custom first-test pattern selection. P8 includes a pure Python *reference-only* resolver for exactly `3000–3002`, with independent switches and explicit 41-bit values, including distinct +0/-0. It intentionally does **not** modify `Kyiv_memory_t`, install panel hardware, assign historical switch positions or read arbitrary ROM values. This is a design contract for a later, separately tested implementation; in P8 the full-cycle C++ test NEVER writes `3000/3001`.

## Source controls and known limitations

The structural checker requires committed source Git blobs for the P6 and P7 probes, the P7 panel/entry evidence and repository ROM, plus exact matching of all 39 documented P6 machine words to the new P8 C++ test. P8's 40th word `0117` must match the original word in P7. The reader-facing source manifest carries the GY62 PDF SHA-256 and precise printed pages; the audit **does not pretend to image-read those pages**. Source-preserving, CRLF-tolerant checks avoid raw filesystem SHA-256 pitfalls previously found in D8-P2.

No code changes are proposed to the CPU, ROM, historical test data, or simulation of NK switches. `H2 E022` remains **RETRACTED** and the physical opcode-01 zero-sign oracle remains **OPEN**.
