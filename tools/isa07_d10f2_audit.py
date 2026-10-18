#!/usr/bin/env python3
"""D10-F2 read-only pins and staged-only code shape (not hardware oracle)."""
from pathlib import Path
import subprocess
import sys

BASE='5c2ff45229ae536d50462dc22859b0337d4c82d5'
PINS={
 'src/main.cpp':'d263706708efd958401df4818baa21249d99105a',
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'inc/kyiv_decimal_ascii.h':'93e47fd34b5133964fb5a9addab3430dd25f71ae',
 'inc/kyiv_decimal_input_plan.h':'9135962f7d41c9b619f0875e6fe7deac666d2ba1',
}
NEW=(
 'docs/ISA_07_D10F2_PROVISIONAL_TRUNCATION_DECISION.md',
 'inc/kyiv_decimal_trunc.h',
 'tests/isa/isa07_d10f2_trunc_probe.cpp',
 'tools/isa07_d10f2_trunc_sandbox.py',
 'tools/isa07_d10f2_audit.py',
)

def git(*args):
    return subprocess.check_output(('git',)+args,stderr=subprocess.PIPE,text=True).strip()

def req(ok,msg):
    if not ok: raise RuntimeError(msg)

def main():
    try:
        req(not git('rev-parse','--show-prefix'),'wrong repository root')
        req(git('rev-parse','HEAD')==BASE,'wrong HEAD; baseline is 5c2ff45')
        for rel,sha in PINS.items():
            req(git('rev-parse',f'HEAD:{rel}')==sha,'committed baseline pin drift: '+rel)
            req(not git('diff','--',rel),'working tracked mutation: '+rel)
            req(not git('diff','--cached','--',rel),'staged tracked mutation: '+rel)
        for rel in NEW:
            req(Path(rel).is_file(),'missing new component: '+rel)
            req(not git('ls-files','--',rel),'new file unexpectedly tracked: '+rel)
        h=Path(NEW[1]).read_text(encoding='utf-8')
        for term in ('namespace kyiv_decimal_trunc','enum class status { exact, truncated, invalid_bcd }',
                     'digits * shift_factor','scaled / exact_divisor','scaled % exact_divisor',
                     'negative ? sign_bit : 0','return {status::invalid_bcd, 0, 0}'):
            req(term in h,'converter contract missing: '+term)
        docs=Path(NEW[0]).read_text(encoding='utf-8')
        for term in ('DPS64 pp. 120–122','GY62 pp. 10–11','GY62 printed p. 17',
                     'GY62 printed pp. 117–118','PROVISIONAL','SOURCE_STRICT','OPEN',
                     '9_765_625','mathematical models, NOT hardware traces',BASE):
            req(term in docs,'documentary qualification missing: '+term)
        runner=Path(NEW[3]).read_text(encoding='utf-8')
        req('random.Random(0xD10F2)' in runner and 'divmod(n * SCALE, DIVISOR)' in runner,
            'independent oracle missing')
        req('CPU_MUTATION=0 HARDWARE_ORACLE=0' in runner,'qualification missing')
        print('D10F2-AUDIT PASS BASELINE=5c2ff45 PINS=5/5 NEW_FILES=5/5 '
              'CPU_MUTATION=0 D10C_D10D_D10E2_MUTATION=0 '
              'TRUNCATION=PROVISIONAL HISTORICAL_ORACLE=OPEN')
        return 0
    except (OSError,RuntimeError,subprocess.CalledProcessError) as ex:
        print('D10F2-AUDIT FAIL',ex,file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
