#!/usr/bin/env python3
"""H115-A: deterministic, pinned H66 TSV -> sparse 41-bit KYIV41-OCT1 (SOURCE ONLY).

No CPU calls; no historical simulation or implied filling of unprinted ROM words.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile
from collections import Counter

H66_SOURCE_ARCHIVE_SHA = '5298a4c0ab93fc901bd01d4d3c5a1944db0808ffea642d3e745ccfb24b492ab1'
H66_EVIDENCE_ARCHIVE_SHA = 'a01802511c97e0341d3523e58424e2a73feb69ec23e507ff7644e4b4029763f1'
H66_TSV_SHA = '7da6f589a14603697b4314c8472a36c1e8368209d9a4e1d4af50e1b117c527f0'
H66_WORD_CORPUS_SHA = '1144c2c5e62af1753b87d2eea64eea28a2c90b5c4d406df53d7bd23eda67c3b6'
H115_K41_SHA = 'ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba'
H65_ANCHOR_SHA = '5d1dd19f9e6bbc7f0d84a6d270eb30609318f29cd95a0fe01dc67fc5273e78a6'
H65_COVERAGE_SHA = 'b8c4305ebb02e0819668de53d9c3b8be4ded649aea5a6658be5cb983ce46440d'
H66_OCR_SHA = '6ee2d050000447cb169319428baad2d760a9d7cf4545f983039791451546e1e9'
EXPECTED_FIELDS = ['address','word','opcode','a1','a2','a3','printed_page',
                   'printed_column','printed_line','ocr_text_layer_row','qualification']
PAGE_COUNTS = {'112':18,'113':42,'114':47,'115':40,'116':80,'117':24}
SLOT_COUNTS = {1:64,2:64,3:53,4:64,5:6}
WORD_RE = re.compile(r'[0-7]{2}( [0-7]{4}){3}\Z')

class GateError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise GateError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def records(raw):
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError as exc:
        raise GateError('TSV is not UTF-8') from exc
    return list(csv.DictReader(io.StringIO(text, newline=''),delimiter='\t'))

def slots():
    return set(range(0o3300,0o4000))

def holes():
    return (set(range(0o3506,0o3510)) | set(range(0o3552,0o3557)) |
            set(range(0o3574,0o3600)) | set(range(0o3706,0o4000)))

def verify_h66_data(tsv, coverage, anchors, normalizations):
    # The H66 source corpus digest is pinned independently of the 41-bit packing.
    require(sha(tsv)==H66_TSV_SHA,'H66 TSV byte-level SHA mismatch')
    require(sha(coverage)==H65_COVERAGE_SHA,'H65 coverage SHA mismatch')
    require(sha(anchors)==H65_ANCHOR_SHA,'H65 anchor SHA mismatch')
    require(sha(normalizations)==H66_OCR_SHA,'H66 OCR correction SHA mismatch')
    return parse_source(tsv,coverage,anchors,normalizations)

def parse_source(tsv,coverage,anchors,normalizations,*,pin_corpus=True):
    arr=records(tsv)
    require(len(arr)==251,'Expected exactly 251 printed records')
    require(list(arr[0])==EXPECTED_FIELDS,'H66 TSV header changed')
    expected=sorted(slots()-holes())
    addr_list=[]
    corpus=[]
    known={}
    for row in arr:
        address=row['address']
        require(re.fullmatch(r'[0-7]{4}',address) is not None,'Invalid octal address')
        addr=int(address,8)
        addr_list.append(addr)
        require(WORD_RE.fullmatch(row['word']) is not None,'Malformed word '+address)
        fields=row['word'].split()
        require(fields==[row['opcode'],row['a1'],row['a2'],row['a3']], 'Field mismatch '+address)
        require(int(fields[0],8)<32, 'Opcode larger than five bits '+address)
        word=int(''.join(fields),8)
        require(word < (1<<41),'Not a 41-bit machine word '+address)
        require(row['printed_page'] in PAGE_COUNTS,'Unknown printed page '+address)
        require(row['printed_column'] in ('left','right'),'Unknown source column '+address)
        require(row['printed_line'].isdigit() and 1<=int(row['printed_line'])<=80, 'Invalid source line '+address)
        require(row['ocr_text_layer_row'].strip()!='','Missing original text-layer row '+address)
        require(row['qualification'] in ('SCAN_CHECKED','SCAN_CORRECTED_OCR'),'Unknown qualification '+address)
        known[address]=row
        corpus.append(f"{address} {row['word']}\n")
    require(addr_list==expected,'Missing, additional, duplicated or unsorted printed addresses')
    require(Counter(r['printed_page'] for r in arr)==PAGE_COUNTS,'Unexpected counts per printed page')
    require(Counter((a-0o3300)//64+1 for a in addr_list)==SLOT_COUNTS,'Unexpected count per 64-word slot')
    require(len(holes())==69 and 0o3574 in holes(),'ROM holes unexpectedly changed')
    require(known['3566']['word']=='14 0021 3574 0021', 'Direct unknown reference changed')
    require(known['3300']['word']=='01 0000 3621 0026', 'FP slot 1 first word changed')
    require(known['3600']['word']=='11 0000 0000 0000', 'FP slot 4 first word changed')
    corpus_sha=sha(''.join(corpus).encode('ascii'))
    if pin_corpus:
        require(corpus_sha==H66_WORD_CORPUS_SHA,'Printed-word corpus digest mismatch')
    cov=records(coverage)
    require(len(cov)==320,'H65 coverage must list all 320 ROM positions')
    cov_map={r['address']:r for r in cov}
    require(len(cov_map)==320 and {int(x,8) for x in cov_map}==slots(),'H65 coverage address mismatch')
    for address,row in known.items():
        require(cov_map[address]['status']=='PRINTED_ADDRESS','Word at H65 unprinted address '+address)
        require(row['printed_page'] in cov_map[address]['printed_pages'].split(','),'Page not in H65 coverage '+address)
    for missing in holes():
        require(cov_map[f'{missing:04o}']['status']=='NO_PRINTED_ADDRESS','H65 hole discrepancy')
    anchor_rows=records(anchors)
    require(len(anchor_rows)==13 and len({r['address'] for r in anchor_rows})==13,'Expected 13 distinct H65 anchors')
    for anchor in anchor_rows:
        require(known[anchor['address']]['word']==anchor['word'],'H65 anchor mismatch '+anchor['address'])
    norm_rows=records(normalizations)
    require(len(norm_rows)==45 and len({r['address'] for r in norm_rows})==45,'Expected 45 distinct OCR corrections')
    norm={r['address']:r for r in norm_rows}
    for address,row in known.items():
        corrected=row['qualification']=='SCAN_CORRECTED_OCR'
        require(corrected==(address in norm),'OCR qualifier mismatch '+address)
        if corrected:
            n=norm[address]
            require((n['printed_page'],n['ocr_raw_row'],n['confirmed_word'])==
                    (row['printed_page'],row['ocr_text_layer_row'],row['word']),'OCR correction mismatch '+address)
    return arr,corpus_sha

def make_k41(arr):
    out=('KYIV41-OCT1\n'+''.join(f"{r['address']} {''.join(r['word'].split())}\n" for r in arr)).encode('ascii')
    require(sha(out)==H115_K41_SHA,'Rendered K41 does not match verified H115 pin')
    return out

def zip_verified(z, *, expected, prefix=''):
    require(sha(Path(z).read_bytes())==expected,'Archive SHA-256 mismatch: '+str(z))
    with zipfile.ZipFile(z) as arc:
        require(arc.testzip() is None,'Corrupted ZIP: '+str(z))
        names=arc.namelist()
        require(len(names)==len(set(names)),'Duplicate ZIP path')
        sums_name=prefix+'SHA256SUMS.txt'
        manifest=arc.read(sums_name).decode('utf-8').splitlines()
        for line in manifest:
            h,filename=line.split('  ',1)
            require(filename!='' and '..' not in Path(filename).parts, 'Unsafe checksum path')
            raw=arc.read(prefix+filename)
            require(sha(raw)==h,'Checksum mismatch: '+filename)
        return {name.removeprefix(prefix):arc.read(name) for name in names if name.startswith(prefix) and not name.endswith('/')}

def build(source_zip,evidence_zip):
    src=zip_verified(source_zip,expected=H66_SOURCE_ARCHIVE_SHA,prefix='kyiv_h66_v1/')
    ev=zip_verified(evidence_zip,expected=H66_EVIDENCE_ARCHIVE_SHA)
    required=['FP_1962_PRINTED_251_WORDS.tsv','H65_PRINTED_ADDRESS_COVERAGE.tsv',
              'H65_SOURCE_ANCHORS.tsv','OCR_NORMALIZATIONS.tsv','SOURCE_DECISION.md']
    for name in required:
        require(src[name]==ev[name],'H66 source/evidence disagreement: '+name)
    state=json.loads(ev['RESULT.json'])
    require(state['gate']=='PASS_FP_251_PRINTED_WORDS_PROVENANCE_NOT_COMPLETE_ROM' and
            state['stage']=='complete' and state['printed_words']==251,'H66 acceptance state not qualified')
    source_state=json.loads(ev['SOURCE_VERIFICATION.json'])
    require(source_state['word_corpus_sha256']==H66_WORD_CORPUS_SHA and
            source_state['h65_anchor_matches']==13 and source_state['missing_printed_addresses']==69,
            'H66 verification report unexpected')
    arr,corpus_sha=verify_h66_data(*(ev[name] for name in required[:4]))
    k41=make_k41(arr)
    report={'schema':'KYIV_H115_A_SOURCE_V1','stage':'SOURCE_ONLY_NOT_NATIVE',
            'evidence_type':'SOURCE_TRANSCRIPTION_WITH_SCAN_CHECK_NOT_INDEPENDENT_HUMAN_RETRANSCRIPTION',
            'source_archive_sha256':H66_SOURCE_ARCHIVE_SHA,'evidence_archive_sha256':H66_EVIDENCE_ARCHIVE_SHA,
            'source_tsv_sha256':H66_TSV_SHA,'word_corpus_sha256':corpus_sha,
            'k41_sha256':sha(k41),'k41_records':251,'h65_anchors':13,'ocr_normalizations':45,
            'unprinted_addresses':69,'unprinted_address_3574':'OPEN_SOURCE','nominal_256':'OPEN_UNRECONCILED',
            'source_pages':[112,113,114,115,116,117],
            'source_configuration':'FP_ALTERNATIVE_ONLY','hardware_oracle':'NO',
            'cpu_execution':'NOT_ATTEMPTED','numerical_fp':'NOT_QUALIFIED'}
    return k41,ev[required[0]],report

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-zip',type=Path,required=True)
    ap.add_argument('--evidence-zip',type=Path,required=True)
    ap.add_argument('--check-k41',type=Path,help='Optional exact K41 artifact for byte-level comparison')
    ap.add_argument('--check-provenance',type=Path,help='Optional exact H66 TSV artifact for byte-level comparison')
    ap.add_argument('--out',type=Path,help='Create new directory with k41, provenance and result.json; never overwrite')
    args=ap.parse_args(argv)
    try:
        k41,tsv,report=build(args.source_zip,args.evidence_zip)
        if args.check_k41:
            require(args.check_k41.read_bytes()==k41,'Prepared K41 differs from pinned H66 transcription')
        if args.check_provenance:
            require(args.check_provenance.read_bytes()==tsv,'Provenance TSV differs from H66 original')
        if args.out:
            require(not args.out.exists(),'Output directory already exists')
            args.out.mkdir(parents=True)
            (args.out/'fp_simulation_251_printed.k41').write_bytes(k41)
            (args.out/'fp_simulation_251_provenance.tsv').write_bytes(tsv)
            (args.out/'result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print('H115_A_STATUS=PASS_SOURCE_MATERIALIZATION_NOT_NATIVE')
        print(json.dumps(report,sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
        print(f'H115_A_STATUS=HOLD_SOURCE {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
if __name__=='__main__':
    sys.exit(main())
