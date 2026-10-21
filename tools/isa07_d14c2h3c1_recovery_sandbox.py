#!/usr/bin/env python3
"""D14-C2-H3/C1: real-process recovery after a failed replacement.

Test-only C++ fault injection runs in a private marked temporary directory.
The Python byte oracle is independent of B3 and of the H3/B2 oracle.
No production source changes, no crash-durability or multi-writer claims.
"""
import argparse
import pathlib
import struct
import subprocess
import tempfile

SIGN = 1 << 40
MASK = (1 << 41) - 1
DRUMS, TRACKS, SLOTS = 3, 2, 8
N = DRUMS * TRACKS * SLOTS
PROFILE = 'h3c1-recovery'
POLY = 0x42F0E1EBA9EA3693
ALL64 = (1 << 64) - 1
INITIAL = (0, SIGN, 0x111001)
UPDATED = (SIGN, 0, 0x22334)


def check(ok, name, proc=None):
    if not ok:
        details = '' if proc is None else (
            f' rc={proc.returncode} stdout={proc.stdout[-800:]!r}'
            f' stderr={proc.stderr[-800:]!r}')
        raise AssertionError(name + details)


def crc64(blob):
    v = 0
    for byte in blob:
        v ^= byte << 56
        for _ in range(8):
            v = ((v << 1) ^ (POLY if v & (1 << 63) else 0)) & ALL64
    return v


