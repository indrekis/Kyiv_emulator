#!/usr/bin/env python3
"""D14-C2-H3/A2: exact Git-blob and deterministic production CLI delta audit."""
from __future__ import annotations
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

BASE='d75f38cbbc946545d5feb5e6fddae0cf6759f09e'
TRACKED='src/asm_disasm.cpp'
NEW=(
    'docs/ISA_07_D14C2H3A2_DECISION_LEDGER.tsv',
    'docs/ISA_07_D14C2H3A2_REAL_CLI_ATTACHMENT.md',
    'tools/isa07_d14c2h3a2_audit.py',
    'tools/isa07_d14c2h3a2_cli_sandbox.py',
)
PINS={
    'src/asm_disasm.cpp':'8be2c86a55f37459667a6678f5f1e99e886bee0a',
    'inc/kyiv_drum_cli_v1.h':'3925ec9503b92c614a43f877686a47fc6884a2b6',
    'inc/kyiv.h':'7134240ee47838fb8dca57d12b4d149d4c496e27',
    'src/main.cpp':'79604ea237e090e99f9da980c9b00567ae7bd804',
    'inc/kyiv_drum_transaction_v1.h':'1aab83a4735280df0cf4331191c5521dcc5ddcb4',
    'inc/kyiv_drum_logical_media.h':'910911f7181bfb455e334b1f66fd00ee94ef1e97',
    'CMakeLists.txt':'071d1f534c5d34494ad79d8abaf900216f4bf845',
    'tools/isa07_d14c2h3a1_audit.py':'7d122ac50383f54c697327780d7e53ef42a1d26d',
}
SHA={
    # Filled by the packaging builder, excluding this audit's own bytes.
    'docs/ISA_07_D14C2H3A2_DECISION_LEDGER.tsv':'69bcc0902be0685385409511c44db55f344bf1d4840b60759389b3b80aa3136e',
    'docs/ISA_07_D14C2H3A2_REAL_CLI_ATTACHMENT.md':'a6116cb7bd13140d3fce1888a17001ac26beaee7d7839ec5377075ca2113f9a8',
    'tools/isa07_d14c2h3a2_cli_sandbox.py':'34e5bee8756dffff466a0565df49f9f6fc960565299b7b32aceef6f01db37636',
}

INCLUDE_OLD='#include "asm_disasm.h"\n'
INCLUDE_NEW='#include "asm_disasm.h"\n#include "kyiv_drum_cli_v1.h"\n'
MAIN_OLD='''    // Parse only the optional *last* argument. Preserve all legacy positionals.
    bool block_overflow_stop = (argc > 2 &&
        std::string(argv[argc - 1]) == "--block-overflow-stop");
    if (block_overflow_stop) {
        --argc;
    }
    Kyiv_t machine;
    machine.emergency_stop_blocked = block_overflow_stop;
'''
MAIN_NEW='''    // D14-C2-H3/A2: explicit HOST-only suffix; legacy positionals survive.
    kyiv_drum_cli_v1::parsed_suffix parsed;
    try {
        parsed = kyiv_drum_cli_v1::parse(argc, argv);
    } catch (const std::exception& e) {
        std::cerr << "D14C2H3A2-CLI-ERROR " << e.what() << std::endl;
        return 2;
    }
    argc = parsed.legacy_argc;
    const bool block_overflow_stop = parsed.block_overflow_stop;
    Kyiv_t machine;
    machine.emergency_stop_blocked = block_overflow_stop;
    if (parsed.drum) {
        // Construction fully validates an EXISTING KYIVDRM1 image. No creation,
        // historical geometry selection or fallback to a decimal text file.
        try {
            machine.attach_experimental_drum(
                parsed.drum->existing_image,
                parsed.drum->expected_geometry,
                kyiv_drum_host_address::policy::a3_linear_v1,
                parsed.drum->pinned_drum);
        } catch (const std::exception& e) {
            std::cerr << "D14C2H3A2-ATTACH-ERROR " << e.what() << std::endl;
            return 3;
        }
    }
'''


def norm(b):
    if b'\r' in b.replace(b'\r\n',b''):
        raise RuntimeError('BARE_CR_REJECTED')
    return b.replace(b'\r\n',b'\n')


