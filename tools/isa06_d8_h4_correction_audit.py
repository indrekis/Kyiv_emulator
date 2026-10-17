#!/usr/bin/env python3
"""ISA-06 D8-H4 source-table and conditional event-envelope audit.

This is NOT a historical hardware circuit simulator or signed-zero oracle.
"""
import argparse
import csv
import hashlib
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'docs'


def tsv(file, columns):
    with (D / file).open(encoding='utf-8', newline='') as f:
        table = csv.DictReader(f, delimiter='\t')
        if not set(columns).issubset(set(table.fieldnames or [])):
            raise ValueError(f'{file}: missing required columns')
        rows = list(table)
    if not rows or any(not all(row.values()) for row in rows):
        raise ValueError(f'{file}: blank field or missing rows')
    return rows


def unique(rows, key):
    ids = [r[key] for r in rows]
    assert len(ids) == len(set(ids)), f'duplicate {key}'


def events(first_sign, second_sign):
    """All possible *C16/C18 only* contributions, assuming C17=0 and no overlap.

    The gate enable parameters are deliberately UNKNOWN and enumerated (0,1).
    These are model assumptions, not observed hardware events.
    """
    n1, n2 = int(first_sign == '-'), int(second_sign == '-')
    return sorted({(n1 & g16) + (n2 & g18) for g16, g18 in product((0, 1), repeat=2)})


CASES = (
    ('plus_zero_plus_zero', '+', '+', (0,)),
    ('plus_zero_minus_zero', '+', '-', (0, 1)),
    ('minus_zero_plus_zero', '-', '+', (0, 1)),
    ('minus_zero_minus_zero', '-', '-', (0, 1, 2)),
    ('plus_five_minus_five', '+', '-', (0, 1)),
    ('minus_five_plus_five', '-', '+', (0, 1)),
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--show-envelope', action='store_true')
    p.add_argument('--verify-source', type=Path, help='directory containing original kiev0073.png')
    args = p.parse_args()
    g = tsv('ISA_06_D8_H4_CORRECTION_GATES.tsv', ['node_id','figure','printed_page','kind','drawn_input_or_interface','evidence_type','conclusion','unresolved'])
    ev = tsv('ISA_06_D8_H4_EVIDENCE.tsv', ['id','printed_page','figure_or_text','basis','claim','classification','qualification'])
    open_ = tsv('ISA_06_D8_H4_OPEN_ITEMS.tsv', ['id','blocking_topic','why_it_blocks_a_terminal_sign','next_evidence_or_test','priority','status'])
    unique(g, 'node_id'); unique(ev, 'id'); unique(open_, 'id')
    assert len(g)==5 and len(ev)==16 and len(open_)==12
    assert {r['node_id'] for r in g} == {'F71.C16','F71.C17','F71.C18','F71.P_CORR','F71.COUNT_INTERFACE'}
    assert all(r['figure']=='71' for r in g)
    assert all(r['status']=='OPEN' for r in open_)
    assert all(r['basis'] in {'SOURCE_TEXT','SOURCE_FIGURE','OPEN'} for r in ev)
    assert sum(r['classification']=='OPEN' for r in ev)==2
    assert any('−Ч1' in r['drawn_input_or_interface'] or '-Ч1' in r['drawn_input_or_interface'] for r in g if r['node_id']=='F71.C16')
    assert any('−Ч2' in r['drawn_input_or_interface'] or '-Ч2' in r['drawn_input_or_interface'] for r in g if r['node_id']=='F71.C18')
    assert all('historical oracle' not in r['conclusion'].lower() for r in g)

    # Cross-check snapshot statuses: old H1 and H2 are NOT rewritten.
    h1 = tsv('ISA_06_D8_H1_EDGES.tsv',['edge_id','from_node','to_node','evidence_class'])
    overrides = tsv('ISA_06_D8_H2_EDGE_OVERRIDES.tsv',['h1_edge_id','disposition','h1_from','h1_to'])
    assert any(r['edge_id']=='E022' for r in h1), 'Missing H1 snapshot'
    assert any(r['h1_edge_id']=='E022' and r['disposition']=='RETRACT_AS_DIRECTED_EDGE'
               and r['h1_from']=='F71.Z1' for r in overrides), 'H2 E022 retraction lost'
    h3 = tsv('ISA_06_D8_H3_CONVENTION_EVIDENCE.tsv', ['record_id','topic','classification'])
    assert any(r['record_id']=='H3-013' and r['topic']=='SIGN_CORRECTION_COUNT_INPUT' for r in h3)
    sm = tsv('ISA_06_D8_H3_SOURCE_MANIFEST.tsv',['file_name','sha256','printed_pages'])
    src = next(r for r in sm if r['file_name']=='kiev0073.png')
    assert src['sha256']=='60d672ceb4eac0fa6079b13817b05a80224e51d08ff5b9908f0919fb5c794773'
    if args.verify_source:
        data = (args.verify_source/'kiev0073.png').read_bytes()
        assert hashlib.sha256(data).hexdigest()==src['sha256'], 'Source scan changed'
        # Native PNG header and 3510x2550 image size, no image library dependency.
        assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert (int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big'))==(3510,2550)

    for name, first, second, expected in CASES:
        observed = tuple(events(first, second))
        assert observed==expected, (name, observed, expected)
        # Under C17=0 and no overlap, OR/AND truth must agree with enumerated events.
        for g16, g18 in product((0,1), repeat=2):
            e1=(first=='-' and bool(g16));e2=(second=='-' and bool(g18))
            assert (bool(e1) or bool(e2)) == ((int(e1)+int(e2))>0)
    print('ISA-06 D8-H4: CONDITIONAL correction-pulse envelope ONLY; signed-zero oracle OPEN')
    print(f'CORRECTION-CHECK PASS gates={len(g)} evidence={len(ev)} open_items={len(open_)} cases={len(CASES)} H2_E022=RETRACTED')
    if args.verify_source:
        print('SOURCE-CHECK PASS kiev0073.png SHA256 and 3510x2550')
    if args.show_envelope:
        print('case                            sign1 sign2  C16_C18_only_events   actual_trigger_sign')
        for name, first, second, _ in CASES:
            values=events(first,second)
            print(f'{name:<31}  {first:^5} {second:^5}  [{min(values)},{max(values)}] (C17=0, gated)       OPEN')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