def image_bytes(values=None):
    label = PROFILE.encode('ascii')
    written = {} if values is None else {3 + i: x for i, x in enumerate(values)}
    assert all(0 <= x <= MASK for x in written.values())
    bitmap = bytearray((N + 7) // 8)
    cells = [0] * N
    for i, word in written.items():
        bitmap[i // 8] |= 1 << (i % 8)
        cells[i] = word
    prefix = struct.pack('<8sIIQQQQQII', b'KYIVDRM1', 1, 64,
                         DRUMS, TRACKS, SLOTS, N, len(written), len(label), 0)
    blob = prefix + label + bitmap + b''.join(struct.pack('<Q', c) for c in cells)
    return blob + struct.pack('<Q', crc64(blob))


def cmd(op, a1, a2, a3):
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3


def expressions(values, read):
    p = [(0o500, cmd(0o25, 0 if read else 1, 0o100, 3))]
    if read:
        p += [(0o501, cmd(0o24, 0o210, 0o212, 0o502))]
        p += [(0o502 + i, cmd(0o14, 0o210 + i, 0, 0o3)) for i in range(3)]
        p += [(0o505, cmd(0o33, 0, 0, 0))]
    else:
        p += [(0o501, cmd(0o23, 0o200, 0o202, 0o502)),
              (0o502, cmd(0o33, 0, 0, 0))]
        p += [(0o200 + i, word) for i, word in enumerate(values)]
    return ['expression', *(f'({a},{v})' for a, v in p), '0500']


def invoke(executable, args, cwd, timeout):
    return subprocess.run([str(executable), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout, check=False)


def attachment(path):
    return ['--experimental-drum', path, PROFILE, str(TRACKS), str(SLOTS), '1']


def raw_read(exe, cwd, path, values, timeout):
    p = invoke(exe, expressions(values, True) + attachment(path), cwd, timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'READ_FAILED', p)
    found = [int(line.strip()[3:]) for line in p.stdout.splitlines()
             if line.strip().startswith('orr') and line.strip()[3:].isdigit()]
    check(found == list(values), f'RAW_READ_MISMATCH expected={values} got={found}', p)


def write(exe, cwd, path, values, timeout):
    p = invoke(exe, expressions(values, False) + attachment(path), cwd, timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'WRITE_FAILED', p)


def entries(root):
    return sorted(p.name for p in root.iterdir())


def self_test():
    check(crc64(b'123456789') == 0x6C40DF5F0B497347, 'CRC_STANDARD')
    check(len({image_bytes(), image_bytes(INITIAL), image_bytes(UPDATED)}) == 3,
          'WRITTEN_ZERO_NEGATIVE_ZERO')
    check(struct.unpack_from('<Q', image_bytes(INITIAL), 48)[0] == 3,
          'WRITTEN_COUNT')
    mutant = bytearray(image_bytes(INITIAL))
    mutant[-9] ^= 1
    check(struct.unpack_from('<Q', mutant, len(mutant) - 8)[0] !=
          crc64(mutant[:-8]), 'CRC_MUTANT')
    check(cmd(0o25, 1, 0o100, 3) < (1 << 41), 'COMMAND_WIDTH')
    print('D14C2H3C1-SELFTEST PASS CRC64=1 RAW41=1 SIGNED_ZERO=1 MUTANT_REJECTED=1')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--create-exe', type=pathlib.Path)
    ap.add_argument('--emu-exe', type=pathlib.Path)
    ap.add_argument('--fault-exe', type=pathlib.Path)
    ap.add_argument('--timeout', type=float, default=15)
    a = ap.parse_args()
    if a.self_test:
        self_test()
        if not (a.create_exe or a.emu_exe or a.fault_exe):
            return
    check(0 < a.timeout <= 120, 'INVALID_TIMEOUT')
    check(all(x is not None and x.is_file()
              for x in (a.create_exe, a.emu_exe, a.fault_exe)), 'MISSING_EXECUTABLE')
    creator, emu, fault = (x.resolve() for x in (a.create_exe, a.emu_exe, a.fault_exe))
    fault_self = invoke(fault, ['--self-test'], pathlib.Path.cwd(), a.timeout)
    check(fault_self.returncode == 0 and 'D14C2H3C1-PROBE-SELFTEST PASS'
          in fault_self.stdout, 'PROBE_SELFTEST', fault_self)
    count = 0

    def case(name, fn):
        nonlocal count
        fn()
        count += 1
        print(f'D14C2H3C1-CASE {count:02d} {name}: PASS', flush=True)

    with tempfile.TemporaryDirectory(prefix='d14c2h3c1_') as tmp:
        cwd = pathlib.Path(tmp)
        folder = cwd / 'private folder with spaces'
        folder.mkdir()
        target = folder / 'recovery.kdr'
        marker = folder / '.h3c1-isolated-sandbox'
        marker.write_bytes(b'H3C1-PRIVATE-TEST-ONLY\n')

        def create():
            p = invoke(creator, ['create', target, PROFILE, TRACKS, SLOTS], cwd, a.timeout)
            check(p.returncode == 0 and 'D14C2H3B1-CREATE PASS' in p.stdout,
                  'CREATE_FAILED', p)
            check(target.read_bytes() == image_bytes(), 'CREATED_NONCANONICAL', p)
            check(entries(folder) == [marker.name, target.name], 'CREATE_RESIDUE')
        case('create-real-process', create)

        def initial_write():
            write(emu, cwd, target, INITIAL, a.timeout)
            check(target.read_bytes() == image_bytes(INITIAL), 'INITIAL_BYTES_MISMATCH')
        case('persist-initial-raw-words', initial_write)

        def failed_replace():
            original = target.read_bytes()
            p = invoke(fault, [target], cwd, a.timeout)
            check(p.returncode == 0 and
                  'D14C2H3C1-FAULT PASS REPLACE_FAILED=1' in p.stdout,
                  'FAULT_PROBE_FAILED', p)
            check(target.read_bytes() == original, 'REPLACEMENT_MUTATED_IMAGE')
            check(entries(folder) == [marker.name, target.name], 'FAILURE_TEMP_RESIDUE')
        case('forced-replace-failure-rollback', failed_replace)

        def restart_read():
            raw_read(emu, cwd, target, INITIAL, a.timeout)
            check(target.read_bytes() == image_bytes(INITIAL), 'RESTART_READ_SIDE_EFFECT')
        case('fresh-process-reopens-prior-commit', restart_read)

        def resume_write():
            write(emu, cwd, target, UPDATED, a.timeout)
            check(target.read_bytes() == image_bytes(UPDATED), 'RESUMED_WRITE_NONCANONICAL')
        case('subsequent-successful-write', resume_write)

        def resumed_read():
            raw_read(emu, cwd, target, UPDATED, a.timeout)
            check(target.read_bytes() == image_bytes(UPDATED), 'UPDATED_READ_SIDE_EFFECT')
        case('fresh-process-reopens-recovered-state', resumed_read)

        # Non-authoritative sidecars from an interrupted process must not be
        # mistaken for the canonical target or deleted without operator action.
        orphan_a = folder / (target.name + '.tmp.orphan')
        orphan_b = folder / (target.name + '.provision.orphan')
        orphan_a.write_bytes(image_bytes(INITIAL))
        orphan_b.write_bytes(b'incomplete-untrusted-sidecar')

        def orphan_ignored():
            raw_read(emu, cwd, target, UPDATED, a.timeout)
            check(target.read_bytes() == image_bytes(UPDATED), 'ORPHAN_CHANGED_CANONICAL')
            check(orphan_a.read_bytes() == image_bytes(INITIAL) and
                  orphan_b.read_bytes() == b'incomplete-untrusted-sidecar',
                  'ORPHAN_AUTO_RECOVERY_OR_GC')
        case('no-implicit-orphan-recovery-or-gc', orphan_ignored)

        def corrupt_target():
            original = target.read_bytes()
            bad = bytearray(original)
            bad[-9] ^= 1
            target.write_bytes(bad)
            p = invoke(emu, expressions(UPDATED, True) + attachment(target), cwd, a.timeout)
            check(p.returncode != 0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
                  'CORRUPT_TARGET_ACCEPTED', p)
            check(target.read_bytes() == bytes(bad), 'CORRUPT_TARGET_REWRITTEN')
            check(orphan_a.read_bytes() == image_bytes(INITIAL) and
                  orphan_b.read_bytes() == b'incomplete-untrusted-sidecar',
                  'CORRUPT_TARGET_AUTO_RESTORED')
            target.write_bytes(original)  # explicit fixture restoration, never production
            raw_read(emu, cwd, target, UPDATED, a.timeout)
            check(target.read_bytes() == original, 'REPAIRED_READ_SIDE_EFFECT')
        case('corrupt-target-fails-closed-no-sidecar-promotion', corrupt_target)

        check(entries(folder) == sorted([marker.name, target.name,
                                         orphan_a.name, orphan_b.name]),
              'UNEXPECTED_TEMP_FILES')
    print(f'D14C2H3C1-RECOVERY PASS CASES={count}/{count} '
          'REAL_PROCESSES=1 FAULT_REPLACE=1 SESSION_ROLLBACK=1 '
          'FRESH_REOPEN=1 CONTINUE_AFTER_FAILURE=1 BYTE_EXACT_KDR=1 '
          'CRC64_ECMA=1 ORPHAN_NOT_PROMOTED=1 NO_AUTO_REPAIR=1 '
          'CRASH_DURABILITY=OPEN CONCURRENT_WRITERS=OPEN '
          'HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


if __name__ == '__main__':
    main()