def once(s, original, updated, name):
    n=s.count(original)
    if n!=1: raise RuntimeError(f'ANCHOR_{name}_COUNT={n}')
    return s.replace(original,updated,1)


def transform(text):
    text=once(text,INCLUDE_OLD,INCLUDE_NEW,'INCLUDE')
    text=once(text,MAIN_OLD,MAIN_NEW,'CLI_BLOCK')
    return text


def git(*args, cwd=None):
    p=subprocess.run(['git',*args],cwd=cwd,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError('GIT_FAILED '+repr(args)+' '+p.stderr.decode('utf8','replace')[-400:])
    return p.stdout


def self_test():
    toy=INCLUDE_OLD+'\n'+MAIN_OLD
    updated=transform(toy)
    assert updated.count('kyiv_drum_cli_v1::parse(argc, argv)')==1
    assert updated.count('attach_experimental_drum')==1
    assert transform(toy).encode()==updated.encode()
    for mutant in (toy.replace(MAIN_OLD,''),toy+MAIN_OLD,toy+INCLUDE_OLD):
        try: transform(mutant)
        except RuntimeError: pass
        else: raise AssertionError('MUTANT_NOT_REJECTED')
    assert norm(b'A\r\nB\n')==b'A\nB\n'
    try: norm(b'A\rB'); raise AssertionError('BARE_CR_MUTANT')
    except RuntimeError as e: assert str(e)=='BARE_CR_REJECTED'
    assert len(NEW)==4 and len(PINS)==8 and len(SHA)==3
    print('D14C2H3A2-AUDIT-SELFTEST PASS ANCHORS=2/2 MUTANTS=3/3 PINS=8/8 EOL=2/2 BARE_CR_REJECTED=1')


def audit(root):
    if git('rev-parse','HEAD',cwd=root).decode().strip()!=BASE:
        raise RuntimeError('WRONG_BASELINE')
    if git('rev-parse','--show-prefix',cwd=root).strip()!=b'':
        raise RuntimeError('RUN_FROM_REPO_ROOT')
    for path,sha in PINS.items():
        if git('rev-parse','HEAD:'+path,cwd=root).decode().strip()!=sha:
            raise RuntimeError('BLOB_PIN_MISMATCH '+path)
    changed=git('diff','--name-only',cwd=root).decode().splitlines()
    if changed!=[TRACKED]: raise RuntimeError('TRACKED_SCOPE '+repr(changed))
    if git('diff','--cached','--name-only',cwd=root).strip():
        raise RuntimeError('STAGED_CHANGES')
    untracked=sorted(git('ls-files','--others','--exclude-standard',cwd=root).decode().splitlines())
    if untracked!=sorted(NEW):
        raise RuntimeError('UNTRACKED_SCOPE '+repr(untracked))
    original=norm(git('show','HEAD:'+TRACKED,cwd=root)).decode('utf8')
    expected=transform(original).encode('utf8')
    actual=norm((root/TRACKED).read_bytes())
    if actual!=expected:
        raise RuntimeError('PRODUCTION_DELTA_NOT_EXACT')
    for path,sha in SHA.items():
        dest=root/path
        if not dest.is_file() or hashlib.sha256(norm(dest.read_bytes())).hexdigest()!=sha:
            raise RuntimeError('CONTENT_SHA '+path)
    for name in NEW:
        if not (root/name).is_file(): raise RuntimeError('MISSING_NEW_FILE '+name)
    # All other sources remain tracked and clean by path gate.
    print('D14C2H3A2-AUDIT PASS BASELINE=d75f38c PINS=8/8 TRACKED=1/1 NEW_FILES=4/4 CONTENT_SHA=3/3 SOURCE_MATCH_EXACT=1/1 CPU_UNCHANGED=1 A1_PARSER_UNCHANGED=1 PRODUCTION_CLI_MUTATION=EXPLICIT REAL_CLI_GATE=PENDING HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    if a.self_test: self_test(); return
    audit(Path.cwd())

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('D14C2H3A2-AUDIT FAIL',str(e),file=sys.stderr)
        raise SystemExit(1)
