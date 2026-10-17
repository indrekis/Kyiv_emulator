#!/usr/bin/env python3
"""Validate D8-H5 documentary transfer-pulse selection, not a signed-zero oracle.

Only Table 4 opcode 01 is decoded. Fig71 C16/C17/C18 enables, physical
waveforms and sign-register states remain open by construction.
"""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs'
SIX = (
    ('plus_zero_plus_zero', '+', '+'),
    ('plus_zero_minus_zero', '+', '-'),
    ('minus_zero_plus_zero', '-', '+'),
    ('minus_zero_minus_zero', '-', '-'),
    ('plus_five_minus_five', '+', '-'),
    ('minus_five_plus_five', '-', '+'),
)


def load(name, required):
    with (DOC / name).open(encoding='utf-8', newline='') as f:
        r = csv.DictReader(f, delimiter='\t')
        assert set(required) <= set(r.fieldnames or ()), f'{name}: missing columns'
        rows = list(r)
    assert rows and all(set(row) == set(r.fieldnames) for row in rows)
    assert all(all(v.strip() for v in row.values()) for row in rows), f'{name}: empty field'
    return rows


def uniquely(rows, column):
    v = [row[column] for row in rows]
    assert len(v) == len(set(v)), (column, v)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--show-matrix', action='store_true')
    p.add_argument('--verify-source', type=Path, help='folder containing ORIGINAL kiev0051/0052/0073.png')
    a = p.parse_args()

    ev = load('ISA_06_D8_H5_TRANSFER_EVIDENCE.tsv',
              ('id', 'printed_page', 'locator', 'grade', 'claim', 'qualification'))
    m = load('ISA_06_D8_H5_OPCODE01_TRANSFER_MATRIX.tsv',
             ('case_id','sign1','sign2','I1_selected','I2_selected','minus_Ch1','minus_Ch2','g16','g18','C17','trigger_sign'))
    op = load('ISA_06_D8_H5_OPEN_DELTA.tsv',
              ('parent_id','topic','disposition','new_constraint','still_needed'))
    sources = load('ISA_06_D8_H5_SOURCE_MANIFEST.tsv',
                   ('source_image','sha256','printed_pages','locator'))
    for rows, col in [(ev,'id'), (m,'case_id'), (op,'parent_id'), (sources,'source_image')]:
        uniquely(rows, col)
    assert len(ev) == 20 and len(m) == 6 and len(op) == 12 and len(sources) == 3
    assert {r['grade'] for r in ev} == {'SOURCE_TEXT','SOURCE_TABLE','SOURCE_TEXT_FIGURE','SOURCE_FIGURE','OPEN'}
    assert len([r for r in ev if r['grade']=='OPEN']) == 4
    assert {r['source_image'] for r in sources} == {'kiev0051.png','kiev0052.png','kiev0073.png'}
    assert {r['parent_id'] for r in op} == {f'H4-O{i:02}' for i in range(1,13)}
    assert set(r['disposition'] for r in op) == {'OPEN','NARROWED_NOT_CLOSED'}
    assert all(r['still_needed'] for r in op)

    h4 = load('ISA_06_D8_H4_CORRECTION_GATES.tsv', ('node_id','kind','unresolved'))
    assert {'F71.C16','F71.C17','F71.C18','F71.P_CORR','F71.COUNT_INTERFACE'} == {r['node_id'] for r in h4}
    overrides = load('ISA_06_D8_H2_EDGE_OVERRIDES.tsv', ('h1_edge_id','disposition','h1_from'))
    assert any(r['h1_edge_id']=='E022' and r['disposition']=='RETRACT_AS_DIRECTED_EDGE'
               and r['h1_from']=='F71.Z1' for r in overrides)

    for (case,s1,s2),row in zip(SIX,m):
        assert (row['case_id'],row['sign1'],row['sign2']) == (case,s1,s2)
        assert row['I1_selected'] == ('minus' if s1=='-' else 'plus')
        assert row['I2_selected'] == ('minus' if s2=='-' else 'plus')
        assert int(row['minus_Ch1']) == (s1=='-')
        assert int(row['minus_Ch2']) == (s2=='-')
        assert (row['g16'],row['g18'],row['C17'],row['trigger_sign']) == ('OPEN',)*4
        # Table 4 selects exactly one of the two transfer paths at each I1/I2;
        # it DOES NOT specify whether C16 or C18 is enabled in figure 71.
        assert row['I1_selected'] in ('plus','minus') and row['I2_selected'] in ('plus','minus')

    for row in sources:
        sha = row['sha256']
        assert len(sha) == 64 and all(c in '0123456789abcdef' for c in sha)
        if a.verify_source:
            raw = (a.verify_source / row['source_image']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sha, row['source_image']
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', row['source_image']
            assert (int.from_bytes(raw[16:20], 'big'),int.from_bytes(raw[20:24], 'big')) == (3510,2550)

    print('ISA-06 D8-H5: OPCODE-01 SOURCE TRANSFER DECODE ONLY; downstream C16/C17/C18 enable and signed-zero oracle OPEN')
    print(f'TRANSFER-CHECK PASS evidence={len(ev)} cases={len(m)} open_delta={len(op)} sources={len(sources)} H2_E022=RETRACTED')
    if a.verify_source:
        print('SOURCE-CHECK PASS kiev0051/0052/0073.png SHA256 and original 3510x2550 dimensions')
    if a.show_matrix:
        print('case                            I1_transfer I2_transfer  -Ch1 -Ch2  C16_en C18_en C17  actual_sign')
        for r in m:
            print(f"{r['case_id']:<31} {r['I1_selected']:^11} {r['I2_selected']:^11}  {r['minus_Ch1']:^4} {r['minus_Ch2']:^4}  {r['g16']:^6} {r['g18']:^6} {r['C17']:^4}  {r['trigger_sign']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
