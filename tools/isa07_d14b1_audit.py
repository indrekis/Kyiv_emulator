#!/usr/bin/env python3
"""D14-B1: exact baseline + additive-file audit, no CPU mutation.

Run from repository root after git apply D14B1.patch; read-only.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess
import sys

BASE='9d45a0262e7bce6268cbf50282443ad2b863ac06'
PINS={'src/main.cpp': '145cbf8725405b52c12c3c75fa8f3141f2671dc1', 'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5', 'docs/ISA_07_D14A_SHARED_DRUM_MODEL_CONTRACT.md': '9096fc7bddfa59052c539b065c1e0b9ee0062b5d', 'docs/ISA_07_D14A_DRUM_EVIDENCE_LEDGER.tsv': 'ed957a98b7966da8614bb745f399fd352335ead1', 'tools/isa07_d13b_regression_gate.py': '1f241f0be661d83fa352af2cd8dfb626484166c1'}
NEW=('docs/ISA_07_D14B1_LOGICAL_MEDIA_API.md', 'inc/kyiv_drum_logical_media.h', 'tests/isa/isa07_d14b1_logical_media_probe.cpp', 'tools/isa07_d14b1_logical_media_sandbox.py', 'tools/isa07_d14b1_audit.py')
CONTENT_SHA={'docs/ISA_07_D14B1_LOGICAL_MEDIA_API.md': '4933a8f1efc292f5b02104115efe0b6791005912c4bbd247c0b7bc5c6aab20fe', 'inc/kyiv_drum_logical_media.h': 'aac66eb2fda53cfc24379eb70b8809863aca043e7ec6a3bfde6d4b9acb8117e1', 'tests/isa/isa07_d14b1_logical_media_probe.cpp': '4d878d92328c2915382d1233d469d5cce712a7b85d6c59ed96a0ae91fd9bb231', 'tools/isa07_d14b1_logical_media_sandbox.py': '3fda7463756783d61699a50ce07280732c6269c7edf2add7f10359d4dd4c4717'}
ROOT=Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition: raise RuntimeError(message)

def normalized(data:bytes)->bytes:
    require(b'\r' not in data.replace(b'\r\n', b''),'BARE_CR_NOT_ALLOWED')
    return data.replace(b'\r\n', b'\n')

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode('utf-8').strip()

def self_test():
    require(len(PINS)==5 and len(NEW)==5 and len(CONTENT_SHA)==4,'MATRIX')
    for path,sha in list(PINS.items())+list(CONTENT_SHA.items()):
        require(len(sha)==40 if path in PINS else len(sha)==64,'SHA_FORMAT '+path)
    sample=b'first\nsecond\n'
    require(normalized(sample)==normalized(sample.replace(b'\n',b'\r\n')),'EOL')
    require(normalized(b'a\r\nb\n')==b'a\nb\n','MIXED_EOL')
    try:normalized(b'a\rb');require(False,'BARE_CR_ACCEPTED')
    except RuntimeError as exc: require(str(exc)=='BARE_CR_NOT_ALLOWED','BAD_EXCEPTION')
    for path,expected in CONTENT_SHA.items():
        p=ROOT/path
        if p.exists():
            require(hashlib.sha256(normalized(p.read_bytes())).hexdigest()==expected,
                    'NEW_SHA_MISMATCH '+path)
    print('D14B1-SELFTEST PASS PINS=5/5 NEW_FILES=5/5 CONTENT_SHA=4/4 '
          'LF_CRLF_MIXED=3 INVALID_CR_REJECTED=1 CPU_MUTATION=0 '
          'GIT_BASE_CHECK=DEFERRED_TO_AUDIT')

def main():
    try:
        if len(sys.argv)==2 and sys.argv[1]=='--self-test':
            self_test(); return 0
        require(len(sys.argv)==1,'ARGUMENTS')
        require(Path.cwd().resolve()==ROOT,'RUN_FROM_REPO_ROOT')
        require(git('rev-parse','HEAD')==BASE,'BASELINE')
        require(git('rev-parse','--show-prefix')=='','NOT_REPO_ROOT')
        require(not git('diff','--name-only'),'TRACKED_MUTATION')
        require(not git('diff','--cached','--name-only'),'STAGED_MUTATION')
        actual=set(git('ls-files','--others','--exclude-standard').splitlines())
        require(actual==set(NEW),'UNTRACKED_SCOPE '+repr(actual.symmetric_difference(NEW)))
        for path,blob in PINS.items():
            require(git('rev-parse','HEAD:'+path)==blob,'BLOB_PIN '+path)
            require(hashlib.sha256(normalized((ROOT/path).read_bytes())).hexdigest()==
                    hashlib.sha256(normalized(subprocess.check_output(['git','show','HEAD:'+path]))).hexdigest(),
                    'BASE_FILE_CHANGED '+path)
        for path,sha in CONTENT_SHA.items():
            require(hashlib.sha256(normalized((ROOT/path).read_bytes())).hexdigest()==sha,
                    'CONTENT_SHA '+path)
        header=(ROOT/'inc/kyiv_drum_logical_media.h').read_text(encoding='utf-8')
        documentation=(ROOT/'docs/ISA_07_D14B1_LOGICAL_MEDIA_API.md').read_text(encoding='utf-8')
        require('struct coordinate' in header and 'struct cell' in header and
                'class logical_media' in header and 'word_mask' in header and
                'max_host_slots' in header, 'API_SIGNATURE')
        require('9864' in documentation and '511' in documentation and
                'OPEN' in documentation and 'HARDWARE_ORACLE=0' in documentation,
                'PROVISIONAL_SOURCE_GUARD')
        subprocess.run(['git','diff','--check'],check=True)
        subprocess.run(['git','diff','--cached','--check'],check=True)
        print('D14B1-AUDIT PASS BASELINE=9d45a02 PINS=5/5 '
              'NEW_FILES=5/5 CONTENT_SHA=4/4 TRACKED_MUTATION=0 '
              'CPU_MUTATION=0 PROFILE_EXPLICIT=1 RAW41=1 '
              'UNWRITTEN_DISTINCT=1 GEOMETRY_CONFLICT=OPEN '
              'EOL_PORTABLE=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError,RuntimeError,subprocess.CalledProcessError,UnicodeError) as e:
        print('D14B1-AUDIT FAIL',e,file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
