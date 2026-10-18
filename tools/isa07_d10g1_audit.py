#!/usr/bin/env python3
"""D10-G1 read-only structural/source provenance gate. NO CPU tests."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

BASE='6ac9660b20218de2d28e89d6eca5336905f5a6e0'
PINS={
 'src/main.cpp':'e6d00248705668156c29b376b3dd1b26ed40e275',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'inc/kyiv_decimal_trunc.h':'e6ab074335a2337de3a5b0eadd3bf46adf0b09fe',
 'inc/kyiv_decimal_ascii.h':'e92fda12785ea2ed79a215461003a13eb85fb076',
 'inc/kyiv_decimal_input_plan.h':'a38b137291c7e218bf9d81c5eebfcc6ac9d3b6a3',
 'docs/ISA_07_D10F2_PROVISIONAL_TRUNCATION_DECISION.md':'2bcdac01b954ad84ba3a3836e115fd0388951729',
 'docs/ISA_07_D10F3_PROVISIONAL_TRUNCATION_INTEGRATION.md':'b0dcf7f8e4a38facac3f8aa66eca2ee4a502fbc4',
 'tools/isa07_d10f3_regression_gate.py':'dfca8db030a42416321d126a081a9abe4326c44a',
}
NEW=(
 'docs/ISA_07_D10G1_DECIMAL_MICROPROGRAM_RECONSTRUCTION.md',
 'docs/ISA_07_D10G1_EVIDENCE_LEDGER.tsv',
 'docs/ISA_07_D10G1_COMPARISON.tsv',
 'tools/isa07_d10g1_reference.py',
 'tests/isa/isa07_d10g1_reference_test.py',
 'tools/isa07_d10g1_audit.py',
)
PDFS={
 'gy62':'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea',
 'dps64':'ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5',
}

def git(*args):
    return subprocess.check_output(('git',)+args,stderr=subprocess.PIPE,text=True).strip()


def req(ok,msg):
    if not ok: raise RuntimeError(msg)


def audit(args):
    req(git('rev-parse','--show-prefix')=='','wrong repository root')
    req(git('rev-parse','HEAD')==BASE,'wrong HEAD: require 6ac9660')
    for path,blob in PINS.items():
        req(git('rev-parse','HEAD:'+path)==blob,'baseline Git blob drift: '+path)
        req(not git('diff','--',path),'tracked worktree mutation: '+path)
        req(not git('diff','--cached','--',path),'staged tracked mutation: '+path)
    for path in NEW:
        req(Path(path).is_file(),'new source missing: '+path)
        req(not git('ls-files','--',path),'G1 new file unexpectedly committed/staged: '+path)
        # Git may check out these text files with Windows CRLF.
        data=Path(path).read_bytes().replace(b'\r\n', b'\n')
        req(b'\r' not in data,'unexpected bare CR in G1 source: '+path)
        req(all(line.rstrip(b' \t')==line for line in data.split(b'\n')),
            'trailing whitespace in '+path)
    prose=Path(NEW[0]).read_text(encoding='utf-8')
    for token in ('DPS64 p.121','DPS64 p.122','DPS64 pp.124–125','GY62 pp.10–11',
                  '6ac9660b20218de2d28e89d6eca5336905f5a6e0',
                  'SOURCE_STRICT','INFERRED / PROVISIONAL','counterfactual',
                  'E_s = 10^(-s) / 2^(n-4*s)',
                  'x_i = 2*x_(i-1) + a_i*E_s',
                  'No change'):
        req(token in prose,'documentary condition missing: '+token)
    ledger=Path(NEW[1]).read_text(encoding='utf-8')
    for token in ('G1-S01','G1-S07','G1-H02','G1-H03','G1-D01',
                  'SOURCE_STRICT','COUNTERFACTUAL_REJECTED','INFERRED_PROVISIONAL'):
        req(token in ledger,'ledger evidence missing: '+token)
    # Reproduce the TSV using a distinct independent calculation of ideal values.
    sys.path.insert(0,str(Path('tools').resolve()))
    import isa07_d10g1_reference as ref
    table=Path(NEW[2]).read_text(encoding='utf-8').splitlines()
    header=table[0].split('\t')
    req(len(header)==9,'wrong table schema')
    req(len(table)==13,'wrong sample table length')
    for line in table[1:]:
        fields=line.split('\t')
        req(len(fields)==9,'bad sample row')
        v=ref.vector(fields[0]);m=v['models']
        actual=[fields[0],v['ideal_octal'],str(int(v['ideal_exact']))]
        for prec,mode in ((40,'floor'),(64,'floor'),(72,'floor'),
                          (80,'floor'),(80,'nearest'),(88,'nearest')):
            actual.append(str(m[f'P{prec}_{mode}'].get('delta_ulps','OVERFLOW')))
        req(fields==actual,'counterfactual table drift: '+fields[0])
    for key in ('gy62','dps64'):
        source=getattr(args,key)
        if source:
            p=Path(source)
            req(p.is_file(),'missing PDF: '+key)
            h=hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
            req(h.hexdigest()==PDFS[key],'PDF checksum mismatch: '+key)
    print('D10G1-AUDIT PASS BASELINE=6ac9660 PINS=8/8 NEW_FILES=6/6 '
          'CPU_MUTATION=0 CONVERTER_MUTATION=0 SOURCE_LEDGER=1 '
          'COMPARISON_REGENERATED=1 HARDWARE_ORACLE=0 '
          'PDF_HASH_CHECKS='+str(int(bool(args.gy62))+int(bool(args.dps64))))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--gy62',help='optional local 1962 PDF for SHA256 verification')
    p.add_argument('--dps64',help='optional local 1964 PDF for SHA256 verification')
    a=p.parse_args()
    try: audit(a)
    except (RuntimeError, OSError, subprocess.CalledProcessError, AssertionError, ValueError) as e:
        print('D10G1-AUDIT FAIL: '+str(e),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
