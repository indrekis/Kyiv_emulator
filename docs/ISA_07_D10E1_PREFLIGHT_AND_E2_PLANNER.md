# ISA-07 D10-E1 preflight / D10-E2 standalone input planner

**Reviewed exact baseline:** `2d0aaf48ab848b6789f85dca355d05e8c0e0f03f` (HEAD must not move before application).
**Stage E1:** READ-ONLY documentary/code preflight (this report).
**Stage E2:** add one side-effect-free staged input planner and its independent tests. **No CPU modification or real IO20 integration** until separate E3 after user-side PASS.

## Sources and immutable pins

- GY62: Glushkov / Yushchenko (1962), printed pp. 6–8, 15–17, 58; local PDF SHA256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea` (verified on package preparation host).
- DPS64: Dashevskii / Pogrebinskii / Shkabara (1964), printed pp. 15–16 (two pages in scan PDF pp. 8–9); local scan PDF SHA256 `ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5` (verified on package preparation host).
- `src/main.cpp` SHA1 Git blob `bc9331b178333d2e3ef32789972bc16bc70c39ea`.
- `inc/kyiv.h` SHA1 Git blob `ff4aa592f12b07d32b4961b49cb97b15289d38e0`.
- `inc/kyiv_decimal_exact.h` SHA1 Git blob `6a09319f3eef53236c87647d4e4d155ce9addd75`.
- `inc/kyiv_decimal_ascii.h` SHA1 Git blob `93e47fd34b5133964fb5a9addab3430dd25f71ae`.
- Historical evidence and their immutable source pins are not rewritten.

## SOURCE_STRICT (digital only)

1. GY62 pp. 6–7, 16–17 and DPS64 pp. 15–16: one input number has ten BCD decimal fractional digits and a separate sign; opcode `20` converts numeric input to the 41-bit binary sign/magnitude word, with 40 binary fractional bits.
2. GY62 pp. 16 and 58: group input fills OЗУ addresses `a1, a1+1, ..., a2` inclusive; number of words is `a2-a1+1` for qualified nondecreasing addresses.
3. GY62 p. 16: for punched CARD input, instruction III address specifies the **zone**. No ASCII byte-column convention follows from this.
4. GY62 p. 58: successful IO20 completes with `C <- C+1` and `K <- M[C]`; existing D10-A code already does this.
5. GY62 p. 8: RAM cell `0000` reads 0 and rejects mutations at the architectural level; future CPU tests must avoid treating a write there as ordinary memory storage.
6. GY62 p. 15: I/O group operations destroy the modification register, but its precise numeric result is not modeled here; this is an OPEN longer-term work item. Do not add speculative writes to `A_reg`.

## HOST_OBS at pinned main.cpp (lines 243–299)

- File is `../../mem/punch_cards_in.txt`, resolved relative to the current process working directory. Opening errors are not checked; missing file simply yields no records, then PC proceeds.
- `counter` starts at 0, `num_counter` starts at 0 and `perfo_num` is a member `int` (default 0). The selected line test is `counter == perfo_num`.
- On the selected line, the current code calls `line.substr(addr3_shifted.destination, line.size())`: this uses **effective a3 as a byte offset**. `substr`'s length argument is oversized but harmless after a valid offset; offset past line length throws. This is a host interpretation, NOT GY62's card-zone definition.
- Selected line is split by Boost on literal SP with `token_compress_off`; numeric tokens use `std::stol(token,nullptr,8)`. On other lines with `counter > num_counter`, an unrelated condition compares PHYSICAL LINE count with WRITTEN WORD count and uses `std::stoi(token,nullptr,8)`; no full-token consumption check exists.
- Both branches write into RAM **immediately** at `a1+num_counter`. Two guards test `num_counter > a2-a1`, preserving the inclusive range only when a1<=a2. Invalid input may leave some RAM words written before exception; short/missing input may silently leave unchanged cells.
- When completion was reached with exactly the requested number of values and no surplus, the outer loop need not break immediately; later lines can be reconsidered. `perfo_num` is not advanced in the IO20 body.
- Successful and short/missing paths all perform `++C_reg; K_reg = kmem.read_memory(C_reg)` after EOF (D10-A fix).
- `21` uses `../punched_tape.txt`, `h` to select records, and parses octal codes, independently; `22–25` have independent I/O control paths.

### Counterexample to current selection

Take `perfo_num=2`, `counter=1`, `num_counter=0`. The condition `counter > num_counter` evaluates true and reads **line 1 before requested line 2**. This is a concrete host-code defect, but fixing that selection logic belongs to a distinct, explicitly qualified step, not a silent incidental change while replacing numeric conversion.

## Separation of facts and decisions

| Question | Classification | Stage decision |
|---|---|---|
| 41-bit sign/magnitude result for exact fractions | SOURCE_STRICT | D10-C/D10-D, unchanged |
| Inclusive target RAM interval | SOURCE_STRICT | unchanged; E3 will validate RAM bounds before commit |
| Sequential C/K on successful IO20 | SOURCE_STRICT | unchanged; real CPU two-step tests in E3 |
| Meaning of third address on punched cards | SOURCE_STRICT | zone selector, **not** an ASCII byte offset |
| Effective `a3` as offset in chosen text file | HOST_OBS / HOST_POLICY | E2 makes it explicit ONLY as current text-adapter convention |
| `perfo_num` as zero-based line number | HOST_OBS / HOST_POLICY | E2 takes a specified zero-based line index; interpretation remains host-only |
| `counter > num_counter` logic | HOST_OBS / HOST_CODE_FIX pending | E2 substitutes deterministic staged selection; CPU untouched until E3 |
| Rounding, nonexact input, underflow sign, hardware errors | OPEN | no invented historical behavior; D10-C rejects NONEXACT |
| Reversed intervals, invalid addresses, modify register after IO | OPEN | no machine claim; separate E3 fail-closed host validation |
| Failure of file/record processing | HOST_POLICY | explicit failure; no partial staged output or CPU continuation invented |

## Chosen minimal E2 HOST_POLICY

The function `kyiv_decimal_input_plan::collect(stream, start_line, first_offset, count)`:

1. Uses a caller-supplied input stream (source path and availability are E3 responsibilities). A closed/bad stream is `UNAVAILABLE_STREAM`.
2. Skips precisely `start_line` LF/CRLF-delimited host text records. It then interprets `first_offset` as a **byte position** into the first selected record only. Following records are processed whole. These definitions are not physical device descriptions.
3. Uses D10-D `parse_record()` to validate an ENTIRE consumed record, even if only its prefix is needed. Empty record, invalid token and NONEXACT are errors. UTF-8 input outside ASCII is rejected by D10-D. A single final CR is removed after `getline` for LF/CRLF parity.
4. Collects exactly `count` 41-bit machine words (between 1 and 1024). A too-short stream is an error. Excess valid tokens from the final consumed record are ignored, preserving the notion of a bounded destination group.
5. On ANY failure, returns status and **an EMPTY vector**. The caller must not write before receiving `EXACT`. No partial state is exposed. This is STAGING-ONLY, not yet CPU memory atomicity.

The deliberately strict **whole-consumed-record validation** means an invalid/`NONEXACT` surplus token after the requested final word also fails: this is an explicit safety tradeoff and may be revisited in its own HOST_POLICY step. Blank lines are NOT silently skipped. Repeated IO20 behavior (`perfo_num` state progression) is not decided here.

## Proposed E3 CPU contract (NOT in this patch)

At IO20 start: check `perfo_num>=0`, `a1<=a2`, `a1>0` if the intended test needs ordinary RAM storage, and `a2<03000` (RAM only). Special cell `0000` may be explicitly allowed as discard with its documented zero behavior, but tests must not treat it as an ordinary destination. Compute count without unsigned underflow. Open the existing path, reject a missing file. Collect all data, require `EXACT`, then commit exactly one word per destination and preserve successful `++C_reg; K_reg=M[C_reg]`. Any host error should report explicit failure **before writes**; prefer throwing a precise `std::runtime_error` with C unchanged and no emulated physical HALT assertion. The initial instruction fetch at `execute_opcode()` already loads K and cannot be undone by a later file error.

E3 must perform genuine `Kyiv_t::execute_opcode()` twice for success, separately check failure-side CPU registers and RAM, test both signs/zeros, shifted ranges, zone offsets, multiple records, short/missing/empty/nonexact/invalid data, and preserve 21–25 + ISA-06 regression. Do **not** count E2's standalone probe as CPU integration evidence.

## Regressions and obsolete oracles

Use ISA-06 STRICT 89/89 and POLICY 40/40, D8-B 10/10, D9-A 7/7, D9-B 8/8, D10-A 12/12 as regression targets only if their post-E3 expectations are still semantically applicable. D10-A **IO20 numeric HOST_OBS** test fixtures depend on octal parsing and will cease to be correct after E3 (its IO21 subset and two-step control logic remain relevant). D10-B deliberately asserts wrong host-octal observations and must not gate E3. Pre-fix D7/D8-A/D3 results and whole-file D10-C/D10-D audits that pin CPU are archival only. Retain all old artifacts untouched.

## Local sandbox evidence (not Windows CPU proof)

D10-E2 new standalone probe: 26 independent Python cases with rational `Fraction` oracle and 7 source-calibrated word vectors; local Linux GCC compilation and sandbox passed `26/26`. Exact D10-C/D10-D headers used in local probe had Git hash-object values matching the base blobs above. No `Kyiv_t` instance was run and no real CPU register was observed. User-side MSYS2 evidence is required before any commit.
