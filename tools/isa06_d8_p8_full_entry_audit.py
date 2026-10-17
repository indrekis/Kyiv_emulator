#!/usr/bin/env python3
"""D8-P8 source-anchored documentary/integration-audit — not a hardware oracle."""
import argparse
import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/ISA_06_D8_P8_FULL_ENTRY_AND_NK_BOUNDARY.md'
GATES=ROOT/'docs/ISA_06_D8_P8_ENTRY_GATES.tsv'
CONTRACT=ROOT/'docs/ISA_06_D8_P8_NK_SELECTOR_CONTRACT.tsv'
MANIFEST=ROOT/'docs/ISA_06_D8_P8_SOURCE_MANIFEST.tsv'
CPP=ROOT/'tests/isa/isa06_d8_p8_full_entry_78_cycles_probe.cpp'
SEL=ROOT/'tools/isa06_d8_p8_nk_selector_reference.py'
P6=ROOT/'tests/isa/isa06_d8_p6_natural_terminal_reach_probe.cpp'
P7=ROOT/'tests/isa/isa06_d8_p7_documented_entry_probe.cpp'
ROM=ROOT/'mem/ROM.txt'
PDF_SHA='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
PINS={
 'tests/isa/isa06_d8_p6_natural_terminal_reach_probe.cpp':'3c17f28f9e45e082f0d5ab162c119e5cc039ecbc',
 'tests/isa/isa06_d8_p7_documented_entry_probe.cpp':'401c98b014e28df760b20de0c398289305e313d1',
 'docs/ISA_06_D8_P7_PANEL_CONTROL_AND_ENTRY.md':'581b30d273f634f5fcf182404d65983e88650c9d',
 'mem/ROM.txt':'bb6224e130c59564a8ccc4b224c55e41e50784a3',
}

def git_blob(rel):
    return subprocess.check_output(['git','rev-parse','HEAD:'+rel],cwd=ROOT,text=True).strip()

def txt(p):
    b=p.read_bytes().replace(b'\r\n',b'\n')
    assert b'\r' not in b, f'invalid EOL in {p.name}'
    return b.decode('utf-8')

