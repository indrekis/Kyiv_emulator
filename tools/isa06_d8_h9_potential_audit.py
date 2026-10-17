#!/usr/bin/env python3
"""D8-H9: preserve source-scoped operation decoder evidence; NOT a gate simulator."""
import argparse
import csv
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'
PREFIX='ISA_06_D8_H9_'
def read(name):
    with (DOC/(PREFIX+name+'.tsv')).open(encoding='utf8',newline='') as f:
        return list(csv.DictReader(f,delimiter='\t'))
def assert_true(ok,reason):
    if not ok: raise AssertionError(reason)
def main():
    a=argparse.ArgumentParser()
    a.add_argument('--check',action='store_true')
    a.add_argument('--show-obligations',action='store_true')
    a.add_argument('--verify-source',type=Path)
    args=a.parse_args()
    glossary,coverage,proof,sources=(read('POTENTIAL_GLOSSARY'),read('SOURCE_REVIEW'),read('PROOF_OBLIGATIONS'),read('SOURCE_MANIFEST'))
    assert_true(len(glossary)==11 and {r['id'] for r in glossary}=={'G%02d'%i for i in range(1,12)},'glossary rows')
    assert_true(len(coverage)==8 and len(sources)==8,'review manifest counts')
    assert_true(len(proof)==7 and {r['id'] for r in proof}=={'P%02d'%i for i in range(1,8)},'proof rows')
    assert_true(all(r['status']=='OPEN' for r in proof),'unsupported completion of proof obligation')
    assert_true({r['original_scan'] for r in coverage}=={r['name'] for r in sources},'scan coverage mismatch')
    terms={r['symbol_id']:r for r in glossary}
    assert_true(terms['UU_ARITH_O']['grade']=='DOC' and terms['OP01_IN_UU_ARITH_FAMILY']['grade']=='DERIVED_LIMITED','УУ potential overclaim')
    assert_true('not numeric zero' in terms['UU_ARITH_O']['excluded_inference'],'УУ glyph caution missing')
    assert_true(terms['SR3_EXACT_COMPARISON']['grade']=='DOC','Ср3 source missing')
    assert_true(all(r['grade'] in {'DOC','DOC_SCOPED','DERIVED_LIMITED'} for r in glossary),'invalid grades')
    assert_true(all(r['scope_status']=='reviewed' for r in coverage),'unreviewed page claimed')
    h8=DOC/'ISA_06_D8_H8_OPCODE01_BOUNDARIES.tsv'
    with h8.open(newline='',encoding='utf8') as f: old=list(csv.DictReader(f,delimiter='\t'))
    assert_true(len(old)==6,'H8 cases not found')
    for r in old:
        for k in ('C16_admission','C17_admission','C18_admission','TZn2Sm_at_IVA3','historical_01_zero_sign'):
            assert_true(r[k]=='OPEN',f'unsupported output: {r["case_id"]}.{k}')
        assert_true(r['TZn1Sm_after_reset']==r['TZn2Sm_after_reset']=='0','reset evidence regressed')
    overrides=(DOC/'ISA_06_D8_H2_EDGE_OVERRIDES.tsv').read_text(encoding='utf8')
    assert_true('E022' in overrides and ('RETRACT' in overrides.upper() or 'contradict' in overrides.lower()), 'E022 missing')
    h8_sources=DOC/'ISA_06_D8_H8_SOURCE_MANIFEST.tsv'
    with h8_sources.open(newline='',encoding='utf8') as f: original={r['name']:r for r in csv.DictReader(f,delimiter='\t')}
    for s in sources:
        assert_true(len(s['sha256'])==64 and int(s['bytes'])>0,'bad hash')
        if s['name'] in original:
            assert_true((s['sha256'],s['bytes'])==(original[s['name']]['sha256'],original[s['name']]['bytes']),'source manifest conflicts with H8')
        if args.verify_source is not None:
            p=args.verify_source/s['name']
            assert_true(p.is_file(),'missing original scan '+str(p))
            data=p.read_bytes()
            assert_true(len(data)==int(s['bytes']) and hashlib.sha256(data).hexdigest()==s['sha256'],'SHA mismatch '+str(p))
    print('ISA-06 D8-H9: SOURCE-GROUNDED POTENTIAL GLOSSARY; F71 ELECTRICAL MAPPING AND SIGNED-ZERO ORACLE OPEN')
    print(f'POTENTIAL-CHECK PASS glossary={len(glossary)} reviewed_spreads={len(coverage)} obligations={len(proof)} sources={len(sources)} UU_arith_O=DOC opcode01_UU_membership=DERIVED_LIMITED H2_E022=RETRACTED')
    if args.show_obligations:
        for r in proof: print(r['id']+': '+r['target']+' status='+r['status']+' required='+r['required_evidence'])
    if args.verify_source: print(f'SOURCE-SHA256 PASS originals={len(sources)}')
if __name__=='__main__':main()
