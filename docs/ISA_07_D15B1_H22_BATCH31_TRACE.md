# D15/B1-H22 — GY1962 consolidated 31-word test of AU test I

**Source:** V. Glushkov / K. Yushchenko, *Вычислительная машина «Киев»* (1962), printed p. 174. Exact octal transcription occupies addresses `0241–0277` inclusive, 31 words: 28 instructions and 3 data constants `0260–0262`.

**Intent:** larger evidence package but smaller, independently qualified test units. Not a claim of a historically validated complete program. Source transcription status `VISUAL_FIRST_PASS`; independent visual proofreading before any source promotion is recommended.

## Subgroup matrix

| Group | Address block | Purpose | Safety / oracle |
|---|---|---|---|
| A | `0241–0246` | Subtraction, rounded product, loopback/exit | Bounded prefixes; private exit input and source zero-initialized loop |
| B | `0247–0253` | Division, subtraction, magnitudes, I/O/STOP | Check `C=0252` on false without *executing* I/O; test host division-zero stop |
| C | `0254–0257` | Negative-sign fork, STOP, branch to `0042` | Test opcode 31 true/false with private rewrite, stop before external `0214/0042/0043` |
| D | `0260–0262` | Three data constants | Never execute as code; `0260=01777777777777` (37-bit mask) |
| E | `0263–0267` | Normalize, exact compare against positive/negative zero, STOP | Independent entry from H18; store order in `0350`, normalized value `0347` |
| F | `0270–0277` | Normalize and compare including ROM3026=-0 | Explicitly test signed-zero mismatch, private signed-zero success, and stop before `0300` |

## Evidence model

- Full source image has **no appended scratch seeds**. Historical initial scratch state is unknown.
- `A_SOURCE_LOOP`, `E_SOURCE_NORMALIZE`, `F_SOURCE_NORMALIZE` exercise HOST-zero initialization, not verified historical state.
- Private input sets are separate `.k41` images in a temporary directory. The private opcode-31 discriminator replaces only `0254`; it never changes the canonical source image or repository CPU.
- Independently computed 41-bit sign-magnitude fixed-point HOST interpreter checks PC, stop/limit status, instruction count, and eight watched words after **every bounded checkpoint**. It deliberately mirrors documented emulator policy where the primary source lacks a hardware oracle; matching it does *not* promote a historical claim.
- Existing H9/H10/H11/H13/H14/H17 contradictions are open. H19 seed and H20/H21 scratch remain unknown. H17 division-low-bits discrepancy is not resolved by passing this batch.
- Safety: do not execute I/O instruction `0252`; do not execute `0300`, `0214`, `0042`, or `0043`; never use unbounded execution.

## Release criteria

1. Exact base Git SHA, pinned previous source files, only 1 modified README + 6 added files.
2. ZIP SHA manifest, append-only README, full word table and provenance exact audit, rollback on installation failure.
3. Native runner self-test and all bounded native cases PASS for **each** profile in both CWDs. Any divergence gets a local FAIL/OPEN report, never aggregate historical PASS.
4. One native build, one controlled Git release after user-observed success; CPU and ROM unchanged.

**Historical status:** `SOURCE_TRANSCRIBED / HOST_OBSERVATION_PENDING / HARDWARE_ORACLE=0`. No historical seed, no full historical pseudorandom-output oracle, no externally observed historical runtime.
