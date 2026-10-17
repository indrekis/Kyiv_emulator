#!/usr/bin/env python3
"""D8-H2 evidence-layer integrity only, NOT a historical gate simulation.

Run from the repo root:
  python tools/isa06_d8_h2_review_audit.py --check
  python tools/isa06_d8_h2_review_audit.py --check --verify-scans PATH_TO_SCANNED_PNGS
The --verify-scans option requires separately provided full scans; their bytes
are not committed to this repository. The script verifies SHA256 against D8.
"""
import argparse
import collections
import csv
import hashlib
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / 'docs'
IMAGE_PAGES = {
    'kiev0069.png': (136, 137),
    'kiev0073.png': (144, 145),
    'kiev0074.png': (146, 147),
}
IMAGE_DIMS = (3510, 2550)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def records(filename):
    with (DOC / filename).open(encoding='utf-8', newline='') as f:
        rs = list(csv.DictReader(f, delimiter='\t'))
    require(bool(rs), f'empty TSV {filename}')
    for i, r in enumerate(rs, 2):
        require(all(str(v).strip() for v in r.values()), f'empty cell in {filename}:{i}')
    return rs


def rect(value, page, image):
    p = [int(x) for x in value.split(',')]
    require(len(p) == 4, f'bad bbox {value}')
    x1,y1,x2,y2 = p
    require(0 <= x1 < x2 <= IMAGE_DIMS[0] and 0 <= y1 < y2 <= IMAGE_DIMS[1], f'out of image {value}')
    # A whole spread is legitimate ONLY for provenance; otherwise require
    # the x rectangle to fall wholly within the printed page half.
    if page == IMAGE_PAGES[image][0]:
        require(x2 <= IMAGE_DIMS[0]//2, f'left-page bbox crosses gutter: {image} {value}')
    else:
        require(x1 >= IMAGE_DIMS[0]//2, f'right-page bbox crosses gutter: {image} {value}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', required=True)
    ap.add_argument('--verify-scans', type=Path, metavar='DIR')
    ap.add_argument('--emit-filtered-edges', type=Path, metavar='TSV',
                    help='write an H1 evidence table excluding retracted edges; NOT a physical netlist')
    args = ap.parse_args()
    reviews = records('ISA_06_D8_H2_SECOND_PASS.tsv')
    overrides = records('ISA_06_D8_H2_EDGE_OVERRIDES.tsv')
    h1_edges = {e['edge_id']: e for e in records('ISA_06_D8_H1_EDGES.tsv')}
    h1_open = {x['id'] for x in records('ISA_06_D8_H1_OPEN_ITEMS.tsv')}
    manifest = {m['file_name']: m for m in records('ISA_06_D8_SOURCE_MANIFEST.tsv')}
    require(len(h1_edges) == 81, 'unexpected H1 edge baseline')
    require(len(h1_open) == 16, 'unexpected H1 issue baseline')
    require(len(reviews) == 22 and len(overrides) == 1, 'unexpected H2 packet size')
    seen = set()
    tally = collections.Counter()
    for r in reviews:
        rid=r['review_id']
        require(rid not in seen, f'duplicate review ID {rid}')
        seen.add(rid)
        require(r['h1_issue'] in h1_open, f'unknown H1 open item for {rid}')
        img=r['source_image']
        require(img in IMAGE_PAGES and img in manifest, f'unpinned image for {rid}')
        page=int(r['printed_page'])
        require(page in IMAGE_PAGES[img], f'wrong page/image mapping for {rid}')
        if r['basis'] != 'PROVENANCE':
            rect(r['bbox_px'],page,img)
        else:
            require(r['assessment']=='OPEN', 'provenance cannot automatically close independent-review item')
        for name in r['h1_refs'].split(';'):
            if re.fullmatch(r'E\d{3}',name):
                require(name in h1_edges, f'unknown H1 edge {name}')
        require(r['assessment'] in {'LABEL_VISIBLE','CONTRADICTS_H1','CONFIRMS_LIMITED','OPEN'}, f'invalid classification {rid}')
        tally[r['assessment']] += 1
    seen = set()
    for o in overrides:
        ident = o['h1_edge_id']
        require(ident in h1_edges and ident not in seen, f'invalid/duplicate override {ident}')
        seen.add(ident)
        orig=h1_edges[ident]
        require((o['h1_from'], o['h1_to'], o['h1_class']) == (orig['from_node'],orig['to_node'],orig['evidence_class']), f'override fails H1 provenance {ident}')
        require(o['disposition'] == 'RETRACT_AS_DIRECTED_EDGE',f'unsupported disposition {ident}')
        require(o['source_image'] in manifest, f'unpinned source for override {ident}')
        rect(o['bbox_px'], int(o['printed_page']), o['source_image'])
        require(any(r['assessment']=='CONTRADICTS_H1' and ident in r['h1_refs'].split(';') for r in reviews), f'override {ident} without review contradiction')
    require('E022' in seen, 'critical H1 E022 correction not tracked')
    require(tally['CONTRADICTS_H1'] == 1, 'unexpected contradiction count')
    require(len(reviews) == sum(tally.values()), 'classification total mismatch')
    print('ISA-06 D8-H2: SOURCE-BASED SECOND PASS (same researcher, NOT independent sign-off)')
    print('REVIEW-CHECK PASS reviews={} confirmed_limited={} open={} label_visible={} contradicted={} overridden={} H1_edges={}'.format(
        len(reviews),tally['CONFIRMS_LIMITED'],tally['OPEN'],tally['LABEL_VISIBLE'],tally['CONTRADICTS_H1'],len(overrides),len(h1_edges)))
    print('E022 RETRACTED as a confirmed directed edge; signed-zero oracle remains OPEN')
    if args.emit_filtered_edges:
        path=args.emit_filtered_edges
        path.parent.mkdir(parents=True, exist_ok=True)
        original=records('ISA_06_D8_H1_EDGES.tsv')
        with path.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(original[0]),delimiter='\t')
            writer.writeheader()
            writer.writerows(e for e in original if e['edge_id'] not in seen)
        print(f'FILTERED-H1-EVIDENCE edges={len(original)-len(seen)} excluded={len(seen)} (NOT a verified electrical netlist)')
    if args.verify_scans:
        for img in sorted({r['source_image'] for r in reviews}):
            path=args.verify_scans/img
            content=path.read_bytes()
            actual=hashlib.sha256(content).hexdigest()
            expected=manifest[img]['sha256']
            require(actual==expected, f'source hash changed: {img}')
            require(content[:8]==b'\x89PNG\r\n\x1a\n',f'not a PNG {img}')
            dims=struct.unpack('>II',content[16:24])
            require(dims==IMAGE_DIMS,f'bad dimensions {img}: {dims}')
            print(f'SOURCE-OK {img} sha256={actual} size={dims[0]}x{dims[1]}')


if __name__=='__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as e:
        raise SystemExit(f'REVIEW-CHECK FAIL: {e}')
