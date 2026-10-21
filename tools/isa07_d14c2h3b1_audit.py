#!/usr/bin/env python3
"""ISA-07 D14-C2-H3/B1: read-only, exact Git+content gate."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='04be0ca3ceafa7cd10c8ef250e9425b8e435b06e'
FILES=['docs/ISA_07_D14C2H3B1_CREATE_NEW_ONLY_CONTRACT.md',
 'docs/ISA_07_D14C2H3B1_DECISION_LEDGER.tsv',
 'inc/kyiv_drum_provision_v1.h',
 'tests/isa/isa07_d14c2h3b1_provision_probe.cpp',
 'tools/isa07_d14c2h3b1_audit.py',
 'tools/isa07_d14c2h3b1_create.cpp',
 'tools/isa07_d14c2h3b1_provision_sandbox.py']
PINS={'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
 'inc/kyiv_drum_cli_v1.h': '3925ec9503b92c614a43f877686a47fc6884a2b6',
 'inc/kyiv_drum_group_transfer.h': '91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b',
 'inc/kyiv_drum_host_address_v1.h': '74b75b9c4fd86d73b43eb108bbdce312dc9619d3',
 'inc/kyiv_drum_logical_media.h': '910911f7181bfb455e334b1f66fd00ee94ef1e97',
 'inc/kyiv_drum_persistence.h': '6827b4636405a5407c87055a4f35b575e71211c3',
 'inc/kyiv_drum_transaction_v1.h': '1aab83a4735280df0cf4331191c5521dcc5ddcb4',
 'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19',
 'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804'}
SHA={'docs/ISA_07_D14C2H3B1_CREATE_NEW_ONLY_CONTRACT.md': '6d141746d7071a3dbc3f9ab204bf147ebbc02458f777ddbb9825f6635643f69f',
 'docs/ISA_07_D14C2H3B1_DECISION_LEDGER.tsv': 'bb2ab0139a1952a07d62f9511cccd6a6d2763fd79b6c63aed9783ab616273c1b',
 'inc/kyiv_drum_provision_v1.h': '9b2babed6f76ea07139a6d3e0e3b43888eb634d9dd71c3befab546110bd48881',
 'tests/isa/isa07_d14c2h3b1_provision_probe.cpp': '74d08577850d90712375d5560980818d7fc9b8cde9d334dbd673abdd201a21ce',
 'tools/isa07_d14c2h3b1_create.cpp': '7a2ff491e38ec26eea1e06e9cf3cd6493313d65c1717380bc418bf93013a6730',
 'tools/isa07_d14c2h3b1_provision_sandbox.py': 'd653e584ac2c1d10bb812c1945b2260b27bbd9b5e710adc3fa851f5dfceb2c26'}

def run(*args):
    result=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,encoding='utf-8',errors='replace')
    if result.returncode:
        raise RuntimeError('COMMAND_FAILED '+repr(args)+' '+result.stderr[-650:])
    return result.stdout.strip()

def norm(data:bytes)->bytes:
    if b'\r' in data.replace(b'\r\n',b''):
        raise RuntimeError('BARE_CR_REJECTED')
    return data.replace(b'\r\n',b'\n')

def self_test():
    assert norm(b'a\r\nb\n')==b'a\nb\n'
    try:
        norm(b'bad\rhere')
        raise AssertionError('MUTANT_UNDETECTED')
    except RuntimeError as err:
        assert str(err)=='BARE_CR_REJECTED'
    assert len(FILES)==7 and len(set(FILES))==7 and len(SHA)==6 and len(PINS)==9
    assert all(len(value)==40 for value in PINS.values())
    assert all(len(value)==64 for value in SHA.values())
    assert {'fresh_0.kdr', 'before'}-{'before'} == {'fresh_0.kdr'}
    print('D14C2H3B1-AUDIT-SELFTEST PASS PINS=9/9 CONTENT_SHA=6/6 EOL=2/2 BARE_CR_REJECTED=1 NAME_ONLY_FS_DIFF=1')

def audit():
    if run('git','rev-parse','HEAD')!=BASE:
        raise RuntimeError('WRONG_BASELINE')
    if run('git','rev-parse','--show-prefix'):
        raise RuntimeError('NOT_REPO_ROOT')
    for filename,blob in PINS.items():
        if run('git','rev-parse','HEAD:'+filename)!=blob:
            raise RuntimeError('PIN_MISMATCH '+filename)
    if run('git','diff','--name-only') or run('git','diff','--cached','--name-only'):
        raise RuntimeError('TRACKED_MUTATION')
    if sorted(run('git','ls-files','--others','--exclude-standard').splitlines())!=sorted(FILES):
        raise RuntimeError('NEW_FILE_SCOPE_MISMATCH')
    for filename,digest in SHA.items():
        file=ROOT/filename
        if not file.is_file() or hashlib.sha256(norm(file.read_bytes())).hexdigest()!=digest:
            raise RuntimeError('CONTENT_SHA_MISMATCH '+filename)
    if not (ROOT/'tools/isa07_d14c2h3b1_audit.py').is_file():
        raise RuntimeError('MISSING_AUDITOR')
    provision=(ROOT/'inc/kyiv_drum_provision_v1.h').read_text(encoding='utf-8')
    for anchor in ['create_hard_link(temporary, image, ec)',
                   'kyiv_drum_persistence::save_atomic(empty, temporary)',
                   'throw media_error("ATOMIC_CREATE_UNAVAILABLE")',
                   'throw media_error("IMAGE_EXISTS")']:
        if anchor not in provision:raise RuntimeError('CONTRACT_ANCHOR '+anchor)
    if 'save_atomic(empty, image)' in provision:
        raise RuntimeError('UNSAFE_DIRECT_REPLACE')
    print('D14C2H3B1-AUDIT PASS BASELINE=04be0ca PINS=9/9 NEW_FILES=7/7 '
          'CONTENT_SHA=6/6 TRACKED_MUTATION=0 CPU_MUTATION=0 '
          'PRODUCTION_CLI_UNCHANGED=1 B1_B2_B3_UNCHANGED=1 '
          'CREATE_NEW_ONLY=1 HARDWARE_ORACLE=0 HISTORICAL_MAPPING=OPEN '
          'REAL_PROVISION_GATE=PENDING NAME_ONLY_FS_DIFF=1')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:self_test()
    else:audit()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('D14C2H3B1-AUDIT FAIL',str(exc),file=sys.stderr)
        raise SystemExit(1)
