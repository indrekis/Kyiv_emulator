#!/usr/bin/env python3
"""ISA-06 D8-H1: static audit of a *partial source transcription*.

This is NOT a gate simulation or a proof of historical signed-zero semantics.
Requires Python 3 standard library only, run from any working directory.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / 'docs'

def tsv(file, fields):
    with (DOC / file).open('r', encoding='utf-8', newline='') as f:
        r=csv.DictReader(f, delimiter='\t')
        assert r.fieldnames == fields, (file, r.fieldnames)
        rows=list(r)
    assert all(all(row[k].strip() for k in fields) for row in rows), file
    return rows

def check():
    nodes=tsv('ISA_06_D8_H1_NODES.tsv',
              ['node_id','source_figure','printed_page','kind','visible_label_or_alias','reading_status','note'])
    edges=tsv('ISA_06_D8_H1_EDGES.tsv',
              ['edge_id','from_node','to_node','evidence_class','source_locator','observation_or_limitation'])
    todo=tsv('ISA_06_D8_H1_OPEN_ITEMS.tsv',
             ['id','figure','source','target','action_or_unknown','state'])
    ids={n['node_id'] for n in nodes}
    assert len(ids)==len(nodes), 'duplicate node IDs'
    assert len(set(e['edge_id'] for e in edges))==len(edges), 'duplicate edge IDs'
    assert len(set(e['id'] for e in todo))==len(todo), 'duplicate open-item IDs'
    figpages={'F67':'137','F71':'144','F72':'145','F73':'146'}
    for n in nodes:
        prefix=n['node_id'].split('.')[0]
        assert n['source_figure']== 'Fig '+prefix[1:]
        assert n['printed_page']==figpages[prefix]
        if n['kind']=='P_GLYPH_GROUP':
            assert n['reading_status']=='FUNCTIONAL_ALIAS'
    missing=[(e['edge_id'],p,e[p]) for e in edges for p in ['from_node','to_node'] if e[p] not in ids]
    assert not missing, ('missing endpoints',missing)
    assert all(e['evidence_class'] in {'PHOTO_CLEAR','TEXT_CONFIRMED','DIAGRAM_GROUP'} for e in edges)
    assert not any('STRICT-PASS' in e['observation_or_limitation'] or
                   'historical oracle' in e['observation_or_limitation'].lower() for e in edges)
    for f,ct in [(67,16),(71,18),(72,23),(73,12)]:
        assert all(f'F{f}.C{x:02}' in ids for x in range(1,ct+1)), f
    assert all(x in ids for x in ('F71.TZ1','F71.TZ2','F71.TZ1SM','F71.TZ2SM'))
    assert len(todo)>=12
    count=Counter(e['evidence_class'] for e in edges)
    print('ISA-06 D8-H1: PARTIAL transcription; no historical zero-sign oracle')
    print(f'STRUCTURE-CHECK PASS nodes={len(nodes)} edges={len(edges)} '
          f'open_items={len(todo)} diagram_groups={count["DIAGRAM_GROUP"]} '
          f'text_confirmed={count["TEXT_CONFIRMED"]} '
          f'photo_clear={count["PHOTO_CLEAR"]}')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--check', action='store_true', help='validate TSV structure (no hardware simulation)')
    args=p.parse_args()
    check()
