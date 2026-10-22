#!/usr/bin/env python3
"""D15/A2 exact-blob, exact-scope, source-contract audit (read-only precommit)."""
import argparse
from pathlib import Path
import hashlib
import subprocess

BASE='68fa06f247f3b3a70ba37a72283469b6cec6b137'
ROOT=Path(__file__).resolve().parents[1]
PINS={'src/main.cpp': '79604ea237e090e99f9da980c9b00567ae7bd804', 'src/asm_disasm.cpp': 'cef71de85aec29878207ed91e08f1d6e698baa19', 'inc/kyiv.h': '7134240ee47838fb8dca57d12b4d149d4c496e27', 'inc/kyiv_drum_cli_v1.h': '3925ec9503b92c614a43f877686a47fc6884a2b6', 'tools/isa07_d15a1_run_image.cpp': '49865ba58d3f6fa22dd0245d57cf9fd1fadcb2ae'}
NEW=set(['inc/kyiv_host_image_v1.h', 'docs/ISA_07_D15A2_CLI_IMAGE_CONTRACT.md', 'docs/ISA_07_D15A2_DECISION_LEDGER.tsv', 'tools/isa07_d15a2_cli_sandbox.py', 'tools/isa07_d15a2_audit.py'])
MOD=set(['src/asm_disasm.cpp', 'tools/isa07_d15a1_run_image.cpp'])
CONTENT_SHA={'inc/kyiv_host_image_v1.h': '3a54f9ad5fe5509f1823fcae7af21c8a70374702e89f6018d36917516c174511', 'docs/ISA_07_D15A2_CLI_IMAGE_CONTRACT.md': '382e9399c46de94b25c00a7c4f15ea1282e30f22b9abdc1384eecbf313ae78a5', 'docs/ISA_07_D15A2_DECISION_LEDGER.tsv': 'fe8623603f818469ba6a59efab7faef9ea233e8cc1b4c4d1680d7709f9cfba79', 'tools/isa07_d15a2_cli_sandbox.py': 'aea6d67cf6635e64d18af0e50ca6fc5211c9154b73a0409cabe384ceac44ebe8', 'tools/isa07_d15a1_run_image.cpp': 'b1d5e01fbc64d604f00dcc343e97e94214332ead2970367d36201c7e6714aa39'}

def need(ok,code):
    if not ok: raise RuntimeError(code)

