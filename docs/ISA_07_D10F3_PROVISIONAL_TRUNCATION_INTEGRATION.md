# ISA-07 D10-F3 — provisional truncation enabled in IO20

**Status:** proposed (uncommitted), requires user's MSYS2 evidence; **base:** `98964fd96dfc8dbea692accd1ffb00d5d8719abb` (D10-F2 committed and pushed).

## Source evidence and reasoning

See `docs/ISA_07_D10F2_PROVISIONAL_TRUNCATION_DECISION.md` for the fuller citation and counter-hypothesis table. **Printed pages**, not PDF indices:

- **DPS64 (1964), pp. 120–122:** BCD→binary microprogram with additions, shifts and decimal position equivalents; no explicit final round-up. This supports **truncation as a tentative reconstruction only**. Internal equivalents' actual bit precision remains `OPEN`.
- **GY62 (1962), pp. 10–11; DPS64 p. 17:** distinct multiply-without-rounding (10) and multiply-with-rounding (11) opcodes. Their distinction does not prove opcode 20's rounding semantics.
- **GY62 p. 17:** manual binary/octal digit extraction to required precision; no final increment described. This is not itself a hardware specification.
- **GY62 pp. 117–118:** explicit rounding in *software floating-point simulation*, NOT a rule for input opcode 20.
- **GY62 pp. 7–8, 16, 58; DPS64 pp. 15–16:** ten decimal positions plus sign, 40 fractional magnitude bits and a sign bit, inclusive RAM interval, `C+1 → C`, `M[C] → K`. These boundaries remain `SOURCE_STRICT`.

**Provisional mathematical behavior:** `magnitude = floor(N * 2^30 / 9,765,625)` for ten-digit `N`, `0 <= N < 10^10`. Negative values are truncated *toward zero* (sign stored separately); preserve `−0`. Integer-only algorithm is independently tested in D10-F2. This is **not** an independently verified actual hardware microprogram for nonexact inputs.

## Exact, truncated and error semantics

1. D10-C `kyiv_decimal_exact::convert_bcd10()` stays byte-identical and exact-only. D10-F2 `kyiv_decimal_trunc::convert_bcd10()` stays byte-identical. No refactor of these proofs.
2. D10-D `parse_token()` now returns `exact`, `truncated` or `invalid_token`, using D10-F2 for conversion. Old enum `nonexact` remains available for source compatibility but is no longer returned for grammatically valid ten-digit decimals. `parse_record()` keeps an all-or-nothing rejection and distinguishes `record_status::truncated` if any *parsed token* is truncated.
3. D10-E2 `collect()` retains the same line/offset/count and record-validation host policy. It returns `status::exact` if *all stored words* are exact; `status::truncated` if at least one stored word is truncated, irrespective of ignored-but-validated surplus tokens. Both success statuses own a complete staged vector; errors own **no** staged words. Invalid extra tokens still reject the whole operation. Legacy `nonexact` enum is retained for compatibility, not emitted by the current parser.
4. IO20 accepts only `exact` and `truncated`; other statuses throw as in D10-E3. Before any write, it validates the inclusive RAM interval and stages all selected words. Successful C/K control transfer and the second CPU step are unchanged. Failure leaves RAM and `C` unchanged (K may have fetched the current instruction). `IO21–25` remain untouched.
5. Host framing (`perfo_num`, `a3` byte offset, LF/CRLF, ASCII) is **HOST_POLICY**, never claimed to be the historical card-zone encoding. True sign-on-card wiring, finite `Э_s` constants, physical device errors and real nonexact low bits are `OPEN`.

## Evidence and deliberate breaks from archival tests

- D10-F3 parser/planner C++ probe + Python independent integer oracle: ≥98 token/record/plan cases, including invalid record extras, two-line atomicity, signed zero, random nonexact ten-digit fractions and excluding surplus truncated tokens from the reported *stored* status.
- D10-E3 *real* `Kyiv_t` CPU test executable is reused unchanged; new Python runner reuses the 31 archived fixtures but **updates only three historical `NONEXACT` rejection cases**, plus 19 fresh truncated/error fixtures, checking 50 cases total (32 two-step successes and 18 one-step atomic rejections). The new runner also checks original source-aligned exact vectors, full 1024-word nonmutation on errors, C/K prefetch and XOR in step 2.
- D10-F2 exact and truncated standalone code remains untouched. Previous D10-E2 test expectations for `NONEXACT` (and three original D10-E3 error expectations) are **archival and intentionally not valid new acceptance oracles**. Never rewrite those old tests.
- Post-F3 functional regression for unaffected `IO21–25`: D8-B=10, D9-A=7, D9-B=8, IO21-only=6. ISA-06: 17 programs, `STRICT=89/89`, `POLICY=40/40`. Old structural auditors tied to earlier CPU Git blobs must not be rerun as current gates.
- Any failed precommit gate: stop; only a narrow H1 patch, no partial commit. After user PASS, commit exactly three modified plus six added files. No SIMH changes or additional cleanup.

## Pinned Git evidence

- Baseline: `98964fd96dfc8dbea692accd1ffb00d5d8719abb`.
- `src/main.cpp` at baseline: `d263706708efd958401df4818baa21249d99105a`.
- `inc/kyiv_decimal_ascii.h`: `93e47fd34b5133964fb5a9addab3430dd25f71ae`.
- `inc/kyiv_decimal_input_plan.h`: `9135962f7d41c9b619f0875e6fe7deac666d2ba1`.
- `inc/kyiv_decimal_trunc.h` (already committed H1 rationale): `e6ab074335a2337de3a5b0eadd3bf46adf0b09fe`.
- `inc/kyiv_decimal_exact.h` (D10-C): `6a09319f3eef53236c87647d4e4d155ce9addd75`.
- `inc/kyiv.h`: `ff4aa592f12b07d32b4961b49cb97b15289d38e0`.

**Next:** user MSYS2 verification, regressions, commit and post-commit baseline; do not silently promote provisional low-bit model to historical `SOURCE_STRICT`.
