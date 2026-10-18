# ISA-07 D9-B — IO25 sequential control transfer

**Pinned base:** `5ee37f7` (ISA-07 D9-A). **Primary documentary source:** Glushkov–Yushchenko 1962 (**GY62**), **printed p. 15**, source SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`. The document states that IO25 passes control to the **next instruction in order**, which must be IO23 or IO24. This is `SOURCE_STRICT` for the sequential control transfer only; the exact file encoding, tracks/zones and physical drum are not oracles.

## Exact CPU delta

Add **two statements** after the existing field-I selection for IO25, just before the handler closes:

```cpp
++C_reg;
K_reg = kmem.read_memory(C_reg);
```

`++C_reg` is the documented digital transition. `K_reg` loading follows the **existing emulator prefetch convention**, also used in IO22, IO23 and D9-A IO24. The next `execute_opcode()` unconditionally fetches K again. This stage does not claim independent historical evidence that prefetch occurs at the precise instruction boundary.

The current IO25 field interpretation is preserved exactly: I=0 writes `drum_num_read` and `drum_zone_read`; I=1 writes `drum_num_write` and `drum_zone_write`, using the existing shifted-fields implementation. GY62 describes raw II/III; the implications of register-A modification, direction wording and track encoding remain **OPEN** rather than silently resolved.

## Two real CPU steps and host isolation

A fresh `Kyiv_t` executes IO25 at octal 0100, then a genuine IO23 or IO24 at octal 0101. The second command branches to octal 0120 (or 0130), containing a STOP instruction fetched into `K_reg` by the second handler. The two-step probe verifies PC after both steps, K prefetch, full read/write setup state, and that IO25 alone does not mutate target RAM. It also verifies actual memory output for IO23 and actual RAM input for IO24.

Python launches eight independent processes under disposable filesystems; there is **no modification to repository peripheral files**. IO23 emits signed decimal host tokens via `word_to_number`; IO24 consumes host decimal text. `read-missing` is explicitly **HOST_POLICY**, not a claim about historic machine-error behavior. All testing is digital; no physical timing or analog model.

## Historical gates and unresolved issues

- Current-CPU behavioral cases: `write-basic`, `write-single`, `write-offset`, `write-alt`, `read-basic`, `read-single`, `read-trackzone`, `read-missing`.
- The D9-B audit pins exact Git blobs at `5ee37f7` and accepts only this two-line CPU addition. It does not modify D9-A and previous auditors or their source pins.
- Existing D8-B outputs remain valid. D9-A two-step reading remains valid. D8-A's legacy IO24 `C=0100` expectation is obsolete, but its eight IO20/21 cases remain usable.
- The semantics of IO20/21 PC, IO25 when the following instruction is not 23/24, control register modification, invalid I field, host I/O failures, and physical drum layout remain **OPEN**.
- No commit until actual `Kyiv_t` run and full regressions pass.
