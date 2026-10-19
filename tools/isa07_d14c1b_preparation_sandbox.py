#!/usr/bin/env python3
"""Independent reference for the partial opcode-025 decoder."""
import argparse
import random
import subprocess


def encode(op, a1, a2, a3, marks=(0, 0, 0)):
    m1, m2, m3 = marks
    return (
        (op << 36) |
        (m1 << 35) |
        (a1 << 24) |
        (m2 << 23) |
        (a2 << 12) |
        (m3 << 11) |
        a3
    )


def reference(word):
    if word >= (1 << 41):
        return "ERR INVALID_WORD"

    if ((word >> 36) & 0o37) != 0o25:
        return "ERR INVALID_OPCODE"

    a1 = (word >> 24) & 0o3777
    a2 = (word >> 12) & 0o3777
    a3 = word & 0o3777

    if a1 not in (0, 1):
        return "ERR INVALID_DIRECTION"

    drum = (a2 >> 6) & 7

    if drum not in (1, 2, 3):
        return "ERR INVALID_DRUM"

    remaining = a2 & 0o3077
    m1 = (word >> 35) & 1
    m2 = (word >> 23) & 1
    m3 = (word >> 11) & 1

    return (
        f"OK {a1} {drum} {a2} {a3} "
        f"{remaining} {m1} {m2} {m3}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--random-steps", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()

    rng = random.Random(0xD14C1B)
    cases = []

    # Six basic source-derived direction/drum combinations.
    for drum in (1, 2, 3):
        for direction in (0, 1):
            cases.append((
                f"drum-{drum}-dir-{direction}",
                encode(0o25, direction, drum << 6, 0),
                0,
            ))

    # Eight fixed boundary/negative cases.
    cases.extend([
        ("all-marks",
         encode(0o25, 1, 0o0100, 0o0123, (1, 1, 1)), 0o3777),
        ("low-II",
         encode(0o25, 0, 0o0107, 0o3777), 0),
        ("high-II",
         encode(0o25, 1, 0o1100, 0), 0),
        ("bad-direction",
         encode(0o25, 2, 0o0100, 0), 0),
        ("drum-zero",
         encode(0o25, 1, 0, 0), 0),
        ("drum-four",
         encode(0o25, 0, 0o0400, 0), 0),
        ("bad-opcode",
         encode(0o24, 0, 0o0100, 0), 0),
        ("overwide",
         (1 << 41) | encode(0o25, 1, 0o0100, 0), 0),
    ])

    for i in range(args.random_steps):
        drum = rng.randrange(8)
        a2 = (
            (rng.randrange(4) << 9) |
            (drum << 6) |
            rng.randrange(64)
        )
        a1 = rng.randrange(3)
        a3 = rng.randrange(0o4000)
        marks = tuple(rng.randrange(2) for _ in range(3))
        opcode = rng.choice((0o25, 0o25, 0o25, 0o24))

        word = encode(opcode, a1, a2, a3, marks)

        if i % 31 == 0:
            word |= (1 << 41)

        cases.append((f"random-{i}", word, rng.randrange(0o4000)))

    payload = "".join(
        f"{word} {modifier}\n"
        for _, word, modifier in cases
    )

    result = subprocess.run(
        [args.exe],
        input=payload,
        text=True,
        capture_output=True,
        timeout=args.timeout,
        check=True,
    )

    actual = result.stdout.splitlines()

    assert len(actual) == len(cases), (
        f"COUNT {len(actual)} != {len(cases)} "
        f"STDERR={result.stderr!r}"
    )

    for (name, word, _), observed in zip(cases, actual):
        expected = reference(word)
        assert observed == expected, (
            f"{name}: expected={expected!r}, actual={observed!r}"
        )

    print(
        f"D14C1B-PARTIAL PASS={len(cases)}/{len(cases)} "
        "INDEPENDENT_PYTHON=1 RAW_A2_A3=1 "
        "DRUM_DIGIT=6..8 TRACK_MAPPING=OPEN "
        "CPU_MUTATION=0 HARDWARE_ORACLE=0"
    )


if __name__ == "__main__":
    main()
