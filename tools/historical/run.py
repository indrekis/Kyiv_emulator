#!/usr/bin/env python3
"""H114: read-only historical ROM-set validator / sparse FP preparation.

No substitute for H115 native execution. No implicit values for unprinted words.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / 'examples' / 'historical' / 'gy1962' / 'rom_sets'
IMAGE_MODULE1 = ROOT / 'examples' / 'historical' / 'gy1962' / 'rom_modules' / 'module1_3300_3377.k41'
OCT = re.compile(r'^[0-7]+$')
WORD_LIMIT = 1 << 41

class GateError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_k41(raw):
    try:
        lines = raw.decode('utf-8-sig').splitlines()
    except UnicodeDecodeError as exc:
        raise GateError('Image is not valid UTF-8') from exc
    header = [(n, s.strip()) for n, s in enumerate(lines, 1) if s.strip() and not s.lstrip().startswith('#')]
    if not header or header[0][1] != 'KYIV41-OCT1':
        raise GateError('Missing KYIV41-OCT1 header')
    words = {}
    for number, line in header[1:]:
        fields = line.split()
        if len(fields) != 2 or len(fields[0]) != 4 or len(fields[1]) != 14 or not all(OCT.fullmatch(f) for f in fields):
            raise GateError(f'Bad octal 41-bit record at line {number}')
        addr, word = int(fields[0], 8), int(fields[1], 8)
        if addr > 0o3777 or word >= WORD_LIMIT:
            raise GateError(f'Out-of-range address/word at line {number}')
        if addr in words:
            raise GateError(f'Duplicate address {addr:04o} at line {number}')
        words[addr] = f'{word:014o}'
    if not words:
        raise GateError('Empty image')
    return words


def slot_addresses(start, stop):
    return set(range(int(start, 8), int(stop, 8) + 1))


def known_holes():
    return set(range(0o3506, 0o3507 + 1)) | set(range(0o3552, 0o3556 + 1)) | set(range(0o3574, 0o3577 + 1)) | set(range(0o3706, 0o3777 + 1))


def validate_spec(spec, words):
    if spec.get('schema') != 'KYIV_H114_ROMSET_V1':
        raise GateError('Unsupported ROM-set manifest')
    slots = spec['slots']
    allowed = set()
    for pair in slots:
        group = slot_addresses(*pair)
        if not group or min(group) < 0o3300 or max(group) > 0o3777 or allowed.intersection(group):
            raise GateError('Overlapping or invalid ROM slots')
        allowed.update(group)
    if not set(words).issubset(allowed):
        raise GateError('Word outside declared replaceable ROM slots')
    required = set(allowed)
    if spec['id'] == 'fp_simulation':
        required -= known_holes()
        if allowed != slot_addresses('3300', '3777'):
            raise GateError('FP requires five replaceable slots')
    if set(words) != required:
        extra = sorted(set(words) - required)
        missing = sorted(required - set(words))
        raise GateError(f'ROM source mismatch: missing={len(missing)}, extra={len(extra)}; examples missing={[f"{a:04o}" for a in missing[:5]]}')
    if len(words) != spec['expected_printed_records']:
        raise GateError('Unexpected record count')
    return sorted(allowed - set(words))


def prepare(name, image=None, expected_sha=None, output=None):
    if name not in {'module1', 'fp_simulation'}:
        raise GateError('Unknown ROM-set id')
    spec = json.loads((MANIFESTS / (name + '.json')).read_text(encoding='utf-8'))
    src = Path(image) if image else IMAGE_MODULE1 if name == 'module1' else None
    if src is None:
        raise GateError('FP image is absent from tracked repository; use --image with H66 source')
    raw = src.read_bytes()
    sha = digest(raw)
    pinned_sha = expected_sha or spec.get('pinned_source_sha256')
    if pinned_sha is not None:
        if not re.fullmatch(r'[a-f0-9]{64}', pinned_sha) or sha != pinned_sha:
            raise GateError('ROM source SHA-256 mismatch')
    words = parse_k41(raw)
    holes = validate_spec(spec, words)
    if name == 'module1' and image is not None and sha != spec['pinned_source_sha256']:
        raise GateError('Module1 source must match canonical pinned words')
    report = dict(schema='KYIV_H114_PREPARED_V1',rom_set=name,source_path=str(src),source_sha256=sha,
                  source_pin_verified=bool(pinned_sha),records=len(words),known_missing=[f'{a:04o}' for a in holes],
                  classification='SOURCE_TRANSCRIPTION_INPUT' if pinned_sha else 'UNPINNED_EXPERIMENTAL_INPUT',
                  execution='NOT_EXECUTED',physical_hardware='NOT_TESTED',
                  unknown_fill='FORBIDDEN',fixed_rom_changed=False)
    if output:
        dest = Path(output)
        if dest.exists():
            raise GateError('Output already exists; refusing overwrite')
        dest.mkdir(parents=True)
        (dest / 'words.k41').write_bytes(('KYIV41-OCT1\n'+''.join(f'{a:04o} {words[a]}\n' for a in sorted(words))).encode())
        (dest / 'result.json').write_bytes((json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode())
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('list')
    for action in ('validate','prepare'):
        p=sub.add_parser(action)
        p.add_argument('rom_set',choices=['module1','fp_simulation'])
        p.add_argument('--image',help='KYIV41-OCT1 file; REQUIRED for FP')
        p.add_argument('--sha256',help='SHA-256 of the original H66 transcription, when independently established')
        if action=='prepare':p.add_argument('--out',required=True,help='New directory, normally under tempkyiv/')
    args=parser.parse_args(argv)
    if args.action=='list':
        for n in ('module1','fp_simulation'):
            spec=json.loads((MANIFESTS/(n+'.json')).read_text(encoding='utf-8'))
            print(n, 'expected_records='+str(spec['expected_printed_records']))
        return 0
    try:
        result=prepare(args.rom_set,args.image,args.sha256,getattr(args,'out',None))
    except (GateError,OSError,KeyError,ValueError) as exc:
        print('H114_STATUS=HOLD_H114_ROMSET '+str(exc),file=sys.stderr)
        return 2
    print('H114_STATUS=PASS_H114_SOURCE_LAYOUT_NOT_NATIVE')
    print(json.dumps(result,sort_keys=True,ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
