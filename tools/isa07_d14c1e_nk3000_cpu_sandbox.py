#!/usr/bin/env python3
"""D14-C1e independent exact-integer expected-value oracle.

The program under test executes *real* Kyiv_t CPU steps from src/main.cpp.
Different outcomes are reported as CODE_OBS_MISMATCH, not reclassified as
historical errors. No 23/24/25 execution; no hardware oracle.
"""
import argparse
import random
import subprocess
import sys


def ins(op, a, b, c):
    return (op << 36) | (a << 24) | (b << 12) | c


STEPS = [
    ("copy-write", 0o03, ins(0o01, 0o52, 0, 0o24)),
    ("copy-read", 0o05, ins(0o01, 0o54, 0, 0o26)),
    ("multiply", 0o11, ins(0o10, 0o3000, 0o3040, 0o60)),
    ("select-write", 0o16, ins(0o03, 0o3002, 0o24, 0o24)),
    ("select-read", 0o17, ins(0o03, 0o3002, 0o26, 0o26)),
    ("advance-write", 0o35, ins(0o03, 0o60, 0o24, 0o24)),
    ("advance-read", 0o36, ins(0o03, 0o60, 0o26, 0o26)),
]


def reference(case):
    name, n, drum, start, mode, modifier = case
    selection = (drum << 18) | start
    delta = n << 12
    w0 = ins(0o25, 1, 0, 0)
    r0 = ins(0o25, 0, 0, 0)
    v60 = 0o777
    w24 = 0
    w26 = 0
    states = []
    for phase, pc, command in STEPS:
        if phase == "copy-write":
            w24 = w0
        elif phase == "copy-read":
            w26 = r0
        elif phase == "multiply":
            v60 = delta
        elif phase == "select-write":
            w24 = w0 + selection
        elif phase == "select-read":
            w26 = r0 + selection
        elif phase == "advance-write":
            w24 = w0 + selection + delta
        elif phase == "advance-read":
            w26 = r0 + selection + delta
        states.append({
            "id": name, "phase": phase, "ret": 1, "pc": pc,
            "C": pc + 1, "K": command, "v60": v60,
            "w24": w24, "w26": w26, "A": modifier, "T": 0,
            "error": "NONE",
        })
    return states


def parse_line(line):
    chunks = line.split()
    if not chunks or chunks[0] not in ("D14C1E-BEGIN", "D14C1E-STEP"):
        return None
    fields = {}
    for chunk in chunks[1:]:
        key, sep, value = chunk.partition("=")
        if not sep or key in fields:
            raise ValueError("INVALID_PROBE_RECORD: " + line)
        fields[key] = value
    return chunks[0], fields


def checked(case, beginning, steps):
    name, n, drum, start, mode, modifier = case
    expected_begin = {
        "id": name, "nk0": n << 24,
        "nk2": (drum << 18) | start, "rom3040": 1 << 28,
    }
    errors = []
    if beginning is None:
        return ["MISSING_BEGIN"]
    for key, value in expected_begin.items():
        got = beginning.get(key)
        if got != str(value):
            errors.append(f"BEGIN.{key} expected={value} observed={got}")
    expected_steps = reference(case)
    if len(steps) != len(expected_steps):
        errors.append(f"STEPS expected={len(expected_steps)} observed={len(steps)}")
    for i, (observed, expected) in enumerate(zip(steps, expected_steps)):
        for key, value in expected.items():
            if observed.get(key) != str(value):
                errors.append(
                    f"STEP{i}.{key} expected={value} observed={observed.get(key)}"
                )
    return errors


def cases_for_test(random_cases):
    fixed = []
    # Boundary n values; test two drums, two NK source modes and two starts.
    for n in (0, 1, 63, 64, 137, 256, 500):
        for drum in (1, 2):
            for mode in ("cabinet", "panel"):
                for start in (0, 0o1777):
                    fixed.append((f"fixed-{n}-{drum}-{mode}-{start}", n,
                                  drum, start, mode, 0o17))
    rng = random.Random(0xD14C1E)
    random_list = [
        (f"random-{i}", rng.randrange(501), rng.choice((1, 2)),
         rng.randrange(0o4000), rng.choice(("cabinet", "panel")),
         rng.randrange(0o4000))
        for i in range(random_cases)
    ]
    return fixed + random_list


def self_test():
    sample = ("case", 64, 1, 0o17, "panel", 0o11)
    expected = reference(sample)
    assert len(expected) == 7
    assert expected[2]["v60"] == 64 << 12
    assert expected[4]["w24"] == ins(0o25, 1, 0o100, 0o17)
    assert expected[-1]["w24"] == ins(0o25, 1, 0o200, 0o17)
    assert checked(sample, {"id": "case", "nk0": str(64 << 24),
                            "nk2": str((1 << 18) | 0o17),
                            "rom3040": str(1 << 28)},
                   [{key: str(value) for key, value in d.items()}
                    for d in expected]) == []
    mutant = [{key: str(value) for key, value in d.items()} for d in expected]
    mutant[-1]["w24"] = "0"
    assert checked(sample, {"id": "case", "nk0": str(64 << 24),
                            "nk2": str((1 << 18) | 0o17),
                            "rom3040": str(1 << 28)}, mutant)
    print("D14C1E-SANDBOX-SELFTEST PASS INDEPENDENT_MODEL=1 MUTANT_REJECTED=1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=False)
    parser.add_argument("--random-cases", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.exe or args.random_cases < 0:
        parser.error("--exe required, --random-cases nonnegative")
    cases = cases_for_test(args.random_cases)
    data = "".join(f"{name} {n} {drum} {start} {mode} {mod}\n"
                   for name, n, drum, start, mode, mod in cases)
    proc = subprocess.run([args.exe], input=data, capture_output=True,
                          text=True, timeout=args.timeout, check=False)
    parsed = [v for v in (parse_line(l) for l in proc.stdout.splitlines())
              if v is not None]
    begins = {}
    steps = {}
    for kind, fields in parsed:
        name = fields.get("id", "")
        if kind == "D14C1E-BEGIN":
            if name in begins:
                raise AssertionError("DUPLICATE_BEGIN " + name)
            begins[name] = fields
        else:
            steps.setdefault(name, []).append(fields)
    mismatches = 0
    for case in cases:
        name = case[0]
        errors = checked(case, begins.get(name), steps.get(name, []))
        if errors:
            mismatches += 1
            print(f"D14C1E-CASE {name}: CODE_OBS_MISMATCH " + "; ".join(errors[:5]))
        else:
            print(f"D14C1E-CASE {name}: MATCH STEPS=7")
    unexpected = (set(begins) | set(steps)) - {case[0] for case in cases}
    if unexpected:
        mismatches += len(unexpected)
        print("D14C1E-UNEXPECTED_RECORDS", sorted(unexpected))
    if proc.returncode != 0:
        mismatches += 1
        print(f"D14C1E-PROBE-EXIT code={proc.returncode} stderr={proc.stderr[-1000:]!r}")
    print(f"D14C1E-CPU {'PASS' if mismatches == 0 else 'MISMATCH'} "
          f"CASES={len(cases)} STEPS={len(cases)*7} MISMATCHES={mismatches} "
          "NK_SOURCE_BOTH=1 CPU_REAL=1 ORIGINAL_OPCODES=1 "
          "TRACK_MAPPING=OPEN CPU_MUTATION=0 HARDWARE_ORACLE=0")
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
