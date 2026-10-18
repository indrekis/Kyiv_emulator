#!/usr/bin/env python3
"""D10-F3 read-only audit: pinned baseline, exact CPU delta, three modifications.

Git blob hashing here normalizes CRLF only (Windows autocrlf safety).
Functional correctness must also be established by C++/Python and real CPU gates.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

BASE='98964fd96dfc8dbea692accd1ffb00d5d8719abb'
BASE_PINS={
 'src/main.cpp':'d263706708efd958401df4818baa21249d99105a',
 'inc/kyiv_decimal_ascii.h':'93e47fd34b5133964fb5a9addab3430dd25f71ae',
 'inc/kyiv_decimal_input_plan.h':'9135962f7d41c9b619f0875e6fe7deac666d2ba1',
 'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
 'inc/kyiv_decimal_trunc.h':'e6ab074335a2337de3a5b0eadd3bf46adf0b09fe',
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'tests/isa/isa07_d10e3_io20_cpu_probe.cpp':'08e0c8b855ba3be3741c998bf3db7aa8f2ff05d9',
 'tools/isa07_d10e3_io20_cpu_sandbox.py':'f58d04f55cdbc7c379a924996bf3715ca448ee1e',
}
MODIFIED={
 'src/main.cpp',
 'inc/kyiv_decimal_ascii.h',
 'inc/kyiv_decimal_input_plan.h',
}
EXPECTED_BLOBS={
 'inc/kyiv_decimal_ascii.h':'e92fda12785ea2ed79a215461003a13eb85fb076',
 'inc/kyiv_decimal_input_plan.h':'a38b137291c7e218bf9d81c5eebfcc6ac9d3b6a3',
}
NEW={
 'docs/ISA_07_D10F3_PROVISIONAL_TRUNCATION_INTEGRATION.md',
 'tests/isa/isa07_d10f3_pipeline_probe.cpp',
 'tools/isa07_d10f3_pipeline_sandbox.py',
 'tools/isa07_d10f3_io20_cpu_sandbox.py',
 'tools/isa07_d10f3_audit.py',
 'tools/isa07_d10f3_regression_gate.py',
}

def git(*args):
    return subprocess.check_output(('git',)+args,text=True,stderr=subprocess.PIPE).strip()
def need(test,message):
    if not test:raise RuntimeError(message)
def normalize(data):
    data=data.replace(b'\r\n',b'\n')
    need(b'\r' not in data, 'standalone CR in source (possible encoding drift)')
    return data
def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()

def check():
    need(not git('rev-parse','--show-prefix'),'not at repository root')
    need(git('rev-parse','HEAD')==BASE,'HEAD not D10-F2 98964fd')
    for path,sha in BASE_PINS.items():
        need(git('rev-parse','HEAD:'+path)==sha,'baseline blob mismatch '+path)
    for path in BASE_PINS.keys()-MODIFIED:
        need(blob(normalize(Path(path).read_bytes()))==BASE_PINS[path],
             'protected file changed '+path)
    for path,sha in EXPECTED_BLOBS.items():
        need(blob(normalize(Path(path).read_bytes()))==sha,
             'D10-F3 modified header not exact expected '+path)
    # Baseline CPU -> exactly one new provisional-success guard + switch case.
    before=subprocess.check_output(('git','show',BASE+':src/main.cpp'))
    need(blob(before)==BASE_PINS['src/main.cpp'],'unexpected source CPU blob')
    old=(b'            if (staged.state != kyiv_decimal_input_plan::status::exact) {')
    new=(b'            // D10-F2 truncation is PROVISIONAL, not a proven IO20 hardware rule.\n'
         b'            // Both exact and truncated inputs are commit-ready after full validation.\n'
         b'            if (staged.state != kyiv_decimal_input_plan::status::exact &&\n'
         b'                staged.state != kyiv_decimal_input_plan::status::truncated) {')
    needle=b'                case S::exact: break;'
    need(before.count(old)==1 and before.count(needle)==1,'IO20 patch anchor absent/ambiguous')
    target=before.replace(old,new,1).replace(needle,needle+b'\n                case S::truncated: break;',1)
    need(normalize(Path('src/main.cpp').read_bytes())==target,
         'CPU modified beyond the TWO prescribed IO20 hunks')
    tracked_changes=set(git('diff','--name-only','HEAD','--').splitlines())
    staged_changes=set(git('diff','--cached','--name-only','--').splitlines())
    need(tracked_changes | staged_changes == MODIFIED,
         'expected three and only three tracked source changes')
    for path in NEW:
        need(Path(path).is_file(),'missing new source '+path)
        need(not git('ls-files','--',path),'new file already tracked '+path)
    docs=Path('docs/ISA_07_D10F3_PROVISIONAL_TRUNCATION_INTEGRATION.md').read_text(encoding='utf8')
    for term in ('PROVISIONAL','SOURCE_STRICT','HOST_POLICY','OPEN','98964fd',
                 'DPS64 (1964), pp. 120–122','GY62 pp. 117–118'):
        need(term in docs,'missing documentary qualifier '+term)
    cpp=Path('tests/isa/isa07_d10f3_pipeline_probe.cpp').read_text(encoding='utf8')
    pipe=Path('tools/isa07_d10f3_pipeline_sandbox.py').read_text(encoding='utf8')
    real=Path('tools/isa07_d10f3_io20_cpu_sandbox.py').read_text(encoding='utf8')
    regression=Path('tools/isa07_d10f3_regression_gate.py').read_text(encoding='utf8')
    for term in ('std::cin','kyiv_decimal_ascii::parse_token','kyiv_decimal_input_plan::collect'):
        need(term in cpp,'pipeline C++ missing '+term)
    need('random.Random(0xD10F3)' in pipe and 'divmod(int(digits)*(1<<40),10**10)' in pipe,
         'independent pure integer parser oracle missing')
    need('isa07_d10e3_io20_cpu_sandbox as old' in real and
         'divmod(int(digits)*(1<<40),10**10)' in real and
         "'nonexact-extra'" in real,'D10-E3 CPU oracle parity override missing')
    need('ISA06' in regression and 'IO_CASES' in regression and 'IO21_PROBE' in regression,
         'unaffected regression coverage absent')
    print('D10F3-AUDIT PASS BASELINE=98964fd PINS=8/8 TRACKED_DELTA=3/3 '
          'NEW_FILES=6/6 IO20_ONLY=1 IO21_25_UNCHANGED=1 '
          'D10C_D10F2_UNCHANGED=1 HOST_POLICY=1 TRUNCATION=PROVISIONAL HARDWARE_ORACLE=0')
    return 0

if __name__=='__main__':
    try:sys.exit(check())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as ex:
        print('D10F3-AUDIT FAIL',ex,file=sys.stderr)
        sys.exit(1)
