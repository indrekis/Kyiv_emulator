#!/usr/bin/env python3
"""ISA-06 D8: deterministic HYPOTHESIS comparator, NOT a Kyiv gate-level emulator.

Read docs/ISA_06_D8_ADDER_SIGN_RECONSTRUCTION.md before interpreting outputs.
No historical oracle is generated here; checks verify our toy model definitions only.
Usage from repository root:
    python tools/isa06_d8_sign_models.py --check
    python tools/isa06_d8_sign_models.py --json > tempkyiv/isa06_d8_models.json
"""

import argparse
import json
from dataclasses import dataclass
from typing import Callable, Dict, List

SIGN = 1 << 40
MAG = SIGN - 1
MASK41 = (1 << 41) - 1


@dataclass(frozen=True)
class Case:
    name: str
    a: int  # external 41-bit sign/magnitude word
    b: int


CASES = [
    Case("plus_zero_plus_zero", 0, 0),
    Case("plus_zero_minus_zero", 0, SIGN),
    Case("minus_zero_plus_zero", SIGN, 0),
    Case("minus_zero_minus_zero", SIGN, SIGN),
    Case("plus_five_minus_five", 5, SIGN | 5),
    Case("minus_five_plus_five", SIGN | 5, 5),
]


def external_decode(w: int) -> int:
    """Mathematical integer used by M0, loses distinction between signed zeros."""
    assert 0 <= w <= MASK41
    magnitude = w & MAG
    return -magnitude if w & SIGN else magnitude


def encode_external(magnitude: int, is_negative: bool) -> int:
    assert 0 <= magnitude <= MAG
    return magnitude | (SIGN if is_negative else 0)


def m0_host_integer(a: int, b: int) -> int:
    """Model M0: current opcode-01 sign selection for a representable sum."""
    res = external_decode(a) + external_decode(b)
    if abs(res) > MAG:
        raise ValueError("test case outside non-overflow model")
    return encode_external(abs(res), res < 0)


def into_ones_complement(a: int) -> int:
    """TOY: convert external sign/magnitude into 41-bit one's-complement code."""
    mag = a & MAG
    return (MASK41 ^ mag) if a & SIGN else mag


def out_of_ones_complement(code: int) -> int:
    """TOY inverse; all-ones is -0 and all-zeros is +0 by construction."""
    code &= MASK41
    return encode_external((~code) & MAG, True) if code & SIGN else code & MAG


def m1_ones_complement_toy(a: int, b: int) -> int:
    """Model M1: end-around carry over 41 bits (NOT the Kyiv sign circuit)."""
    total = into_ones_complement(a) + into_ones_complement(b)
    while total > MASK41:
        total = (total & MASK41) + (total >> 41)
    return out_of_ones_complement(total)


def m2_first_operand_sign_on_zero(a: int, b: int) -> int:
    """Model M2a: illustrative order-dependent rule, unsupported by sources."""
    res = external_decode(a) + external_decode(b)
    if abs(res) > MAG:
        raise ValueError("test case outside non-overflow model")
    return encode_external(abs(res), bool(a & SIGN) if res == 0 else res < 0)


def m2_second_operand_sign_on_zero(a: int, b: int) -> int:
    """Model M2b: illustrative alternate order rule, unsupported by sources."""
    res = external_decode(a) + external_decode(b)
    if abs(res) > MAG:
        raise ValueError("test case outside non-overflow model")
    return encode_external(abs(res), bool(b & SIGN) if res == 0 else res < 0)


MODELS: Dict[str, Callable[[int, int], int]] = {
    "M0_host_integer_policy": m0_host_integer,
    "M1_ones_complement_toy": m1_ones_complement_toy,
    "M2a_first_sign_on_zero": m2_first_operand_sign_on_zero,
    "M2b_second_sign_on_zero": m2_second_operand_sign_on_zero,
}


def oct41(w: int) -> str:
    return f"{w:014o}"  # 41-bit external code fits in 14 octal digits


def signed_zero_label(w: int) -> str:
    if (w & MAG) == 0:
        return "-0" if w & SIGN else "+0"
    return f"{'-' if w & SIGN else '+'}{w & MAG:o}"


def rows() -> List[dict]:
    result = []
    for case in CASES:
        row = {"case": case.name, "a_octal": oct41(case.a),
               "b_octal": oct41(case.b), "historical_01_verdict": "OPEN"}
        for name, impl in MODELS.items():
            val = impl(case.a, case.b)
            row[name] = {"external_octal": oct41(val),
                         "display": signed_zero_label(val)}
        result.append(row)
    return result


def self_check() -> None:
    # Tests verify model definitions only. They are NOT assertions about Kyiv.
    assert len(CASES) == 6
    for case in CASES:
        assert external_decode(case.a) + external_decode(case.b) == 0
        assert m0_host_integer(case.a, case.b) == 0
        assert m1_ones_complement_toy(case.a, case.b) in (0, SIGN)
        assert m2_first_operand_sign_on_zero(case.a, case.b) == (case.a & SIGN)
        assert m2_second_operand_sign_on_zero(case.a, case.b) == (case.b & SIGN)
    assert m1_ones_complement_toy(0, 0) == 0
    assert all(m1_ones_complement_toy(c.a, c.b) == SIGN for c in CASES[1:])
    # Known controls in toy M1, no overflow in these examples.
    for a, b, expected in [(2, 3, 5), (SIGN | 5, 2, SIGN | 3),
                           (SIGN | 3, SIGN | 2, SIGN | 5)]:
        assert m0_host_integer(a, b) == expected
        assert m1_ones_complement_toy(a, b) == expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check toy-model invariants; NOT historical tests")
    parser.add_argument("--json", action="store_true", help="Emit rows as deterministic JSON")
    args = parser.parse_args()
    if args.check:
        self_check()
    result = rows()
    if args.json:
        print(json.dumps({"classification": "HYPOTHESIS_ONLY", "base": "41a452b",
                          "models": list(MODELS), "rows": result},
                         ensure_ascii=False, indent=2))
        return 0
    print("ISA-06 D8: MODELS ONLY (no historical 01 sign oracle)")
    print(f"{'case':29} {'M0':>4} {'M1':>4} {'M2a':>4} {'M2b':>4}  verdict")
    for item in result:
        m = [item[key]["display"] for key in MODELS]
        print(f"{item['case']:29} {m[0]:>4} {m[1]:>4} {m[2]:>4} {m[3]:>4}  OPEN")
    print("MODEL-CHECK PASS (toy invariants only)" if args.check else
          "MODEL-CHECK NOT REQUESTED (--check); no historical assertion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
