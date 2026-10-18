#!/usr/bin/env python3
"""W1 read-only source-delta audit; pins full Git blobs, LF/CRLF tolerant."""
from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess
import sys

BASE = 'd6d435b3147053e65a7f6d0f7c2c0f4d6d4a7095'
PINS = {
    'src/main.cpp': '1f7400708613a93d783a5a206f59d2057d31b75f',
    'inc/kyiv.h': 'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
}
DOC_SHA256 = '1943b4dee32bcbda9b503d20fb3dd1e1273f03f280a2e18ff36715b9ee17dc42'

# Exact line/block substitutions; source text comes from git show HEAD:path.
SRC_RULES = (
    ('    constexpr word_t Addr_3_mask_shift = 0; // Для одноманітності\n', ''),
    ('static word_t parse_kyiv_number(const char* str) {\n'
     '    long long val = std::stoll(str);\n'
     '    if (val < 0) {\n'
     '        return to_negative(static_cast<word_t>(-val));\n'
     '    }\n'
     '    return static_cast<word_t>(val);\n'
     '}\n\n', ''),
    ('            int num_counter = 0;\n', '            addr_t num_counter = 0;\n'),
    ('        uint16_t leftmost = leftmost_one(res_mul);\n', ''),
)
HDR_RULES = ((
    '    aproxy(word_t& r, addr_t addres) : mPtr(&r), ref(addres) {}\n',
    '    aproxy(word_t& r, addr_t addres) : ref(addres), mPtr(&r) {}\n',
),)

def run_git(*args: str) -> str:
    return subprocess.check_output(('git', *args), stderr=subprocess.PIPE, text=True).strip()

def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)

def normalize(raw: bytes) -> bytes:
    require(b'\r' not in raw.replace(b'\r\n', b''), 'BARE_CR')
    return raw.replace(b'\r\n', b'\n')

def expected(base: bytes, rules: tuple[tuple[str,str], ...]) -> bytes:
    s = normalize(base).decode('utf-8')
    for old,new in rules:
        # Decode backslash escapes in the static rule notation without eval.
        old = old.replace('\\n','\n')
        new = new.replace('\\n','\n')
        require(s.count(old)==1, 'SOURCE_ANCHOR_UNEXPECTED_COUNT')
        s=s.replace(old,new,1)
    return s.encode('utf-8')

def main() -> int:
    try:
        require(run_git('rev-parse','--show-prefix')=='', 'RUN_AT_REPO_ROOT')
        require(run_git('rev-parse','HEAD')==BASE,'BASE_HEAD_DRIFT')
        require(run_git('diff','--cached','--name-only')=='','STAGED_MUTATION')
        actual=set(run_git('diff','--name-only').splitlines())
        require(actual==set(PINS),'TRACKED_DELTA_NOT_EXACT_TWO_FILES')
        for path, sha in PINS.items():
            require(run_git('rev-parse',f'HEAD:{path}')==sha,'GIT_BLOB_PIN '+path)
            original=subprocess.check_output(['git','show',f'HEAD:{path}'])
            rules=SRC_RULES if path=='src/main.cpp' else HDR_RULES
            target=expected(original, rules)
            require(normalize(Path(path).read_bytes())==target,'DELTA_NOT_EXACT '+path)
        doc=Path('docs/W1_COMPILER_WARNING_CLEANUP.md')
        require(doc.is_file() and hashlib.sha256(normalize(doc.read_bytes())).hexdigest()==DOC_SHA256,'DOC_SHA')
        require(Path('tools/w1_warning_audit.py').is_file(),'AUDITOR_MISSING')
        allowed=set(PINS)|{'docs/W1_COMPILER_WARNING_CLEANUP.md','tools/w1_warning_audit.py'}
        untracked=run_git('ls-files','--others','--exclude-standard').splitlines()
        require(set(untracked)==allowed-set(PINS),'UNTRACKED_DELTA_NOT_EXACT_TWO_FILES')
        subprocess.run(['git','diff','--check'],check=True)
        print('W1-AUDIT PASS BASELINE=d6d435b CPU_PIN=1 HEADER_PIN=1 EDITS=5/5 '
              'TRACKED=2/2 NEW_FILES=2/2 EOL_PORTABLE=1 IO24_CONTROL_UNCHANGED=1 '
              'MUL_DATAFLOW_UNCHANGED=1 HARDWARE_ORACLE=0')
        return 0
    except (OSError,UnicodeError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
        print('W1-AUDIT FAIL',str(e),file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
