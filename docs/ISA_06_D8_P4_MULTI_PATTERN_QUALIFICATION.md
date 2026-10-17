# ISA-06 D8-P4 — two natural RAM pattern sweeps and terminal-branch boundaries

**Base:** `fb02099` (P3 PASS on user MSYS2). **Changes:** additive test, documentary gate TSV, source manifest, structural Python audit. No CPU, ROM, historical-corpus or prior-test edits. **Not** a hardware oracle. All new behavioral checks remain `POLICY` and no `STRICT` is promoted.

## Source

Glushkov–Yushchenko (1962), Appendix 2, **printed pp. 170–171**: fourth RAM write/read diagnostic and its original octal command words. P3 introduced 27 body words (`0122–0136`, `0140–0155`) and 6 bridge words (`0120`, `0121`, `0137`, `0156`, `0157`, `0160`). This phase additionally transcribes printed-p.171 `0161–0166`, with `0164–0166` **included only in the source corpus, not executed**. The structural checker pins the committed P3 Git blob and verifies that the P4 HIST and BRIDGE words match P3 exactly.

## Scenario A: two *uninterrupted* original sweeps

A single `Kyiv_t` instance starts at octal `0120`, using the same **controlled** P3 fixtures: ROM `[3012]=+1`, `[3026]=-0`, `[3042]=2^39`; RAM `[0014]=+0`; RAM `0017`, `0020`, `0021`, and sweep addresses `0200..1777` initialized to `077`; registers `C=0120`, `A=0`, `Cy=077`, `P=0371`, `T=false`. This is not an authenticated front-panel start and bypasses the working-directory-dependent ROM loader.

1. Pattern #1 is produced by original `0120` and copied by `0121`: expected `0017=1`. Original instructions write/compare all **896** RAM cells, preserving all **41 bits**, through `0137→0140` and `0156→0157→0160→0121`; shift `0156` advances the source pattern to `0017=2`.
2. Without resetting the CPU or changing RAM/ROM/registers, instruction `0121` naturally starts pattern #2, `0017=2`. Repeat 896 writes and 896 exact comparisons. The next shift produces `0017=4`, then reenters at `0121`.
3. Assert that the second pass **actually changes** data RAM compared with a frozen snapshot of the first sweep; verify all 896 locations against the second pass, that signed `-0` codes are preserved across write/read, that each expected literal historical K was fetched, and that no STOP or out-of-scope PC occurred. Counts of negative-zero words may differ between passes and **are not pinned as an independent historical oracle**. Limit each pass to 25,000 instructions and capture the first mismatch with `PC`, fetched `K` and reason.

The two-sweep gate is a *conditional consistency check* of current opcode `01` signed-zero policy, opcode `05` equality policy, opcode `13` shift, and the test ROM fixtures; its success is **not** independent proof of any of those policies.

## Scenario B: terminal positive control (fixture injection)

In a **fresh** fixture instance, set RAM `[0017]=2^39` and `C=0157`, *without claiming to have executed the preceding 39 shifts*. Under ROM `[3042]=2^39` and RAM `[0014]=+0`, original words must trace `0157→0161→0162→0163→0120`. Command `0162` subtracts equal zeros, producing `RAM[0014]=-0` under the documented subtraction rule (GY62 printed p.13); `0163` is a `05` branch whose zero-equality decision is still emulator `POLICY`. This complete scenario is `POLICY` because its entry and ROM values are fixtures.

## Scenario C: terminal negative control (bounded)

In another **fresh** fixture instance inject `[0017]=2^39`, `[0014]=-0`, `C=0157` and check `0157→0161→0164`. **Stop before executing `0164`.** The latter refers to ROM `[3000]` and leads into unqualified terminal handling, including `0022/0177`, so the actual end state, stop code, and paths `0165/0166` are `OPEN`. No invented ROM input or stop expectation is used.

## Compact trace

Run the P4 test with optional `--trace tempkyiv/isa06_d8_p4_trace.tsv` to record gate and sampled data events (`0126`/`0144`: first two, every 64, last), plus terminal-branch steps. Columns: `scenario`, `cycle`, `step`, `pc`, `k`, `a_before`, `cy_before`, `pattern_before`, `cell`, `code`, `next_pc`, `status`. All machine fields are **octal**. The trace is generated in the untracked/ignored `tempkyiv` workspace; it is not a historical ROM dump.

## Structural QA and evidence policy

The Python auditor checks the literal original P3 arrays against P4, the six appendix terminal words, the P3 Git blob (`d4c181f967bc2fe327fddd35b6fea69bfa88b916`), fixture provenance, gate classes, column integrity, and whitespace. The P3 source has already passed its own audit; this checker does not substitute for running the P4 executable on the user's actual MSYS2 toolchain. If P4 fails, do not change the CPU to satisfy its assumed trace: diagnose fixture assumptions and the first failing opcode/PC first.

## After P4

The natural next stage is an independently bounded analysis of `0164–0166` and the opposite-sign branch via ROM `[3036]`, with separate proof obligations before any additional `STRICT` status. Full automatic test-pattern exhaustion is not claimed by P4.
