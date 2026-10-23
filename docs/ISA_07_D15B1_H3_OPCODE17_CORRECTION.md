# D15/B1-H3 — operation 17: 41-bit XNOR correction and current documentation

Pinned baseline: `6f20450b656374e8c9ad199d3d2ae1e09424d297` (D15/B1-H2).

## Source adjudication — evidence versus observed hardware

- GY1962, *Vychislitelnaya mashina «Kiev»*, printed p. 11: **XOR** truth table (inequivalence). This is **genuine contrary primary evidence**.
- GY1962, printed pp. 172–173: the authentic AU logic diagnostic `0043..0107` requires **XNOR** at `0073`, `0076`, `0101`, `0104`.
- Dashevskii, Pogrebinskii, Shkabara, *Vychislitelnaya mashina «Kiev»* (1964), printed p. 18: operation 17 explicitly called *ravnoznachno*, with **XNOR** truth table `00→1, 01→0, 10→0, 11→1`.

Decision: implement `OP17(a,b) = (~(a ^ b)) & ((1ULL << 41) - 1)`, including sign bit 40; **not** unmasked `~`, which would set nonexistent bits 41–63 in host `uint64_t`. This is a software model decision supported by two source witnesses, **not** an original-machine hardware measurement. Preserve H2 evidence and the GY1962 contradiction.

## Code and public documentation changed together

- Production `src/main.cpp`: only logical opcode 17 case changes its arithmetic expression. Other opcodes, ROM and the HOST image parser are unchanged.
- `README.md`, `documentation/documentation.txt`, `docs/isa_opcode_registry.csv`: current meaning documented as XNOR, including the legacy `xor` assembler mnemonic. The mnemonic is **not renamed** in this step to preserve assembler/disassembler compatibility; callers using `xor` should know execution is XNOR.
- ISA-06 D1 and D2 audit notes: explicit H3 supersession. Original stage-qualification narrative remains traceable, rather than being misrepresented as XNOR evidence.
- `tests/isa/isa06_d1_logic_probe.cpp` and `tests/isa/isa06_d2_logic_sequence_probe.cpp`: existing functional postconditions updated for 41-bit XNOR, including sign-only, identical operands, current-instruction self-modification, and opcode 17 executed as a second instruction.
- `examples/historical/gy1962/README.md`: distinguishes the **old** H1 `CPU_STOP STEPS=19 C=0076` observation from the **new** candidate success route. The original `.k41` image and its provenance remain byte-for-byte unchanged.
- H2 `--expect xor` log remains historical evidence; the same H2 executable oracle, using `--expect xnor`, is the primary new qualification gate.

## Qualification requirements

Run actual MSYS2 native binaries, do **not** claim PASS from static source alone:

1. Full H2 independent 41-bit / sign-bit / historical-image discriminator: `18/18`, `--expect xnor`, `HISTORICAL_TEST_MATCH=1`, with the authentic image bounded to **22 instructions**, stopping before selector `0107` is executed.
2. Recompiled ISA-06 D1 regression: `STRICT=38/38 DOC-MISMATCH=0 POLICY=0 OBS=2` (OBS are **not** hardware oracles).
3. Recompiled ISA-06 D2 regression: `STRICT=17/17 DOC-MISMATCH=0 POLICY=0 OBS=0`.
4. Exact SHA pins for unchanged `mem/ROM.txt`, `au1_logic.k41` and historical provenance. `INDEPENDENT_SECOND_PASS=PENDING`, `HARDWARE_ORACLE=0`.
5. Confirm exactly 9 targeted existing files modified, 5 new (two docs, transform/audit/regression), with no unintended production mutation.

A successful run of `18/18` establishes reproduction of a documentary expectation, **not** electrical-level accuracy of the physical Kyiv computer. Do not silently revise the GY1962 p. 11 description.
