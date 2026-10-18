#!/usr/bin/env python3
"""ISA-07 D9-B exact two-line IO25 PC+K delta with baseline Git blob pins."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='5ee37f7'
CPU_BLOB='f63736d0f7b9b55d07fe7c077cb4ff56b4b9f21a'
PDF_SHA='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
PINS={
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'tests/isa/isa07_d9a_io24_branch_probe.cpp':'260f0bdfc6ad90af7e600c294e40d53ae641d57f',
 'tools/isa07_d9a_io24_branch_audit.py':'0c9cdc4bd41d0d207c6cfc62d917a8c9ffcfdee0',
 'tools/isa07_d8b_output_interval_sandbox.py':'7d6317c346a58d838bd90b2217225663c84961ca',
 'docs/ISA_07_D9A_IO24_BRANCH_AND_PREFETCH.md':'9c7a9e0f30b507daa3f904afd948d59114a2984d',
}
OLD=(b'        case IO_operations_t::opcode_init_magnetic_drum:{\n'
     b'            if (addr3_shifted.source_1 == 0) {\n'
     b'                drum_num_read = addr3_shifted.source_2;\n'
     b'                drum_zone_read = addr3_shifted.destination;\n'
     b'            } else if (addr3_shifted.source_1 == 1) {\n'
     b'                drum_num_write = addr3_shifted.source_2;\n'
     b'                drum_zone_write = addr3_shifted.destination;\n'
     b'            }\n'
     b'        }\n'
     b'            break;')
NEW=OLD.replace(b'            }\n        }\n',
                b'            }\n            ++C_reg;\n'
                b'            K_reg = kmem.read_memory(C_reg);\n        }\n')
CASES=('write-basic','write-single','write-offset','write-alt',
       'read-basic','read-single','read-trackzone','read-missing')
GATES={'D9B_CPU_DELTA','D9B_NEXT_PC','D9B_K_PREFETCH','D9B_TWO_STEPS',
       'D9B_WRITE','D9B_READ','D9B_DRUM_STATE','D9B_MISSING','D9B_PREVIOUS','D9B_OPEN'}

def git(*args):
    return subprocess.check_output(('git',)+args,cwd=ROOT,stderr=subprocess.PIPE).strip()

def blob(s):
    return hashlib.sha1(b'blob '+str(len(s)).encode('ascii')+b'\0'+s).hexdigest().encode('ascii')

def need(condition,message):
    if not condition:raise RuntimeError(message)

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.parse_args()
    need(git('cat-file','-t',BASE)==b'commit','D9-A pinned base unavailable')
    need(subprocess.run(('git','merge-base','--is-ancestor',BASE,'HEAD'),cwd=ROOT).returncode==0,
         'D9-A base not ancestor of HEAD')
    original=subprocess.check_output(('git','show',BASE+':src/main.cpp'),cwd=ROOT)
    need(git('rev-parse',BASE+':src/main.cpp')==CPU_BLOB.encode(),'D9-A original CPU blob drift')
    need(blob(original)==CPU_BLOB.encode(),'D9-A CPU content/blob mismatch')
    need(original.count(OLD)==1,'expected precisely one IO25 body')
    need(NEW != OLD and NEW.count(b'            ++C_reg;')==1,'bad D9B transformation')
    expected=original.replace(OLD,NEW,1)
    actual=(ROOT/'src/main.cpp').read_bytes().replace(b'\r\n',b'\n')
    need(actual==expected,'CPU drift: D9B may add ONLY two IO25 PC/K statements')
    need(git('rev-parse','HEAD:src/main.cpp') in (CPU_BLOB.encode(),blob(expected)),
         'HEAD CPU not before or after the exact D9B patch')
    for rel,pin in PINS.items():
        enc=pin.encode('ascii')
        need(git('rev-parse',BASE+':'+rel)==enc,'D9-A pin drift: '+rel)
        need(git('rev-parse','HEAD:'+rel)==enc,'HEAD source pin drift: '+rel)
        raw=(ROOT/rel).read_bytes().replace(b'\r\n',b'\n')
        need(blob(raw)==enc,'working source pin drift: '+rel)
    manifest=(ROOT/'docs/ISA_07_D9B_SOURCE_MANIFEST.tsv').read_text(encoding='utf-8')
    need('src/main.cpp\tGIT_BLOB_AT_'+BASE+'\t'+CPU_BLOB+'\t' in manifest,
         'CPU missing from manifest')
    for rel,pin in PINS.items():
        need(rel+'\tGIT_BLOB_AT_'+BASE+'\t'+pin+'\t' in manifest,
             'source missing from manifest: '+rel)
    need(PDF_SHA in manifest,'GY62 SHA not recorded')
    gates=(ROOT/'docs/ISA_07_D9B_GATES.tsv').read_text(encoding='utf-8').splitlines()
    labels={l.split('\t')[0] for l in gates[1:] if l.strip()}
    need(len(gates)==11 and labels==GATES,'D9B gate registry mismatch')
    cpp=(ROOT/'tests/isa/isa07_d9b_io25_sequential_probe.cpp').read_text(encoding='utf-8')
    run=(ROOT/'tools/isa07_d9b_io25_sequential_sandbox.py').read_text(encoding='utf-8')
    for case in CASES:
        need('"'+case+'"' in cpp and "'"+case+"'" in run,
             'missing two-step case: '+case)
    for s in ('execute_opcode(); // CPU STEP 1','execute_opcode(); // CPU STEP 2',
              'pc+1, next_command','k1 == next_command','k2 == target_command',
              'memory_unchanged1'):
        need(s in cpp,'missing two-step witness: '+s)
    need('TemporaryDirectory' in run and 'OBS.findall' in run and
         'out_file.is_file()' in run and 'wrong_file.exists()' in run,
         'runner lacks isolation/output gates')
    report=(ROOT/'docs/ISA_07_D9B_IO25_SEQUENTIAL_AND_PREFETCH.md').read_text(encoding='utf-8')
    for token in ('GY62','SOURCE_STRICT','OPEN','HOST_POLICY','K_reg','IO25','two-step'):
        need(token in report,'report missing qualifier: '+token)
    print('ISA-07 D9-B: GY62 IO25 SEQUENTIAL CONTROL TRANSFER; HOST I/O ADAPTER ONLY')
    print('IO25-SEQUENTIAL-CHECK PASS base=5ee37f7 exact_cpu_delta=TWO_LINES '
          '25=C_PLUS_ONE 25=K_PREFETCH IO23_24=NEXT_OPCODE '
          'D9A_BRANCH24=PRESERVED D8B_OUTPUTS=PRESERVED unchanged_files=5 '
          'source_blobs=PINNED IO20_21_PC=OPEN INVALID_NEXT=OPEN '
          'HISTORICAL_DEVICE_ORACLES=0')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as ex:
        print('IO25-SEQUENTIAL-CHECK FAIL:',ex,file=sys.stderr);sys.exit(1)
