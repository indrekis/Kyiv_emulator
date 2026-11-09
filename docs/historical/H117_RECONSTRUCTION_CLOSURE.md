# H117 — Functional AU continuation at 0360 and closure policy for historical gaps

**Baseline:** `main` at `f7e2b69c497b983c9163d04acf28a44bb5e783b1` (2026-11-09).
**Status of AU continuation:** `HOST_FUNCTIONAL_RECONSTRUCTION / TWO_EPOCH_NATIVE_ACCEPTED`
**Status of the *historical* word 0360:** `SOURCE_NOT_RECOVERED / RESEARCH_DEFERRED_UNTIL_NEW_EVIDENCE`.
**User decision (2026-11-09):** do not schedule repeated speculative source archaeology for the same unresolved fragments. Deliver useful, clearly labelled functional reconstruction; archive uncertainties and move forward. Reopen historical-source analysis only on *new* independently inspectable evidence.

## 1. What is actually known

- GY62 (Glushkov–Yushchenko, 1962), printed pp. 122–123: two AU tests share one tape; the first has three sections, the fourth entry checks multiply/divide with pseudorandom numbers. The program repeats until an operator stops it or a wrong result is detected. This establishes a **cyclic behavioural intention**, not the machine word at 0360.
- GY62 printed p. 173 contains `0042: 01 3066 0000 0353` (source-only H37 word). GY62 printed p. 174 and tracked AU segment contain `0334: 05 0000 0000 0360`.
- H52 observed a bounded 97-command execution from `0042` with HOST-configured NK3000 panel negative zero, ending **before** the instruction at `0360`. The 20 canonical `.k41` images contain 238 records / 220 unique source addresses; **none contains an AU word at `0360`**.
- A different test (control unit, УУ) has a printed word at address `0360`. Its equal address is **not evidence** that this word belongs to the AU test. Never transplant it across programs.
- The source does not establish the true AU instruction at `0360`, subsequent RAM words, original operator cycles, or the actual physical machine's fault-coverage oracle.

## 2. Functional hypothesis, exact machine code

For a useful repeated AU demonstration we add one **separate** HOST candidate:

```
0360 05 0000 0000 0042
```

41-bit octal word `05000000000042`; opcode `05` is unconditional transfer to `0042`. This is a *conscious synthetic decision*, motivated by the documented intention that the program should repeat. It is not source transcription, an unknown source word filled with zero, a claim about historical operator behaviour, or a ROM extension. It belongs in RAM only.

Tracked image: [`au1_0360_functional_v1.k41`](../../examples/historical/gy1962/reconstructions/au1_0360_functional_v1.k41), which deliberately contains **only the invented word**. The canonical 20 `.k41`, their provenance TSV, `mem/ROM.txt`, `inc/kyiv.h`, and original source-only `0042` manifest stay unchanged.

The native runner [`au_0360_reconstruction_v1.py`](../../tools/historical/au_0360_reconstruction_v1.py) assembles the 20 canonical images **in a private, new `tempkyiv/` directory**, rejects disagreements, adds source-only `0042` with separate provenance, and adds the labelled reconstruction `0360` only to an experiment variant. It compiles/uses the normal production C++ backend and runs two epochs in **one persistent `Kyiv_t`**, with no hidden CPU/RAM reset. It refuses unsourced RAM entry points and the dangerous source-visible I/O boundaries `0232` and `0252`. First it establishes the original 97-command boundary without the reconstructed word, then tests that `0360` really transfers to `0042` and that the next bounded epoch reaches the same source boundary. Source state and diagnostic traces are retained.

**Acceptance scope:** `PASS_FUNCTIONAL_LOOP_TWO_EPOCHS_NOT_HISTORICAL` requires first-epoch source boundary (97 commands), identical source-boundary state with or without synthetic `0360`, real native jump `0360→0042`, and a second bounded epoch in persistent memory reaching `0360`. No assertion about physical print, all errors, unlimited repetitions, exact original instruction or hardware speed follows. If a native probe fails, its evidence is retained and this paragraph is **not** an accepted result; do not claim pass just from an assembled image.

## 3. Explicit historical-source closure register

The rightmost column specifies **planning**, not an assertion that the historical unknown has been solved. `DEFERRED` means: do not keep presenting the same old question as next work; no repeated small research stages without a genuinely new lead.

