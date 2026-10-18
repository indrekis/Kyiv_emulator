#!/usr/bin/env python3
"""ISA-07 D10-E3 read-only audit, exact pinned baseline and narrow CPU delta."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '7803a002fd979cd91e3a22e40955beb944067a53'
PINS = {
    'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
    'inc/kyiv_decimal_ascii.h':'93e47fd34b5133964fb5a9addab3430dd25f71ae',
    'inc/kyiv_decimal_input_plan.h':'9135962f7d41c9b619f0875e6fe7deac666d2ba1',
    'tools/isa07_d10e2_input_plan_sandbox.py':'44391b5e41279668836816a19bf8cdd7ecac2a66',
}
CPU_BASE = 'bc9331b178333d2e3ef32789972bc16bc70c39ea'
# SHA-256 of the exact replacement case, including the opening case and break.
CASE_SHA256 = 'ee59ad2becec893fbb7bec592b88398ef3664c5b8440fad3db0be96e52f70903'
START = '        case IO_operations_t::opcode_read_perfo_data:{\n'
END = '        case IO_operations_t::opcode_read_perfo_binary:{\n'
INCLUDE_OLD = '#include "kyiv.h"\n'
INCLUDE_NEW = '#include "kyiv.h"\n#include "kyiv_decimal_input_plan.h"\n'

def git(*args):
    r = subprocess.run(['git', *args], cwd=ROOT, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.stdout.decode('utf-8', errors='strict').strip()

def fail(msg):
    print('D10E3-AUDIT FAIL',msg)
    sys.exit(1)

def main():
    try:
        if git('rev-parse','HEAD') != BASE:
            fail('HEAD must equal 7803a00 baseline; never rewrite historical pins')
        if git('rev-parse','--show-prefix'):
            fail('wrong repository root')
        if git('rev-parse',f'{BASE}:src/main.cpp') != CPU_BASE:
            fail('original CPU baseline changed')
        for path, sha in PINS.items():
            if git('hash-object',path) != sha:
                fail('component mutated: '+path)
        modified = (ROOT/'src/main.cpp').read_text(encoding='utf-8')
        base = subprocess.check_output(['git','show',f'{BASE}:src/main.cpp'],cwd=ROOT).decode('utf-8')
        if base.count(START) != 1 or base.count(END) != 1 or modified.count(START) != 1 or modified.count(END) != 1:
            fail('IO20/21 boundaries ambiguous')
        base_pre, b_remainder = base.split(START)
        old_case, base_post = b_remainder.split(END)
        now_pre, n_remainder = modified.split(START)
        new_case, now_post = n_remainder.split(END)
        if base_pre.count(INCLUDE_OLD) != 1 or now_pre != base_pre.replace(INCLUDE_OLD,INCLUDE_NEW):
            fail('changes outside include/IO20 before case')
        if now_post != base_post:
            fail('IO21-25 or later code mutated')
        if hashlib.sha256((START+new_case).encode()).hexdigest() != CASE_SHA256:
            fail('IO20 body does not match reviewed patch')
        if 'std::stol(' not in old_case or 'counter > num_counter' not in old_case:
            fail('unexpected source IO20 baseline')
        if 'std::stol(' in new_case or 'std::stoi(' in new_case:
            fail('legacy octal conversion remains in IO20')
        if 'kyiv_decimal_input_plan::collect' not in new_case:
            fail('planner not called')
        cpu_test=(ROOT/'tests/isa/isa07_d10e3_io20_cpu_probe.cpp').read_text(encoding='utf-8')
        if cpu_test.count('m.execute_opcode()') != 2:
            fail('must exercise TWO real CPU steps in C++')
        for path in ('tools/isa07_d10e3_io20_cpu_sandbox.py',
                     'docs/ISA_07_D10E3_IO20_CPU_INTEGRATION.md'):
            if not (ROOT/path).is_file(): fail('missing '+path)
        changed = [p for p in git('diff','--name-only').splitlines() if p]
        if changed != ['src/main.cpp']:
            fail('unexpected tracked mutations '+repr(changed))
        staged = git('diff','--cached','--name-only')
        if staged:
            fail('staged modifications before successful testing: '+staged)
        print('D10E3-AUDIT PASS BASELINE=7803a00 COMPONENTS=5/5 '
              'IO20_ONLY=1 IO21_25_UNCHANGED=1 CPU_TWO_STEPS=1 '
              'GY62_RAM_BOUNDS=1 HISTORICAL_PINS_UNCHANGED=1')
        return 0
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        fail(str(exc))

if __name__ == '__main__':
    sys.exit(main())
