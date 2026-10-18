#!/usr/bin/env python3
"""D10-E2 standalone planner tests; NOT tests of real Kyiv_t CPU execution."""
import argparse
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import sys

PAT = re.compile(r'^D10E2-PLAN status=([A-Z_]+) count=(\d+) '
                 r'words=(NONE|[0-7]{14}(?:/[0-7]{14})*) STAGED_ONLY=1 CPU_MUTATION=0\r?$',re.M)
SOURCE = {
    '+0.6250000000': '12000000000000',
    '-0.6250000000': '32000000000000',
    '+0.5000000000': '10000000000000',
    '-0.5000000000': '30000000000000',
    '+0.2500000000': '04000000000000',
    '+0.0000000000': '00000000000000',
    '-0.0000000000': '20000000000000',
}

def oracle(token):
    neg = token.startswith('-')
    raw = token.lstrip('+-')
    digits = raw[2:] if raw.startswith('0.') else raw
    assert len(digits) == 10 and digits.isascii() and digits.isdigit()
    scaled = Fraction(int(digits), 10**10) * (1 << 40)
    assert scaled.denominator == 1, ('test fixture not exact',token)
    actual = f'{int(scaled) | ((1 << 40) if neg else 0):014o}'
    if token in SOURCE: assert actual == SOURCE[token], ('literal source conflict',token)
    return actual

V = ('+0.6250000000', '-0.6250000000', '+0.5000000000',
     '-0.5000000000', '+0.2500000000', '+0.0000000000', '-0.0000000000')
# label, start_line, first_offset, count, raw bytes, status, independently expected tokens
CASES = [
    ('seven-source-words',0,0,7,(' '.join(V)+'\n').encode(),'EXACT',V),
    ('compact-single',0,0,1,b'6250000000\n','EXACT',('+0.6250000000',)),
    ('signed-zero',0,0,2,b'-0000000000 0000000000\n','EXACT',('-0.0000000000','+0.0000000000')),
    ('offset',0,4,2,b'xxxx6250000000 -5000000000\n','EXACT',('+0.6250000000','-0.5000000000')),
    ('selected-row',2,3,2,b'ignore\nignore more\nxxx2500000000 5000000000\n','EXACT',('+0.2500000000','+0.5000000000')),
    ('multiline',0,0,3,b'6250000000\n5000000000 -2500000000\n','EXACT',('+0.6250000000','+0.5000000000','-0.2500000000')),
    ('crlf',0,0,2,b'6250000000\r\n-5000000000\r\n','EXACT',('+0.6250000000','-0.5000000000')),
    ('tabs-spaces',0,0,2,b' \t6250000000 \t -0000000000 \t\n','EXACT',('+0.6250000000','-0.0000000000')),
    ('surplus-valid',0,0,1,b'6250000000 5000000000\n','EXACT',('+0.6250000000',)),
    ('nonexact-first',0,0,2,b'1000000000 6250000000\n','NONEXACT',()),
    ('nonexact-second',0,0,2,b'6250000000\n1000000000\n','NONEXACT',()),
    ('nonexact-extra',0,0,1,b'6250000000 1000000000\n','NONEXACT',()),
    ('invalid-token-second',0,0,2,b'6250000000\n0.625\n','INVALID_TOKEN',()),
    ('invalid-token-extra',0,0,1,b'6250000000 nonsense\n','INVALID_TOKEN',()),
    ('invalid-utf8',0,0,1,'０.6250000000\n'.encode('utf-8'),'INVALID_TOKEN',()),
    ('invalid-tab-inside-number',0,0,1,b'62500\t00000\n','INVALID_TOKEN',()),
    ('invalid-cr-inside-line',0,0,1,b'6250000000\r 5000000000\n','INVALID_TOKEN',()),
    ('empty-first',0,0,1,b'\n6250000000\n','EMPTY_RECORD',()),
    ('empty-second',0,0,2,b'6250000000\n\n5000000000\n','EMPTY_RECORD',()),
    ('no-file-contents',0,0,1,b'','MISSING_START_LINE',()),
    ('start-beyond-eof',3,0,1,b'6250000000\n','MISSING_START_LINE',()),
    ('short-file',0,0,3,b'6250000000\n5000000000\n','SHORT_INPUT',()),
    ('offset-too-large',0,50,1,b'6250000000\n','INVALID_FIRST_OFFSET',()),
    ('offset-to-empty',0,10,1,b'6250000000\n','EMPTY_RECORD',()),
    ('zero-count',0,0,0,b'6250000000\n','INVALID_COUNT',()),
    ('huge-count',0,0,1025,b'6250000000\n','INVALID_COUNT',()),
]

def test(exe, entry, timeout):
    label,start,offset,count,source,status,tokens=entry
    try:
        p=subprocess.run([str(exe),str(start),str(offset),str(count)],input=source,
                         capture_output=True,timeout=timeout)
        output=p.stdout.decode('utf-8','replace')
    except subprocess.TimeoutExpired:
        print(f'D10E2-CASE {label}: TIMEOUT FAIL'); return False
    matches=PAT.findall(output)
    words=tuple(oracle(t) for t in tokens)
    expected=(status,str(len(words)),'/'.join(words) if words else 'NONE')
    actual=matches[0] if len(matches)==1 else None
    ok=p.returncode==0 and actual==expected
    print(f'D10E2-CASE {label}: {"PASS" if ok else "FAIL"} status={actual[0] if actual else "NONE"} count={actual[1] if actual else "NA"}')
    if not ok:
        print('  expected:',expected,'actual:',actual,'stdout:',repr(output[-1200:]),
              'stderr:',repr(p.stderr.decode('utf-8','replace')[-1200:]))
    return ok

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5.0)
    opts=ap.parse_args()
    exe=Path(opts.exe).resolve()
    if not exe.is_file() or not 0.2 <= opts.timeout <= 60:
        ap.error('existing executable and timeout 0.2..60 required')
    passed=sum(test(exe,entry,opts.timeout) for entry in CASES)
    print(f'ISA-07 D10-E2 STAGING PASS={passed}/{len(CASES)} '
          'SOURCE_WORDS=7 HOST_POLICY=1 WHOLE_COMMAND_STAGING=1 '
          'NO_PARTIAL_VALUES_ON_REJECTION=1 CPU_MUTATION=0')
    return int(passed != len(CASES))

if __name__=='__main__': sys.exit(main())