| Gap | Available functioning substitute / existing acceptance | Historical uncertainty | Project decision |
|---|---|---|---|
| AU `0360` (RAM) | H117 functional return to `0042`; bounded 2-epoch native acceptance | True word and possible continuation/second tape segment unknown | `FUNCTIONAL_ACCEPTED; SOURCE_DEFERRED` |
| FP-MP `3574` / printed 251 vs stated 256 | H115 opt-in 257-word functional FP ROM, with explicit differences and independent Euler/RK4/affine tests | Missing printed word(s), original implementation and overflow behaviour remain unproven | `FUNCTIONAL_SCOPE_DONE; HISTORICAL_DEFERRED` |
| Fixed-point RK4 `3200` | H91–H100 functional HOST output and a **separate synthetic** machine path `3200→3400..3403` with `IO22`, qualified only in scoped native runs | Historical 18/26-command group-print implementation, device output and operator setup not recovered | `FUNCTIONAL_SCOPE_DONE; HISTORICAL_DEFERRED` |
| RK4 `3677` | Functional RK4 bounded demonstrations H83–H113, H97–H100 and H115 FP RK4 (different program) | Printed indication of a block checksum, numerical value and exact historical checking procedure unknown | `NO_INVENTED_WORD; SOURCE_DEFERRED` |
| AU scratch seed, `RAM[0005–0007]/[0012]`, zero-step pointer | Accepted bounded synthetic/reconstructed scenarios; previous `PROPOSED` origin/validation decisions preserved | Historical RAM initialization and operator chronology not established | `HOST_SCENARIOS_RETAINED; HISTORICAL_DEFERRED` |
| AU/ISA negative-zero and shift timing | H14/H17 qualified native arithmetic, H23 and other source-constrained tests | Exact signal-level/physical behaviour not measured for all disputed cases | `REGRESSION_RETAINED; PHYSICAL_RESEARCH_DEFERRED` |
| Variable ROM physical `3777`, full original modules | H116 declarative ROM slots/SHA and safe transactional installation | Exact special physical handling and missing physical sources | `CATALOG_DONE; HISTORICAL_DEFERRED` |
| AU full 4-part test / `0360` | Bounded known-source execution and optional functional loop | Full original AU PASS and real hardware coverage not established | `FUNCTIONAL_DEMO_ONLY; SOURCE_DEFERRED` |

**Reopen trigger:** a newly obtained primary scan/tape/listing with verifiable provenance; a new independent source that uniquely identifies the missing word or algorithm; access to instrumented original hardware; or a reproducible regression where currently accepted **functional** scenarios fail. A functional regression deserves engineering correction; it does **not** retroactively authenticate a historical word. Mere availability of old logs, repeating the same search, an unverified guessed machine word, or an increase in test iterations is not a historical-source trigger.

**PP-2:** full runnable historical binary is presently unavailable, but is a **separate future program feature**, not a requirement for the above reconstructions. A general future archival program inventory may include PP-2 without repeatedly reopening these closed source gaps.

## 4. Next feature work (not further 0360 archaeology)

Advance in **large, internally gated packages**, on `main` only:

1. Integrate existing declarative C2a and persistent C2b operator scenarios with Qt and display the machine/numerical oracle status (without a second CPU executor).
2. Extend the demonstration catalog with block-1 arithmetic, source-bounded AU tests and functional fixed-point RK4, each with provenance and exact acceptance scope.
3. Continue PP-2 and peripheral work when useful. Historical unknowns above stay DEFERRED absent new evidence.

Private build and evidence under `tempkyiv/`; pinned HEAD/source SHA and fail-closed self-test / preflight / native check; no mutation of original printed machine images; precise `git add --` only for accepted files; normal commits to `main` after evidence review.

## 5. Reproduce the experiment

From the repository root, after compiling the production Qt backend with `bash gui/qt6/run.sh --smoke-only`:

```sh
python -B tools/historical/au_0360_reconstruction_v1.py --selftest
python -B tools/historical/au_0360_reconstruction_v1.py --repo . --validate
python -B tools/historical/au_0360_reconstruction_v1.py --repo . --run \
  --backend tempkyiv/qt6_build/kyiv_gui_backend.exe \
  --out tempkyiv/h117_au0360_independent_run_01
```

Output includes `RESULT.json`, SHA manifest, canonical/private input composites and per-instruction trace. The only accepted indicator is the `decision` field `PASS_FUNCTIONAL_LOOP_TWO_EPOCHS_NOT_HISTORICAL` accompanied by SHA/ROM/native evidence. This command is a **new** run in a new directory, never an overwrite.
