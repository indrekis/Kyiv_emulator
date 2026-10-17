#!/usr/bin/env python3
"""Structural audit of D8-P2 original-word/PC trace; NOT a hardware oracle."""
import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
P2=ROOT/'tests/isa/isa06_d8_p2_historical_ram_policy_probe.cpp'
D5=ROOT/'tests/isa/isa06_d5_historical_ram_iterations_probe.cpp'
WALK=ROOT/'docs/ISA_06_D8_P2_EXPECTED_WALK.tsv'
MAN=ROOT/'docs/ISA_06_D8_P2_SOURCE_MANIFEST.tsv'
PAIRS=[('write_zero','WRITE_NEG_ZERO'),('write_one','WRITE_POS_ONE'),('read_zero','READ_NEG_ZERO'),('read_one','READ_POS_ONE')]

def oct_words(s):
    match=re.search(r'constexpr HistoricalWord HIST\[\] = \{(.*?)\n\};',s,re.S)
    assert match, 'HistoricalWord table not found'
    words=re.findall(r'\{(0[0-7]+),\s*(0\x27[0-7\x27]+ULL)\}',match.group(1))
    assert len(words)==27, '27 original words expected'
    assert len({a for a,b in words})==27, 'duplicate original PC'
    return words

def trace_array(s,label):
    match=re.search(r'const std::vector<Transition> '+label+r'=\{(.*?)\n\};',s,re.S)
    assert match, f'missing {label}'
    items=re.findall(r'\{(0[0-7]+),(0[0-7]+)\}',match.group(1))
    assert len(items)==8, f'{label} should have 8 steps'
    return items

def run(show=False):
    new=P2.read_text();old=D5.read_text()
    assert oct_words(new)==oct_words(old), 'original historical words diverged from D5'
    with WALK.open(newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
    assert len(rows)==32
    assert all(x['pc_oct'] in {a for a,b in oct_words(new)} for x in rows)
    for phase,label in PAIRS:
        group=[r for r in rows if r['phase']==phase]
        assert len(group)==8
        expect=trace_array(new,label)
        assert [(r['pc_oct'],r['next_pc_oct']) for r in group]==expect, f'{phase} differs from C++'
        assert [r['ordinal'] for r in group]==list(map(str,range(1,9)))
        for (pc,nxt),(next_pc,_) in zip(expect,expect[1:]):
            assert nxt==next_pc, f'broken trace in {phase} after {pc}'
    assert trace_array(new,'WRITE_NEG_ZERO')[-1][1]==trace_array(new,'WRITE_POS_ONE')[0][0]
    assert trace_array(new,'READ_NEG_ZERO')[-1][1]==trace_array(new,'READ_POS_ONE')[0][0]
    assert trace_array(new,'WRITE_POS_ONE')[-1][1]=='0123'
    assert trace_array(new,'READ_POS_ONE')[-1][1]=='0141'
    assert "cpu.kmem.write_memory(0020,0); // explicitly injected M0-like +0" in new
    assert 'cpu.kmem.write_rom(03012, 1);' in new
    assert 'cpu.kmem.write_rom(03026, SIGN);' in new
    assert 'cpu.kmem.write_rom(03042, UPPER_MAG);' in new
    assert "enter_read(cpu)" in new
    assert "stop_running=step(cpu);" in new, "counterfactual STOP must execute"
    with MAN.open(newline='') as f: sources=list(csv.DictReader(f,delimiter='\t'))
    assert len(sources)==2
    assert sources[0]['id']=='GY62_1962_PDF' and sources[1]['id']=='D5_CPP_REFERENCE'
    assert all(re.fullmatch('[a-f0-9]{64}',r['sha256']) for r in sources)
    # Check committed D5 identity and normalize only LF/CRLF.
    blob = subprocess.check_output(
        ['git', 'rev-parse',
         'HEAD:tests/isa/isa06_d5_historical_ram_iterations_probe.cpp'],
        cwd=ROOT, text=True).strip()
    assert blob == '979bc8317cf2ec4d660f750a0d24bb2cef0510f6', 'D5 Git blob drift'

    original = D5.read_bytes()
    normalized = original.replace(b'\r\n', b'\n')
    assert b'\r' not in normalized, 'Unexpected D5 line endings'
    assert hashlib.sha256(normalized).hexdigest() == sources[1]['sha256'], \
        'D5 content drift (after LF/CRLF normalization)'
    assert "D8-P1" in (ROOT/'docs/ISA_06_D8_P1_SIGNED_ZERO_POLICY.md').read_text()
    assert 'ISA-06 D8-P1' in (ROOT/'src/main.cpp').read_text()
    print('ISA-06 D8-P2: HISTORICAL INSTRUCTIONS + CONTROLLED POLICY; NOT A CERTIFIED HARDWARE TRACE')
    print('WALK-CHECK PASS original_words=27 transitions=32 phases=4 signed_zero=POLICY stop_mismatch=STRICT rom=FIXTURE D5_SHA256=OK')
    if show:
        for phase,_ in PAIRS:
            group=[r for r in rows if r['phase']==phase]
            print(f'{phase:11}: '+ ' '.join(x['pc_oct'] for x in group)+' -> '+group[-1]['next_pc_oct'])
        print('WARNING phase entry, ROM constants and RAM signs are controlled test fixtures; M0 counterfactual is injected')

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--check',action='store_true')
    a.add_argument('--show-walk',action='store_true')
    args=a.parse_args()
    run(args.show_walk)
