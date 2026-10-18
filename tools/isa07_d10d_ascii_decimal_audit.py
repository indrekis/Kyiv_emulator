#!/usr/bin/env python3
"""ISA-07 D10-D: pin old Git blob sources; verify standalone HOST_POLICY only."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='46cfb2f'
CPU_BLOB='bc9331b178333d2e3ef32789972bc16bc70c39ea'
PINS={
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'docs/ISA_07_D10C_EXACT_BCD_CONVERTER.md':'81cd5a19fdd240732e888570cee84f140d476a92',
 'docs/ISA_07_D10C_SOURCE_MANIFEST.tsv':'b28bcd7602b783bb5af34cdb24d94c62c0b16ea1',
 'tools/isa07_d10c_exact_converter_audit.py':'364778abb6e79810dc42997f36e4d599a6e92689',
 'tests/isa/isa07_d10c_exact_converter_probe.cpp':'f1afb6e789c24fec1de62de92dcfaef7a23bd693',
 'tools/isa07_d10b_numeric_vectors.py':'fdf2a51557805e601cbfe75454e0e7c81b75ae03',
 'docs/ISA_07_D10B_DECIMAL_INPUT_SOURCE_QUALIFICATION.md':'6e114872533f3e4903fd4242ce09f06d25334c4a',
}
PDF_SHA={
 'GY62_1962_PDF':'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea',
 'DPS64_1964_SCAN_PDF':'ee263a70393e500f039296535ef1e1742fd279f92bb8d6747efeef0239dd90c5',
}
NEW=(
 'inc/kyiv_decimal_ascii.h',
 'tests/isa/isa07_d10d_ascii_decimal_probe.cpp',
 'tools/isa07_d10d_ascii_decimal_sandbox.py',
 'tools/isa07_d10d_ascii_decimal_audit.py',
 'docs/ISA_07_D10D_ASCII_HOST_POLICY.md',
 'docs/ISA_07_D10D_SOURCE_MANIFEST.tsv',
 'docs/ISA_07_D10D_GATES.tsv',
)
GATES={'D10D_CPU_IMMUTABLE','D10D_PRIOR_SOURCES','D10D_GY62_DPS64',
       'D10D_ASCII_GRAMMAR','D10D_EXACT_BRIDGE','D10D_SIGN_ZERO',
       'D10D_REJECT','D10D_RECORD_ATOMIC','D10D_SWEEP','D10D_OPEN'}

def git(*args):
    return subprocess.check_output(('git',)+args,cwd=ROOT,stderr=subprocess.PIPE).strip()

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest().encode('ascii')

def need(condition,message):
    if not condition:raise RuntimeError(message)

def normalized(rel):
    return (ROOT/rel).read_bytes().replace(b'\r\n',b'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.parse_args()
    need(git('cat-file','-t',BASE)==b'commit','D10C commit missing')
    need(subprocess.run(('git','merge-base','--is-ancestor',BASE,'HEAD'),cwd=ROOT).returncode==0,
         'D10C baseline not ancestor of HEAD')
    original=subprocess.check_output(('git','show',BASE+':src/main.cpp'),cwd=ROOT)
    need(git('rev-parse',BASE+':src/main.cpp')==CPU_BLOB.encode(), 'base CPU blob drift')
    need(blob(original)==CPU_BLOB.encode(),'base CPU body drift')
    need(git('rev-parse','HEAD:src/main.cpp')==CPU_BLOB.encode(),'HEAD CPU mutation')
    need(normalized('src/main.cpp')==original,'working CPU mutation')
    manifest=(ROOT/'docs/ISA_07_D10D_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_'+BASE+'\t'+CPU_BLOB+'\t' in manifest,
         'CPU missing from source manifest')
    for rel,pin in PINS.items():
        need(git('rev-parse',BASE+':'+rel)==pin.encode(), 'base source drift: '+rel)
        need(git('rev-parse','HEAD:'+rel)==pin.encode(), 'HEAD source drift: '+rel)
        need(blob(normalized(rel))==pin.encode(),'working source drift: '+rel)
        need(rel+'\tGIT_BLOB_AT_'+BASE+'\t'+pin+'\t' in manifest,
             'pin missing in source manifest: '+rel)
    for rel,pin in PDF_SHA.items():
        need(rel+'\tSHA256\t'+pin+'\t' in manifest,'PDF digest absent: '+rel)
    for rel in NEW:
        need((ROOT/rel).is_file(),'new file missing: '+rel)
        # Once committed, HEAD must contain the same bytes. Before commit the
        # new path does not exist in HEAD; this is an explicitly permitted stage.
        proc=subprocess.run(('git','rev-parse','--verify','HEAD:'+rel),cwd=ROOT,
                            capture_output=True,text=True)
        if proc.returncode==0:
            need(proc.stdout.strip().encode()==blob(normalized(rel)),
                 'committed new file drift: '+rel)
    gates=(ROOT/'docs/ISA_07_D10D_GATES.tsv').read_text(encoding='utf-8').splitlines()
    need(len(gates)==11 and {line.split('\t')[0] for line in gates[1:]}==GATES,
         'D10D gates mismatch')
    header=(ROOT/'inc/kyiv_decimal_ascii.h').read_text(encoding='utf-8')
    probe=(ROOT/'tests/isa/isa07_d10d_ascii_decimal_probe.cpp').read_text(encoding='utf-8')
    runner=(ROOT/'tools/isa07_d10d_ascii_decimal_sandbox.py').read_text(encoding='utf-8')
    report=(ROOT/'docs/ISA_07_D10D_ASCII_HOST_POLICY.md').read_text(encoding='utf-8')
    for token in ('parse_token(', 'parse_record(', 'convert_bcd10(packed, negative)',
                  "record[i] == ' '", "record[i] == '\\t'", 'status::nonexact',
                  'return {record_status::invalid_token, {}}',
                  'return {record_status::nonexact, {}}'):
        need(token in header,'missing HOST parser semantics: '+token)
    need('4096' in probe and 'HOST_POLICY=1' in probe and
         '#include "kyiv_decimal_ascii.h"' in probe,
         'standalone C++ witness missing')
    # Non-ASCII grammar rejection must be tested INSIDE C++, not through argv:
    # MinGW/Windows command-line conversion can transliterate U+FF10 to '0'.
    need('std::string("\\xEF\\xBC\\x90")' in probe and
         'std::string(argv[1]) == "--nonascii"' in probe and
         "cmd_args = ['--nonascii'] if label == 'not-ascii' else [token]" in runner,
         'non-ASCII test must bypass locale-dependent Windows argv transcoding')
    need('Fraction' in runner and 'SOURCE = (' in runner and
         'TOKEN_LINE' in runner and 'RECORD_LINE' in runner and
         'RECORDS = (' in runner and '4096/4096' in runner and
         'subprocess.TimeoutExpired' in runner,
         'independent host runner missing')
    for token in ('HOST_POLICY','SOURCE_STRICT','GY62','DPS64',
                  'ASCII', '4096', 'all-or-nothing', 'OPEN',
                  'NO modifications','not wired into IO20'):
        need(token in report,'documentation missing qualifier: '+token)
    need('#include "kyiv_decimal_ascii.h"' not in normalized('src/main.cpp').decode('utf-8'),
         'IO20 erroneously integrated in standalone stage')
    print('ISA-07 D10-D: STANDALONE ASCII TEN-DIGIT FRACTION HOST_POLICY; CPU READ-ONLY')
    print('IO20-ASCII-POLICY-CHECK PASS base=46cfb2f CPU_BLOB=PINNED CPU_MUTATION=0 '
          'D10C_CONVERTER=PINNED unchanged_sources=8 GY62_SHA=PINNED DPS64_SHA=PINNED '
          'ASCII_FORMS=COMPACT_OR_ZERO_DOT TEN_DIGITS=STRICT SP_TAB_RECORD=ATOMIC '
          'EXACT_GRID=4096 IO20_INTEGRATION=NOT_DONE ROUNDING=OPEN DEVICE_ORACLES=0')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as e:
        print('IO20-ASCII-POLICY-CHECK FAIL:',e,file=sys.stderr);sys.exit(1)
