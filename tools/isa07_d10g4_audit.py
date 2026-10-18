#!/usr/bin/env python3
"""D10-G4 read-only Git/source/document gate. No source or CPU mutation."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

BASE='75a401107b03e9fb535d9aaf97b56c85a434293f'
PINS={
 'src/main.cpp':'e6d00248705668156c29b376b3dd1b26ed40e275',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'inc/kyiv_decimal_trunc.h':'e6ab074335a2337de3a5b0eadd3bf46adf0b09fe',
 'inc/kyiv_decimal_ascii.h':'e92fda12785ea2ed79a215461003a13eb85fb076',
 'inc/kyiv_decimal_input_plan.h':'a38b137291c7e218bf9d81c5eebfcc6ac9d3b6a3',
 'docs/ISA_07_D10G3_CONTROL_MICROPROGRAM_RECONSTRUCTION.md':'8700ab535284ca4cb86f6454a4d8bf68afaf2dd6',
 'docs/ISA_07_D10G3_SOURCE_LEDGER.tsv':'808384ba78bce853a82ca9b567442e098e7bf1e9',
 'tools/isa07_d10g3_microsteps.py':'c44a6aa876179448a014496b9ec7fbfc321f3c89',
 'tools/isa07_d10g3_audit.py':'66182849a9c43334a057ff5ae4267ce320ae408b',
 'docs/ISA_07_D10G2_ARITHMETIC_DATAPATH_RECONSTRUCTION.md':'1264622760a5a794834e96a07aaa99ac1bced5a2',
 'docs/ISA_07_D10G2_SOURCE_LEDGER.tsv':'6c7aa983ecf411af5ecdceedb3b17559a07fdeff',
 'docs/ISA_07_D10G1_DECIMAL_MICROPROGRAM_RECONSTRUCTION.md':'146dd098afbe51b1ff87e5191ee23dfb7968f49a',
}
NEW=(
 'docs/ISA_07_D10G4_CONTROL_SIGNALS_AND_COEFFICIENT_SOURCE.md',
 'docs/ISA_07_D10G4_TABLE5_SIGNAL_MATRIX.tsv',
 'docs/ISA_07_D10G4_SOURCE_DECISION_LEDGER.tsv',
 'tools/isa07_d10g4_evidence.py',
 'tests/isa/isa07_d10g4_evidence_test.py',
 'tools/isa07_d10g4_audit.py',
)
# The audit's own SHA cannot be noncircularly self-embedded.
NEW_SHA={
 'docs/ISA_07_D10G4_CONTROL_SIGNALS_AND_COEFFICIENT_SOURCE.md':'ecb1349c75659d4b33a892773fccd5d7d60370d2cfc5e3ae986229bc49c26405',
 'docs/ISA_07_D10G4_SOURCE_DECISION_LEDGER.tsv':'d4bf737c09f2401a135b074e1ab4419eb8a70c9c1d36853c691a28f4fcf7b442',
 'docs/ISA_07_D10G4_TABLE5_SIGNAL_MATRIX.tsv':'16bd84e354f57d9b1e4ecb27ec8621c998e89d010a9691e0c7bb96f1ab207542',
 'tests/isa/isa07_d10g4_evidence_test.py':'06edb5ed2bb75fd557dc7321e43196915acf6ad11477e0434bfe601fc184a33c',
 'tools/isa07_d10g4_evidence.py':'5e00a6d7d58f080eea60655688ca628b9a45b26c2d45d97beb1320ba8f0fd08f',
}

def git(*args):
    return subprocess.check_output(('git',)+args,text=True,stderr=subprocess.PIPE).strip()

def req(ok,msg):
    if not ok: raise RuntimeError(msg)

def normalized(path):
    data=Path(path).read_bytes()
    req(b'\r' not in data.replace(b'\r\n',b''),'bare CR in '+path)
    return data.replace(b'\r\n',b'\n')

def load(path):
    spec=importlib.util.spec_from_file_location('g4_readonly_evidence',Path(path).resolve())
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def main():
    try:
        req(git('rev-parse','--show-prefix')=='','must run at repository root')
        req(git('rev-parse','HEAD')==BASE,'wrong baseline; require 75a4011')
        req(not git('diff','--name-only') and not git('diff','--cached','--name-only'),
            'tracked or staged mutation')
        for path,sha in PINS.items():
            req(git('rev-parse','HEAD:'+path)==sha,'source pin drift: '+path)
        for path in NEW:
            req(Path(path).is_file(),'missing new G4 file: '+path)
            req(not git('ls-files','--',path),'G4 file unexpectedly staged/tracked: '+path)
            body=normalized(path)
            if path in NEW_SHA:
                req(hashlib.sha256(body).hexdigest()==NEW_SHA[path],
                    'G4 normalized sha mismatch: '+path)
        doc=normalized(NEW[0]).decode('utf-8')
        for marker in ('DPS64','GY62','pp.124–125','p.121','SOURCE_STRICT',
                       'READING_QUALIFIED','PROVISIONAL','OPEN',
                       'DO NOT MODIFY `IO20`','При наличии набора кодов',
                       'ПЧ₁','ПЧ₂','READING_QUALIFIED'):
            req(marker.casefold() in doc.casefold(),'source qualification missing: '+marker)
        ledger=normalized(NEW[2]).decode('utf-8')
        for marker in ('G4-S01','G4-S05','G4-S08','G4-I01','G4-D01','G4-D02'):
            req(marker in ledger,'ledger missing '+marker)
        model=load(NEW[3]); mat=model.signal_tsv().encode('utf-8')
        req(mat==normalized(NEW[1]),'Table5 TSV regeneration mismatch')
        req(len(model.SIGNALS)==9,'Table5 source selection changed')
        test=normalized(NEW[4]).decode('utf-8')
        req('Random(0xD10A4)' in test and 'G3_PARITY=' in test and
            'HARDWARE_ORACLE=0' in test,'test oracle contract missing')
        source=normalized(NEW[3]).decode('utf-8')
        req('Fraction' in source and 'historical_io20_word_oracle' in source and
            'READING_QUALIFIED' in source,'model qualification missing')
        req(len(PINS)==12 and len(NEW)==6 and len(NEW_SHA)==5,
            'unexpected gate scope')
        print('D10G4-AUDIT PASS BASELINE=75a4011 PINS=12/12 NEW_FILES=6/6 '
              'CONTENT_SHA=5/5 CPU_MUTATION=0 F2_F3_G1_G2_G3_UNCHANGED=1 '
              'TABLE5_REGENERATED=1 EOL_PORTABLE=1 E_S_SOURCE=OPEN '
              'IO20_DECISION=UNCHANGED HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (RuntimeError,UnicodeError,OSError,subprocess.CalledProcessError,ImportError) as e:
        print('D10G4-AUDIT FAIL:',e,file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
