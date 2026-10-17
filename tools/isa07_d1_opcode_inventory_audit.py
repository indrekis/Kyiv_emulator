#!/usr/bin/env python3
"""Read-only ISA-07 D1 inventory, pinned to pre-stage CPU/header blob versions.

This verifies the actual opcode declarations/dispatch and an explicit list of
C++ IO anomalies. It does NOT prove historical semantics or run any IO devices.
"""
import argparse
import csv
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "docs" / "ISA_07_D1_OPCODE_MATRIX.tsv"
ISSUES = ROOT / "docs" / "ISA_07_D1_OPEN_ISSUES.tsv"
SOURCE = ROOT / "src" / "main.cpp"
HEADER = ROOT / "inc" / "kyiv.h"
BASE = "d57ef2c"
PINNED_BLOBS = {
    "src/main.cpp": "f84acfb22fa3e00f598f3cdb05d4ed2a6618f893",
    "inc/kyiv.h": "ff4aa592f12b07d32b4961b49cb97b15289d38e0",
}
EXPECTED_FAMILIES = {"ZERO": 1, "ARITH": 9, "LOGIC": 4, "CONTROL": 10, "IO": 6, "UNMAPPED": 2}


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def table(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require(reader.fieldnames is not None, f"Missing header: {path}")
        data = list(reader)
    for i, row in enumerate(data, 2):
        require(all(k and v is not None and v.strip() for k, v in row.items()),
                f"Empty field: {path.name}:{i}")
    return data


def git_blob(path):
    result = subprocess.run(["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def io_body(text, code):
    pattern = (r"case\s+IO_operations_t::" + re.escape(code) +
               r"\s*:\s*\{(?P<body>.*?)(?=\n\s*case\s+IO_operations_t::|\n\s*default\s*:)")
    result = re.search(pattern, text, re.DOTALL)
    require(result is not None, f"Cannot delimit handler {code}")
    return result.group("body")


def check(skip_git_pin=False, show_issues=False):
    matrix = table(MATRIX)
    issues = table(ISSUES)
    expected_codes = set(range(0o40))
    opcodes = [int(row["opcode_octal"], 8) for row in matrix]
    require(len(opcodes) == len(set(opcodes)) == 32 and set(opcodes) == expected_codes,
            "Opcode matrix must cover 00..37 once each")
    from collections import Counter
    families = Counter(row["family"] for row in matrix)
    require(dict(families) == EXPECTED_FAMILIES, f"Unexpected family counts: {families}")
    require(sum(row["implementation"] != "NOT_MAPPED" for row in matrix) == 30,
            "Expected 30 mapped codes (including 00)")
    unmapped = {row["opcode_octal"] for row in matrix if row["implementation"] == "NOT_MAPPED"}
    require(unmapped == {"36", "37"}, "36/37 are the only unassigned codes in current C++ enums")

    issue_index = {row["issue_id"]: row for row in issues}
    require(len(issue_index) == len(issues), "Duplicate issue ID")
    for row in matrix:
        for name in row["open_issue_ids"].split(","):
            require(name in issue_index, f"Unknown issue in opcode {row['opcode_octal']}: {name}")

    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    decls = re.findall(r"\b(opcode_[A-Za-z0-9_]+)\s*=\s*0'([0-7]+)\b", header)
    by_code = {}
    for symbol, octal in decls:
        n = int(octal, 8)
        require(n not in by_code, f"Duplicate numeric opcode {octal}")
        by_code[n] = symbol
    require(len(by_code) == 29, f"Expected 29 explicitly declared opcodes, got {len(by_code)}")
    # Every ARITH/CONTROL opcode appears twice: first in execute_opcode()'s
    # dispatch and then in its family-specific handler. LOGIC and IO have
    # one case each. Counting 29 `case`s would incorrectly reject the real CPU.
    dispatch = re.findall(r"\bcase\s+\w+::(opcode_[A-Za-z0-9_]+)\s*:", source)
    counts = Counter(dispatch)
    expected_counts = {
        row["symbol"]: (2 if row["family"] in ("ARITH", "CONTROL") else 1)
        for row in matrix if row["symbol"] != "-"
    }
    require(dict(counts) == expected_counts,
            f"CPU case layout drift (dispatch + family handlers): "
            f"expected={expected_counts} observed={dict(counts)}")
    for row in matrix:
        n = int(row["opcode_octal"], 8)
        symbol = row["symbol"]
        if symbol == "-":
            require(n in (0, 0o36, 0o37), f"Unexpected unmapped opcode {row['opcode_octal']}")
        else:
            require(by_code.get(n) == symbol,
                    f"Opcode {row['opcode_octal']} symbol drift: {by_code.get(n)} != {symbol}")
    require(re.search(r"if\s*\(\s*opcode\s*==\s*0\s*\)", source) is not None,
            "No special-case handling for opcode zero")

    io = {key: io_body(source, key) for key in [
        "opcode_read_perfo_data", "opcode_read_perfo_binary", "opcode_write_perfo_binary",
        "opcode_write_magnetic_drum", "opcode_read_magnetic_drum", "opcode_init_magnetic_drum"]}
    require("break;" not in io["opcode_write_perfo_binary"],
            "IO_FALLTHROUGH was changed; reconcile issue classification before continuing")
    require("C_reg = addr3_shifted.destination" in io["opcode_write_perfo_binary"],
            "IO_WRITE_PERFO control-flow shape changed")
    for op in ("opcode_read_perfo_data", "opcode_read_magnetic_drum"):
        require(re.search(r"\bbool\s+flag\s*;", io[op]) is not None,
                f"IO_UNINIT no longer seen in {op}; update evidence before changing status")
    for op in ("opcode_read_perfo_data", "opcode_read_perfo_binary", "opcode_read_magnetic_drum", "opcode_init_magnetic_drum"):
        require(re.search(r"(?:\+\+\s*C_reg|C_reg\s*\+\+|\bC_reg\s*(?:=|\+=|-=))", io[op]) is None,
                f"IO_PC handler {op} has changed; review and reclassify")
    binary = io["opcode_read_perfo_binary"]
    require(re.search(r"\bint\s+counter\s*=\s*0\s*;", binary) is not None and
            re.search(r"\b(?:counter\+\+|\+\+counter|counter\s*\+=)", binary) is None,
            "IO_COUNTER status has changed; review issue")

    if not skip_git_pin:
        for path, expected in PINNED_BLOBS.items():
            observed = git_blob(path)
            require(observed == expected, f"Source snapshot drift {path}: expected={expected} observed={observed}")
        # Exact Git blob pins above are the source-identity contract for this
        # read-only stage. BASE is a provenance label, not a dependency on
        # local Git history: shallow/single-commit or differently packed
        # checkouts need not retain the historical commit object. Do not
        # weaken or skip the two HEAD:<path> source blob comparisons.
    else:
        print("QA-MODE SKIP_GIT_PIN=1 — not a release qualification")

    from collections import Counter
    status = Counter(row["classification"] for row in issues)
    defect_markers = 3  # fallthrough; uninitialized flag; binary counter
    print("ISA-07 D1: CODE INVENTORY AND OUTSTANDING DIGITAL ISA ISSUES; NOT A HARDWARE ORACLE")
    print(f"INVENTORY-CHECK PASS all_codes=32 mapped=30 explicit_enums=29 reserved_unmapped=2 "
          f"arithmetic=9 logic=4 control=10 io=6 zero=1 issues={len(issues)} "
          f"code_defects={status['CODE_DEFECT']} code_anomalies={status['CODE_ANOMALY']} "
          f"io_static_markers={defect_markers} base={BASE} "
          f"source_pins={'PINNED' if not skip_git_pin else 'SKIPPED_QA'} cpu=UNCHANGED")
    for field, label in (("IO_FALLTHROUGH", "22_falls_through_23"),
                         ("IO_UNINIT", "20_24_uninitialized_flags"),
                         ("IO_COUNTER", "21_nonadvancing_record_counter"),
                         ("IO_PC", "20_21_24_25_no_C_change")):
        require(field in issue_index, f"Missing known issue: {field}")
        print(f"CODE-OBS id={field} marker={label} classification={issue_index[field]['classification']}")
    if show_issues:
        for row in issues:
            print(f"issue={row['issue_id']} priority={row['priority']} class={row['classification']} "
                  f"opcodes={row['opcodes_octal']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Audit the current source without mutation")
    parser.add_argument("--show-issues", action="store_true")
    parser.add_argument("--skip-git-pin", action="store_true", help="QA fixtures only: NOT a release result")
    args = parser.parse_args()
    try:
        check(skip_git_pin=args.skip_git_pin, show_issues=args.show_issues)
    except (AssertionError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print("INVENTORY-CHECK FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
