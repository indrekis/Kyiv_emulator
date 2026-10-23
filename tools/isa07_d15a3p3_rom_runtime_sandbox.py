#!/usr/bin/env python3
"""D15/A3-P3 native runtime gates. Run from repository root on MSYS2 MINGW64."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '372fc2fc5fe0d5e48fe0087d6e47066f3b7ae8bc'
DEFAULT_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
ROM = ROOT / 'mem/ROM.txt'
STOP = b'KYIV41-OCT1\n0500 33000000000000\n'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cli-exe', required=True)
    parser.add_argument('--timeout', type=int, default=20)
    a = parser.parse_args()
    exe = Path(a.cli_exe).resolve()
    assert exe.is_file(), 'MISSING_CLI'
    assert git('rev-parse', 'HEAD').decode() == BASE, 'WRONG_BASE'
    assert not git('diff', '--cached', '--name-only'), 'STAGED_CHANGES'
    assert hashlib.sha256(ROM.read_bytes()).hexdigest() == DEFAULT_SHA, 'DEFAULT_ROM_SHA'

    passed = 0
    with tempfile.TemporaryDirectory(prefix='d15a3p3_', dir=ROOT/'tempkyiv') as scratch:
        base = Path(scratch)
        test_image = base/'one stop.k41'
        test_image.write_bytes(STOP)
        rom = ROM.read_bytes()
        def run(*opts, cwd=ROOT, executable=exe):
            command = [str(executable), 'image', str(test_image), '0500', '2',
                       '--watch', '3121', '--watch', '3123', '--watch', '3036',
                       '--watch', '3200', *opts]
            return subprocess.run(command, cwd=cwd, capture_output=True,
                                  text=True, encoding='utf-8', errors='replace',
                                  timeout=a.timeout)
        def ok(name, pred, context=''):
            nonlocal passed
            assert pred, (name, context)
            passed += 1
            print(f'D15A3P3-CASE {passed:02d} {name}: PASS', flush=True)
        def rejection(name, opts, code, cwd=ROOT, executable=exe):
            r = run(*opts, cwd=cwd, executable=executable)
            ok(name, r.returncode == 2 and 'D15A2-ERROR '+code in r.stderr and
               'D15A2-RUN STATUS=' not in r.stdout, (r.stdout, r.stderr))

        r1 = run(cwd=ROOT)
        ok('default-rom', r1.returncode == 0 and
           'D15A3P3-ROM PASS SOURCE=DEFAULT WORDS=183 UNKNOWN_3200=1' in r1.stdout and
           'SHA_PINNED=1' in r1.stdout and
           'D15A2-RUN STATUS=CPU_STOP STEPS=1' in r1.stdout,
           (r1.stdout,r1.stderr))
        for addr, code in {'3121':'01000530110005', '3123':'12301100050004',
                           '3036':'37777777777777', '3200':'00000000000000'}.items():
            ok('default-word-'+addr, f'D15A2-WATCH ADDR={addr} RAW={code}' in r1.stdout)

        r2 = run(cwd=base)
        ok('cwd-independent', r2.returncode == 0 and
           [s for s in r1.stdout.splitlines() if s.startswith('D15A')]==
           [s for s in r2.stdout.splitlines() if s.startswith('D15A')],
           (r2.stdout,r2.stderr))

        explicit = ('--rom-file',str(ROM),'--rom-sha256',DEFAULT_SHA)
        r3 = run(*explicit, cwd=base)
        ok('explicit-sha', r3.returncode == 0 and
           'D15A3P3-ROM PASS SOURCE=EXPLICIT WORDS=183 UNKNOWN_3200=1' in r3.stdout and
           'SHA_PINNED=1' in r3.stdout and
           'D15A2-RUN STATUS=CPU_STOP STEPS=1' in r3.stdout,
           (r3.stdout,r3.stderr))
        rejection('sha-mismatch', ('--rom-file',str(ROM),'--rom-sha256','0'*64),
                  'ROM_SHA256_MISMATCH')
        rejection('missing-rom', ('--rom-file',str(base/'missing.txt'),
                  '--rom-sha256',DEFAULT_SHA), 'ROM_OPEN_FAILED')
        rejection('missing-rom-without-sha',
                  ('--rom-file',str(base/'missing.txt')), 'ROM_OPEN_FAILED')
        r_unpinned = run('--rom-file',str(ROM), cwd=base)
        ok('explicit-without-sha', r_unpinned.returncode == 0 and
           'D15A3P3-ROM PASS SOURCE=EXPLICIT WORDS=183 UNKNOWN_3200=1' in r_unpinned.stdout and
           'SHA_PINNED=0' in r_unpinned.stdout and
           'SHA256='+DEFAULT_SHA in r_unpinned.stdout and
           'D15A2-RUN STATUS=CPU_STOP STEPS=1' in r_unpinned.stdout,
           (r_unpinned.stdout,r_unpinned.stderr))
        rejection('sha-without-file', ('--rom-sha256', DEFAULT_SHA), 'ROM_SHA_REQUIRES_FILE')
        rejection('invalid-sha', ('--rom-file',str(ROM),'--rom-sha256','ff00'),
                  'ROM_INVALID_SHA256')
        rejection('duplicate-rom-option', (*explicit,'--rom-file',str(ROM)),
                  'ROM_DUPLICATE_PATH')

        def mutated(name, data, expected_code):
            p = base/(name+'.txt')
            p.write_bytes(data)
            sha = hashlib.sha256(data).hexdigest()
            rejection(name, ('--rom-file',str(p),'--rom-sha256',sha),expected_code)

        mutated('nonascii', rom.replace(b'3010\t00',b'3010\t\xef\xbf\xbd0',1), 'ROM_NON_ASCII')
        mutated('missing-known', b'\n'.join(line for line in rom.split(b'\n')
                if not line.startswith(b'3010\t')),'ROM_MISSING_REQUIRED_WORD')
        line = next(x for x in rom.splitlines() if x.startswith(b'3010\t'))
        mutated('duplicate-address', rom+line+b'\r\n','ROM_DUPLICATE_ADDRESS')
        mutated('overwide-raw-word',rom.replace(b'3010\t00 0001',b'3010\t77 0001',1),
                'ROM_OVERWIDE_WORD')
        mutated('extra-token', rom.replace(b'3010\t00 0001 0000 0000',
                b'3010\t00 0001 0000 0000 extraneous',1),'ROM_INVALID_RECORD')
        mutated('outside-ROM-address', rom.replace(b'3010\t',b'3000\t',1),
                'ROM_ADDRESS_OUTSIDE_FIXED_RANGE')
        bad_octal = rom.replace(b'3010\t00',b'3010\t0X',1)
        mutated('invalid-octal',bad_octal, 'ROM_INVALID_OCTAL_DIGIT')
        bad_path = base/'invalid-octal-without-sha.txt'
        bad_path.write_bytes(bad_octal)
        rejection('invalid-octal-without-sha',
                  ('--rom-file',str(bad_path)), 'ROM_INVALID_OCTAL_DIGIT')
        # User-provided full ROM can include 3200, but this must never be
        # represented as an established historical reconstruction.
        full = rom.replace(b'3201\t',b'3200\t00 0000 0000 0000\r\n3201\t',1)
        full_path = base/'explicit-with-3200.txt'
        full_path.write_bytes(full)
        full_sha = hashlib.sha256(full).hexdigest()
        r4 = run('--rom-file',str(full_path),'--rom-sha256',full_sha)
        ok('explicit-3200', r4.returncode == 0 and
           'D15A3P3-ROM PASS SOURCE=EXPLICIT WORDS=184 UNKNOWN_3200=0' in r4.stdout,
           (r4.stdout,r4.stderr))

        # Reject default source missing, even if an image does not touch ROM.
        isolated = base/'isolated'/'bin'
        isolated.mkdir(parents=True)
        unrelated = isolated/'kyivemu.exe'
        shutil.copyfile(exe, unrelated)
        rejection('missing-default-rom', (), 'ROM_DEFAULT_NOT_FOUND',
                  executable=unrelated)

        # Exercise the actual default pinned hash, not merely explicit sha mode.
        (isolated/'mem').mkdir()
        (isolated/'mem'/'ROM.txt').write_bytes(rom + b'\n')
        rejection('mutated-default-rom', (), 'ROM_SHA256_MISMATCH', executable=unrelated)

        ok('source-image-immutable',test_image.read_bytes()==STOP and ROM.read_bytes()==rom)

    assert passed == 26, ('CASE_COUNT', passed)
    print('D15A3P3-NATIVE PASS CASES=26/26 DEFAULT_SHA_PIN=1 EXPLICIT_SHA=1 OPTIONAL_SHA=1 '
          'CWD_INDEPENDENT=1 LEGACY_UNMODIFIED=1 CPU_MUTATION=0 UNKNOWN_3200=1')

if __name__ == '__main__':
    main()
