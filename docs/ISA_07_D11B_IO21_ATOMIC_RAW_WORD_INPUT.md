# ISA-07 D11-B — IO21 host raw-word input: strict, bounded, atomic

**Baseline:** `707cdf7ef72467e305056c0ff22d6582d16c8f76` (D11-A committed/pushed; D11-A actual MinGW 11/11, `LONG_BITS=32`, D10-G4 finished). This patch changes only the opcode-21 arm of `src/main.cpp`, adds one header and seven test/documentation utilities. The independent `IO20` and `IO22–25` implementations are untouched.

## Historic source versus explicitly modern host policy

- `SOURCE_STRICT` GY62 (Glushkov/Yushchenko, 1962), **printed p.16**: В2 opcode 21 inputs *machine codes*, **without decimal-to-binary conversion**, to the inclusive `[a1,a2]` destination range. Printed **p.58** documents `C+1 -> C`, `M[C] -> K` after the operation. Printed pp.7–8 specify 41-bit words (40 magnitude bits plus sign) and physical RAM `0000..1777`, with hardwired zero cell `0000`.
- `HOST_POLICY` here: each text **line** in `../punched_tape.txt` is one 41-bit raw unsigned bit pattern expressed in **one to fourteen ASCII octal digits**. ASCII spaces or tabs may surround digits; LF/CRLF accepted; no whitespace or NUL within a number. A leading `+` or `-`, prefix `0o`, suffix, nonoctal digit, >14 digits, or numeric value `> 037777777777777` is invalid. Input `020000000000000` is the SIGN BIT (`-0` as a raw pattern), **not** `-1` textual arithmetic. Variable-width leading zeros are allowed to preserve existing 1–3 digit D10-A positive host fixtures. This text encoding is NOT a specification of historical tape punches, parity, device timing or an actual physical card format.
- `HOST_POLICY` cursor: `h` is the 0-based starting *text line*. One **successfully stored** word consumes one selected line. After a success, `h += (a2-a1+1)`; after failure, `h` stays unchanged. Unread trailing records (including malformed ones) are out of scope of the current command, not validated. `../heads.txt` was opened/discarded and did not actually select a record; remove this dead host code; historical heads structure remains `OPEN`.
- `HOST_POLICY` errors: missing input file `UNAVAILABLE_STREAM`; unavailable requested starting record `MISSING_START_LINE`; truncated record block `SHORT_INPUT`; an all-space/empty record `EMPTY_RECORD`; malformed or overflowing word `INVALID_TOKEN`; reversed effective interval `INVALID_INTERVAL`; destination beyond `01777` `INVALID_RAM_ADDRESS`; invalid parser count and impossible line-selection addition are separate checked statuses. These errors raise `std::runtime_error("IO21: STATUS")`, rather than pretending to describe historical halt behavior.

## Exact commit / failure boundary

1. Decode address modifications **through existing** `shift_addr3_byA`; validate nondecreasing interval and upper physical-RAM bound **before opening stream**. The hardwired address `0000` accepts an input position but never stores a word.
2. Read and validate exactly the selected `count=a2-a1+1` lines into a local vector. Every rejection returns no words from `collect`; **no RAM write**, **no `h` advance**, **no `C` advance**. Initial `execute_opcode` fetch may have loaded the current command into `K`, and that initial fetch is **not** rolled back.
3. On validated complete block, write the count words into `[a1,a2]`, update `h`, then execute documented `++C_reg; K_reg=kmem.read_memory(C_reg)`. For a valid RAM interval writes are deterministic and do not allocate. The atomic guarantee applies to **host input validation failures**; asynchronous interruptions or unrelated CPU faults (for example failed following-command fetch) are not represented as transactional hardware behavior.
4. `A`, `P`, `Loop`, `perfo_num`, `T` unaffected by this handler, and the consecutive true CPU step still executes the following XOR test instruction. `IO20` and `IO22–25` untouched, no new external dependencies.

## Evidence from D11-A / why necessary

Actual user's **MinGW Windows `LONG_BITS=32`**: `std::stol` rejected a legal 41-bit word, treated `11xyz` as `11`, accepted `-1` as an unsigned machine word, returned success on nonexistent tape, and partially wrote two or one RAM cells before throwing on short/malformed input. These were `CURRENT_CODE` observations (11/11), not historical behavior. D11-B replaces these exact host defects; **do not rerun D11-A observation gates as post-fix functional truth**.

## Qualification and regression gates

- Strict parser/collect in `inc/kyiv_binary_input_plan.h`: standalone C++ probe with independent Python integer oracle and deterministic randomized sample; default `PASS=225/225`. Corrupt records return **zero** staged words, including records that fail after earlier valid lines.
- True `Kyiv_t` C++ probe, not a mock: 28 sandbox cases; success **12 two-step** PC/K/XOR witnesses, failure **16 fully atomic** checks for all 1024 physical RAM cells. Sign bit `020000000000000` and maximum `037777777777777` are accepted on LLP64/LP64, independently of `sizeof(long)`.
- Functional regressions: `IO22–25` D8B=10, D9A=7, D9B=8; five valid IO21 D10-A legacy modes (exclude superseded `21-missing`), D10-F3 IO20 **50/50**; ISA06 **STRICT=89/89 POLICY=40/40**. The old D11-A runner and older **structural** auditors pin obsolete CPU blobs and must remain archival.
- Repo audit pins `HEAD` to D11-A, the original CPU Git blob SHA, and proves **exactly** the single IO21-arm substitution plus single header include, with normalized LF/CRLF handling. No broad refactor and no README or older test edits. New-file SHA-256 of seven non-auditor files; `tempkyiv` only for generated artifacts. CPU compilation and runtime verification must be completed by user's MinGW before commit.

## Remaining OPEN

Actual punched-media binary encoding, hardware input/parity errors, pointer/index vs punched tape indexing, console-switch implications, machine stop state and failure-control signals. Strict text grammar is a **compatibility-oriented host adapter**, not `SOURCE_STRICT` for physical media.
