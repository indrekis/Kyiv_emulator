#!/usr/bin/env python3
"""D14-A evidence-only review gate. No emulator behavior or CPU mutations."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

BASE='9e9ff811f6199991f782fb2fd69549135a78a1d9'
PINS={
    'src/main.cpp':'145cbf8725405b52c12c3c75fa8f3141f2671dc1',
    'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
    'inc/kyiv_drum_input_plan.h':'29e8e442341dba3668f8fe12aabff6bf0ff6b4e3',
    'inc/kyiv_drum_output_plan.h':'b7a102d9d212b0eb2e6a4e089a7e628cd7f4bd62',
    'tools/isa07_d13b_regression_gate.py':'1f241f0be661d83fa352af2cd8dfb626484166c1',
}
NEW=(
 'docs/ISA_07_D14A_MAGNETIC_DRUM_SOURCE_REVIEW.md',
 'docs/ISA_07_D14A_SHARED_DRUM_MODEL_CONTRACT.md',
 'docs/ISA_07_D14A_DRUM_EVIDENCE_LEDGER.tsv',
 'tools/isa07_d14a_audit.py',
)
# SHA256 on LF-normalized contents for every new document, not self-referential script.
CONTENT_SHA={'docs/ISA_07_D14A_DRUM_EVIDENCE_LEDGER.tsv': '4fa2cde7d861d5daf19cc0797b29d08759cb12139e2f6ff52fcd7670cdffcc3b', 'docs/ISA_07_D14A_MAGNETIC_DRUM_SOURCE_REVIEW.md': '3ab08cb240eac55d4dc8233eceb4b63d4e1f4d9a71e2425a3c9fd69453825e90', 'docs/ISA_07_D14A_SHARED_DRUM_MODEL_CONTRACT.md': '8ba45bf87a4559a5df2181453d95bacbb8db8d68a880c4db9141cf12869700c3'}
GY62_SHA='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
DPS64_SHA='ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5'

def need(v,msg):
    if not v: raise RuntimeError(msg)

def normalize(data:bytes)->bytes:
    need(b'\r' not in data.replace(b'\r\n',b''),'BARE_CR')
    return data.replace(b'\r\n',b'\n')

def git(*args):
    return subprocess.check_output(('git',*args),stderr=subprocess.PIPE).decode().strip()

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while True:
            b=f.read(1<<20)
            if not b: break
            h.update(b)
    return h.hexdigest()

def self_test():
    x=b'A\nB\n'
    need(normalize(x)==normalize(x.replace(b'\n',b'\r\n')),'CRLF_SELFTEST')
    try: normalize(b'A\rB\n')
    except RuntimeError: pass
    else: raise RuntimeError('BARE_CR_NOT_REJECTED')
    need(9864 == 3*24*137 and 3*24*511 != 9864,'GEOMETRY_CONFLICT_UNMODELED')
    need(len(NEW)==4 and len(PINS)==5 and len(CONTENT_SHA)==3,'COVERAGE')
    print('D14A-SELFTEST PASS EOL=2/2 CONFLICT_RETAINED=1 PINS=5/5 NEW_FILES=4/4 CPU_MUTATION=0')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--gy62',type=Path)
    ap.add_argument('--dps64',type=Path)
    a=ap.parse_args()
    try:
        if a.self_test: self_test(); return 0
        need(git('rev-parse','--show-prefix')=='','RUN_FROM_REPO_ROOT')
        need(git('rev-parse','HEAD')==BASE,'UNEXPECTED_HEAD')
        need(not git('diff','--name-only'),'TRACKED_MUTATION')
        need(not git('diff','--cached','--name-only'),'STAGED_CHANGES')
        observed=set(filter(None,git('ls-files','--others','--exclude-standard').splitlines()))
        need(observed==set(NEW),'NEW_SCOPE_MISMATCH '+str(observed^set(NEW)))
        for path,blob in PINS.items():
            need(git('rev-parse','HEAD:'+path)==blob,'PIN_MISMATCH '+path)
            need(not git('diff','--',path),'PIN_FILE_MUTATION '+path)
        for path,sha in CONTENT_SHA.items():
            content=normalize(Path(path).read_bytes())
            need(hashlib.sha256(content).hexdigest()==sha,'DOC_HASH_MISMATCH '+path)
        doc=normalize(Path(NEW[0]).read_bytes()).decode('utf-8')
        contract=normalize(Path(NEW[1]).read_bytes()).decode('utf-8')
        ledger=normalize(Path(NEW[2]).read_bytes()).decode('utf-8')
        for required in ('9864','511','137','GY62','DPS64','SOURCE_CONFLICT','24-й'):
            need(required in doc,'SOURCE_REVIEW_MISSING '+required)
        for required in ('HOST_POLICY','PROVISIONAL','25(write)','D14-C','41-біт'):
            need(required in contract,'CONTRACT_MISSING '+required)
        keys=[line.split('\t',1)[0] for line in ledger.splitlines()[1:] if line.strip()]
        need(len(keys)>=24 and len(keys)==len(set(keys)),'LEDGER_KEY_COVERAGE')
        need('GEOMETRY_CONFLICT' in keys and 'MZ_ROM_SOURCE' in keys and 'MZ_ADDR_MOD_REG' in keys,'SOURCE_RISK_MISSING')
        pdfchecks=0
        for p,sha in ((a.gy62,GY62_SHA),(a.dps64,DPS64_SHA)):
            if p is not None:
                need(p.is_file(),'PDF_MISSING '+str(p))
                need(file_sha(p)==sha,'PDF_SHA_MISMATCH '+str(p))
                pdfchecks+=1
        subprocess.run(('git','diff','--check'),check=True)
        print('D14A-AUDIT PASS BASELINE=9e9ff81 PINS=5/5 NEW_FILES=4/4 '
              'CONTENT_SHA=3/3 CPU_MUTATION=0 D13B_UNCHANGED=1 SOURCE_CONFLICTS=OPEN '
              'ARCHITECTURE_ONLY=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS='+str(pdfchecks))
        return 0
    except (OSError,UnicodeError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
        print('D14A-AUDIT FAIL',str(e),file=sys.stderr)
        return 1
if __name__=='__main__': raise SystemExit(main())
