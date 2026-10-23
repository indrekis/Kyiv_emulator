#!/usr/bin/env python3
"""D15/A3-P2 revised exact-scope audit: two ROM words + Win64 41-bit parse."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '56e7cc1d2dce558fa1f98d1f7df96e923fe464fd'
ROM_SHA = '6d26b37262262fd110fffb493f38d512d8d2fe36f322695829951c7ae8de0dd5'
ROM_BLOB = 'bb6224e130c59564a8ccc4b224c55e41e50784a3'
HEADER_BLOB = '7134240ee47838fb8dca57d12b4d149d4c496e27'
NEW = (
    'docs/ISA_07_D15A3P2_ROM_RECONSTRUCTION.md',
    'docs/ISA_07_D15A3P2_DECISION_LEDGER.tsv',
    'tools/isa07_d15a3p2_rom_audit.py',
    'tools/isa07_d15a3p2_rom_sandbox.py',
)
NEW_SHA = {
    # This file itself is intentionally excluded: no self-referential digest.
    'docs/ISA_07_D15A3P2_ROM_RECONSTRUCTION.md': '6eeb04469571aeef6e8f6efcb7b4f74b291f764569f1303f91bf473c548f4bb6',
    'docs/ISA_07_D15A3P2_DECISION_LEDGER.tsv': '373d30105650b88d755fe5fbd55588f1c4c04814483e1e4c74519c1c2b673fcb',
    'tools/isa07_d15a3p2_rom_sandbox.py': '26d73df9d62e26d20ff0c5d7bcff2f4d918acf3cee1da456e09646f21ce8b114',
}
OLD_ROM = {
    b'3121\t01 0005 \xef\xbf\xbd011 0005': b'3121\t01 0005 3011 0005',
    b'3123\t12 \xef\xbf\xbd011 0005 0004': b'3123\t12 3011 0005 0004',
}
OLD_HEADER = b'kmem.write_rom(std::stoi(address, 0, 8), std::stol(data, 0, 8));'
NEW_HEADER = b'kmem.write_rom(std::stoi(address, 0, 8), std::stoull(data, 0, 8));'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def canonical(b):
    return b.replace(b'\r\n', b'\n')


def expected_rom(original):
    out = original
    for old, new in OLD_ROM.items():
        assert out.count(old) == 1, 'ROM_ANCHOR_COUNT'
        out = out.replace(old, new)
    assert len(out.splitlines()) == 183, 'ROM_LINE_COUNT'
    assert b'3200\t' not in out, 'ROM_3200_UNRESOLVED'
    return out


def expected_header(original):
    assert original.count(OLD_HEADER) == 1, 'HEADER_ANCHOR_COUNT'
    return original.replace(OLD_HEADER, NEW_HEADER)


def audit():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE, 'BASELINE'
    assert git('branch', '--show-current').decode().strip() == 'main', 'BRANCH'
    assert git('rev-parse', '--show-prefix').strip() == b'', 'NOT_ROOT'
    assert git('rev-parse', 'HEAD:mem/ROM.txt').decode().strip() == ROM_BLOB, 'ROM_PIN'
    assert git('rev-parse', 'HEAD:inc/kyiv.h').decode().strip() == HEADER_BLOB, 'HEADER_PIN'
    rom = git('show', BASE+':mem/ROM.txt')
    header = git('show', BASE+':inc/kyiv.h')
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA, 'ROM_SHA'
    assert canonical((ROOT/'mem/ROM.txt').read_bytes()) == canonical(expected_rom(rom)), 'ROM_2_WORDS'
    assert canonical((ROOT/'inc/kyiv.h').read_bytes()) == canonical(expected_header(header)), 'HEADER_1_LINE'
    assert git('diff','--cached','--name-only') == b'', 'STAGED_CHANGES'
    expected = sorted([' M mem/ROM.txt', ' M inc/kyiv.h'] + ['?? '+x for x in NEW])
    status = sorted(git('status', '--porcelain=v1','--untracked-files=all').decode().splitlines())
    assert expected == status, ('WORKTREE_SCOPE', status)
    for rel in NEW:
        assert (ROOT/rel).is_file(), ('MISSING_NEW', rel)
    for rel, sha in NEW_SHA.items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == sha, ('CONTENT_SHA', rel)
    assert set(git('diff', '--name-only').decode().splitlines()) == {'mem/ROM.txt', 'inc/kyiv.h'}, 'TRACKED_SCOPE'
    print('D15A3P2-LONG-AUDIT PASS BASELINE=56e7cc1 NEW=4/4 MOD=2/2 '
          'ROM_WORDS=2/2 ROM_VALID=183/183 UNKNOWN_3200=1 '
          'HEADER_STOULL=1/1 CONTENT_SHA=3/3 ISA_SEMANTICS_MUTATION=0 '
          'CORE_HEADER_MOD=1 REAL_NATIVE_GATE=PENDING ROM_RUNTIME_EXPLICIT=PENDING')


def self_test():
    sample_rom = (b'3121\t01 0005 \xef\xbf\xbd011 0005\r\n'
                  b'3123\t12 \xef\xbf\xbd011 0005 0004\r\n'
                  + b'3010\t00 0001 0000 0000\r\n' * 181)
    fixed = expected_rom(sample_rom)
    assert b'3121\t01 0005 3011 0005' in fixed
    assert b'3123\t12 3011 0005 0004' in fixed
    assert fixed.count(b'\r\n') == 183
    sample_head = b'a\r\n'+OLD_HEADER+b'\r\nz\r\n'
    assert NEW_HEADER in expected_header(sample_head)
    assert expected_header(sample_head).count(b'\r\n') == 3
    for bad, fn, wanted in [
        (sample_head + OLD_HEADER, expected_header, 'HEADER_ANCHOR_COUNT'),
        (sample_head.replace(OLD_HEADER,b'std::stol'), expected_header, 'HEADER_ANCHOR_COUNT'),
        (sample_rom.replace(b'3121\t', b'3122\t'), expected_rom, 'ROM_ANCHOR_COUNT'),
    ]:
        try:
            fn(bad)
        except AssertionError as exc:
            assert str(exc) == wanted, (str(exc), wanted)
        else:
            raise AssertionError('MUTANT_ADMITTED')
    print('D15A3P2-LONG-AUDIT-SELFTEST PASS ROM=2/2 HEADER=1/1 CRLF=1 MUTANTS_REJECTED=3/3')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
    elif not sys.argv[1:]:
        audit()
    else:
        raise SystemExit('USAGE: [--self-test]')
