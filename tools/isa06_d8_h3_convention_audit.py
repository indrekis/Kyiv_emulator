#!/usr/bin/env python3
"""ISA-06 D8-H3: check documentary evidence, not simulated Kyiv hardware."""
import argparse
import csv
import re
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'docs'

def records(name, required):
    with (D/name).open(encoding='utf-8', newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        assert set(required) <= set(reader.fieldnames or []), name
        data=list(reader)
        assert data and all(row.values() and all(row.values()) for row in data), name
        return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--show-truth',action='store_true')
    a=ap.parse_args()
    ev=records('ISA_06_D8_H3_CONVENTION_EVIDENCE.tsv',['record_id','printed_page','basis','topic','classification','claim'])
    ov=records('ISA_06_D8_H3_DECISION_OVERLAY.tsv',['decision_id','h1_issue','h2_review','disposition'])
    src=records('ISA_06_D8_H3_SOURCE_MANIFEST.tsv',['file_name','sha256','printed_pages','container'])
    assert len(ev)==20 and len(ov)==6 and len(src)==7
    assert len({r['record_id'] for r in ev})==len(ev)
    assert len({r['decision_id'] for r in ov})==len(ov)
    assert len({r['file_name'] for r in src})==len(src)
    assert all(re.fullmatch(r'[a-f0-9]{64}',r['sha256']) for r in src)
    assert {r['file_name'] for r in src} == {f'kiev{n:04d}.png' for n in [21,22,25,26,27,73,74]}
    h1={r['id'] for r in records('ISA_06_D8_H1_OPEN_ITEMS.tsv',['id'])}
    h2={r['review_id'] for r in records('ISA_06_D8_H2_SECOND_PASS.tsv',['review_id'])}
    assert all(r['h1_issue'] in h1 and r['h2_review'] in h2 for r in ov)
    assert ov[-1]['disposition']=='RETRACTION_PRESERVED'
    h2_override=records('ISA_06_D8_H2_EDGE_OVERRIDES.tsv',['h1_edge_id','disposition'])
    assert any(r['h1_edge_id']=='E022' and r['disposition']=='RETRACT_AS_DIRECTED_EDGE' for r in h2_override)
    lookup={r['topic']:r for r in ev}
    for topic in ['POTENTIAL_C_IS_AND','POTENTIAL_P_IS_OR','COUNT_IF_0','COUNT_IF_1','SIGN_CORRECTION_COUNT_INPUT']:
        assert lookup[topic]['basis']=='DIRECT_TEXT'
    assert lookup['SIGNED_ZERO_ORACLE']['classification']=='OPEN'
    assert lookup['SIGN_TRIGGER_COUNT_EDGE']['classification']=='OPEN'
    # This is the scoped historical Fig. 6 potential truth table.
    for x,y in product((0,1),repeat=2):
        coincidence=int(bool(x and y)); separation=int(bool(x or y))
        assert coincidence==(x & y) and separation==(x|y)
    # This is the Fig. 14 example, NOT a sign-trigger electrical model.
    assert tuple((1-bit,bit) for bit in [0,1])==((1,0),(0,1))
    print('ISA-06 D8-H3: DOCUMENTARY CONVENTIONS ONLY; no historical 01 sign oracle')
    print(f'CONVENTION-CHECK PASS evidence={len(ev)} overlay={len(ov)} sources={len(src)} '
          'H2_E022=RETRACTED signed_zero=OPEN')
    if a.show_truth:
        for x,y in product((0,1),repeat=2):
            print(f'POTENTIAL x={x} y={y} C_AND={x & y} P_OR={x | y}')
        for bit in [0,1]:
            print(f'FIG14_COUNT prior={bit} next={1-bit} carry={bit} (not F71 trigger model)')

if __name__=='__main__':main()
