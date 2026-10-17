#!/usr/bin/env python3
"""D8-P10 documentary source and integrated-test structural audit, not hardware oracle."""
import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'ad2bda7'
PINS = {
    'tests/isa/isa06_d8_p8_full_entry_78_cycles_probe.cpp':'b4b1f51b9cbcb6b9e027055be99aeeca63d28d4f',
    'inc/kyiv_nk_panel.h':'6ebcb09ae55df7ee7eb37b0e315e5b87bef39b14',
    'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
    'src/main.cpp':'f84acfb22fa3e00f598f3cdb05d4ed2a6618f893',
    'mem/ROM.txt':'bb6224e130c59564a8ccc4b224c55e41e50784a3',
}

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def text(path):
    raw=(ROOT/path).read_bytes().replace(b'\r\n',b'\n')
    assert b'\r' not in raw, f'unsupported line ending: {path}'
    return raw.decode('utf-8')

def blocks(code):
    out={}
    for name,n in [('ENTRY',1),('HIST',27),('BRIDGE',6),('TAIL',6)]:
        m=re.search(r'constexpr HistoricalWord\s+'+name+r'\[\]\s*=\s*\{(.*?)\};',code,re.S)
        assert m, 'missing original group '+name
        words=re.findall(r'\{\s*(0[0-7]{3})\s*,\s*(0\'[0-7]{2}\'[0-7]{4}\'[0-7]{4}\'[0-7]{4}ULL)\s*\}',m.group(1))
        assert len(words)==n, f'original {name} count changed'
        for addr,word in words:
            a=int(addr,8)
            assert a not in out, 'duplicate historical address'
            out[a]=word
    assert len(out)==40
    return out

def check(skip_git=False):
    if not skip_git:
        for path,pin in PINS.items():
            assert git('rev-parse',f'{BASE}:{path}')==pin,f'baseline Git blob drift: {path}'
            assert git('rev-parse',f'HEAD:{path}')==pin,f'HEAD Git blob drift: {path}'
            assert not git('diff','--',path) and not git('diff','--cached','--',path),f'production/source touched: {path}'
        p8=git('show',f'{BASE}:tests/isa/isa06_d8_p8_full_entry_78_cycles_probe.cpp')
    else:
        p8=(ROOT/'tests/isa/isa06_d8_p8_full_entry_78_cycles_probe.cpp').read_text()
    probe=text('tests/isa/isa06_d8_p10_natural_nk_dispatch_probe.cpp')
    assert blocks(probe)==blocks(p8),'P8 historical machine words altered'
    for token in (
        'cpu.kmem.write_memory(0014,SIGN);',
        'result.cycles!=78','result.positive!=39','result.negative!=39',
        'current.writes!=CELLS||current.reads!=CELLS',
        'cpu.kmem.write_rom(03000,0);','cpu.kmem.set_panel_nk_word(03000,SIGN);',
        'cpu.kmem.select_panel_nk(03000,panel_selected);',
        'cpu.kmem.is_panel_nk_selected(03000)!=panel_selected',
        'cpu.kmem.read_memory(03000)!=selected_code',
        'expected_target=panel_selected?0177:0022',
        'cpu.K_reg!=original(0164)','cpu.C_reg!=expected_target',
        'break; // CRITICAL: 0022 / 0177 MUST NOT BE EXECUTED',
        'for(unsigned config=0;config<2;++config)',
        'r.total!=1181828','r.cycles!=78',
        'POLICY=2/2 POLICY-FAIL=0',
        'int disassembly(const uint64_t&,Kyiv_memory_t&,const addr3_t&){return 0;}',
    ):
        assert token in probe, f'P10 essential invariant missing: {token}'
    assert 'src/asm_disasm.cpp' not in probe
    doc=text('docs/ISA_06_D8_P10_NATURAL_NK_DISPATCH.md')
    for token in ('ad2bda7','0117','0164','0022','0177','78','39','41','POLICY','STRICT','OPEN','--trace-prefix'):
        assert token in doc, 'documentation boundary missing: '+token
    with (ROOT/'docs/ISA_06_D8_P10_GATES.tsv').open(newline='',encoding='utf-8') as f:
        gates=list(csv.DictReader(f,delimiter='\t'))
    assert len(gates)==2 and [g['scenario'] for g in gates]==['cabinet_poszero','panel_negzero']
    assert [g['expected_next_pc_octal'] for g in gates]==['0022','0177']
    assert [g['NK3000_source'] for g in gates]==['CABINET','PANEL']
    assert all(g['cycles']=='78' and g['first_epoch']=='39' and g['second_epoch']=='39' and
               g['executed_dispatch']=='0164' and g['entry_pc_octal']=='0117' and
               g['target_executed']=='NO' and g['class']=='POLICY' for g in gates)
    with (ROOT/'docs/ISA_06_D8_P10_SOURCE_MANIFEST.tsv').open(newline='',encoding='utf-8') as f:
        manifest=list(csv.DictReader(f,delimiter='\t'))
    assert len(manifest)==6 and len({r['source'] for r in manifest})==6
    for r in manifest:
        if r['identity']=='GIT_BLOB':
            assert PINS[r['path_or_ref']]==r['pin'],'source manifest pin drift'
        else:
            assert r['identity']=='PRINTED_PAGES' and r['source']=='GY62'
    for path in ('tests/isa/isa06_d8_p10_natural_nk_dispatch_probe.cpp',
                 'tools/isa06_d8_p10_natural_nk_audit.py',
                 'docs/ISA_06_D8_P10_NATURAL_NK_DISPATCH.md',
                 'docs/ISA_06_D8_P10_GATES.tsv',
                 'docs/ISA_06_D8_P10_SOURCE_MANIFEST.tsv'):
        for line_no,line in enumerate(text(path).split('\n'),1):
            assert line==line.rstrip(' \t'),f'trailing whitespace: {path}:{line_no}'
    print('ISA-06 D8-P10: NATURAL 78-CYCLE RAM DIAGNOSTIC WITH NK3000 OPERATOR DISPATCH; ALL BEHAVIOR POLICY')
    print('NK-TERMINAL-CHECK PASS original_words=40 modes=2 natural_cycles=78_each expected_steps=1181828_each targets=UNEXECUTED P8_BLOB=PINNED P9_PANEL_BLOB=PINNED CPU=UNCHANGED ROM=UNCHANGED signed_zero=POLICY')
    for g in gates:
        print(f'mode={g["scenario"]} NK3000={g["NK3000_source"]} next_pc={g["expected_next_pc_octal"]} target_executed=NO class=POLICY')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--local-source-check',action='store_true',help='Test fixture validation without git pins; not qualification')
    a=ap.parse_args()
    try:check(a.local_source_check)
    except Exception as e:
        print(f'NK-TERMINAL-CHECK FAIL: {e}',file=sys.stderr)
        sys.exit(1)
