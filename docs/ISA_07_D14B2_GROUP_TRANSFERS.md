# ISA-07 D14-B2 — атомарні групові передачі логічного барабана

**База:** `31a3c3c26326dcc0ee05ea601300182ab7fd3dcd` (D14-B1).  **Клас:** HOST_POLICY / standalone API, HARDWARE_ORACLE=0.

## Область змін

Додано `inc/kyiv_drum_group_transfer.h` над **незміненим** `inc/kyiv_drum_logical_media.h`. Жодних змін `src/main.cpp`, `inc/kyiv.h`, історичних тестів або обробників `23/24/25`. Немає CPU-інтеграції, фізичного формату барабана, розбору полів `25` і серіалізації. Попередні текстові адаптери були заглушками, не стандартом нового пристрою.

## API

```cpp
#include "kyiv_drum_group_transfer.h"
using namespace kyiv_drum_media;
logical_media m(geometry{"test-mini-2x3x4", 2, 3, 4});
const auto end = write_group(m, {0, 0, 3}, {5, sign_bit, 9});
// end.last == {0, 1, 1}; group crosses track 0 -> track 1.
const auto result = read_group(m, {0, 0, 3}, 3);
// result == {5, sign_bit, 9}; -0 survives unchanged.
```

`validate_span(media,start,count)` produces `transfer_span{first,last,count}` after validating the *entire* range. `write_group` returns the checked span; `read_group` returns `std::vector<uint64_t>`.

- All indexes **zero-based HOST_API**. End-of-track advances to the next track **on the same drum**; never automatically switch drums. Automatic traversal beyond the final track is rejected as `END_OF_DRUM` **before** mutation. The real behavior at historical track 24 remains OPEN.
- `count=0` -> `INVALID_COUNT`; invalid drum/track/slot -> `INVALID_DRUM`, `INVALID_TRACK`, `INVALID_SLOT`; oversized range -> `END_OF_DRUM`; raw bit 41 or above -> `INVALID_WORD`.
- `write_group` validates the entire span **and all words** before any write. The commit phase calls B1 `store` only on prevalidated, in-range positions, with no allocations or failure paths. A failure leaves every cell and `written_count` unchanged. No entire-image snapshot required.
- `read_group` refuses **any** `UNWRITTEN` slot with `UNWRITTEN`; it never supplies an invented zero for unknown data and never mutates media. The caller receives a vector only after success. Physical unreadable-sector behavior is OPEN.
- Words keep all 41 raw bits: `+0=0`, `-0=1<<40`, arbitrary instruction words. Geometry and the `1,000,000` host-capacity guard are inherited unchanged from D14-B1.

These rules specify a **host logical abstraction**, not authentic track encoding or historical device timing. The D14-A source discrepancies (`9864` total vs. `511` codes/track) are still OPEN; `experiment-137`/`experiment-511` are explicit synthetic test profiles only.

## Verification

1. Compile `tests/isa/isa07_d14b2_group_transfer_probe.cpp` with genuine `inc/kyiv_drum_logical_media.h` and `-Wall -Wextra -pedantic -Werror`. Do **not** link `src/main.cpp`.
2. Run `tools/isa07_d14b2_group_transfer_sandbox.py --exe ... --random-steps 200 --timeout 5`. Independent Python dictionary oracle checks 18 static groups plus 4 seeded random profiles, including whole-image readback for mini profiles and deterministic sampling for large profiles.
3. Audit `tools/isa07_d14b2_audit.py` pins baseline Git blobs, all new file digests, exact file scope and absence of any tracked mutation. Self-test checks EOL normalization, byte integrity, and the documented group/test markers.

**Acceptance:** `ISA-07 D14-B2 GROUP PASS=22/22 COMMANDS=1565 ... CPU_MUTATION=0 PERSISTENCE=DEFERRED HARDWARE_ORACLE=0` at `--random-steps 200`. The runner's operation count is deterministic; no new historical oracle is claimed.

## Following stages

**D14-B3:** explicit versioned portable binary image with magic/version, geometry/profile, written bitmap, raw 41-bit words and integrity checks; finalize exact byte layout and commit policy independently. **D14-C:** `25 -> 23 -> 25 -> 24` with genuine `Kyiv_t`, exact byte and `C/K` checks. Future source audit must settle command 25 fields and physical track geometry; no silent defaults.
