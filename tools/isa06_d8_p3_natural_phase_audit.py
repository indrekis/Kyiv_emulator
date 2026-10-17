#!/usr/bin/env python3
"""D8-P3 documentary/structural check; not a hardware timing or ISA oracle."""
import argparse
import csv
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
D5 = ROOT / 'tests/isa/isa06_d5_historical_ram_iterations_probe.cpp'
P2 = ROOT / 'tests/isa/isa06_d8_p2_historical_ram_policy_probe.cpp'
P3 = ROOT / 'tests/isa/isa06_d8_p3_natural_phase_walk_probe.cpp'
DOC = ROOT / 'docs/ISA_06_D8_P3_NATURAL_PHASE_GATE.md'
GATES = ROOT / 'docs/ISA_06_D8_P3_NATURAL_GATES.tsv'
MANIFEST = ROOT / 'docs/ISA_06_D8_P3_SOURCE_MANIFEST.tsv'
EXPECTED_BLOBS = {
    'tests/isa/isa06_d5_historical_ram_iterations_probe.cpp': '979bc8317cf2ec4d660f750a0d24bb2cef0510f6',
    'tests/isa/isa06_d8_p2_historical_ram_policy_probe.cpp': 'daf9afb0bee3771511f9b85e1826a41ba90eddbb',
}
EXTRA = {
    0o120: "0'01'3012'0000'0017ULL",
    0o121: "0'01'0017'0000'0021ULL",
    0o137: "0'01'0017'0000'0021ULL",
    0o156: "0'13'3012'0017'0017ULL",
    0o157: "0'16'0017'3042'0161ULL",
    0o160: "0'05'0000'0000'0121ULL",
}
WORD = re.compile(r"\{\s*(0[0-7]{3})\s*,\s*(0'[0-7]{2}'[0-7]{4}'[0-7]{4}'[0-7]{4}ULL)\s*\}")

def git_blob(path):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:'+path],cwd=ROOT,text=True).strip()

def words_in(text, var):
    m=re.search(r'constexpr HistoricalWord\s+'+var+r'\[\]\s*=\s*\{(.*?)\};',text,re.S)
    assert m, f'{var} historical array missing'
    pairs=WORD.findall(m.group(1))
    rows={int(p,8):word for p,word in pairs}
    assert len(rows)==len(pairs), f'{var} duplicate PC'
    return rows

def rows_for(path):
    with path.open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    return rows

def run(show):
    for path,expected in EXPECTED_BLOBS.items():
        assert git_blob(path)==expected, f'Git source changed: {path}'
    txt5=D5.read_bytes().replace(b'\r\n',b'\n').decode('utf-8')
    txt2=P2.read_bytes().replace(b'\r\n',b'\n').decode('utf-8')
    txt3=P3.read_bytes().replace(b'\r\n',b'\n').decode('utf-8')
    five=words_in(txt5,'HIST')
    two=words_in(txt2,'HIST')
    three=words_in(txt3,'HIST')
    bridge=words_in(txt3,'BRIDGE')
    assert len(five)==len(two)==len(three)==27, '27 original body words required'
    assert five==two==three, 'D5/P2/P3 historical body word drift'
    assert bridge==EXTRA, 'P3 six original bridge words drift'
    assert len(set(three)|set(bridge))==33, 'historical PC overlap'
    manifests=rows_for(MANIFEST)
    gates=rows_for(GATES)
    assert len(manifests)==3 and len(gates)==5, 'incorrect manifest/gate counts'
    assert [g['gate'] for g in gates]==['entry','write_sweep','write_read_handoff','read_sweep','natural_reentry']
    assert all(g['class']=='POLICY' for g in gates), 'must not promote fixture execution to STRICT'
    assert manifests[0]['sha256_or_git_blob']=='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
    assert manifests[1]['sha256_or_git_blob']==EXPECTED_BLOBS['tests/isa/isa06_d5_historical_ram_iterations_probe.cpp']
    assert manifests[2]['sha256_or_git_blob']==EXPECTED_BLOBS['tests/isa/isa06_d8_p2_historical_ram_policy_probe.cpp']
    assert 'MAX_STEPS = 25000' in txt3 and 'CELLS = RAM_LAST - RAM_FIRST + 1' in txt3
    assert '0137' in txt3 and '0156' in txt3 and '0160' in txt3
    assert (0o1777-0o200+1)==896
    for path in [P3, DOC, GATES, MANIFEST,Path(__file__)]:
        for i,line in enumerate(path.read_bytes().replace(b'\r\n',b'\n').split(b'\n'),1):
            assert line==line.rstrip(b' \t'),f'trailing whitespace {path.name}:{i}'
    print('ISA-06 D8-P3: NATURAL PHASE ENTRY QUALIFICATION ONLY; NOT CERTIFIED KYIV HARDWARE')
    print('PHASE-CHECK PASS original_body=27 bridge=6 total_words=33 gates=5 ram_cells=896 D5_BLOB=PINNED P2_BLOB=PINN signed_zero=POLICY rom=FIXTURE')
    if show:
        for row in gates:
            print(f"{row['gate']:<20} {row['start_pc']} -> {row['end_pc']} [{row['class']}] {row['assertion']}")

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--show-gates',action='store_true')
    a=ap.parse_args()
    run(a.show_gates)
