#!/usr/bin/env python3
"""Read-only D10-G3 evidence gate. No repository or CPU mutations."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

BASE='ed80fdb90ee42ba8ebcc8add336a3baade3d76ea'
PINS={
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
 'tools/isa07_d10g1_audit.py':'244c08ffaea0ae4ec8ad8ffd753020a9285aec66',
 'docs/ISA_07_D10G2_ARITHMETIC_DATAPATH_RECONSTRUCTION.md':'1264622760a5a794834e96a07aaa99ac1bced5a2',
 'docs/ISA_07_D10G2_QUANTIZATION_COMPARISON.tsv':'666534d0a71ccbfd806405ec8c47b6c24d648e72',
 'docs/ISA_07_D10G2_SOURCE_LEDGER.tsv':'6c7aa983ecf411af5ecdceedb3b17559a07fdeff',
 'tools/isa07_d10g2_audit.py':'0c5439f8043d965bac734c1bf6c03a85726dfbfb',
 'tools/isa07_d10g2_hypotheses.py':'d28f1b51cf6120a3db67753d89d5af0a1ad5f5ca',
 'tests/isa/isa07_d10g2_hypotheses_test.py':'fea514b66ad0178eaa3093fe61b13cc4918d587d',
}
NEW=(
 'docs/ISA_07_D10G3_CONTROL_MICROPROGRAM_RECONSTRUCTION.md',
 'docs/ISA_07_D10G3_SOURCE_LEDGER.tsv',
 'docs/ISA_07_D10G3_MICROSTEP_COMPARISON.tsv',
 'tools/isa07_d10g3_microsteps.py',
 'tools/isa07_d10g3_comparison.py',
 'tests/isa/isa07_d10g3_microsteps_test.py',
 'tools/isa07_d10g3_audit.py',
)
# SHA256 of normalized LF content. Last auditor source is covered by contract
# checks but cannot contain a noncircular SHA of itself.
NEW_SHA256={
 'docs/ISA_07_D10G3_CONTROL_MICROPROGRAM_RECONSTRUCTION.md':'91d2475b213c83862bd52c063879d4337e88d94a22e7332d1dbec413e813a3fc',
 'docs/ISA_07_D10G3_SOURCE_LEDGER.tsv':'44d924999fa7a84294057f4fe91f57f0fbaf4c85dab565aacf231578c63ae850',
 'docs/ISA_07_D10G3_MICROSTEP_COMPARISON.tsv':'c4951ad7d64f4d805c6721267fbb74792646639c17c323ced197c6d63a504e92',
 'tools/isa07_d10g3_microsteps.py':'cb7373a879a6e37fef964ece342cef8e8a39bc617fd61ad8416bc42f90b50c22',
 'tools/isa07_d10g3_comparison.py':'9a5eb42392ba6531bfadf405e5f406e80c181c65d0c3498c2519d7d57e4d43cb',
 'tests/isa/isa07_d10g3_microsteps_test.py':'a91e2386d31b1a62136f904073dfd6b7ea803e7907bd8c6dfe8011b5cf6385a3',
}

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE,text=True).strip()

def require(cond,reason):
    if not cond: raise RuntimeError(reason)

def normalized(path):
    b=Path(path).read_bytes()
    require(b'\r' not in b.replace(b'\r\n',b''),'unexpected bare CR: '+path)
    return b.replace(b'\r\n',b'\n')

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,Path(path).resolve())
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    try:
        require(git('rev-parse','--show-prefix')=='','must run from repo root')
        require(git('rev-parse','HEAD')==BASE,'wrong HEAD, required ed80fdb')
        require(not git('diff','--name-only') and not git('diff','--cached','--name-only'),
                'unexpected changed tracked file')
        for path,sha in PINS.items():
            require(git('rev-parse','HEAD:'+path)==sha,'baseline Git blob pin drift: '+path)
        for path in NEW:
            require(Path(path).is_file(),'new file missing: '+path)
            require(not git('ls-files','--',path),'G3 file unexpectedly already staged/tracked: '+path)
            text=normalized(path)
            if path in NEW_SHA256:
                require(hashlib.sha256(text).hexdigest()==NEW_SHA256[path],
                        'new G3 content SHA mismatch: '+path)
        doc=normalized(NEW[0]).decode('utf-8')
        for term in ('DPS64','printed p.120','p.121','p.122','pp. 124–125',
                     'SOURCE_STRICT','INFERRED_HIGH','PROVISIONAL','OPEN',
                     'one eighth','40', '30', 'HARDWARE'):
            require(term.casefold() in doc.casefold(), 'documentary qualification missing: '+term)
        ledger=normalized(NEW[1]).decode('utf-8')
        for term in ('G3-S01','G3-S03','G3-S09','G3-M01','G3-I01','G3-D01'):
            require(term in ledger, 'evidence ledger missing: '+term)
        model=normalized(NEW[3]).decode('utf-8')
        for term in ('def exact_rational_trace','def microstep_model',
                     'def unscaled_literal_rational','Fraction','HARDWARE_ORACLE=0'):
            require(term in model, 'model contract missing: '+term)
        test=normalized(NEW[5]).decode('utf-8')
        require('Random(0xD10F3)' in test and 'INDEPENDENT_FRACTION=1' in test,
                'test independent/seed contract missing')
        require("b'\\r\\n'" in normalized(NEW[6]).decode('utf-8'),
                'auditor EOL portability missing')
        generator=load_module(NEW[4],'isa07_d10g3_comparison')
        require(generator.comparison_tsv().encode('utf-8')==normalized(NEW[2]),
                'comparison TSV does not reproduce')
        require(len(PINS)==17 and len(NEW)==7,'unexpected audit scope')
        print('D10G3-AUDIT PASS BASELINE=ed80fdb PINS=17/17 NEW_FILES=7/7 '
              'NEW_CONTENT_SHA=6/6 CPU_MUTATION=0 F2_F3_MUTATION=0 '
              'D10G1_G2_UNCHANGED=1 SOURCE_LEDGER=1 COMPARISON_REGENERATED=1 '
              'EOL_PORTABLE=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError, RuntimeError, UnicodeError, ImportError, subprocess.CalledProcessError) as e:
        print('D10G3-AUDIT FAIL',e,file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
