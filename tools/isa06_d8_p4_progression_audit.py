#!/usr/bin/env python3
"""P4 literal/evidence guard: source integrity, not emulator runtime or hardware oracle."""
import argparse
import csv
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
P3 = ROOT / 'tests/isa/isa06_d8_p3_natural_phase_walk_probe.cpp'
P4 = ROOT / 'tests/isa/isa06_d8_p4_multi_pattern_probe.cpp'
DOC = ROOT / 'docs/ISA_06_D8_P4_MULTI_PATTERN_QUALIFICATION.md'
GATES = ROOT / 'docs/ISA_06_D8_P4_PROGRESSION_GATES.tsv'
MANIFEST = ROOT / 'docs/ISA_06_D8_P4_SOURCE_MANIFEST.tsv'
P3_BLOB = 'd4c181f967bc2fe327fddd35b6fea69bfa88b916'
D5_BLOB = '979bc8317cf2ec4d660f750a0d24bb2cef0510f6'
P2_BLOB = 'daf9afb0bee3771511f9b85e1826a41ba90eddbb'
EXTRA = {
    0o161: "0'31'0014'0162'0164ULL",
    0o162: "0'02'0000'0000'0014ULL",
    0o163: "0'05'0000'0000'0120ULL",
    0o164: "0'31'3000'0022'0177ULL",
    0o165: "0'33'0000'0001'0077ULL",
    0o166: "0'33'0000'0003'0177ULL",
}
WORD = re.compile(r"\{\s*(0[0-7]{3})\s*,\s*(0'[0-7]{2}'[0-7]{4}'[0-7]{4}'[0-7]{4}ULL)\s*\}")

def git_blob(relpath):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:' + relpath],
                                   cwd=ROOT, text=True).strip()

def historical_words(text, var):
    m = re.search(r'constexpr HistoricalWord\s+' + var + r'\[\]\s*=\s*\{(.*?)\};',
                  text, flags=re.S)
    assert m, f'missing {var} historical words'
    pairs = WORD.findall(m.group(1))
    result = {int(pc, 8): word for pc, word in pairs}
    assert len(result) == len(pairs), f'duplicate historical PC in {var}'
    return result

def normalized(path):
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    assert b'\r' not in raw, f'unsupported line endings in {path}'
    return raw.decode('utf-8')

def table(path):
    with path.open(encoding='utf-8', newline='') as f:
        rdr = csv.DictReader(f, delimiter='\t')
        rows = list(rdr)
        assert all(None not in row and None not in row.values() for row in rows), f'TSV schema drift {path}'
        return rows

def main(show):
    assert git_blob('tests/isa/isa06_d8_p3_natural_phase_walk_probe.cpp') == P3_BLOB, 'P3 Git blob drift'
    assert git_blob('tests/isa/isa06_d5_historical_ram_iterations_probe.cpp') == D5_BLOB, 'D5 Git blob drift'
    assert git_blob('tests/isa/isa06_d8_p2_historical_ram_policy_probe.cpp') == P2_BLOB, 'P2 Git blob drift'
    p3 = normalized(P3)
    p4 = normalized(P4)
    body3 = historical_words(p3, 'HIST')
    bridge3 = historical_words(p3, 'BRIDGE')
    body4 = historical_words(p4, 'HIST')
    bridge4 = historical_words(p4, 'BRIDGE')
    tail4 = historical_words(p4, 'TAIL')
    assert len(body3) == len(body4) == 27 and body3 == body4, 'historical D5/P3 body drift'
    assert len(bridge3) == len(bridge4) == 6 and bridge3 == bridge4, 'historical P3 bridge drift'
    assert tail4 == EXTRA, 'historical terminal words drift'
    assert len(set(body4) | set(bridge4) | set(tail4)) == 39, 'overlap in historical PC'
    gates = table(GATES)
    sources = table(MANIFEST)
    assert len(gates) == 11 and len(sources) == 4, 'gate/manifest row count drift'
    assert [g['gate'] for g in gates] == [
        'first_entry', 'first_write_read', 'first_reentry', 'second_entry',
        'second_write_read', 'second_reentry', 'positive_terminal',
        'positive_sign_flip', 'positive_restart', 'negative_terminal',
        'terminal_after_0164',
    ], 'gate order drift'
    assert all(g['class'] == 'POLICY' for g in gates[:-1]), 'fixture promoted to STRICT'
    assert gates[-1]['class'] == 'OPEN' and gates[-1]['next_pc'] == 'UNEXECUTED'
    assert sources[0]['sha256_or_blob'] == 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
    assert [r['sha256_or_blob'] for r in sources[1:]] == [P3_BLOB, D5_BLOB, P2_BLOB]
    assert 'sweep(cpu,1,trace)' in p4 and 'sweep(cpu,2,trace)' in p4
    assert 'MAX_STEPS = 25000' in p4 and 'r.neg_writes!=r.neg_reads' in p4
    assert 'terminal_negative_0157_0161' in p4 and 'boundary=0164_UNEXECUTED' in p4
    assert 'std::ofstream out' in p4 and '--trace' in p4
    assert 'not' in normalized(DOC).lower() and 'POLICY' in normalized(DOC)
    assert (0o1777 - 0o200 + 1) == 896
    for path in (P4, DOC, GATES, MANIFEST, Path(__file__)):
        for line_number, line in enumerate(path.read_bytes().replace(b'\r\n', b'\n').split(b'\n'), 1):
            assert line == line.rstrip(b' \t'), f'trailing whitespace: {path.name}:{line_number}'
    print('ISA-06 D8-P4: TWO NATURAL SWEEPS + BOUNDED TERMINAL GATES; ALL BEHAVIOR POLICY')
    print('PROGRESSION-CHECK PASS body=27 bridge=6 tail=6 original_words=39 '
          'gates=11 ram_cells=896 P3_BLOB=PINNED D5_BLOB=PINNED P2_BLOB=PINNED '
          'terminal_0164=OPEN cpu=UNCHANGED')
    if show:
        for row in gates:
            print(f"{row['gate']:<24} {row['pc']:>5} -> {row['next_pc']:<11} [{row['class']}] {row['dependency']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--show-gates', action='store_true')
    options = parser.parse_args()
    main(options.show_gates)
