#!/usr/bin/env python3
"""Read-only D10-G2 gate: pinned 635de81, documentation and model only."""
from pathlib import Path
import os
import subprocess
import sys

BASE = '635de81301827128c900b390b374c3fc8bbd032c'
PINS = {
 'src/main.cpp':'e6d00248705668156c29b376b3dd1b26ed40e275',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'inc/kyiv_decimal_trunc.h':'e6ab074335a2337de3a5b0eadd3bf46adf0b09fe',
 'inc/kyiv_decimal_ascii.h':'e92fda12785ea2ed79a215461003a13eb85fb076',
 'inc/kyiv_decimal_input_plan.h':'a38b137291c7e218bf9d81c5eebfcc6ac9d3b6a3',
 'docs/ISA_07_D10G1_DECIMAL_MICROPROGRAM_RECONSTRUCTION.md':'146dd098afbe51b1ff87e5191ee23dfb7968f49a',
 'docs/ISA_07_D10G1_EVIDENCE_LEDGER.tsv':'225b58a97de93103b75f8ca496e7fab5e7674073',
 'docs/ISA_07_D10G1_COMPARISON.tsv':'588a5757c3e56c1736238c480de0a100f31d7feb',
 'tools/isa07_d10g1_reference.py':'e42e11754d9753b80bcf9efc9280982e671e5cb2',
 'tests/isa/isa07_d10g1_reference_test.py':'c46eaed0a2ef4c35a3175bec8b0dccff2c886043',
 'tools/isa07_d10g1_audit.py':'244c08ffaea0ae4ec8ad8ffd753020a9285aec66'
}
NEW = (
 'docs/ISA_07_D10G2_ARITHMETIC_DATAPATH_RECONSTRUCTION.md',
 'docs/ISA_07_D10G2_SOURCE_LEDGER.tsv',
 'docs/ISA_07_D10G2_QUANTIZATION_COMPARISON.tsv',
 'tools/isa07_d10g2_hypotheses.py',
 'tests/isa/isa07_d10g2_hypotheses_test.py',
 'tools/isa07_d10g2_audit.py',
)

def git(*args):
    return subprocess.check_output(('git',)+args,stderr=subprocess.PIPE,text=True).strip()

def require(check, reason):
    if not check: raise RuntimeError(reason)

def normalized(rel):
    data=Path(rel).read_bytes()
    require(b'\r' not in data.replace(b'\r\n',b''), 'bare CR in '+rel)
    data=data.replace(b'\r\n',b'\n')
    # SHA and compare normalized bytes; accept CRLF, not arbitrary edits.
    return data.decode('utf-8')

def main():
    try:
        require(git('rev-parse','--show-prefix')=='', 'run from repository root')
        require(git('rev-parse','HEAD')==BASE, 'HEAD not pinned 635de81')
        for rel,expected in PINS.items():
            require(git('rev-parse','HEAD:'+rel)==expected, 'baseline blob mismatch '+rel)
            require(not git('diff','--',rel), 'tracked unstaged mutation '+rel)
            require(not git('diff','--cached','--',rel), 'tracked staged mutation '+rel)
        for rel in NEW:
            require(Path(rel).is_file(), 'missing G2 file '+rel)
            require(not git('ls-files','--',rel), 'G2 file unexpectedly staged/tracked '+rel)
        doc=normalized(NEW[0])
        for needle in ('DPS64', 'printed p. 105', 'p.109', 'm=5',
                       'INFERRED', 'PROVISIONAL', 'OPEN', 'SOURCE_STRICT',
                       'right-shift', 'multiplicand', '40-bit', 'five', 'extra bits',
                       'HARDWARE'):
            # Source-qualified terms must be substantive, do not require case.
            require(needle.casefold() in doc.casefold(), 'documentation marker missing '+needle)
        ledger=normalized(NEW[1])
        for marker in ('G2-S01','G2-S05','G2-S06','G2-S08','G2-I01','G2-D01'):
            require(marker in ledger,'source ledger incomplete '+marker)
        model=normalized(NEW[3]);probe=normalized(NEW[4]);audit=normalized(NEW[5])
        for marker in ('def shift_multiplicand','def bit_terms','def digit_terms',
                       'Fraction','D10G2-REFERENCE','HARDWARE_ORACLE=0'):
            require(marker in model, 'model contract missing '+marker)
        require('INDEPENDENT_ORACLE=1' in probe and '1014' not in probe,
                'probe oracle missing or hardcoded count')
        require('b\'\\r\\n\'' in audit and 'SOURCE_LEDGER' in audit,
                'auditor EOL portability or file closure missing')
        import isa07_d10g2_hypotheses as m
        expected=m.comparison_tsv()
        require(normalized(NEW[2])==expected,'comparison table does not regenerate')
        require('HARDWARE_ORACLE=0' in model, 'qualification missing')
        print('D10G2-AUDIT PASS BASELINE=635de81 PINS=11/11 NEW_FILES=6/6 '
              'CPU_MUTATION=0 F2_F3_MUTATION=0 D10G1_UNCHANGED=1 '
              'SOURCE_LEDGER=1 COMPARISON_REGENERATED=1 EOL_PORTABLE=1 '
              'HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError, UnicodeError, RuntimeError, subprocess.CalledProcessError,
            ImportError) as e:
        print('D10G2-AUDIT FAIL',e,file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
