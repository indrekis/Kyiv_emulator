#!/usr/bin/env python3
"""D8-B: pin D8-A CPU, require exactly two absolute-address output loops."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '2c4a3da'
CPU_BLOB = '39c49dde7ee48ba73b410826d82495e203ad55cc'
PINS = {
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'tests/isa/isa07_d7_io_documented_boundaries_probe.cpp': '7f246d2900a2b29eae6ba5ba618c7e55c90fa3c3',
    'tools/isa07_d8a_input_interval_audit.py': '89ae9f57b3433a9d395247fd85ab2e7d32435fb2',
    'tools/isa07_d3_io22_sandbox.py': 'e337a5a212f29e991d4aab3f074c8aa8ae5f2ac1',
    'docs/ISA_07_D8A_INCLUSIVE_INPUT_INTERVALS.md': '6c3ffc12b933f91df1fccd9cec812a72c4fd6107',
}
OLD = (b'for(uint64_t i = 0; i <= addr3_shifted.source_2; i++){\n'
       b'                    myfile << word_to_number(kmem.read_memory(addr3_shifted.source_1 + i));')
NEW = (b'for(uint64_t i = addr3_shifted.source_1; i <= addr3_shifted.source_2; i++){\n'
       b'                    myfile << word_to_number(kmem.read_memory(i));')

GATES = {'D8B_CPU_DELTA', 'D8B_22_RANGE', 'D8B_23_RANGE', 'D8B_SINGLE',
         'D8B_OFFSET', 'D8B_D3_NO_FALLTHROUGH', 'D8B_REVERSED', 'D8B_PREVIOUS'}
CASES = tuple(f'{op}-{kind}' for op in ('22','23')
              for kind in ('range','single','offset','legacy','fromzero'))

def git(*args):
    return subprocess.check_output(('git',)+args, cwd=ROOT, stderr=subprocess.PIPE).strip()

def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest().encode('ascii')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.parse_args()
    require(git('cat-file','-t',BASE) == b'commit', 'D8-A baseline commit missing')
    require(subprocess.run(('git','merge-base','--is-ancestor',BASE,'HEAD'),
                           cwd=ROOT).returncode == 0, 'D8-A base not ancestor')
    original = subprocess.check_output(('git','show',BASE+':src/main.cpp'),cwd=ROOT)
    require(git('rev-parse',BASE+':src/main.cpp') == CPU_BLOB.encode(), 'Baseline CPU blob drift')
    require(git_blob(original) == CPU_BLOB.encode(), 'Baseline CPU body/blob drift')
    require(original.count(OLD) == 2, 'Expected exactly two original output loops')
    expected = original.replace(OLD,NEW)
    require(expected != original and expected.count(NEW) == 2, 'CPU loop transformation mismatch')
    current = (ROOT/'src/main.cpp').read_bytes().replace(b'\r\n', b'\n')
    require(current == expected, 'Unexpected CPU drift: exactly two absolute-address loop rewrites required')
    head = git('rev-parse','HEAD:src/main.cpp')
    require(head in (CPU_BLOB.encode(), git_blob(expected)), 'HEAD CPU blob outside D8-B stages')
    for rel,pin in PINS.items():
        pin_b = pin.encode()
        require(git('rev-parse',BASE+':'+rel) == pin_b, 'Base source blob drift: '+rel)
        require(git('rev-parse','HEAD:'+rel) == pin_b, 'HEAD source blob drift: '+rel)
        content = (ROOT/rel).read_bytes().replace(b'\r\n', b'\n')
        require(git_blob(content) == pin_b, 'Working source drift: '+rel)
    manifest = (ROOT/'docs/ISA_07_D8B_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    require('src/main.cpp\tGIT_BLOB_AT_'+BASE+'\t'+CPU_BLOB+'\t' in manifest,
            'CPU manifest pin mismatch')
    for rel,pin in PINS.items():
        require(rel+'\tGIT_BLOB_AT_'+BASE+'\t'+pin+'\t' in manifest,
                'Manifest source mismatch: '+rel)
    require('a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea' in manifest,
            'GY62 document SHA256 missing')
    gates = (ROOT/'docs/ISA_07_D8B_GATES.tsv').read_text(encoding='utf-8').splitlines()
    labels = {line.split('\t')[0] for line in gates[1:] if line.strip()}
    require(len(gates) == 9 and labels == GATES, 'D8-B gates mismatch')
    cpp = (ROOT/'tests/isa/isa07_d8b_absolute_output_probe.cpp').read_text(encoding='utf-8')
    runner = (ROOT/'tools/isa07_d8b_output_interval_sandbox.py').read_text(encoding='utf-8')
    for case in CASES:
        op,kind = case.split('-',1)
        require(op+'-' in cpp and '"'+kind+'"' in cpp and "'"+kind+"'" in runner,
                'Missing output test case: '+case)
    require('ONE_STEP_ONLY' in cpp and 'TemporaryDirectory' in runner and 'forbidden.exists()' in runner,
            'Missing one-step/device separation checks')
    # The output fixture includes immutable RAM cell 0000, not a writable register.
    require('machine.kmem.write_memory(0000, 3);' not in cpp
            and 'Memory cell 0000 is hardwired to zero' in cpp,
            'Invalid attempt to seed hardwired-zero memory cell 0000')
    require("'fromzero': ('0','5','7')" in runner,
            'fromzero output expectation must start with hardwired zero')
    report = (ROOT/'docs/ISA_07_D8B_ABSOLUTE_OUTPUT_INTERVALS.md').read_text(encoding='utf-8')
    for needle in ('Glushkov', 'a₁', 'a₂', 'reversed', 'D3', 'a₃'):
        require(needle in report, 'Missing source/open documentation: '+needle)
    print('ISA-07 D8-B: GY62 ABSOLUTE INCLUSIVE OUTPUT INTERVALS FOR IO22/23; NO DEVICE MODEL')
    print('IO-OUTPUT-INTERVAL-CHECK PASS base=2c4a3da exact_cpu_delta=TWO_OUTPUT_LOOPS '
          '22=ABSOLUTE_END 23=ABSOLUTE_END D3_BREAK=PRESERVED '
          'D8A_INPUTS=PRESERVED unchanged_files=5 source_blobs=PINNED '
          'REVERSED_INTERVAL=OPEN C_REG_22_23=UNCHANGED HISTORICAL_DEVICE_ORACLES=0')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as err:
        print('IO-OUTPUT-INTERVAL-CHECK FAIL:',err,file=sys.stderr)
        sys.exit(1)