def git(*args):
    p=subprocess.run(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    need(p.returncode==0,'GIT_FAILED: '+p.stderr[-300:].decode('utf-8','replace'))
    return p.stdout

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def transform_cli(original: bytes) -> bytes:
    include = b'#include "kyiv_drum_cli_v1.h"\n'
    help_anchor = b'        std::cerr << "Optional trailing flag for all modes: --block-overflow-stop" << std::endl;\n'
    main_anchor = b'    Kyiv_t machine;\n'
    for token in (include, help_anchor, main_anchor):
        need(original.count(token) == 1, 'PATCH_ANCHOR_MISSING_OR_DUPLICATE')
    out = original.replace(include, include + b'#include "kyiv_host_image_v1.h"\n', 1)
    out = out.replace(help_anchor, b'        std::cerr << "./kyivemu image <file.k41> <start-octal> <max-steps-decimal> [--allow-rom] [--watch ADDR]..." << std::endl;\n' + help_anchor, 1)
    out = out.replace(main_anchor, b'    if (mode == "image") {\n        try {\n            if (parsed.drum || block_overflow_stop)\n                throw std::runtime_error("IMAGE_SUFFIX_UNSUPPORTED");\n            const auto cfg = kyiv_host_image_v1::parse(argc - 1, argv + 1);\n            const auto image = kyiv_host_image_v1::load_file(cfg.filename,\n                                                             cfg.allow_rom);\n            Kyiv_t image_machine;\n            return kyiv_host_image_v1::execute(image_machine, cfg, image,\n                                                "D15A2");\n        } catch (const std::exception& e) {\n            std::cerr << "D15A2-ERROR " << e.what() << \'\\n\';\n            return 2;\n        } catch (...) {\n            std::cerr << "D15A2-ERROR UNKNOWN_EXCEPTION\\n";\n            return 2;\n        }\n    }\n' + main_anchor, 1)
    need(out != original and out.count(b'D15A2-ERROR') == 2, 'PATCH_INTERNAL_ERROR')
    return out

def self_test():
    need(len(PINS)==5 and all(len(v)==40 for v in PINS.values()),'PIN_SET_INVALID')
    need(len(NEW)==5 and len(MOD)==2 and not NEW.intersection(MOD),'SCOPE_INVALID')
    need(len(CONTENT_SHA)==5 and all(len(v)==64 for v in CONTENT_SHA.values()),'SHA_SET_INVALID')
    need(b'D15A2-ERROR' in transform_cli(
        b'#include "kyiv_drum_cli_v1.h"\n'+
        b'        std::cerr << "Optional trailing flag for all modes: --block-overflow-stop" << std::endl;\n'+
        b'    Kyiv_t machine;\n'), 'TRANSFORM_SELFTEST')
    try:
        transform_cli(b'unsuitable')
    except RuntimeError:
        pass
    else:
        raise RuntimeError('MUTANT_NOT_REJECTED')
    print('D15A2-AUDIT-SELFTEST PASS PINS=5/5 NEW=5/5 MOD=2/2 CONTENT_SHA=5/5 MUTANT_REJECTED=1')

def audit():
    need(git('rev-parse','HEAD').strip().decode()==BASE,'BASELINE_MISMATCH')
    need(git('branch','--show-current').strip()==b'main','NOT_MAIN')
    need(git('rev-parse','--show-prefix').strip()==b'','NOT_REPO_ROOT')
    need(not git('diff','--cached','--name-only').strip(),'STAGED_MUTATION')
    untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
    need(untracked==NEW,'UNTRACKED_SCOPE_MISMATCH: '+repr(sorted(untracked ^ NEW)))
    modified=set(git('diff','--name-only','--diff-filter=ACMRTUXB').decode().splitlines())
    need(modified==MOD,'TRACKED_SCOPE_MISMATCH: '+repr(sorted(modified ^ MOD)))
    for path,blob in PINS.items():
        need(git('rev-parse','HEAD:'+path).strip().decode()==blob,'PIN_MISMATCH: '+path)
    for path,digest in CONTENT_SHA.items():
        need(hash_file(ROOT/path)==digest,'CONTENT_MISMATCH: '+path)
    original=git('show',BASE+':src/asm_disasm.cpp')
    need((ROOT/'src/asm_disasm.cpp').read_bytes()==transform_cli(original),
         'CLI_PATCH_DEVIATES_FROM_ALLOWED_INSERTIONS')
    header=(ROOT/'inc/kyiv_host_image_v1.h').read_text(encoding='utf-8')
    wrapper=(ROOT/'tools/isa07_d15a1_run_image.cpp').read_text(encoding='utf-8')
    cli=(ROOT/'src/asm_disasm.cpp').read_text(encoding='utf-8')
    need('kyiv_host_image_v1::parse' in wrapper and
         'kyiv_host_image_v1::execute' in wrapper and
         'kyiv_host_image_v1::parse' in cli and
         'kyiv_host_image_v1::execute' in cli and
         'MAX_STEPS_DECIMAL' in header, 'SHARED_COMPONENT_CONTRACT_MISSING')
    print('D15A2-AUDIT PASS BASELINE=68fa06f PINS=5/5 NEW=5/5 MOD=2/2 '
          'CONTENT_SHA=5/5 CLI_EXACT_INSERTIONS=1 CPU_MUTATION=0 '
          'A1_SHARED_COMPONENT=1 REAL_NATIVE_GATE=PENDING '
          'ROM_BASELINE=OPEN HISTORICAL_CORPUS=PENDING HARDWARE_ORACLE=0')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    self_test() if a.self_test else audit()
