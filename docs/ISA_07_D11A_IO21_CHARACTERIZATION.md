# ISA-07 D11-A — IO21 (В2) host-code characterization, no CPU fix

**Status:** staged, requires actual user MSYS2 evidence. **Prerequisite:** D10-G4 is committed as a six-new-file documentation commit whose parent is `75a401107b03e9fb535d9aaf97b56c85a434293f`. Do not amend D10-G4. No existing source file is modified.

## Qualified historical boundaries

- GY62 (Glushkov/Yushchenko 1962), **printed p. 16**: opcode `21` enters *machine codes*, not decimal numbers, into the **inclusive** destination interval `[a1,a2]`. Unlike opcode `20`, this operation does not perform decimal-to-binary conversion. Exact physical punched-code representation, card/paper tape selection and host textual notation **are not specified by this statement**.
- GY62, **printed p. 58**: on successful opcode `21`, `C <- C+1`, then `K <- M[C]`. This control transfer is already implemented and qualified by D10-A (six IO21 two-step cases).
- GY62, **printed pp. 7–8**: one memory word has **41 bits** (40 magnitude plus sign); physical RAM is octal `0000..1777` and cell zero is hardwired zero. A 41-bit raw word can have its top/sign bit set. The source does not prescribe a host text parser or a valid word representation outside the physical peripheral.

## Actual pinned C++ behavior, not historical semantics

- `src/main.cpp` at pre-G4 baseline (`75a4011`) has Git blob `e6d00248705668156c29b376b3dd1b26ed40e275`; D10-G4 changes documentation only. Its `opcode_read_perfo_binary` opens `../punched_tape.txt` and `../heads.txt`, discards two `heads` lines, uses `h` as a host record index, and runs a `while(punch_cards)` loop with `std::getline()` followed by `std::stol(line,0,8)`.
- It immediately calls `kmem.write_memory` for each converted line. An invalid *later* record can therefore throw **after previous writes**. There is no whole-command prevalidation or rollback. D11-A probes **observe** this condition without asserting historical peripheral error semantics.
- `std::stol` uses C++ `long`, whose width is platform-dependent (commonly **32 bits** on MinGW/Windows). It is not a safe general 41-bit code parser. `std::stoull` with full-string validation and 41-bit bound is a possible **future HOST_POLICY**, not a source-prescribed textual encoding.
- There is no explicit failure for a missing file, no check of `std::getline()` success *before* parsing, no full-string consumption check, no nondecreasing-interval guard, and no physical RAM-boundary check. `heads.txt` is opened and its lines read but currently does not determine the selected input line. `h` increases by the number of accepted words **only if execution reaches the end**.
- `C++ CODE OBS`: successful execution increments `C` and prefetches K, whether or not any words were read. Failed `stol` conversions throw, leaving `C` at the current instruction and possibly leaving some RAM already changed. These are host implementation observations, **not** demonstrated historical error handling.

## Work division and acceptance

**D11-A:** keep all existing files byte-identical, add isolated real-`Kyiv_t` probe and host sandbox. Test six known-good IO21 source-qualified continuation modes separately with existing D10-A probe/runner; additionally characterize 11 new normal, malformed, missing and width-sensitive host inputs. For dangerous reversed addresses or out-of-physical-RAM addresses, use static evidence only in this stage: unguarded read may be unsafe to execute.

**D11-B:** choose an explicit *provisional host raw-word textual grammar* (likely exactly 14 octal digits, optional compatibility mode by separate decision), strict 41-bit bound, whole-block staging and atomic commit. Validate inclusive physical RAM addresses before touching memory, and preserve the source-strict `C/K` continuation and `h` host behavior on success. Error behavior remains HOST_POLICY. Do not change IO20 or IO22–25. Avoid assuming negative numeric `-1` is a valid raw machine-code notation; signed negative zero is a bit pattern.

**D11-C:** real two-step CPU gate, failure nonmutation checks over entire physical RAM, no partial `h/C` on rejection; 6/6 IO21 exact old positive fixtures requalified against the explicitly changed grammar, D10-F3 IO20 50/50, unaffected IO22–25 25/25, and ISA06 89/89+40/40. Archival auditors with older CPU SHA must not be misused after changes.

Never promote the current `stol` host adapter to `SOURCE_STRICT`. No analog tape mechanics, drum simulation, SIMH migration, or peripheral timing in D11-A.
