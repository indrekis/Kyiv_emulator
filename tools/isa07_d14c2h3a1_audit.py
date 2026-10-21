#!/usr/bin/env python3
"""D14-C2-H3/A1 read-only content+Git pin audit. Not a hardware oracle."""
import argparse, hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='540d55dfb00a1f94271ccd91f89180d697b63797'
FILES=['docs/ISA_07_D14C2H3A1_DECISION_LEDGER.tsv', 'docs/ISA_07_D14C2H3A1_EXPLICIT_CLI_SUFFIX_CONTRACT.md', 'inc/kyiv_drum_cli_v1.h', 'tests/isa/isa07_d14c2h3a1_cli_probe.cpp', 'tools/isa07_d14c2h3a1_audit.py', 'tools/isa07_d14c2h3a1_cli_sandbox.py']
PINS={'src/asm_disasm.cpp': '8be2c86a55f37459667a6678f5f1e99e886bee0a', 'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804', 'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27', 'inc/kyiv_drum_logical_media.h': '910911f7181bfb455e334b1f66fd00ee94ef1e97', 'inc/kyiv_drum_transaction_v1.h': '1aab83a4735280df0cf4331191c5521dcc5ddcb4', 'inc/kyiv_drum_host_address_v1.h': '74b75b9c4fd86d73b43eb108bbdce312dc9619d3'}
SHA={'docs/ISA_07_D14C2H3A1_DECISION_LEDGER.tsv': '009c4cfbe22f5b13dc041b729de32ede776f6ae195d9645d4651b78c73405b30', 'docs/ISA_07_D14C2H3A1_EXPLICIT_CLI_SUFFIX_CONTRACT.md': '7e9235c52962441ddccf4d1edb48e47b6292ba73feacefa7a6bcbc17a9d838c8', 'inc/kyiv_drum_cli_v1.h': '6bfd2e79f593cb3a2e9fc39371d32f2bee14ee0ffcd764bed89ce66187877b64', 'tests/isa/isa07_d14c2h3a1_cli_probe.cpp': '320657292e857c049d3f27fbdd2e5392633974eb7e09af430fa37b02db8d91ad', 'tools/isa07_d14c2h3a1_cli_sandbox.py': '25f8f120dcae7e8d93f3177a9317d564ea749c95bd510b03c0229ccb41bddfd6'}

def run(*args):
    result=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,encoding='utf-8',errors='replace')
    if result.returncode:
        raise RuntimeError('COMMAND_FAILED '+repr(args)+' '+result.stderr[-600:])
    return result.stdout.strip()

def normalized(b):
    if b'\r' in b.replace(b'\r\n',b''):
        raise RuntimeError('BARE_CR_REJECTED')
    return b.replace(b'\r\n',b'\n')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test:
        assert normalized(b'A\r\nB\n') == b'A\nB\n'
        try: normalized(b'A\rB'); raise AssertionError('BARE_CR_MUTANT')
        except RuntimeError as e: assert str(e)=='BARE_CR_REJECTED'
        assert len(FILES)==6 and len(SHA)==5 and len(PINS)==6
        print('D14C2H3A1-AUDIT-SELFTEST PASS PINS=6/6 CONTENT_SHA=5/5 EOL=2/2 BARE_CR_REJECTED=1')
    if run('git','rev-parse','HEAD')!=BASE: raise RuntimeError('WRONG_BASELINE')
    if run('git','rev-parse','--show-prefix')!='': raise RuntimeError('RUN_FROM_REPO_ROOT')
    for path,sha in PINS.items():
        if run('git','rev-parse','HEAD:'+path)!=sha:
            raise RuntimeError('PIN_MISMATCH '+path)
    if run('git','diff','--name-only') or run('git','diff','--cached','--name-only'):
        raise RuntimeError('TRACKED_MUTATION')
    if sorted(run('git','ls-files','--others','--exclude-standard').splitlines())!=sorted(FILES):
        raise RuntimeError('UNTRACKED_SCOPE_MISMATCH')
    for path,sha in SHA.items():
        p=ROOT/path
        if not p.is_file() or hashlib.sha256(normalized(p.read_bytes())).hexdigest()!=sha:
            raise RuntimeError('CONTENT_SHA '+path)
    if not (ROOT/FILES[4]).is_file():raise RuntimeError('MISSING_AUDITOR')
    parser=(ROOT/'inc/kyiv_drum_cli_v1.h').read_text(encoding='utf-8')
    for anchor in ['--experimental-drum','--block-overflow-stop','kyiv_drum_media::logical_media validation','CLI_INCOMPLETE_EXPERIMENTAL_DRUM']:
        if anchor not in parser:raise RuntimeError('PARSER_ANCHOR '+anchor)
    for prohibited in ['attach_experimental_drum(', 'save_atomic(', 'std::ifstream', 'std::ofstream']:
        if prohibited in parser:raise RuntimeError('PARSER_SIDE_EFFECT')
    print('D14C2H3A1-AUDIT PASS BASELINE=540d55d PINS=6/6 NEW_FILES=6/6 CONTENT_SHA=5/5 TRACKED_MUTATION=0 CPU_MUTATION=0 PRODUCTION_ENTRY_UNCHANGED=1 FILE_CREATION=0 HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')
if __name__=='__main__':
    try: main()
    except Exception as e:
        print('D14C2H3A1-AUDIT FAIL',str(e),file=sys.stderr)
        raise SystemExit(1)
