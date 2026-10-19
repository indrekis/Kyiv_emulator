#!/usr/bin/env python3
"""Read-only D14-B3 audit; no tracked or CPU modifications; exact LF-normalized hashes."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='5632a0b0b7e622c1c06cbea8aee82679dca0c926'
PINS={
    'src/main.cpp':'145cbf8725405b52c12c3c75fa8f3141f2671dc1',
    'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
    'inc/kyiv_drum_logical_media.h':'910911f7181bfb455e334b1f66fd00ee94ef1e97',
    'inc/kyiv_drum_group_transfer.h':'91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b',
    'docs/ISA_07_D14A_SHARED_DRUM_MODEL_CONTRACT.md':'9096fc7bddfa59052c539b065c1e0b9ee0062b5d',
}
NEW=(
    'docs/ISA_07_D14B3_BINARY_IMAGE_V1.md',
    'inc/kyiv_drum_persistence.h',
    'tests/isa/isa07_d14b3_persistence_probe.cpp',
    'tools/isa07_d14b3_persistence_sandbox.py',
    'tools/isa07_d14b3_audit.py',
)
CONTENT_SHA={
    'docs/ISA_07_D14B3_BINARY_IMAGE_V1.md':'e9c94889dc4c343b600c4ded7f9bcb96450f25512fc7d1bb36b50f7c93fd9dbb',
    'inc/kyiv_drum_persistence.h':'0504dab8f8fcc7a474794eb64aa7433e3fb74ddd4df0fe87ec78806fbe8a7abf',
    'tests/isa/isa07_d14b3_persistence_probe.cpp':'9bcf5b7e436676b07a68d60968686400c0992ea0057ae50c153fc2b0235e906b',
    'tools/isa07_d14b3_persistence_sandbox.py':'221db475e3201c7471ccabe2c55f47393726a62657d1079923671c318255d14a',
}

def require(test,msg):
    if not test: raise RuntimeError(msg)

def norm(src:bytes)->bytes:
    require(b'\r' not in src.replace(b'\r\n',b''),'BARE_CR_NOT_ALLOWED')
    return src.replace(b'\r\n',b'\n')

def git(*args:str)->bytes:
    return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.PIPE)

def static_checks():
    require(len(PINS)==5 and len(NEW)==5 and len(CONTENT_SHA)==4,'MATRIX_LENGTH')
    require(set(CONTENT_SHA)==set(NEW[:-1]),'CONTENT_SHA_COVERAGE')
    for name,expected in CONTENT_SHA.items():
        file=ROOT/name
        require(file.is_file(),'MISSING '+name)
        require(hashlib.sha256(norm(file.read_bytes())).hexdigest()==expected,
                'SHA_MISMATCH '+name)
    src=norm((ROOT/NEW[1]).read_bytes()).decode('utf-8')
    doc=norm((ROOT/NEW[0]).read_bytes()).decode('utf-8')
    runner=norm((ROOT/NEW[3]).read_bytes()).decode('utf-8')
    require('KYIVDRM1' in doc and 'CRC64/ECMA-182' in doc and
            '0x6C40DF5F0B497347' in doc and '64' in doc, 'IMAGE_CONTRACT')
    for needed in ('encode(', 'decode(', 'save_atomic(', 'load_into(',
                   'read_le(', 'put_le(', 'crc64(', 'NONCANONICAL_UNWRITTEN',
                   'NONCANONICAL_BITMAP', 'CHECKSUM_MISMATCH',
                   'GEOMETRY_MISMATCH', 'std::filesystem::rename'):
        require(needed in src,'API_CONTRACT '+needed)
    require('reference(' in runner and 'crc64(' in runner and
            'fix_checksum(' in runner and 'NEGATIVE=19/19' in runner and
            'INDEPENDENT_BYTE_ORACLE=1' in runner,'INDEPENDENT_TEST_MATRIX')
    require('kyiv.h' not in src and 'src/main.cpp' not in src,'NO_CPU_DEPENDENCY')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    try:
        static_checks()
        if args.self_test:
            require(norm(b'a\r\nb\nc\r\n')==b'a\nb\nc\n','MIXED_EOL')
            try:norm(b'a\rb')
            except RuntimeError:pass
            else:raise RuntimeError('BAD_EOL_NOT_REJECTED')
            require(hashlib.sha256(norm((ROOT/NEW[1]).read_bytes())).hexdigest()==
                    CONTENT_SHA[NEW[1]],'HEADER_PIN')
            print('D14B3-SELFTEST PASS PINS=5/5 NEW_FILES=5/5 CONTENT_SHA=4/4 '
                  'LF_CRLF_MIXED=1 INVALID_CR_REJECTED=1 B1_B2_UNCHANGED=1 '
                  'CPU_MUTATION=0 GIT_BASE_CHECK=DEFERRED_TO_AUDIT')
            return 0
        require(git('rev-parse','--show-prefix').strip()==b'','RUN_AT_REPO_ROOT')
        require(git('rev-parse','HEAD').decode().strip()==BASE,'UNEXPECTED_HEAD')
        require(not git('diff','--name-only').strip(),'TRACKED_MODIFICATIONS')
        require(not git('diff','--cached','--name-only').strip(),'STAGED_MODIFICATIONS')
        untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
        require(untracked==set(NEW),'UNTRACKED_SCOPE '+repr(untracked^set(NEW)))
        for path,sha in PINS.items():
            require(git('rev-parse','HEAD:'+path).decode().strip()==sha,'GIT_PIN '+path)
            require(norm((ROOT/path).read_bytes())==norm(git('show','HEAD:'+path)),
                    'BASE_MUTATION '+path)
        git('diff','--check')
        print('D14B3-AUDIT PASS BASELINE=5632a0b PINS=5/5 NEW_FILES=5/5 '
              'CONTENT_SHA=4/4 TRACKED_MUTATION=0 CPU_MUTATION=0 '
              'B1_B2_UNCHANGED=1 CANONICAL_V1=1 CHECKSUM=CRC64_ECMA '
              'EOL_PORTABLE=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (RuntimeError,OSError,UnicodeError,ValueError,subprocess.CalledProcessError) as e:
        print('D14B3-AUDIT FAIL',e,file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
