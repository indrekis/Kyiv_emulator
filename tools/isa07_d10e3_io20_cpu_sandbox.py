#!/usr/bin/env python3
"""ISA-07 D10-E3. Genuine two-step Kyiv_t CPU, isolated temporary cwd.

Independent expected exact fractions use fractions.Fraction rather than
kyiv_decimal_* code. Existing 20 octal HOST_OBS cases are not accepted.
"""
import argparse
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Case:
    name: str
    a1: int
    a2: int
    a3: int
    line: int
    a_reg: int
    data: bytes | None
    values: tuple[str, ...] = ()
    error: str = ''

V = ('+0.6250000000', '-0.6250000000', '+0.5000000000',
     '-0.5000000000', '+0.2500000000', '+0.0000000000', '-0.0000000000')

CASES = (
    Case('source-seven',0o200,0o206,0,0,0,(' '.join(V)+'\n').encode(),V),
    Case('single',0o201,0o201,0,0,0,b'6250000000\n',(V[0],)),
    Case('single-minus',0o201,0o201,0,0,0,b'-6250000000\n',(V[1],)),
    Case('signed-zeros',0o200,0o201,0,0,0,b'-0000000000 0000000000\n',(V[6],V[5])),
    Case('offset',0o200,0o201,3,0,0,b'xxx6250000000 -5000000000\n',(V[0],V[3])),
    Case('selected-line',0o200,0o201,3,2,0,b'IGNORE\n1000000000\nxxx2500000000 5000000000\n',(V[4],V[2])),
    Case('multiline',0o200,0o202,0,0,0,b'6250000000\n5000000000 -2500000000\n',(V[0],V[2],'-0.2500000000')),
    Case('crlf',0o200,0o201,0,0,0,b'6250000000\r\n-5000000000\r\n',(V[0],V[3])),
    Case('spaces-tabs',0o200,0o201,0,0,0,b' \t6250000000 \t -0000000000 \t\n',(V[0],V[6])),
    Case('surplus-valid',0o200,0o200,0,0,0,b'6250000000 5000000000\n',(V[0],)),
    Case('shifted-addresses',0o4200,0o4202,0,0,1,b'6250000000 5000000000 2500000000\n',(V[0],V[2],V[4])),
    Case('shifted-a3',0o200,0o200,0o4002,0,1,b'xxx6250000000\n',(V[0],)),
    Case('last-ram',0o1777,0o1777,0,0,0,b'2500000000\n',(V[4],)),
    Case('zero-cell-discard',0o0,0o1,0,0,0,b'6250000000 -5000000000\n',(V[0],V[3])),
    Case('missing-file',0o200,0o200,0,0,0,None,error='UNAVAILABLE_STREAM'),
    Case('empty-file',0o200,0o200,0,0,0,b'',error='MISSING_START_LINE'),
    Case('start-past-eof',0o200,0o200,0,2,0,b'6250000000\n',error='MISSING_START_LINE'),
    Case('short-file',0o200,0o201,0,0,0,b'6250000000\n',error='SHORT_INPUT'),
    Case('empty-record',0o200,0o200,0,0,0,b'\n6250000000\n',error='EMPTY_RECORD'),
    Case('empty-second',0o200,0o201,0,0,0,b'6250000000\n\n',error='EMPTY_RECORD'),
    Case('offset-too-large',0o200,0o200,50,0,0,b'6250000000\n',error='INVALID_FIRST_OFFSET'),
    Case('bad-token',0o200,0o201,0,0,0,b'6250000000\n0.625\n',error='INVALID_TOKEN'),
    Case('bad-extra',0o200,0o200,0,0,0,b'6250000000 nonsense\n',error='INVALID_TOKEN'),
    Case('unicode',0o200,0o200,0,0,0,'０.6250000000\n'.encode('utf-8'),error='INVALID_TOKEN'),
    Case('nonexact-first',0o200,0o201,0,0,0,b'1000000000 6250000000\n',error='NONEXACT'),
    Case('nonexact-second',0o200,0o201,0,0,0,b'6250000000\n1000000000\n',error='NONEXACT'),
    Case('nonexact-extra',0o200,0o200,0,0,0,b'6250000000 1000000000\n',error='NONEXACT'),
    Case('negative-selector',0o200,0o200,0,-1,0,b'6250000000\n',error='INVALID_PERFO_NUM'),
    Case('reversed-interval',0o202,0o200,0,0,0,b'6250000000\n',error='INVALID_INTERVAL'),
    Case('ram-over-boundary',0o1777,0o2000,0,0,0,b'6250000000 5000000000\n',error='INVALID_RAM_ADDRESS'),
    Case('non-ram-start',0o2000,0o2000,0,0,0,b'6250000000\n',error='INVALID_RAM_ADDRESS'),
)

