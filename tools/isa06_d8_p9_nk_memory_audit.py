#!/usr/bin/env python3
"""D8-P9: validate bounded NK memory API and pinned immutable P8 sources.

The audit is structural, not a historical-hardware oracle. Always run the
C++ integration test and earlier regression tests before committing.
"""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'bbfb995'
PINS = {
    'inc/kyiv.h': '1d2afebf5c05ccd8e875451aab9ce864e04dc7be',
    'src/main.cpp': 'f84acfb22fa3e00f598f3cdb05d4ed2a6618f893',
    'mem/ROM.txt': 'bb6224e130c59564a8ccc4b224c55e41e50784a3',
    'tools/isa06_d8_p8_nk_selector_reference.py': '6985ee599103ca9bcb8c70632ae50c77828511e7',
}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def ensure(ok, reason):
    if not ok:
        raise AssertionError(reason)

def contents(path):
    return (ROOT / path).read_text(encoding='utf-8')

def check():
    for path, sha in PINS.items():
        ensure(git('rev-parse', f'{BASE}:{path}') == sha, 'Pinned baseline drift: ' + path)
    # HEAD may be P8 before commit or P9 after commit. In both cases the CPU,
    # reference-model and ROM source blobs must not change.
    for path in ('src/main.cpp', 'mem/ROM.txt', 'tools/isa06_d8_p8_nk_selector_reference.py'):
        ensure(git('rev-parse', f'HEAD:{path}') == PINS[path], 'Committed source drift: ' + path)
        ensure(not git('diff', '--', path), 'Unstaged mutable source: ' + path)
        ensure(not git('diff', '--cached', '--', path), 'Staged mutable source: ' + path)

    panel = contents('inc/kyiv_nk_panel.h')
    header = contents('inc/kyiv.h')
    docs = contents('docs/ISA_06_D8_P9_NK_MEMORY_INTEGRATION.md')
    contract = contents('docs/ISA_06_D8_P9_INTERFACE_CONTRACT.tsv').splitlines()
    manifest = contents('docs/ISA_06_D8_P9_SOURCE_MANIFEST.tsv')
    probe = contents('tests/isa/isa06_d8_p9_nk_memory_integration_probe.cpp')

    for token in ('first_addr = 03000', 'last_addr = 03002',
                  'word_mask = (std::uint64_t{1} << 41) - 1',
                  'std::array<std::uint64_t, 3> panel_words_{}',
                  'std::array<bool, 3> selected_{}',
                  'std::array<bool, 3> configured_{}',
                  'enabled && !configured_[i]', 'word & ~word_mask',
                  'return panel_words_[i]'):
        ensure(token in panel, 'Missing panel contract: ' + token)
    for token in ('#include "kyiv_nk_panel.h"', 'Kyiv_NK_panel_t nk_panel_;',
                  'Kyiv_NK_panel_t::is_selectable(addr)',
                  'nk_panel_.is_panel_selected(addr)',
                  'nk_panel_.panel_word(addr)',
                  'void set_panel_nk_word(', 'void select_panel_nk(',
                  'bool is_panel_nk_selected('):
        ensure(token in header, 'Missing memory integration: ' + token)
    ensure(header.count('nk_panel_.panel_word(addr)') == 1, 'Multiple memory source overlays')
    ensure('return mem_array_m[addr];' in header, 'Cabinet fallback lost')
    ensure(len(contract) == 4 and
           [line.split('\t', 1)[0] for line in contract[1:]] == ['3000', '3001', '3002'],
           'Three selectable NK cells required')
    ensure('NO_HARDWARE_PANEL_IMPLEMENTATION' not in contract[0], 'Old P8 contract reused')
    ensure('POLICY' in docs and 'STRICT' in docs and 'bbfb995' in manifest,
           'Missing qualification boundary')
    for token in ('for (unsigned bits = 0; bits < 8; ++bits)',
                  'MASK + 1', 'unconfigured panel selection accepted',
                  "0'31'3000'0022'0177ULL", 'policy == 12'):
        ensure(token in probe, 'Missing essential test: ' + token)
    print('ISA-06 D8-P9: NK3000..3002 CABINET/PANEL SOURCE SOFTWARE INTEGRATION; ALL NEW BEHAVIOR POLICY')
    print('NK-INTEGRATION-CHECK PASS base=bbfb995 selectable=3 configurations=8 ' +
          'guards=3 opcode31=2 signed_zero_distinct=1 panel_defaults=FAIL_CLOSED ' +
          'P8_REF_BLOB=PINNED CPU_BLOB=PINNED ROM_BLOB=PINNED ' +
          'historical_initial_switch_positions=OPEN')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.parse_args()
    check()