def tsv(p):
    with p.open('r',encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    assert rows and all(None not in r and None not in r.values() for r in rows),f'TSV columns drift: {p.name}'
    return rows

def words(code,groups=('HIST','BRIDGE','TAIL')):
    out={}
    word_pat=r'\{\s*(0[0-7]{3})\s*,\s*(0\'[0-7]{2}\'[0-7]{4}\'[0-7]{4}\'[0-7]{4}ULL)\s*\}'
    for group in groups:
        block=re.search(r'constexpr HistoricalWord\s+'+group+r'\[\]\s*=\s*\{(.*?)\};',code,re.S)
        assert block is not None,f'missing {group}'
        entries=re.findall(word_pat,block.group(1))
        assert len(entries)=={'HIST':27,'BRIDGE':6,'TAIL':6,'ENTRY':1}[group],f'invalid {group} count'
        for addr,word in entries:
            key=int(addr,8)
            assert key not in out,f'duplicate address {addr}'
            out[key]=word
    return out

def main(show,pdf):
    for rel,sha in PINS.items():
        assert git_blob(rel)==sha,f'committed source drift: {rel}'
    entries=tsv(MANIFEST)
    assert len(entries)==5 and len({r['source'] for r in entries})==5
    for r in entries:
        if r['identity']=='GIT_BLOB':
            assert PINS[r['path']]==r['sha256_or_blob'],f'manifest Git blob drift: {r["path"]}'
        else:
            assert r['source']=='GY62_1962_PDF' and r['identity']=='SHA256' and r['sha256_or_blob']==PDF_SHA
    if pdf is not None:
        assert hashlib.sha256(Path(pdf).read_bytes()).hexdigest()==PDF_SHA,'GY62 PDF actual SHA drift'
    code=txt(CPP);p6=txt(P6);p7=txt(P7)
    previous=words(p6)
    new=words(code,('ENTRY','HIST','BRIDGE','TAIL'))
    assert len(previous)==39 and len(new)==40 and {a:w for a,w in new.items() if a!=0o117}==previous,'Original 39 words altered'
    assert new[0o117]=="0'01'0000'0000'0014ULL" and 'constexpr W w117 = 0\'01\'0000\'0000\'0014ULL;' in p7
    assert 'cpu.C_reg=0117;' in code and 'cpu.kmem.write_memory(0014,SIGN);' in code
    assert 'cpu.kmem.write_memory(0014,0);' not in code
    assert 'cpu.kmem.read_memory(0014)!=0' in code and 'documented_entry_seen=true;' in code
    for line in ('result.cycles!=78','result.positive!=39','result.negative!=39','break; // CRITICAL: 0164 IS NOT EXECUTED','ROM3000_NOT_INJECTED=1','if(pc==0162)','if(pc==0163)'):
        assert line in code,f'P8 long-run guard missing: {line}'
    assert 'cpu.kmem.write_rom(03000,' not in code and 'cpu.kmem.write_rom(03001,' not in code
    assert code.count('cpu.kmem.write_rom(')==3,'Unregistered ROM fixture count'
    gates=tsv(GATES)
    assert len(gates)==5 and [r['gate'] for r in gates]==['entry','first_epoch','epoch_transition','second_epoch','terminal_before_dispatch']
    assert gates[0]['entry_pc_octal']=='0117' and gates[-1]['next_pc_octal']=='UNEXECUTED'
    assert all(r['classification']!='STRICT' for r in gates)
    nk=tsv(CONTRACT)
    assert len(nk)==3 and [r['address_octal'] for r in nk]==['3000','3001','3002']
    assert all(r['selector_scope']=='INDEPENDENT_SWITCH' and r['source_choice']=='PANEL_OR_CABINET' for r in nk)
    assert all('NO_HARDWARE_PANEL_IMPLEMENTATION' in r['implementation_status'] or 'NO_DEFINED_DIAGNOSTIC_ROLE' in r['implementation_status'] for r in nk)
    reference=txt(SEL)
    assert 'SELECTABLE=(0o3000,0o3001,0o3002)' in reference and 'signed_zero_distinct=1' in reference and 'emulator_integration=NONE' in reference
    prose=txt(DOC)
    for phrase in ('40054e0','printed pp. 120, 170–171','**p. 161**','POLICY','STRICT','ROM','fixtures','0117','0164','3000','3001','3002','0177','RETRACTED','OPEN'):
        assert phrase in prose,f'documentary boundary missing: {phrase}'
    for item in (DOC,GATES,CONTRACT,MANIFEST,CPP,SEL,Path(__file__)):
        for ix,line in enumerate(item.read_bytes().replace(b'\r\n',b'\n').split(b'\n'),1):
            assert line==line.rstrip(b' \t'),f'trailing whitespace: {item.name}:{ix}'
    print('ISA-06 D8-P8: DOCUMENTED ENTRY 0117 + 78 CYCLES POLICY; OPERATOR NK REFERENCE ONLY')
    print('ENTRY-CHECK PASS original_p6_words=39 entry_words=1 total_words=40 gates=5 nk_selectors=3 epochs=2 expected_cycles=78 P6_BLOB=PINNED P7_BLOB=PINNED ROM_BLOB=PINNED CPU=UNCHANGED ROM=FIXTURE 0164=UNEXECUTED signed_zero=POLICY')
    if show:
        for g in gates:
            print(f'gate={g["gate"]} entry_pc={g["entry_pc_octal"]} next_pc={g["next_pc_octal"]} class={g["classification"]}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--show-gates',action='store_true')
    parser.add_argument('--pdf',help='Optional local original GY62 PDF to verify actual SHA256')
    a=parser.parse_args()
    try:main(a.show_gates,a.pdf)
    except Exception as e:
        print(f'ENTRY-CHECK FAIL: {e}',file=sys.stderr)
        raise