SOURCE = {
    V[0]: '12000000000000', V[1]: '32000000000000',
    V[2]: '10000000000000', V[3]: '30000000000000',
    V[4]: '04000000000000', V[5]: '00000000000000',
    V[6]: '20000000000000',
}

def exact_word(token):
    negative = token.startswith('-')
    digits = token.lstrip('+-')
    if digits.startswith('0.'):
        digits = digits[2:]
    assert len(digits) == 10 and digits.isascii() and digits.isdigit()
    rational = Fraction(int(digits), 10**10) * (1 << 40)
    assert rational.denominator == 1, token
    expected = f'{int(rational) | ((1 << 40) if negative else 0):014o}'
    if token in SOURCE:
        assert expected == SOURCE[token], (token, expected, SOURCE[token])
    return expected

def oct_arg(number):
    return '0' + format(number, 'o')

def parse_summary(output, label):
    lines = [line for line in output.splitlines()
             if line.startswith('D10E3-CPU mode=')]
    if len(lines) != 1:
        return None
    try:
        parts = dict(part.split('=', 1) for part in lines[0].split()[1:])
    except ValueError:
        return None
    return parts if parts.get('mode') == label else None

def run_case(exe, case, timeout, parent):
    with tempfile.TemporaryDirectory(prefix='isa07_d10e3_', dir=parent) as folder:
        home = Path(folder)
        (home/'a'/'b').mkdir(parents=True)
        (home/'mem').mkdir()
        if case.data is not None:
            (home/'mem'/'punch_cards_in.txt').write_bytes(case.data)
        command = [str(exe),case.name,oct_arg(case.a1),oct_arg(case.a2),
                   oct_arg(case.a3),str(case.line),oct_arg(case.a_reg)]
        try:
            p = subprocess.run(command,cwd=home/'a'/'b',capture_output=True,
                               text=True,encoding='utf-8',errors='replace',timeout=timeout)
            obs = parse_summary(p.stdout, case.name)
            state = f'EXIT_{p.returncode}'
        except subprocess.TimeoutExpired:
            obs = None
            state = 'TIMEOUT'
            p = None
        if case.error:
            ok = (p is not None and p.returncode == 0 and obs is not None and
                  obs.get('status') == 'ERROR' and
                  obs.get('reason') == case.error and obs.get('pc') == '100' and
                  obs.get('k') == '1' and obs.get('unchanged') == '1' and
                  obs.get('regs') == '1' and obs.get('steps') == '1')
        else:
            expected = tuple(exact_word(v) for v in case.values)
            if case.a1 == 0: # Documented hardwired cell zero, discard one word.
                expected = ('00000000000000',) + expected[1:]
            ok = (p is not None and p.returncode == 0 and obs is not None and
                  obs.get('status') == 'OK' and obs.get('pc1') == '101' and
                  obs.get('pc2') == '102' and obs.get('k1') == '1' and
                  obs.get('k2') == '1' and obs.get('guard') == '1' and
                  obs.get('regs') == '1' and obs.get('xor') == '6' and
                  obs.get('run') == '1/1' and obs.get('steps') == '2' and
                  obs.get('words') == '/'.join(expected))
        print(f"D10E3-CASE {case.name}: {'PASS' if ok else 'FAIL'} "
              f"expected={case.error or 'EXACT'} observed={obs.get('status') if obs else 'NONE'} "
              f"process={state}")
        if not ok:
            print('  expected_words:', None if case.error else expected)
            print('  observed_fields:', obs)
            if p is not None:
                print('  output_tail:',repr(p.stdout.splitlines()[-9:]))
                print('  error_tail:',repr(p.stderr.splitlines()[-5:]))
        return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--timeout',type=float,default=5)
    args=ap.parse_args()
    exe=Path(args.exe).resolve()
    parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():
        ap.error('compiled real-CPU executable and tempkyiv required')
    if not 0.2 <= args.timeout <= 60:
        ap.error('timeout must be in 0.2..60 seconds')
    passed = sum(run_case(exe,c,args.timeout,parent) for c in CASES)
    print(f'ISA-07 D10-E3 CPU PASS={passed}/{len(CASES)} '
          f'TWO_STEP_SUCCESS={sum(not c.error for c in CASES)} '
          f'ATOMIC_REJECTION={sum(bool(c.error) for c in CASES)} '
          'SOURCE_STRICT_GY62=1 HOST_POLICY=1 GENUINE_KYIV_T=1')
    return 0 if passed == len(CASES) else 1

if __name__ == '__main__':
    sys.exit(main())
