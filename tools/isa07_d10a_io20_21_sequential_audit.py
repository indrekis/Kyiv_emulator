#!/usr/bin/env python3
"""Exact four-statement IO20/21 PC fix from pinned da84dee CPU Git blob.

All source-byte comparisons normalize CRLF ONLY. D7/D8A old tests remain pinned
as historic, not current-CPU PC oracles.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='da84dee'
CPU_BLOB='757740c7e52adc4ee5e17ed563c989c9496ae96f'
PDF_SHA='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
PINS={
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'tests/isa/isa07_d9b_io25_sequential_probe.cpp':'9fabacc0b0767d9cb594b79824f62a29b8b19171',
 'tools/isa07_d9b_io25_sequential_audit.py':'acd37781c585656ab2d5bac0f3d6ad89faf91caf',
 'docs/ISA_07_D9B_SOURCE_MANIFEST.tsv':'d49b8560b0209d948633f5944f077f763bd8cfcf',
 'tests/isa/isa07_d8a_inclusive_input_probe.cpp':'a47e33601d05ca94fa38f769a78054813a00c1da',
 'docs/ISA_07_D7_DOCUMENTED_IO_BOUNDARIES.md':'debc8a21a73e4a0e2ab965f938b6b46e90f5323b',
}
OLD20=(b'                punch_cards.close();\n'
       b'        }\n'
       b'            break;\n\n'
       b'        case IO_operations_t::opcode_read_perfo_binary:{')
NEW20=OLD20.replace(b'                punch_cards.close();\n',
                    b'                punch_cards.close();\n'
                    b'                ++C_reg;\n'
                    b'                K_reg = kmem.read_memory(C_reg);\n')
OLD21=(b'            h += com_counter;\n'
       b'        }\n'
       b'            break;\n\n'
       b'        case IO_operations_t::opcode_read_magnetic_drum:{')
NEW21=OLD21.replace(b'            h += com_counter;\n',
                    b'            h += com_counter;\n'
                    b'            ++C_reg;\n'
                    b'            K_reg = kmem.read_memory(C_reg);\n')
CASES=('20-range','20-single','20-offset','20-short','20-missing','20-zone1',
       '21-range','21-single','21-offset','21-h1','21-a3','21-missing')
GATES={'D10A_CPU_DELTA','D10A_SOURCE','D10A_IO20','D10A_IO21',
       'D10A_K_PREFETCH','D10A_PC_A3','D10A_MISSING_SHORT','D10A_PREVIOUS',
       'D10A_NUMERIC','D10A_DEVICE'}

def git(*args):
    return subprocess.check_output(('git',)+args,cwd=ROOT,stderr=subprocess.PIPE).strip()

def blob(s):
    return hashlib.sha1(b'blob '+str(len(s)).encode('ascii')+b'\0'+s).hexdigest().encode('ascii')

def need(ok,message):
    if not ok:raise RuntimeError(message)

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.parse_args()
    need(git('cat-file','-t',BASE)==b'commit','pinned D9B baseline missing')
    need(subprocess.run(('git','merge-base','--is-ancestor',BASE,'HEAD'),cwd=ROOT).returncode==0,
         'D9B is not an ancestor of HEAD')
    original=subprocess.check_output(('git','show',BASE+':src/main.cpp'),cwd=ROOT)
    need(git('rev-parse',BASE+':src/main.cpp')==CPU_BLOB.encode(),'baseline CPU blob drift')
    need(blob(original)==CPU_BLOB.encode(),'baseline CPU body/blob drift')
    need(original.count(OLD20)==1,'IO20 original suffix not unique')
    need(original.count(OLD21)==1,'IO21 original suffix not unique')
    expected=original.replace(OLD20,NEW20,1).replace(OLD21,NEW21,1)
    actual=(ROOT/'src/main.cpp').read_bytes().replace(b'\r\n',b'\n')
    need(actual==expected,'CPU changed beyond EXACT FOUR IO20/21 PC and K statements')
    head=git('rev-parse','HEAD:src/main.cpp')
    need(head in (CPU_BLOB.encode(),blob(expected)),'HEAD CPU outside D10A before/after states')
    for rel,pin in PINS.items():
        need(git('rev-parse',BASE+':'+rel)==pin.encode(),'baseline file pin drift: '+rel)
        need(git('rev-parse','HEAD:'+rel)==pin.encode(),'HEAD file pin drift: '+rel)
        need(blob((ROOT/rel).read_bytes().replace(b'\r\n',b'\n'))==pin.encode(),
             'working source file drift: '+rel)
    manifest=(ROOT/'docs/ISA_07_D10A_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_'+BASE+'\t'+CPU_BLOB+'\t' in manifest,
         'CPU pin not in manifest')
    for rel,pin in PINS.items():
        need(rel+'\tGIT_BLOB_AT_'+BASE+'\t'+pin+'\t' in manifest,
             'missing manifest pin: '+rel)
    need(PDF_SHA in manifest and 'printed pp 17 and 58' in manifest,
         'GY62 documentary source pin/page missing')
    gates=(ROOT/'docs/ISA_07_D10A_GATES.tsv').read_text(encoding='utf-8').splitlines()
    got={line.split('\t')[0] for line in gates[1:] if line.strip()}
    need(len(gates)==11 and got==GATES,'gate registry incomplete')
    cpp=(ROOT/'tests/isa/isa07_d10a_io20_21_sequential_probe.cpp').read_text(encoding='utf-8')
    runner=(ROOT/'tools/isa07_d10a_io20_21_sequential_sandbox.py').read_text(encoding='utf-8')
    for mode in CASES:
        need('"'+mode+'"' in cpp and "'"+mode+"'" in runner,'case missing: '+mode)
    for s in ('execute_opcode(); // CPU STEP 1',
              'execute_opcode(); // CPU STEP 2', 'k1==follow','k2==follow',
              'xor_result','m.kmem.write_memory(0120'):
        need(s in cpp,'no two-step PC/K/XOR witness: '+s)
    need('TemporaryDirectory' in runner and 'OBS.findall' in runner,
         'missing isolated two-step runner')
    report=(ROOT/'docs/ISA_07_D10A_IO20_21_SEQUENTIAL_CONTROL.md').read_text(encoding='utf-8')
    for s in ('GY62','printed p. 58','SOURCE_STRICT','HOST_POLICY',
              'OPEN','K_reg','numeric conversion','D7','40 fractional bits'):
        need(s in report,'missing source/policy clarification: '+s)
    print('ISA-07 D10-A: GY62 P58 EXPLICIT IO20/21 SEQUENTIAL CONTROL; NUMERIC PARSING UNCHANGED')
    print('IO20-21-SEQUENTIAL-CHECK PASS base=da84dee exact_cpu_delta=FOUR_STATEMENTS '
          '20=C_PLUS_ONE_K_PREFETCH 21=C_PLUS_ONE_K_PREFETCH '
          'D7_PC_OPEN=RESOLVED_BY_NEW_P58_SOURCE D8A_INTERVALS=PRESERVED '
          'D9A_D9B=PRESERVED unchanged_files=6 source_blobs=PINNED '
          'DECIMAL_FIXED_POINT=OPEN HOST_DEVICE_ORACLES=0')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as ex:
        print('IO20-21-SEQUENTIAL-CHECK FAIL:',ex,file=sys.stderr);sys.exit(1)
