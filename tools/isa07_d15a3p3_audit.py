#!/usr/bin/env python3
"""D15/A3-P3 strict, CRLF-safe exact-source audit. Never mutates files."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '372fc2fc5fe0d5e48fe0087d6e47066f3b7ae8bc'
SOURCE_BLOBS = {
    'inc/kyiv.h': '84cfc63a905f714f9f0cbe8ba26475d4579eec86',
    'src/asm_disasm.cpp': 'c214fd272047754ea30f209651b5dc8f1a9c302e',
    'inc/kyiv_host_image_v1.h': '60b259d83e32aee174dca5a09c91a21fc0d3e4a7',
    'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1',
}
MOD = ('inc/kyiv.h','src/asm_disasm.cpp')
NEW = (
  'inc/kyiv_sha256_v1.h',
  'inc/kyiv_rom_boot_v1.h',
  'tools/isa07_d15a3p3_rom_runtime_sandbox.py',
  'tools/isa07_d15a3p3_audit.py',
  'docs/ISA_07_D15A3P3_ROM_RUNTIME_CONTRACT.md',
  'docs/ISA_07_D15A3P3_DECISION_LEDGER.tsv',
)

def swap(src, old, new):
    old, new = old.encode('utf-8'), new.encode('utf-8')
    if src.count(old) != 1:
        raise RuntimeError('PATCH_ANCHOR_MISSING_OR_DUPLICATE')
    return src.replace(old, new)

def transform(path, src):
    if path == 'inc/kyiv.h':
        return swap(src, '    Kyiv_t() {', '''    // D15/A3-P3: image mode starts from explicitly verified HOST ROM.
    // The default mode preserves all existing legacy constructor behavior.
    enum class rom_boot_mode { legacy_cwd, deferred };
    explicit Kyiv_t(rom_boot_mode mode = rom_boot_mode::legacy_cwd) {
        if (mode == rom_boot_mode::deferred) return;''')
    if path == 'src/asm_disasm.cpp':
        src = swap(src, '#include "kyiv_host_image_v1.h"',
                    '#include "kyiv_host_image_v1.h"\n#include "kyiv_rom_boot_v1.h"')
        src = swap(src, '''            const auto cfg = kyiv_host_image_v1::parse(argc - 1, argv + 1);
            const auto image = kyiv_host_image_v1::load_file(cfg.filename,
                                                             cfg.allow_rom);
            Kyiv_t image_machine;
            return kyiv_host_image_v1::execute(image_machine, cfg, image,
                                                "D15A2");''', '''            const auto rom_args = kyiv_rom_boot_v1::extract(argc - 1, argv + 1);
            const auto cfg = kyiv_host_image_v1::parse(
                static_cast<int>(rom_args.forwarded.size()),
                rom_args.forwarded.data());
            const auto image = kyiv_host_image_v1::load_file(cfg.filename,
                                                             cfg.allow_rom);
            // ROM and program preflight complete before CPU construction.
            const auto rom = kyiv_rom_boot_v1::read(rom_args, argv[0]);
            Kyiv_t image_machine(Kyiv_t::rom_boot_mode::deferred);
            kyiv_rom_boot_v1::install(image_machine, rom);
            std::cout << "D15A3P3-ROM PASS SOURCE="
                      << (rom.source_is_default ? "DEFAULT" : "EXPLICIT")
                      << " WORDS=" << rom.words.size()
                      << " UNKNOWN_3200=" << (rom.unknown_3200 ? 1 : 0)
                      << " SHA256=" << rom.sha256 << '\\n';
            return kyiv_host_image_v1::execute(image_machine, cfg, image,
                                                "D15A2");''')
        src = swap(src,
                   r"""                      << " SHA256=" << rom.sha256 << '\n';""",
                   r"""                      << " SHA256=" << rom.sha256
                      << " SHA_PINNED=" << (rom.sha_pinned ? 1 : 0) << '\n';""")
        return src
    raise ValueError(path)


def original_canonical(local):
    if b'\r' not in local: return local
    if local.count(b'\r\n') != local.count(b'\n'):
        raise RuntimeError('MIXED_NEWLINES')
    return local.replace(b'\r\n', b'\n')


def transform_local(path, original):
    canonical = original_canonical(original)
    changed = transform(path, canonical)
    return changed.replace(b'\n', b'\r\n') if b'\r\n' in original else changed

ROM_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
NEW_SHA = {
    'inc/kyiv_sha256_v1.h': '27d1406c7776dcf94bbf1b14a3a014adff58b2de5125cd4f78cc131bc8344f43',
    'inc/kyiv_rom_boot_v1.h': '8c9b3a28419914d037fdc913cf0f6d19a88c4e2e823755c9b9380e11cac46e6d',
    'tools/isa07_d15a3p3_rom_runtime_sandbox.py': '23b60c0820ff6503879730d3b0ff4556d96c4bf7e8497024f599ee2f491ce1f5',
    'docs/ISA_07_D15A3P3_ROM_RUNTIME_CONTRACT.md': '7647da5fd3f1bb0311b488762be1ab670cd7b4025ebe2d0e71cf5989506c1c18',
    'docs/ISA_07_D15A3P3_DECISION_LEDGER.tsv': '60d3b674d40b03340860366ee5c3d0f3ba4a9cfa7ae586b0f635af24e902480e',
}

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def require(cond,code):
    if not cond: raise AssertionError(code)

def check():
    require(git('rev-parse','HEAD').decode().strip() == BASE, 'WRONG_BASE')
    require(git('branch','--show-current').decode().strip() == 'main', 'WRONG_BRANCH')
    require(git('rev-parse','--show-prefix').strip() == b'', 'NOT_ROOT')
    require(git('diff','--cached','--name-only') == b'', 'STAGED_CHANGE')
    for rel,sha in SOURCE_BLOBS.items():
        require(git('rev-parse',f'HEAD:{rel}').decode().strip()==sha,('GIT_BLOB_PIN',rel))
    require(hashlib.sha256((ROOT/'mem/ROM.txt').read_bytes()).hexdigest() == ROM_SHA,'ROM_RAW_SHA')
    require(git('diff','--name-only').decode().splitlines() == sorted(MOD), 'MOD_SCOPE')
    for path in MOD:
        expected = transform(path, git('show',f'HEAD:{path}'))
        current = original_canonical((ROOT/path).read_bytes())
        require(current==expected,('EXACT_MODIFIED_CONTENT',path))
    require(set(git('ls-files','--others','--exclude-standard').decode().splitlines())==set(NEW),'NEW_SCOPE')
    for p in NEW:
        require((ROOT/p).is_file(),('NEW_MISSING',p))
    for path,sha in NEW_SHA.items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,('NEW_SHA',path))
    require((ROOT/'mem/ROM.txt').read_bytes().count(b'3200\t')==0,'UNKNOWN_3200_KEPT')
    print('D15A3P3-AUDIT PASS BASELINE=372fc2f SOURCE_PINS=4/4 MOD=2/2 '
          'NEW=6/6 CONTENT_SHA=5/5 ROM_SHA_PIN=1 OPTIONAL_CUSTOM_SHA=1 UNKNOWN_3200=1 '
          'CPU_SEMANTICS_MUTATION=0 REAL_NATIVE_GATE=PENDING HARDWARE_ORACLE=0')

def selftest():
    sample=b'a\r\n    Kyiv_t() {\r\nb\r\n'
    assert original_canonical(sample)==b'a\n    Kyiv_t() {\nb\n'
    assert transform_local('inc/kyiv.h',sample).count(b'rom_boot_mode')==4
    try:
        transform('inc/kyiv.h',b'    Kyiv_t() {\n    Kyiv_t() {')
    except RuntimeError as e:
        assert str(e)=='PATCH_ANCHOR_MISSING_OR_DUPLICATE'
    else:
        raise AssertionError('MUTANT_ACCEPTED')
    try:
        original_canonical(b'a\r\nb\n')
    except RuntimeError as e:
        assert str(e)=='MIXED_NEWLINES'
    else:
        raise AssertionError('MIXED_NEWLINES_ACCEPTED')
    print('D15A3P3-AUDIT-SELFTEST PASS CRLF=1 MUTANTS_REJECTED=2/2')

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        selftest()
    elif sys.argv[1:] == []:
        check()
    else:
        raise SystemExit('USAGE: [--self-test]')
