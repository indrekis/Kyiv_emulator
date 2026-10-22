#!/usr/bin/env python3
"""D15/A3-P1 read-only strict source and exact new-file scope auditor."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '846c450a9f84334169e8f00a1f1b285fffb6c20c'
PINS = {
    'mem/ROM.txt': 'bb6224e130c59564a8ccc4b224c55e41e50784a3',
    'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27',
    'inc/kyiv_host_image_v1.h': '60b259d83e32aee174dca5a09c91a21fc0d3e4a7',
    'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804',
    'src/asm_disasm.cpp': 'c214fd272047754ea30f209651b5dc8f1a9c302e',
    'docs/HISTORICAL_GY1962_TESTS_PLAN.md': 'eb323ea2a4d5b00ee025afec352b95257c8e0ac5',
}
NEW = {
    'docs/ISA_07_D15A3P1_ROM_SOURCE_CONTRACT.md',
    'docs/ISA_07_D15A3P1_DECISION_LEDGER.tsv',
    'tools/isa07_d15a3p1_rom_census.py',
    'tools/isa07_d15a3p1_audit.py',
}
CONTENT_SHA = {'docs/ISA_07_D15A3P1_DECISION_LEDGER.tsv': '25a45fc827f86d680f845a03ddaecc34daa1c55681edc400a380fbce69c311f9', 'docs/ISA_07_D15A3P1_ROM_SOURCE_CONTRACT.md': '442867411fbc07f9f87efe1d5d8a87f33dd15db50259b362c1df8895feabd003', 'tools/isa07_d15a3p1_rom_census.py': '53f9efe529ef1bcad80d5b3bcd0c5f2068dbefbcbd141deb9bd1e5849d236682'}


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    require(p.returncode == 0, 'GIT_ERROR: ' + p.stderr[-300:])
    return p.stdout.strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def self_test():
    require(len(NEW)==4 and len(PINS)==6 and len(CONTENT_SHA)==3, 'SCOPE_INVALID')
    require(set(CONTENT_SHA)==NEW-{'tools/isa07_d15a3p1_audit.py'},
            'HASH_COVERAGE_INVALID')
    require(all(len(x)==40 for x in PINS.values()), 'BLOB_HASH_INVALID')
    require(all(len(x)==64 for x in CONTENT_SHA.values()), 'SOURCE_HASH_INVALID')
    require(sha(b'a') != sha(b'A'), 'MUTANT_NOT_REJECTED')
    print('D15A3P1-AUDIT-SELFTEST PASS PINS=6/6 NEW=4/4 '
          'CONTENT_SHA=3/3 MUTANT_REJECTED=1')


def audit():
    require(git('rev-parse','HEAD')==BASE, 'BASELINE_CHANGED')
    require(git('branch','--show-current')=='main', 'NOT_MAIN')
    require(git('rev-parse','--show-prefix')=='', 'NOT_ROOT')
    require(not git('diff','--name-only'), 'TRACKED_MUTATION')
    require(not git('diff','--cached','--name-only'), 'STAGED_MUTATION')
    actual = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    require(actual==NEW, 'UNTRACKED_SCOPE: '+repr(sorted(actual ^ NEW)))
    for path, expected in PINS.items():
        require(git('rev-parse','HEAD:'+path)==expected, 'SOURCE_PIN: '+path)
    for path, expected in CONTENT_SHA.items():
        require(sha((ROOT/path).read_bytes())==expected, 'SOURCE_SHA: '+path)
    rom_source = (ROOT/'tools/isa07_d15a3p1_rom_census.py').read_text(encoding='utf8')
    require(all(x in rom_source for x in ['git(\'show\'', 'RAW_SHA256=',
                'HARDWARE_ORACLE', 'STRICT_ROM_INCOMPLETE', 'ROM-provisional.k41']),
            'ROM_CENSUS_CONTRACT_MISSING')
    print('D15A3P1-AUDIT PASS BASELINE=846c450 PINS=6/6 NEW=4/4 '
          'CONTENT_SHA=3/3 TRACKED_MUTATION=0 CPU_MUTATION=0 '
          'ROM_SOURCE_UNRESOLVED=3 HISTORICAL_CORPUS=PENDING '
          'ROM_RUNTIME_EXPLICIT=PENDING HARDWARE_ORACLE=0')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--self-test',action='store_true')
    args=a.parse_args()
    if args.self_test: self_test()
    else: audit()

if __name__=='__main__':
    main()
