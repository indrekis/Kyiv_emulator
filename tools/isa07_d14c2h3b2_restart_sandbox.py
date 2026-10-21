#!/usr/bin/env python3
"""D14-C2-H3/B2: cross-process verification of HOST_POLICY KYIVDRM1.
Only external executables, no C++ changes or simulation of CPU execution.
Independent little-endian byte/bitmap/CRC64-ECMA oracle; no imports from B3.
"""
import argparse
import pathlib
import random
import struct
import subprocess
import tempfile

SIGN = 1 << 40
WORD_MASK = (1 << 41) - 1
DRUMS, TRACKS, SLOTS = 3, 2, 8
PER_DRUM = TRACKS * SLOTS
N = DRUMS * PER_DRUM
POLY = 0x42F0E1EBA9EA3693
FULL64 = (1 << 64) - 1


def crc64(data):
    crc = 0
    for byte in data:
        crc ^= byte << 56
        for _ in range(8):
            crc = ((crc << 1) ^ (POLY if crc & (1 << 63) else 0)) & FULL64
    return crc


def canonical(profile, written):
    label = profile.encode('ascii')
    assert 0 < len(label) <= 64 and all(0 <= i < N and 0 <= v <= WORD_MASK
                                        for i, v in written.items())
    bitmap = bytearray((N + 7) // 8)
    cells = [0] * N
    for index, raw in written.items():
        bitmap[index // 8] |= 1 << (index % 8)
        cells[index] = raw
    header = struct.pack('<8sIIQQQQQII', b'KYIVDRM1', 1, 64, DRUMS,
                         TRACKS, SLOTS, N, len(written), len(label), 0)
    assert len(header) == 64
    body = header + label + bitmap + b''.join(struct.pack('<Q', val) for val in cells)
    return body + struct.pack('<Q', crc64(body))


def instruction(op, a1, a2, a3):
    assert 0 < op < 32 and all(0 <= x < 2048 for x in (a1, a2, a3))
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3


def expressions(pin, start, values, reading):
    # Each invocation constructs fresh Kyiv_t registers and memory. The start
    # argument for expression CLI is OCTAL, RAM assignments are DECIMAL.
    assert 1 <= pin <= 3 and 0 <= start <= PER_DRUM - len(values)
    assert len(values) == 3
    selector = pin << 6  # qualified raw a2 0100 / 0200 / 0300
    if reading:
        pairs = [(0o500, instruction(0o25, 0, selector, start)),
                 (0o501, instruction(0o24, 0o210, 0o212, 0o502)),
                 (0o502, instruction(0o14, 0o210, 0, 0o3)),
                 (0o503, instruction(0o14, 0o211, 0, 0o3)),
                 (0o504, instruction(0o14, 0o212, 0, 0o3)),
                 (0o505, instruction(0o33, 0, 0, 0))]
    else:
        pairs = [(0o500, instruction(0o25, 1, selector, start)),
                 (0o501, instruction(0o23, 0o200, 0o202, 0o502)),
                 (0o502, instruction(0o33, 0, 0, 0))]
        pairs += list(zip((0o200, 0o201, 0o202), values))
    return ['expression', *(f'({addr},{value})' for addr, value in pairs), '0500']


def check(condition, why, proc=None):
    if condition:
        return
    evidence = '' if proc is None else (f' RC={proc.returncode} '
       f'STDOUT={proc.stdout[-700:]!r} STDERR={proc.stderr[-700:]!r}')
    raise AssertionError(why + evidence)


def process(binary, cwd, args, timeout):
    return subprocess.run([str(binary), *args], cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          timeout=timeout, check=False)


def assert_clean(image):
    # Compare names, never absolute vs relative Path objects on Windows/MSYS2.
    actual = sorted(item.name for item in image.parent.iterdir())
    check(actual == [image.name], f'TEMP_RESIDUE names={actual!r}')


def create(binary, cwd, image, profile, timeout):
    p = process(binary, cwd, ['create', str(image), profile,
                              str(TRACKS), str(SLOTS)], timeout)
    check(p.returncode == 0 and 'D14C2H3B1-CREATE PASS' in p.stdout,
          'CREATE_FAILED', p)
    check(image.read_bytes() == canonical(profile, {}), 'EMPTY_IMAGE_BYTES', p)
    assert_clean(image)


def attachment_args(image, profile, pin, tracks=TRACKS, slots=SLOTS):
    return ['--experimental-drum', str(image), profile,
            str(tracks), str(slots), str(pin)]


def write_once(binary, cwd, image, profile, pin, start, values, expected, timeout):
    before = image.read_bytes()
    check(before == canonical(profile, expected), 'PREWRITE_ORACLE_MISMATCH')
    cmd = expressions(pin, start, values, False) + attachment_args(image, profile, pin)
    p = process(binary, cwd, cmd, timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'WRITE_PROCESS_FAILED', p)
    result = dict(expected)
    for j, raw in enumerate(values):
        result[(pin - 1) * PER_DRUM + start + j] = raw
    check(image.read_bytes() == canonical(profile, result), 'POSTWRITE_BYTE_MISMATCH', p)
    assert_clean(image)
    return result


def read_fresh(binary, cwd, image, profile, pin, start, values, expected, timeout):
    original = image.read_bytes()
    check(original == canonical(profile, expected), 'PREREAD_BYTE_MISMATCH')
    p = process(binary, cwd,
                expressions(pin, start, values, True) + attachment_args(image, profile, pin),
                timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'READ_PROCESS_FAILED', p)
    # opcode 014 bitwise OR with hardwired RAM[0000]=0 emits a RAW word.
    # Thus signed -0 is observable as 1<<40, unlike word_to_number(+/-0).
    observed = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if line.startswith('orr') and line[3:].isdigit():
            observed.append(int(line[3:]))
    check(observed == list(values),
          f'READBACK_RAW_MISMATCH expected={list(values)!r} actual={observed!r}', p)
    check(image.read_bytes() == original, 'READ_MUTATED_IMAGE', p)
    assert_clean(image)


def self_test():
    check(crc64(b'123456789') == 0x6C40DF5F0B497347, 'CRC_STANDARD_VECTOR')
    p = 'h3b2-self-test'
    empty, positive, negative = (canonical(p, x) for x in
            ({}, {0: 0}, {0: SIGN}))
    check(len(empty) == 64 + len(p) + (N + 7) // 8 + N * 8 + 8,
          'EMPTY_FORMAT_LENGTH')
    check(len({empty, positive, negative}) == 3, 'UNWRITTEN_ZERO_MINUSZERO')
    check(struct.unpack_from('<Q', negative, 48)[0] == 1,
          'WRITTEN_COUNT')
    check(instruction(0o25, 1, 0o100, 3) < 1 << 41, 'INSTRUCTION_BITS')
    # Mutation checks prove CRC and bitmap participate in oracle.
    altered = bytearray(negative)
    altered[-9] ^= 1
    check(struct.unpack_from('<Q', altered, len(altered)-8)[0] != crc64(altered[:-8]),
          'CRC_MUTANT_NOT_REJECTED')
    check(positive != canonical(p, {1: 0}), 'BITMAP_MUTANT_NOT_REJECTED')
    check(expressions(1, 3, (7, 0, SIGN), True)[-1] == '0500', 'START_OCTAL')
    print('D14C2H3B2-SELFTEST PASS CRC_STANDARD=1 SIGNED_ZERO=1 '
          'UNWRITTEN=1 MUTANT_REJECTED=1 RAW_OBSERVATION=1')


def run(creator, emulator, timeout, random_cases):
    passed = 0
    def case(label, fn):
        nonlocal passed
        fn()
        passed += 1
        print(f'D14C2H3B2-CASE {passed:02d} {label}: PASS', flush=True)

    with tempfile.TemporaryDirectory(prefix='d14c2h3b2_') as folder:
        cwd = pathlib.Path(folder)
        directory = cwd / 'a directory with spaces'
        directory.mkdir()
        image = directory / 'restart.kdr'
        profile = 'h3b2-persist'
        expected = {}
        case('create-empty', lambda: create(creator, cwd, image, profile, timeout))

        def duplicate():
            before = image.read_bytes()
            p = process(creator, cwd, ['create', str(image), profile,
                                      str(TRACKS), str(SLOTS)], timeout)
            check(p.returncode != 0 and 'IMAGE_EXISTS' in p.stderr,
                  'DUPLICATE_CREATE_ACCEPTED', p)
            check(image.read_bytes() == before, 'DUPLICATE_MUTATED_IMAGE', p)
            assert_clean(image)
        case('duplicate-create-refused', duplicate)

        def missing():
            path = directory / 'missing.kdr'
            p = process(emulator, cwd,
                expressions(1, 3, (7, 0, SIGN), True) +
                attachment_args(path, profile, 1), timeout)
            check(p.returncode != 0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
                  'MISSING_IMAGE_ACCEPTED', p)
            check(not path.exists(), 'MISSING_IMAGE_CREATED', p)
        case('missing-image-no-auto-create', missing)

        def wrong_geometry():
            before = image.read_bytes()
            p = process(emulator, cwd,
                expressions(1, 3, (7, 0, SIGN), True) +
                attachment_args(image, profile, 1, slots=9), timeout)
            check(p.returncode != 0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
                  'WRONG_GEOMETRY_ACCEPTED', p)
            check(image.read_bytes() == before, 'GEOMETRY_FAILED_ATOMICITY', p)
        case('wrong-geometry-unchanged', wrong_geometry)

        def corrupt_copy():
            bad = directory / 'corrupt.kdr'
            raw = bytearray(image.read_bytes())
            raw[-1] ^= 1
            bad.write_bytes(raw)
            p = process(emulator, cwd,
                expressions(1, 3, (7, 0, SIGN), True) +
                attachment_args(bad, profile, 1), timeout)
            check(p.returncode != 0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
                  'CORRUPT_IMAGE_ACCEPTED', p)
            check(bad.read_bytes() == raw and image.read_bytes() == canonical(profile, {}),
                  'CORRUPT_MUTATION', p)
            bad.unlink()
            assert_clean(image)
        case('corrupt-copy-unchanged', corrupt_copy)

        series = [(1, 3, (7, 0, SIGN)),       # ordinary positions
                  (2, 7, (SIGN, 0, 9)),      # crosses logical track boundary
                  (3, 13, (31, SIGN, 0))]   # reaches last slot of drum
        for pin, start, values in series:
            def do_write(pin=pin, start=start, values=values):
                nonlocal expected
                expected = write_once(emulator, cwd, image, profile, pin, start,
                                      values, expected, timeout)
            case(f'write-process-pin{pin}', do_write)
            case(f'restart-read-pin{pin}',
                 lambda pin=pin,start=start,values=values: read_fresh(
                     emulator, cwd, image, profile, pin, start, values, expected, timeout))
            if pin >= 2:
                case('restart-recheck-pin1-after-pin'+str(pin),
                     lambda: read_fresh(emulator, cwd, image, profile, 1, 3,
                                         (7, 0, SIGN), expected, timeout))
            if pin == 3:
                case('restart-recheck-pin2-after-pin3',
                     lambda: read_fresh(emulator, cwd, image, profile, 2, 7,
                                         (SIGN, 0, 9), expected, timeout))

        rng = random.Random(0xD14C2B2)
        positions = (0, 3, 6, 7, 9, 13)
        for i in range(random_cases):
            random_dir = cwd / f'random_case_{i:03d}'
            random_dir.mkdir()
            rnd_image = random_dir / 'random.kdr'
            rnd_profile = f'h3b2rnd{i:03d}'
            pin = rng.randint(1, 3)
            start = rng.choice(positions)
            values = (rng.choice((0, SIGN, rng.getrandbits(41))),
                      rng.choice((0, SIGN, rng.getrandbits(41))),
                      rng.choice((0, SIGN, rng.getrandbits(41))))
            def random_cycle(image=rnd_image,profile=rnd_profile,pin=pin,start=start,values=values):
                create(creator, cwd, image, profile, timeout)
                written = write_once(emulator, cwd, image, profile, pin, start,
                                     values, {}, timeout)
                read_fresh(emulator, cwd, image, profile, pin, start,
                           values, written, timeout)
            case(f'random-restart-{i:03d}', random_cycle)

    print(f'D14C2H3B2-RESTART PASS CASES={passed}/{passed} '
          f'RANDOM={random_cases}/{random_cases} CREATE_PROCESS=1 WRITE_PROCESS=1 '
          'FRESH_READ_PROCESS=1 BYTE_EXACT_KDR=1 CRC64_ECMA=1 '
          'SIGNED_ZERO=1 UNWRITTEN_DISTINCT=1 PIN_ISOLATION=1 '
          'TRACK_WRAP=1 LAST_SLOT=1 NO_CLOBBER=1 NO_AUTO_CREATE=1 '
          'READ_SIDE_EFFECTS=0 CPU_MUTATION=0 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--create-exe', type=pathlib.Path)
    parser.add_argument('--emu-exe', type=pathlib.Path)
    parser.add_argument('--random-cases', type=int, default=12)
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    if args.random_cases < 0 or args.random_cases > 200 or args.timeout <= 0:
        parser.error('invalid test bounds')
    if args.self_test:
        self_test()
        if not args.create_exe and not args.emu_exe:
            return
    if (not args.create_exe or not args.emu_exe or
        not args.create_exe.is_file() or not args.emu_exe.is_file()):
        parser.error('need existing --create-exe and --emu-exe')
    run(args.create_exe.resolve(), args.emu_exe.resolve(),
        args.timeout, args.random_cases)

if __name__ == '__main__':
    main()
