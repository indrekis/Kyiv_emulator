# ISA-07 D14-B3 — власний бінарний образ логічного барабана (`KYIVDRM1`)

**База:** `5632a0b0b7e622c1c06cbea8aee82679dca0c926` (D14-B2). **Статус:** HOST_POLICY, **NOT** a physical dump of the historical magnetic drum. D14-B3 does **not** alter `Kyiv_t`, opcodes 23/24/25, D14-B1 or D14-B2. The old text-based host adapters are placeholders and are **not** the canonical image format. `HARDWARE_ORACLE=0`.

## v1 immutable wire format, `.kdr`

All integer fields are **unsigned, explicitly encoded little-endian**, without ABI-dependent structures or padding. No compression and no implicit geometry. An image is exactly:

| Offset (decimal bytes) | Size | Meaning |
|---|---:|---|
| 0 | 8 | Magic: ASCII `KYIVDRM1` |
| 8 | 4 | Format version, `uint32`, value **1** |
| 12 | 4 | Fixed header size, `uint32`, value **64** |
| 16 | 8 | `drums`, `uint64` |
| 24 | 8 | `tracks_per_drum`, `uint64` |
| 32 | 8 | `slots_per_track`, `uint64` |
| 40 | 8 | `cell_count = drums * tracks * slots`, `uint64` |
| 48 | 8 | `written_count`, `uint64` |
| 56 | 4 | `profile_len`, `uint32`, **1–64** |
| 60 | 4 | Reserved, `uint32`, **0** |
| 64 | `profile_len` | Exact ASCII `profile_id` bytes `[A-Za-z0-9_.-]`, no NUL |
| `64+profile_len` | `ceil(cell_count/8)` | Written bitmap, bit `i%8` in byte `i/8` identifies written cell `i` (low bit first); padding bits **0** |
| after bitmap | `8*cell_count` | **Every** cell as `uint64 LE`; high 23 bits must be zero; `UNWRITTEN` must have all eight bytes **0** |
| final 8 | 8 | CRC64/ECMA-182, `uint64 LE`, of **all preceding bytes** |

**Exact length and offsets.** Let `N = drums * tracks_per_drum *
slots_per_track`, `P = profile_len`, and `B = (N + 7) // 8`.
The image length is exactly **`64 + P + B + 8*N + 8` bytes**.
Cell `i` occupies bytes
`[64+P+B+8*i, 64+P+B+8*(i+1))`, in drum-major,
track-major, slot-major order. The CRC field starts at
`64+P+B+8*N` and covers the half-open byte interval
`[0, 64+P+B+8*N)`. All offsets are zero-based.


Linear cell index `i=((drum*tracks_per_drum)+track)*slots_per_track+slot`. Coordinates are zero-based `HOST_API`; this does **not** specify historical opcode-25 bitfields. Bit 40 is the sign bit in a raw 41-bit word; `+0=0`, `−0=1<<40`, and `UNWRITTEN` (bitmap 0) are three distinct states. CRC64/ECMA-182: `poly=0x42F0E1EBA9EA3693`, non-reflected, init/xorout 0; check vector `CRC64("123456789")=0x6C40DF5F0B497347`. The checksum detects unintentional corruption, **not malicious tampering**.

**Canonical strictness:** reject unknown versions, unexpected header/reserved values, extra/truncated bytes, geometry mismatch with recorded count, wrong checksum, high bits in words, nonzero padding bits, nonzero payload of unwritten cells and wrong `written_count`. There is no best-effort or partial recovery. A geometry is accepted only via the existing B1 constructor, with explicit profile ID and 1,000,000-cell HOST safety cap; total file HOST safety limit is 9 MiB. No default selection of experiment-137 versus experiment-511; both remain provisional and NOT `SOURCE_STRICT` physical geometry.

## C++17 API (no CPU integration)

```cpp
#include "kyiv_drum_persistence.h"
using namespace kyiv_drum_media;
namespace persist = kyiv_drum_persistence;
logical_media image(geometry{"experiment-137", 3, 24, 137});
image.store({0,0,0}, sign_bit); // raw -0, not numeric zero
persist::save_atomic(image, "some_image.kdr");
logical_media fresh = persist::load("some_image.kdr");
persist::load_into(image, "some_image.kdr"); // exact geometry/profile required
```

- `encode(image)` returns canonical binary bytes; `decode(bytes)` returns a **new** validated image. `load(path)` rejects bad data without mutating an existing `logical_media` object. `load_into(destination,path)` loads and validates **before** replacement and requires full profile/geometry equality (`GEOMETRY_MISMATCH` otherwise). The destination is unchanged on any failure.
- `save_atomic(image,path)` completely encodes before filesystem changes, writes a randomized-named temporary *sibling* file, checks write/flush/close and uses a single `std::filesystem::rename(temp,path)`; on failure removes the temporary file and leaves the original target unchanged. **No delete-old-then-rename fallback.** A target directory and missing parent are tested failures.
- `std::filesystem::rename` replacement semantics and permissions must be checked on the user's target platform (MSYS2/Windows). Atomicity is limited to successful file replacement on a supported filesystem. Crash durability (`fsync` file and directory), concurrent writer serialization, locking, path race/symlink defense, device timing and physical read error semantics remain **OPEN**. The temporary-file naming does not establish a multi-process exclusive lock.
- Binary images use the indicated host `.kdr` extension; they do **not** preserve historical magnetic surface encoding, 7-track electrical patterns or rotational timing. This format is our emulator's v1 logical interchange/persistence format, not a physical reconstruction.

## Independent acceptance

```sh
g++ -std=c++17 -O0 -Wall -Wextra -pedantic -Werror -Iinc \
    tests/isa/isa07_d14b3_persistence_probe.cpp -o tempkyiv/d14b3_image.exe
python tools/isa07_d14b3_persistence_sandbox.py \
    --exe tempkyiv/d14b3_image.exe --random-cases 20 --timeout 5
```

The Python oracle independently constructs **exact bytes** (`struct.pack`) and CRC; compares all complete images byte-for-byte; exercises deterministic and randomized profiles; corrupts individual header/bitmap/payload/checksum fields (including some with recomputed CRC); independently verifies signed zero, unwritten bits and strict negative cases. The C++ CRC also must match the external standard vector. Tests execute without `src/main.cpp` or a real `Kyiv_t`. The only accepted evidence for Windows file replacement is actual user MSYS2 execution, not an external Linux sandbox.

**Next:** D14-C will decode opcode 25's directions/track/initial position from documented sources and connect the logical image to real opcodes 23 and 24, with actual 25→23→25→24 CPU traces. No physical/historical claim before the 9864/511 geometry conflict is resolved.
