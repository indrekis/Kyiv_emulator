from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

root = Path(__file__).resolve().parents[1]
BASE = 'a361ff744befbd76062133a488b00ddcba9565ff'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
assert git('rev-parse', 'HEAD') == BASE, 'PINNED_HEAD_MISMATCH'
assert git('branch', '--show-current') == 'main', 'NOT_MAIN'
assert git('rev-parse', '--show-prefix') == '', 'NOT_REPOSITORY_ROOT'
EXPECTED_UNTRACKED = {
    'docs/ISA_07_D15A1_BOUND_RUN_CONTRACT.md',
    'docs/ISA_07_D15A1_DECISION_LEDGER.tsv',
    'tools/isa07_d15a1_audit.py',
    'tools/isa07_d15a1_extended_regression.py',
    'tools/isa07_d15a1_run_image.cpp',
}
def check_scope():
    current = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert current == EXPECTED_UNTRACKED, (
        'WORKTREE_SCOPE_MISMATCH', sorted(current ^ EXPECTED_UNTRACKED))
    assert not git('diff', '--name-only'), 'TRACKED_SOURCE_MUTATION'
    assert not git('diff', '--cached', '--name-only'), 'STAGED_SOURCE_MUTATION'

check_scope()
exe = (root / 'tempkyiv/d15a1_run_image.exe').resolve()
assert exe.is_file(), 'D15A1_EXE_MISSING'
SIGN = 1 << 40
MASK = (1 << 41) - 1

def ins(op, a1=0, a2=0, a3=0):
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3

def image(pairs):
    return ('KYIV41-OCT1\n' + ''.join(f'{a:04o} {w:014o}\n' for a, w in pairs)).encode('ascii')

passed = 0

def ok(name, statement):
    global passed
    assert statement, name
    passed += 1
    print(f'D15A1-EXT-CASE {passed:02d} {name}: PASS', flush=True)

with TemporaryDirectory(prefix='d15a1_ext_', dir=root/'tempkyiv') as tmp:
    folder = Path(tmp) / 'isolated path with spaces'
    folder.mkdir()
    def file(name, contents):
        p = folder/name
        p.write_bytes(contents)
        return p
    def run(path, *args):
        return subprocess.run([str(exe), str(path), *args], cwd=root,
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=15)
    def reject(name, content, code, *args):
        p = file(name+'.k41', content)
        before = p.read_bytes()
        r = run(p, *(args or ('0500', '3')))
        ok(name, r.returncode == 2 and ('D15A1-ERROR '+code) in r.stderr and
           'D15A1-LOAD PASS' not in r.stdout and p.read_bytes() == before)
    def accept(name, content, args, expected):
        p = file(name+'.k41', content)
        before = p.read_bytes()
        r = run(p, *args)
        ok(name, r.returncode == 0 and expected in r.stdout and
           p.read_bytes() == before)

    accept('bounded-zero-opcode', image([(0o500, 0)]), ('0500','3'),
           'D15A1-RUN STATUS=LIMIT STEPS=3 C=0503')
    accept('bounded-equal-loop', image([(1, 7), (2, 7),
           (0o500, ins(0o16, 1, 2, 0o500))]), ('0500','5'),
           'D15A1-RUN STATUS=LIMIT STEPS=5 C=0500')
    accept('maximal-41-bit-word', image([(1, MASK),
           (0o500, ins(0o33))]), ('0500','2','--watch','0001'),
           'D15A1-WATCH ADDR=0001 RAW='+f'{MASK:014o}')
    accept('comments-and-spaces',
           b'  # preface\n\nKYIV41-OCT1 # header\n 0500 33000000000000 # stop\n',
           ('0500','2'), 'D15A1-RUN STATUS=CPU_STOP STEPS=1')
    accept('decimal-leading-zero-limit', image([(0o500, ins(0o33))]),
           ('0500', '00000000001'), 'D15A1-RUN STATUS=CPU_STOP STEPS=1')
    accept('sign-distinct-comparison', image([(1, 0), (2, SIGN),
           (0o500, ins(0o16, 1, 2, 0o502)),
           (0o501, ins(0o33)), (0o502, ins(0o33))]),
           ('0500','3'), 'D15A1-RUN STATUS=CPU_STOP STEPS=2 C=0502')

    reject('invalid-header', b'KYIV41-OCT2\n0500 33000000000000\n', 'INVALID_IMAGE_HEADER')
    reject('empty-image', b'KYIV41-OCT1\n# no records\n', 'EMPTY_IMAGE')
    reject('bad-octal-word', b'KYIV41-OCT1\n0500 00000000000008\n', 'INVALID_OCTAL_DIGIT')
    reject('overwide-word', image([(0o500, 1<<41)]), 'OVERWIDE_41_BIT_WORD')
    reject('forbidden-memory-gap', image([(0o2000, 0)]), 'INVALID_LOAD_ADDRESS')
    reject('duplicate-address', image([(0o500, 0),(0o500, 1)]), 'DUPLICATE_ADDRESS')
    reject('extra-record-field', b'KYIV41-OCT1\n0500 33000000000000 extra\n', 'INVALID_IMAGE_RECORD')
    reject('rom-preflight-reject', image([(1, 3),(0o3010, ins(0o33))]),
           'ROM_LOAD_REQUIRES_OPT_IN')
    reject('limit-too-large', image([(0o500, ins(0o33))]),
           'STEP_LIMIT_TOO_LARGE', '0500', '100001')
    reject('decimal-limit-wraparound-rejected',
           image([(0o500, ins(0o33))]), 'STEP_LIMIT_TOO_LARGE',
           '0500', '18446744073709551617')
    reject('nondecimal-limit', image([(0o500, ins(0o33))]),
           'INVALID_STEP_LIMIT', '0500', '1x')
    reject('invalid-start', image([(0o500, ins(0o33))]),
           'INVALID_START_ADDRESS', '2000', '2')
    reject('invalid-watch', image([(0o500, ins(0o33))]),
           'INVALID_WATCH_ADDRESS', '0500', '2', '--watch', '2000')
    reject('missing-watch-value', image([(0o500, ins(0o33))]),
           'INVALID_ARGUMENT', '0500', '2', '--watch')
    badpath = folder/'nonexistent.k41'
    r = run(badpath, '0500', '2')
    ok('missing-image', r.returncode == 2 and 'D15A1-ERROR IMAGE_OPEN_FAILED' in r.stderr
       and not badpath.exists())

assert passed == 21, 'CASE_COUNT_MISMATCH'
check_scope()
print(f'D15A1-EXTENDED PASS CASES={passed}/21 SOURCE_IMMUTABLE=1')
