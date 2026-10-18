# ISA-07 D9-A — opcode 24 branch to a3 and K-register prefetch

**Baseline:** `df480cd` (ISA-07 D8-B). **Documentary source:** V. M. Glushkov and E. L. Yushchenko, *Vychislitelnaya mashina «Kiev»* (1962), printed p. 15, SHA-256 `a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea`; cf. `docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md`.

GY62 explicitly states that after magnetic-drum **read** (octal opcode `24`, МБЧ) the machine transfers control to address **a₃**. The baseline D8-B `src/main.cpp` processes the host input but neither updates `C_reg` nor preloads the next instruction in `K_reg`. Opcode `22/23` already uses `C_reg = addr3_shifted.destination; K_reg = kmem.read_memory(C_reg);`.

## Exactly two CPU lines

At the end of the opcode-24 handler, immediately after `magnetic_drum.close();`, add:

```cpp
C_reg = addr3_shifted.destination;
K_reg = kmem.read_memory(C_reg);
```

The **branch to a₃** is source-documented. Reading `K_reg` at this point follows the **existing emulator register convention** for `22/23`; it is *not* an independent documentary oracle for the historical timing of the instruction register. `execute_opcode()` itself fetches `K_reg` from memory at `C_reg` at the beginning of every step, so prefetched `K_reg` is verified separately as an emulator state contract.

The already-established address-modification path supplies `addr3_shifted.destination`; no change to modified-vs-raw address semantics or the address-modification register itself is made in D9-A. No change to drum file contents, parsing, tracks, zones, memory intervals, C-reg control of `20/21/25`, output commands, or analog/electrical timing.

## Gate: seven isolated TWO-STEP cases

`tests/isa/isa07_d9a_io24_branch_probe.cpp` executes **two genuine `Kyiv_t::execute_opcode()` calls**. First `24` reads the host fixture. At target `a₃` there is a nonzero XOR instruction (`017`) that computes `5 XOR 3 = 6` in a distinct destination. The following sequential address `0101` has a STOP instruction as a negative witness. The test checks:

- After the first step: `C=a₃`, `K=memory[a₃]`, the expected RAM data, unchanged drum preparation parameters and `running=1`.
- After the second step: target XOR truly executed (`mem[0206]=6`), `C=a₃+1`, and `running=1`. This distinguishes an actual branch from merely reporting the desired `C`.
- Full, short, empty, missing-host-file, nonzero host track index, single-cell destination and alternate branch target (`0130`) — seven cases; all run in isolated temporary directories.

Empty/missing host files are **HOST_POLICY** expectations of the existing C++ adapter, not historical claims about failed magnetic-drum hardware. Host-file paths, data representation, track switching, and K prefetch timing are not historical device oracles. `24` input address interval semantics were established in D8-A and are unchanged here.

## Historical baseline separation

The D7 `24-range` scenario recorded `C=0100` as a **pre-fix DOC_MISMATCH**. D8-A's `24-*` scenarios similarly expect the old `C=0100` by design. **Do not run them as current-CPU pass gates after D9-A.** D9-A's new runner tests the updated PC path; D8-B output runner and ISA-06 tests remain current. The previous D7 and D8-A tests and their Git blob pins remain unchanged.

Open for later: opcode `25` sequential transfer to the next instruction (D9-B); `20/21` PC behavior; destruction of address-modification register by all I/O commands; host malformed records; reverse address intervals; track rollover and physical device behavior.
