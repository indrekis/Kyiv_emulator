#!/usr/bin/env python3
"""ISA-07 D4: exact two-line C++ flag-initializer repair, no device oracle."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='75312d0'
CPU_BLOB='bbbed3293ee362dbd995ea61bf96f67f4638f894'
UNCHANGED={
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'tests/isa/isa07_d2_io_characterization_probe.cpp':'95b71b0f01d4befacc886afdef11c506327dfea8',
 'tools/isa07_d3_io22_fix_audit.py':'3986203975d284773b573058a11d95f87617b740',
 'tools/isa07_d3_io22_sandbox.py':'e337a5a212f29e991d4aab3f074c8aa8ae5f2ac1',
}
BEFORE_20=b'                bool flag;\n\n                while (punch_cards) {'
AFTER_20=b'                bool flag = false;\n\n                while (punch_cards) {'
BEFORE_24=b'            bool flag;\n            while (magnetic_drum) {'
AFTER_24=b'            bool flag = false;\n            while (magnetic_drum) {'

def git(*args):
 p=subprocess.run(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode:
  raise RuntimeError('git '+ ' '.join(args)+' failed: '+p.stderr.decode(errors='replace').strip())
 return p.stdout

def normalized(path):
 return (ROOT/path).read_bytes().replace(b'\r\n',b'\n')

def check():
 assert git('rev-parse',f'{BASE}:src/main.cpp').decode().strip()==CPU_BLOB,'committed D3 CPU base Git blob mismatch'
 old=git('show',f'{BASE}:src/main.cpp').replace(b'\r\n',b'\n')
 assert old.count(BEFORE_20)==1 and old.count(BEFORE_24)==1,'original flags not uniquely located'
 expected=old.replace(BEFORE_20,AFTER_20,1).replace(BEFORE_24,AFTER_24,1)
 actual=normalized('src/main.cpp')
 assert actual==expected,'current CPU differs from exactly TWO flag=false initializers on D3 baseline'
 assert actual.count(AFTER_20)==1 and actual.count(AFTER_24)==1,'expected initialized input flags specifically in opcodes 20 and 24'
 for path,sha in UNCHANGED.items():
  assert git('rev-parse',f'{BASE}:{path}').decode().strip()==sha,'baseline Git pin mismatch: '+path
  assert normalized(path)==git('show',f'{BASE}:{path}').replace(b'\r\n',b'\n'),'uncommitted source drift: '+path
 ledger=ROOT/'docs/ISA_07_D4_GATES.tsv'
 with ledger.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f,delimiter='\t'))
 expected_gates={
  'D4_CPU_DELTA':'CODE_FIX', 'D4_INPUT_FULL':'CODE_FIX',
  'D4_INPUT_SHORT20':'CODE_FIX', 'D4_INPUT_SHORT24':'HOST_INPUT_OPEN',
  'D4_INPUT_EMPTY':'HOST_INPUT_OPEN', 'D4_INPUT_MISSING':'CODE_OBS',
  'D4_PC':'OPEN', 'D4_PREVIOUS':'HISTORICAL_BASELINE',
 }
 assert len(rows)==len(expected_gates) and {r['gate']:r['classification'] for r in rows}==expected_gates,'unexpected D4 gates or misclassified EOF handling'
 assert (ROOT/'docs/ISA_07_D4_FLAG_INIT.md').is_file() and (ROOT/'docs/ISA_07_D4_SOURCE_MANIFEST.tsv').is_file(),'D4 docs missing'
 print('ISA-07 D4: INITIALIZE UNDEFINED FLAGS FOR IO20/24; NO HISTORICAL DEVICE ORACLE')
 print('IO-FLAG-CHECK PASS base=75312d0 exact_cpu_delta=TWO_FLAG_FALSE 20=FIXED 24=FIXED D3_BREAK=PRESERVED unchanged_files=4 source_blobs=PINNED historical_io_oracles=0 PC_20_24=UNCHANGED')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
 if not args.check:p.error('specify --check')
 try:check()
 except Exception as exc:print('IO-FLAG-CHECK FAIL:',exc,file=sys.stderr);sys.exit(1)
