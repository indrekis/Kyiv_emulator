#!/usr/bin/env python3
"""D11-A read-only pinning of CPU plus documentation and risk characterization.

Requires the user to have committed D10-G4 as its six new files.
This auditor intentionally does not assert any historical host text grammar.
"""
from pathlib import Path
import hashlib
import subprocess
import sys

PARENT = '75a401107b03e9fb535d9aaf97b56c85a434293f'
CPU_BLOB = 'e6d00248705668156c29b376b3dd1b26ed40e275'
KYIV_H_BLOB = 'ff4aa592f12b07d32b4961b49cb97b15289d38e0'
G4 = (
 'docs/ISA_07_D10G4_CONTROL_SIGNALS_AND_COEFFICIENT_SOURCE.md',
 'docs/ISA_07_D10G4_SOURCE_DECISION_LEDGER.tsv',
 'docs/ISA_07_D10G4_TABLE5_SIGNAL_MATRIX.tsv',
 'tests/isa/isa07_d10g4_evidence_test.py',
 'tools/isa07_d10g4_audit.py',
 'tools/isa07_d10g4_evidence.py',
)
NEW = (
 'docs/ISA_07_D11A_IO21_CHARACTERIZATION.md',
 'docs/ISA_07_D11A_IO21_CODE_RISK_LEDGER.tsv',
 'tests/isa/isa07_d11a_io21_host_observation_probe.cpp',
 'tools/isa07_d11a_io21_host_sandbox.py',
 'tools/isa07_d11a_audit.py',
)
# Filled during packaging: normalized LF SHA-256 for four non-auditor files.
SHA256 = {
 'docs/ISA_07_D11A_IO21_CHARACTERIZATION.md': '27fa032be44bbc578bf374720d99d1910c8b3dd350fa2f3c8789b7f943e8e655',
 'docs/ISA_07_D11A_IO21_CODE_RISK_LEDGER.tsv': '75891f59462c72deaeb4618a9b39b086abc452059f12dfb5c1c63f2b2096d1f0',
 'tests/isa/isa07_d11a_io21_host_observation_probe.cpp': '2c7bf3a816fafce6f4abc338f9756a44e502532340056261868839dd3885c9e2',
 'tools/isa07_d11a_io21_host_sandbox.py': '34a9584ddcb623888ca9a569fb61e0a9006699d24203ad84b4fbb932e117555f',
}

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE,text=True).strip()

def req(b,msg):
    if not b:raise RuntimeError(msg)

def canonical(path):
    data=Path(path).read_bytes()
    req(b'\r' not in data.replace(b'\r\n',b''), 'bare CR: '+path)
    return data.replace(b'\r\n',b'\n')

def main():
    try:
        req(git('rev-parse','--show-prefix')=='','must run in repository root')
        req(git('rev-parse','HEAD^')==PARENT,'D10-G4 commit parent differs from 75a4011')
        req(tuple(sorted(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()))==tuple(sorted(G4)),
            'D10-G4 commit must contain exactly six new files')
        req(git('rev-parse','HEAD:src/main.cpp')==CPU_BLOB,'CPU committed baseline drift')
        req(git('rev-parse','HEAD:inc/kyiv.h')==KYIV_H_BLOB,'header committed baseline drift')
        req(not git('diff','--name-only') and not git('diff','--cached','--name-only'),
            'unexpected tracked modifications')
        for p in NEW:
            req(Path(p).is_file(),'missing D11-A file '+p)
            req(not git('ls-files','--',p),'D11-A file already tracked: '+p)
            data=canonical(p)
            if p in SHA256:
                req(hashlib.sha256(data).hexdigest()==SHA256[p],
                    'D11-A normalized content digest mismatch: '+p)
        src=Path('src/main.cpp').read_text(encoding='utf-8')
        a=src.index('case IO_operations_t::opcode_read_perfo_binary:')
        b=src.index('case IO_operations_t::opcode_read_magnetic_drum:',a)
        io=src[a:b]
        for term in ('../punched_tape.txt','../heads.txt','std::stol(line, 0, 8)',
                     'while(punch_cards)','kmem.write_memory(',
                     '++counter;','h += com_counter;','++C_reg;','K_reg = kmem.read_memory(C_reg);'):
            req(term in io,'current IO21 source shape changed: '+term)
        d=canonical(NEW[0]).decode('utf-8')
        for term in ('GY62','printed p. 58','41 bits','SOURCE','HOST_POLICY','D11-B','D11-C'):
            req(term.casefold() in d.casefold(),'D11-A documentary contract missing: '+term)
        ledger=canonical(NEW[1]).decode('utf-8')
        for name in ('D11A-S01','D11A-S03','D11A-C01','D11A-C07','D11A-U01'):
            req(name in ledger,'risk ledger entry missing: '+name)
        print('D11A-AUDIT PASS PARENT=75a4011 G4_FILES=6/6 CPU_PIN=1 KYIV_H_PIN=1 '
              'NEW_FILES=5/5 NEW_CONTENT_SHA=4/4 HOST_RISK_LEDGER=1 '
              'CPU_MUTATION=0 IO21_SOURCE_ONLY=1 HARDWARE_ORACLE=0')
        return 0
    except (OSError,RuntimeError,ValueError,subprocess.CalledProcessError) as e:
        print('D11A-AUDIT FAIL:',e,file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
