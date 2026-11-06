#!/usr/bin/env python3
"""H116-C1a: extensible read-only catalog for Kyiv interchangeable ROM modules.

A new module needs a .k41 and a JSON manifest, and a set JSON selects modules.
No emulator/CPU/ROM writes; prepare creates a NEW output directory only.
This is a HOST loader/validator, not an authentic physical-ROM claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

SCHEMA_MODULE = 'KYIV_H116_ROM_MODULE_V1'
SCHEMA_SET = 'KYIV_H116_ROM_SET_V1'
SCHEMA_REPORT = 'KYIV_H116_ROM_CATALOG_REPORT_V1'
FIXED_ROM_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
ID = re.compile(r'[a-z][a-z0-9_]{1,47}\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')
OCT4 = re.compile(r'[0-7]{4}\Z')
OCT14 = re.compile(r'[0-7]{14}\Z')
SLOT_FIRST = 0o3300
SLOT_LAST = 0o3777
SLOT_SIZE = 0o100

class CatalogError(ValueError):
    pass

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def fail(reason):
    raise CatalogError(reason)

def octal4(s):
    if not isinstance(s,str) or not OCT4.fullmatch(s): fail('INVALID_OCTAL_ADDRESS')
    return int(s,8)

def obj_unique_pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d: fail('DUPLICATE_JSON_KEY')
        d[k]=v
    return d

def read_json(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>65536:
        fail('MANIFEST_MISSING_OR_TOO_LARGE')
    try: return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=obj_unique_pairs)
    except (ValueError,UnicodeDecodeError) as e: fail('INVALID_JSON: '+str(e))

def resolve_beneath(root: Path, rel: str, prefix: str):
    if not isinstance(rel,str) or '\\' in rel or rel.startswith('/'):
        fail('UNSAFE_PATH')
    p = PurePosixPath(rel)
    if any(x in ('','.', '..') for x in p.parts) or not p.parts or p.parts[0]!=prefix:
        fail('UNSAFE_PATH')
    path=root.joinpath(*p.parts)
    # Symlink-free paths avoid aliasing and escaping the checkout, including on MSYS2.
    at=root
    for part in p.parts:
        at=at/part
        if at.is_symlink(): fail('SYMLINK_NOT_ALLOWED')
    if not path.is_file(): fail('IMAGE_MISSING')
    if not path.resolve().is_relative_to(root.resolve()): fail('UNSAFE_PATH')
    return path

def parse_k41(path: Path, sha: str):
    raw=path.read_bytes()
    if not HEX.fullmatch(sha): fail('INVALID_IMAGE_SHA')
    if sha256(raw)!=sha: fail('IMAGE_SHA256_MISMATCH')
    if len(raw)>32768: fail('IMAGE_TOO_LARGE')
    try: lines=raw.decode('ascii').splitlines()
    except UnicodeDecodeError: fail('NON_ASCII_IMAGE')
    if not lines or lines[0]!='KYIV41-OCT1': fail('INVALID_K41_HEADER')
    words={}
    for line in lines[1:]:
        fields=line.split()
        if len(fields)!=2 or not OCT4.fullmatch(fields[0]) or not OCT14.fullmatch(fields[1]):
            fail('INVALID_K41_RECORD')
        addr=int(fields[0],8); word=int(fields[1],8)
        if word >= (1<<41): fail('OVERWIDE_WORD')
        if addr in words: fail('DUPLICATE_WORD_ADDRESS')
        words[addr]=fields[1]
    if not words: fail('EMPTY_K41')
    return words

def slots_from_manifest(raw):
    if not isinstance(raw,list) or not raw or len(raw)>5: fail('INVALID_SLOT_LIST')
    allowed=set(); slots=[]
    for item in raw:
        if not isinstance(item,list) or len(item)!=2: fail('INVALID_SLOT')
        first, last=map(octal4,item)
        if first < SLOT_FIRST or last>SLOT_LAST or (first-SLOT_FIRST)%SLOT_SIZE or last!=first+SLOT_SIZE-1:
            fail('UNALIGNED_ROM_SLOT')
        group=set(range(first,last+1))
        if allowed & group:fail('DUPLICATE_SLOT')
        allowed|=group
        slots.append([f'{first:04o}',f'{last:04o}'])
    return allowed,slots

def id_ok(s):
    return isinstance(s,str) and bool(ID.fullmatch(s))

def require_keys(obj, keys):
    if not isinstance(obj,dict) or set(obj)!=set(keys):fail('BAD_MANIFEST_FIELDS')

def read_module(root: Path, catalog: Path, module_id: str):
    if not id_ok(module_id): fail('INVALID_MODULE_ID')
    spec=read_json(catalog/'modules'/(module_id+'.json'))
    require_keys(spec, ['schema','id','description','image','sha256','slots','records','provenance','critical_unknown'])
    if spec['schema']!=SCHEMA_MODULE or spec['id']!=module_id:fail('MODULE_SCHEMA_OR_ID_MISMATCH')
    if not isinstance(spec['description'],str) or not spec['description'].strip(): fail('MISSING_DESCRIPTION')
    if spec['provenance'] not in ('SOURCE_TRANSCRIPTION','FUNCTIONAL_RECONSTRUCTION','RECONSTRUCTED_ASSUMPTION','SYNTHETIC_TEST'):fail('INVALID_PROVENANCE')
    allowed,slots=slots_from_manifest(spec['slots'])
    path=resolve_beneath(root,spec['image'],'examples')
    if not path.name.endswith('.k41'):fail('INVALID_IMAGE_EXTENSION')
    words=parse_k41(path,spec['sha256'])
    if not isinstance(spec['records'],int) or isinstance(spec['records'],bool) or len(words)!=spec['records']:fail('MODULE_RECORD_COUNT')
    if not set(words)<=allowed:fail('MODULE_OUT_OF_SLOTS')
    missing=allowed-set(words)
    if not isinstance(spec['critical_unknown'],list) or len(set(map(str,spec['critical_unknown'])))!=len(spec['critical_unknown']):fail('INVALID_CRITICAL_UNKNOWN')
    for s in spec['critical_unknown']:
        if octal4(s) not in missing:fail('CRITICAL_UNKNOWN_MATERIALIZED')
    return {'spec':spec,'words':words,'missing':missing,'slots':slots,'path':path}

def validate_set(repo: Path, set_id: str, catalog=None):
    root=Path(repo).resolve()
    if not id_ok(set_id):fail('INVALID_SET_ID')
    catalog=Path(catalog).resolve() if catalog else root/'examples'/'rom_catalog'
    if not catalog.is_dir():fail('CATALOG_MISSING')
    spec=read_json(catalog/'sets'/(set_id+'.json'))
    require_keys(spec,['schema','id','description','modules','fixed_rom_sha256'])
    if spec['schema']!=SCHEMA_SET or spec['id']!=set_id:fail('SET_SCHEMA_OR_ID_MISMATCH')
    if not isinstance(spec['description'],str) or not spec['description'].strip():fail('MISSING_DESCRIPTION')
    mods=spec['modules']
    if not isinstance(mods,list) or not mods or len(mods)>5 or any(not id_ok(m) for m in mods) or len(mods)!=len(set(mods)):
        fail('INVALID_MODULE_SELECTION')
    if spec['fixed_rom_sha256']!=FIXED_ROM_SHA:fail('FIXED_ROM_PIN_MISMATCH')
    fixed=root/'mem'/'ROM.txt'
    if fixed.is_symlink() or not fixed.is_file() or sha256(fixed.read_bytes())!=FIXED_ROM_SHA:
        fail('FIXED_ROM_SOURCE_SHA_MISMATCH')
    allwords={}; allslots=set(); report_modules=[]; missing=set()
    for mid in mods:
        mod=read_module(root,catalog,mid)
        slots,_=slots_from_manifest(mod['spec']['slots'])
        if allslots & slots:fail('ROM_SLOT_COLLISION')
        allslots |= slots
        if set(allwords)&set(mod['words']):fail('ROM_ADDRESS_COLLISION')
        allwords.update(mod['words']);missing |= mod['missing']
        report_modules.append({'id':mid,'image':mod['spec']['image'], 'sha256':mod['spec']['sha256'],
            'provenance':mod['spec']['provenance'],'records':len(mod['words']),'slots':mod['slots'],
            'unknown_words':len(mod['missing']),'critical_unknown':mod['spec']['critical_unknown']})
    result={'schema':SCHEMA_REPORT,'status':'PASS_H116_C1A_SOURCE_LAYOUT_ONLY_NOT_NATIVE',
      'set':set_id,'modules':report_modules, 'words':len(allwords),
      'occupied_slots':len(allslots)//SLOT_SIZE,'unknown_slots_words':len(missing),
      'missing_addresses':[f'{a:04o}' for a in sorted(missing)],
      'fixed_rom_sha256':FIXED_ROM_SHA,'historical_hardware':'NOT_VERIFIED',
      'implicit_fill':False,'native_executed':False}
    return result,allwords

def all_ids(catalog):
    for sub in ('modules','sets'):
        names=[]
        for p in sorted((catalog/sub).glob('*.json')):
            if p.is_symlink() or not id_ok(p.stem):fail('INVALID_CATALOG_FILE')
            names.append(p.stem)
        yield sub,names

def prepare(repo:Path,set_id:str,dest:Path,catalog=None):
    rep,words=validate_set(repo,set_id,catalog)
    dest=Path(dest)
    if dest.exists() or dest.with_suffix('.zip').exists():fail('OUT_ALREADY_EXISTS')
    if dest.is_symlink():fail('UNSAFE_OUTPUT')
    # No change to repository images; destination is a NEW folder under tempkyiv.
    repo=Path(repo).resolve(); safe_root=repo/'tempkyiv'
    if not dest.resolve().is_relative_to(safe_root):fail('OUT_OUTSIDE_TEMPKYIV')
    dest.mkdir(parents=True,exist_ok=False)
    body=('KYIV41-OCT1\n'+''.join(f'{a:04o} {words[a]}\n' for a in sorted(words))).encode('ascii')
    (dest/'replaceable.k41').write_bytes(body)
    (dest/'RESULT.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    sums=''.join(f'{sha256((dest/f).read_bytes())}  {f}\n' for f in ['RESULT.json','replaceable.k41'])
    (dest/'SHA256SUMS.txt').write_text(sums,encoding='ascii')
    return rep

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    v=sub.add_parser('validate'); v.add_argument('set_id')
    p=sub.add_parser('prepare');p.add_argument('set_id');p.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.command=='list':
            catalog=args.repo/'examples'/'rom_catalog'
            print(json.dumps({k:v for k,v in all_ids(catalog)},sort_keys=True))
        elif args.command=='validate':
            result,_=validate_set(args.repo,args.set_id)
            print(json.dumps(result,sort_keys=True,ensure_ascii=False))
        elif args.command=='prepare':
            print(json.dumps(prepare(args.repo,args.set_id,args.out),sort_keys=True,ensure_ascii=False))
    except (CatalogError,OSError,TypeError,KeyError,UnicodeError) as exc:
        print('H116_C1A_HOLD '+str(exc),file=sys.stderr);return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
