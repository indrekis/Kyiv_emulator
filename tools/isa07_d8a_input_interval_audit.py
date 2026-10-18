#!/usr/bin/env python3
"""D8-A exact CPU delta gate: 4 == to > and 2 < to <= in 20/21/24.

Normalize CRLF only; do NOT .strip() Git contents (historical D3 H1 issue).
D7 read-only baseline remains pinned after fixing its observed mismatches.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '6abccb5'
CPU_BLOB = 'eef2d92ce5c39205960aa64bc8839d924730d882'
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d7_io_documented_boundaries_probe.cpp': '7f246d2900a2b29eae6ba5ba618c7e55c90fa3c3',
    'tools/isa07_d7_documented_io_audit.py': '98449eb7e0c9078e586ea66c146fe66329b496e0',
    'docs/ISA_07_D7_SOURCE_MANIFEST.tsv': '567e8bb096290c78eb2ce046df847f988a8faf9a',
    'docs/ISA_07_D7_GATES.tsv': 'd9ac44f902a3be6130cbdb0cb3ed6f75e1a60bd8',
}
SUBS = (
    (b'if(num_counter == addr3_shifted.source_2 - addr3_shifted.source_1){',
     b'if(num_counter > addr3_shifted.source_2 - addr3_shifted.source_1){', 4),
    (b'if(com_counter < addr3_shifted.source_2 - addr3_shifted.source_1){',
     b'if(com_counter <= addr3_shifted.source_2 - addr3_shifted.source_1){', 2),
)

def git(*args):
    return subprocess.check_output(('git',)+args,cwd=ROOT,stderr=subprocess.PIPE).strip()

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest().encode()

def need(pred, message):
    if not pred: raise RuntimeError(message)

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.parse_args()
    need(git('cat-file','-t',BASE)==b'commit','D7 base commit missing')
    need(subprocess.run(('git','merge-base','--is-ancestor',BASE,'HEAD'),cwd=ROOT).returncode==0,
         'D7 base not ancestor of HEAD')
    need(git('rev-parse',BASE+':src/main.cpp')==CPU_BLOB.encode(), 'Original CPU Git blob drift')
    original=subprocess.check_output(('git','show',BASE+':src/main.cpp'),cwd=ROOT)
    need(blob(original)==CPU_BLOB.encode(),'D7 CPU body/blob drift')
    expected=original
    for old,new,n in SUBS:
        need(expected.count(old)==n,f'D7 CPU count for {old.decode()} was not {n}')
        expected=expected.replace(old,new)
    need(expected!=original,'CPU modification missing')
    actual=(ROOT/'src/main.cpp').read_bytes().replace(b'\r\n',b'\n')
    need(actual==expected,'Unexpected CPU drift: expected EXACTLY 6 comparisons changed')
    new_blob=blob(expected)
    head_blob=git('rev-parse','HEAD:src/main.cpp')
    need(head_blob in (CPU_BLOB.encode(),new_blob),'HEAD CPU blob neither before nor after D8-A')
    for rel,pin in PINS.items():
        need(git('rev-parse',BASE+':'+rel)==pin.encode(),f'Baseline Git blob drift: {rel}')
        need(git('rev-parse','HEAD:'+rel)==pin.encode(),f'HEAD Git blob drift: {rel}')
        raw=(ROOT/rel).read_bytes().replace(b'\r\n',b'\n')
        need(blob(raw)==pin.encode(),f'Working source drift: {rel}')
    manifest=(ROOT/'docs/ISA_07_D8A_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_6abccb5\t'+CPU_BLOB+'\t' in manifest,
         'CPU source manifest mismatch')
    for rel,pin in PINS.items():
        need(rel+'\tGIT_BLOB_AT_6abccb5\t'+pin+'\t' in manifest,
             'Source manifest mismatch: '+rel)
    gates=(ROOT/'docs/ISA_07_D8A_GATES.tsv').read_text(encoding='utf-8').splitlines()
    labels={row.split('\t')[0] for row in gates[1:] if row.strip()}
    need(len(gates)==9 and len(labels)==8,'Expected exactly 8 independent gates')
    need(labels=={'D8A_CPU_DELTA','D8A_RANGE20','D8A_RANGE21','D8A_RANGE24',
                  'D8A_SINGLE','D8A_OFFSET','D8A_REVERSED','D8A_PREVIOUS'},
         'Missing/misnamed D8A gate')
    cpp=(ROOT/'tests/isa/isa07_d8a_inclusive_input_probe.cpp').read_text(encoding='utf-8')
    runner=(ROOT/'tools/isa07_d8a_input_interval_sandbox.py').read_text(encoding='utf-8')
    for mode in ('20-range','20-single','20-offset','20-short',
                 '21-range','21-single','21-offset','21-h1',
                 '24-range','24-single','24-offset','24-short'):
        need(mode in cpp and mode in runner,f'D8-A test case missing {mode}')
    need('ONE_STEP_ONLY' in cpp and 'TemporaryDirectory' in runner,
         'Missing step isolation gate')
    report=(ROOT/'docs/ISA_07_D8A_INCLUSIVE_INPUT_INTERVALS.md').read_text(encoding='utf-8')
    need('GY62' in report and 'a₁…a₂' in report and 'reversed' in report,
         'Source or open limitation omitted in report')
    print('ISA-07 D8-A: GY62 INCLUSIVE IO20/21/24 INPUT INTERVALS; NO DEVICE MODEL')
    print('IO-INTERVAL-CHECK PASS base=6abccb5 exact_cpu_delta=SIX_COMPARISONS '
          '20=2_GUARDS 21=2_GUARDS 24=2_GUARDS D7_PRE_FIX=HISTORICAL '
          'unchanged_files=5 source_blobs=PINNED PC_20_21_24=UNCHANGED '
          'REVERSED_INTERVAL=OPEN HISTORICAL_DEVICE_ORACLES=0')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as err:
        print('IO-INTERVAL-CHECK FAIL:',err,file=sys.stderr);sys.exit(1)
