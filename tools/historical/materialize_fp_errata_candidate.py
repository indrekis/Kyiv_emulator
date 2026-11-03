#!/usr/bin/env python3
"""H115-B8: fail-closed materialization of a *derived*, non-historical FP source overlay.

Never modifies the pinned SOURCE_PRINTED file or the repository's active ROM.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
IMAGE = ROOT / 'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'
MANIFEST = ROOT / 'examples/historical/gy1962/rom_sets/fp_simulation_1962_errata_candidate.json'
OCT4 = re.compile(r'[0-7]{4}\Z')
OCT14 = re.compile(r'[0-7]{14}\Z')
PIN = 'ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba'
EXPECTED = {
    '3467': ('15002036070021','15002036050021'),
    '3470': ('15002036070022','15002036060022'),
    '3474': ('10002236110022','01002236110022'),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def checked_source(raw):
    if sha(raw) != PIN:
        raise ValueError('HOLD_SOURCE_SHA256_DRIFT')
    text = raw.decode('ascii')
    lines = text.splitlines()
    if not lines or lines[0] != 'KYIV41-OCT1':
        raise ValueError('HOLD_SOURCE_HEADER')
    result = {}
    for line in lines[1:]:
        parts = line.split(' ')
        if len(parts)!=2 or not OCT4.fullmatch(parts[0]) or not OCT14.fullmatch(parts[1]):
            raise ValueError('HOLD_SOURCE_FORMAT')
        a,w=parts
        if a in result or not 0o3300<=int(a,8)<=0o3777 or int(w,8)>=(1<<41):
            raise ValueError('HOLD_SOURCE_DUPLICATE_OR_RANGE')
        result[a]=w
    if len(result) != 251:
        raise ValueError('HOLD_SOURCE_RECORDS')
    for a,(before,_) in EXPECTED.items():
        if result.get(a) != before:
            raise ValueError('HOLD_SOURCE_ANCHOR_'+a)
    return result

def checked_overlay(text):
    spec=json.loads(text)
    if spec.get('schema')!='KYIV_H115_FP_ERRATA_CANDIDATE_V1' or spec.get('canonical_source_sha256')!=PIN:
        raise ValueError('HOLD_OVERLAY_SCHEMA_OR_PIN')
    rows=spec.get('substitutions')
    if not isinstance(rows,list) or len(rows)!=3:
        raise ValueError('HOLD_OVERLAY_COUNT')
    mapping={}
    for row in rows:
        a=row.get('address')
        if a in mapping or a not in EXPECTED or (row.get('printed'),row.get('candidate'))!=EXPECTED[a]:
            raise ValueError('HOLD_OVERLAY_UNREVIEWED_CHANGE')
        mapping[a]=row['candidate']
    if set(mapping)!=set(EXPECTED):
        raise ValueError('HOLD_OVERLAY_MISSING')
    return mapping

def materialize(source_bytes,overlay_bytes):
    words=checked_source(source_bytes)
    patches=checked_overlay(overlay_bytes.decode('utf-8'))
    derived=dict(words)
    derived.update(patches)
    if len(derived)!=251 or sum(derived[a]!=words[a] for a in words)!=3 or set(derived)!=set(words):
        raise ValueError('HOLD_OVERLAY_LAYOUT')
    data=('KYIV41-OCT1\n'+''.join(f'{a} {derived[a]}\n' for a in sorted(derived,key=lambda x:int(x,8)))).encode('ascii')
    report={
        'schema':'KYIV_H115_FP_DERIVED_CANDIDATE_V1',
        'classification':'SOURCE_DERIVED_CORRECTION_CANDIDATE_NOT_HISTORICALLY_CONFIRMED',
        'source_sha256':sha(source_bytes),
        'derived_sha256':sha(data),
        'records':len(derived),
        'replacements':len(patches),
        'unknowns_filled':0,
        'source_unmodified':True,
        'native_execution':'NOT_PERFORMED_BY_THIS_TOOL',
        'hardware_oracle':'NO',
        'replaced_addresses': sorted(patches)
    }
    return data,report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=IMAGE)
    p.add_argument('--overlay',type=Path,default=MANIFEST)
    p.add_argument('--out',type=Path,help='Must be a NEW private directory (e.g. tempkyiv/h115_b8_candidate_01)')
    args=p.parse_args(argv)
    try:
        image=args.source.read_bytes()
        blob, report=materialize(image,args.overlay.read_bytes())
        if args.out is not None:
            target=args.out.resolve()
            # Repository output is forbidden, private tempkyiv only.
            work=(ROOT/'tempkyiv').resolve()
            if not target.is_relative_to(work) or target==work or target.exists():
                raise ValueError('HOLD_OUTPUT_PATH_NOT_NEW_PRIVATE_DIRECTORY')
            target.mkdir(parents=True)
            (target/'derived_candidate.k41').write_bytes(blob)
            (target/'SOURCE_CLASSIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('H115_B8_OVERLAY=PASS_DERIVED_CANDIDATE_NOT_NATIVE')
        print(json.dumps(report,sort_keys=True))
        return 0
    except (OSError,UnicodeError,ValueError,KeyError) as e:
        print('H115_B8_OVERLAY=HOLD '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
