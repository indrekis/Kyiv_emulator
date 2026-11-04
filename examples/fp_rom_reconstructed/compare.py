#!/usr/bin/env python3
"""B21: read-only, fail-closed comparison of printed and reconstructed FP ROM."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = Path('examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41')
DOC = Path('docs/historical/H115_FP_ROM_PRINTED_VS_FUNCTIONAL.md')
EVIDENCE = HERE/'evidence/H115_B20_FP_ROM_INSTALL_EVIDENCE_V1.zip'
EVIDENCE_SHA = '4865d2ba7275e58a35da90525ca53d71c3052ec8b5dc700896db33e49f9885a0'
PASS = 'PASS_H115_B21_PRINTED_VS_FUNCTIONAL_READONLY_NOT_HISTORICAL'

def need(ok: bool, error: str) -> None:
    if not ok:
        raise ValueError(error)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def verified_evidence(blob: bytes) -> dict:
    need(sha(blob)==EVIDENCE_SHA, 'B20_EVIDENCE_SHA_DRIFT')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=z.namelist()
        need(len(names)==len(set(names)), 'EVIDENCE_DUPLICATE_NAMES')
        need(z.testzip() is None, 'EVIDENCE_CRC')
        from pathlib import PurePosixPath
        for name in names:
            p=PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in name and
                 z.getinfo(name).external_attr>>16&0o170000 != 0o120000,
                 'EVIDENCE_UNSAFE_MEMBER')
        need('SHA256SUMS.txt' in names and 'RESULT.json' in names and 'NATIVE_EVIDENCE.zip' in names,
             'EVIDENCE_MISSING_FILES')
        found=set()
        for line in z.read('SHA256SUMS.txt').decode('ascii').splitlines():
            digest,path=line.split('  ',1)
            need(path not in found and path in names and sha(z.read(path))==digest,
                 'EVIDENCE_MANIFEST_DRIFT:'+path)
            found.add(path)
        need(found==set(names)-{'SHA256SUMS.txt'}, 'EVIDENCE_UNMANIFESTED_FILES')
        result=json.loads(z.read('RESULT.json'))
        need(result['status']=='PASS_H115_B20_FUNCTIONAL_FP_ROM_INSTALLED_NATIVE_REPLAY_NOT_HISTORICAL' and
             result['native_cpu_sessions']==52 and result['rk4_checkpoints']==42 and
             result['numeric_regression_cases']==51 and result['exact_native_tsv_replays']==7 and
             result['files_added']==11, 'B20_NOT_ACCEPTED')
        with zipfile.ZipFile(io.BytesIO(z.read('NATIVE_EVIDENCE.zip'))) as nz:
            need(nz.testzip() is None, 'NESTED_NATIVE_CRC')
            native=json.loads(nz.read('RESULT.json'))
            need(native['status']=='PASS_H115_B20_NATIVE_IMAGE_REPLAY_BYTE_IDENTICAL_NOT_HISTORICAL',
                 'NESTED_NATIVE_STATUS')
    return result

def compare(repo: Path) -> dict:
    spec=importlib.util.spec_from_file_location('h115_b20_reader', HERE/'run.py')
    need(spec is not None and spec.loader is not None, 'B20_READER_MISSING')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prov=json.loads((HERE/'PROVENANCE.json').read_bytes())
    patches=json.loads((HERE/'PATCHES.json').read_bytes())
    orig_bytes=(repo/SOURCE).read_bytes()
    functional_bytes=(HERE/'inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41').read_bytes()
    need(sha(orig_bytes)==prov['source_image_sha256'], 'HISTORICAL_SHA_DRIFT')
    need(sha(functional_bytes)==prov['functional_image_sha256'], 'FUNCTIONAL_SHA_DRIFT')
    orig=module.strict_rom(orig_bytes)
    functional=module.strict_rom(functional_bytes)
    need(len(orig)==251 and len(functional)==257,'WORD_COUNTS')
    need(0o3574 not in orig and 0o3574 not in functional,'UNSUPPORTED_3574')
    need(set(orig).issubset(functional),'SOURCE_WORD_REMOVED')
    changes=[]
    seen=set()
    for item in patches['patches']:
        a=int(item['address_octal'],8)
        need(a not in seen and a in functional,'PATCH_DUPLICATE_OR_ABSENT')
        seen.add(a)
        before=orig.get(a)
        expected=item['original_word_octal']
        after=functional[a]
        need((before is None)==(expected is None),'PATCH_ORIGIN_CLASS_DRIFT')
        need(before==(None if expected is None else int(expected,8)),'PATCH_SOURCE_DRIFT')
        need(after==int(item['functional_word_octal'],8) and after!=before,'PATCH_TARGET_DRIFT')
        changes.append({'address_octal':f'{a:04o}',
                        'original_word_octal':None if before is None else f'{before:014o}',
                        'functional_word_octal':f'{after:014o}',
                        'type':'SYNTHETIC_UNPRINTED' if before is None else 'REPLACEMENT',
                        'stage':item['stage']})
    actual={a for a in functional if functional[a]!=orig.get(a)}
    need(seen==actual and len(seen)==12 and
         sum(x['type']=='REPLACEMENT' for x in changes)==6 and
         sum(x['type']=='SYNTHETIC_UNPRINTED' for x in changes)==6,
         'UNREGISTERED_ROM_DIFFERENCE')
    # Reverse the entire patch register to confirm the ORIGINAL bytes, not just the word sets.
    restored=dict(functional)
    for c in changes:
        a=int(c['address_octal'],8)
        if c['original_word_octal'] is None:del restored[a]
        else:restored[a]=int(c['original_word_octal'],8)
    recovered=('KYIV41-OCT1\n'+''.join(f'{a:04o} {restored[a]:014o}\n' for a in sorted(restored))).encode('ascii')
    need(recovered==orig_bytes,'NOT_REVERSIBLE_TO_HISTORICAL_BYTES')
    evidence=verified_evidence(EVIDENCE.read_bytes())
    need((repo/DOC).is_file() and b'3367' in (repo/DOC).read_bytes(), 'HISTORICAL_NOTE_MISSING')
    return {'status':PASS,'source_path':SOURCE.as_posix(),
            'source_sha256':sha(orig_bytes),'original_records':251,
            'functional_sha256':sha(functional_bytes),'functional_records':257,
            'replacements':6,'synthetic_unprinted':6,
            'unknown_3574':'ABSENT_NOT_GUESSED',
            'reverse_patch_exact_source_bytes':True,'native_cpu_sessions_B20':evidence['native_cpu_sessions'],
            'rk4_checkpoints_B20':evidence['rk4_checkpoints'],
            'historical_hardware_identity':'NOT_CLAIMED',
            'changes':sorted(changes,key=lambda x:int(x['address_octal'],8))}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=HERE.parents[1])
    parser.add_argument('--json',action='store_true',help='read-only machine-readable report')
    args=parser.parse_args(argv)
    try:report=compare(args.repo.resolve())
    except Exception as exc:
        print('H115_B21_HOLD:'+str(exc),file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))
    else:
        print('H115_B21_STATUS='+report['status'])
        print('Printed: 251 words / SHA256 '+report['source_sha256'])
        print('Functional: 257 words / SHA256 '+report['functional_sha256'])
        print('6 replacements; 6 synthetic words; original recovered byte-for-byte')
        print('Address  Printed word     Functional word  Attribution')
        for c in report['changes']:
            print(f"{c['address_octal']}     {(c['original_word_octal'] or 'NOT PRINTED'):14}   {c['functional_word_octal']:14}   {c['stage']} {c['type']}")
        print('3574: UNKNOWN / NOT MATERIALIZED.  Historical hardware equivalence: NOT CLAIMED.')
    return 0

if __name__=='__main__':sys.exit(main())
