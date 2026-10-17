#!/usr/bin/env python3
"""D8-P5 terminal-dispatch literal and provenance guard; NOT an emulator oracle."""
import argparse
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P4 = ROOT / 'tests/isa/isa06_d8_p4_multi_pattern_probe.cpp'
P5 = ROOT / 'tests/isa/isa06_d8_p5_terminal_dispatch_probe.cpp'
DOC = ROOT / 'docs/ISA_06_D8_P5_TERMINAL_DISPATCH_QUALIFICATION.md'
GATES = ROOT / 'docs/ISA_06_D8_P5_TERMINAL_DISPATCH_GATES.tsv'
MANIFEST = ROOT / 'docs/ISA_06_D8_P5_SOURCE_MANIFEST.tsv'
P4_BLOB = '915715f1c74854cc555b0a7aa114d5c975b176dc'
P4_AUDIT_BLOB = 'bbe8e1db89c405daedb61417117e895b58ba7fd9'
GY62_PDF_SHA256 = 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
WORDS = {
    0o157: "0'16'0017'3042'0161ULL",
    0o161: "0'31'0014'0162'0164ULL",
    0o164: "0'31'3000'0022'0177ULL",
    0o165: "0'33'0000'0001'0077ULL",
    0o166: "0'33'0000'0003'0177ULL",
}

def normalized(path):
    raw=path.read_bytes().replace(b'\r\n',b'\n')
    assert b'\r' not in raw, f'unsupported line endings in {path}'
    return raw.decode('utf-8')

def git_blob(path):
    return subprocess.check_output(['git','rev-parse','HEAD:'+path],cwd=ROOT,text=True).strip()

def read_tsv(path):
    with path.open(encoding='utf-8',newline='') as file:
        rows=list(csv.DictReader(file,delimiter='\t'))
    assert all(None not in r and None not in r.values() for r in rows),f'TSV schema drift: {path}'
    return rows

def original_p4_words(source):
    out={}
    word=re.compile(r"\{\s*(0[0-7]{3})\s*,\s*(0'[0-7]{2}'[0-7]{4}'[0-7]{4}'[0-7]{4}ULL)\s*\}")
    for name in ('BRIDGE','TAIL'):
        match=re.search(r'constexpr HistoricalWord\s+'+name+r'\[\]\s*=\s*\{(.*?)\};',source,re.S)
        assert match,f'P4 {name} missing'
        out.update({int(pc,8):raw for pc,raw in word.findall(match.group(1))})
    return out

def main(show):
    assert git_blob('tests/isa/isa06_d8_p4_multi_pattern_probe.cpp')==P4_BLOB,'P4 source Git blob drift'
    assert git_blob('tools/isa06_d8_p4_progression_audit.py')==P4_AUDIT_BLOB,'P4 audit Git blob drift'
    prior=original_p4_words(normalized(P4))
    source=normalized(P5)
    for pc,word in WORDS.items():
        assert prior.get(pc)==word,f'P4 historical word drift at {pc:o}'
        name=f'WORD_{pc:04o}'
        assert re.search(r'constexpr W '+name+r'\s*=\s*'+re.escape(word)+r'\s*;',source),f'P5 historical word drift at {pc:o}'
    gates=read_tsv(GATES)
    sources=read_tsv(MANIFEST)
    assert len(gates)==5 and len(sources)==3
    assert [r['scenario'] for r in gates]==[
        'rom3000_plus_zero_routes_0022','rom3000_minus_zero_routes_0177',
        'rom3000_negative_one_routes_0177','isolated_original_0165_STOP',
        'isolated_original_0166_STOP'], 'scenario drift'
    assert all(row['classification']=='POLICY' for row in gates),'POLICY/STRICT promotion'
    assert [row['terminal_pc'] for row in gates]==['0022','0177','0177','STOP','STOP']
    assert all(r['qualification']=='0022_UNEXECUTED' for r in gates[:1])
    assert all(r['qualification']=='0177_UNEXECUTED' for r in gates[1:3])
    assert all(r['qualification']=='UNPROVEN_REACHABILITY' for r in gates[3:])
    assert [r['sha256_or_git_blob'] for r in sources]==[GY62_PDF_SHA256,P4_BLOB,P4_AUDIT_BLOB]
    assert 'cpu.kmem.write_rom(03000,rom3000);' in source
    assert 'cpu.kmem.write_memory(0014,SIGN);' in source
    assert 'terminal_dispatch("rom3000_plus_zero_routes_0022",0,0022)' in source
    assert 'terminal_dispatch("rom3000_minus_zero_routes_0177",SIGN,0177)' in source
    assert 'terminal_dispatch("rom3000_negative_one_routes_0177",SIGN|1,0177)' in source
    assert 'direct_stop("isolated_original_0165_STOP",0165,WORD_0165)' in source
    assert 'direct_stop("isolated_original_0166_STOP",0166,WORD_0166)' in source
    assert 'STRICT=0/0' in source and 'POLICY=' in source
    doc=normalized(DOC)
    for phrase in ('UNEXECUTED','POLICY','STRICT=0','OPEN','ROM `[3000]`'):
        assert phrase in doc, f'missing caveat {phrase}'
    for path in (P5,DOC,GATES,MANIFEST,Path(__file__)):
        for line_number,line in enumerate(path.read_bytes().replace(b'\r\n',b'\n').split(b'\n'),1):
            assert line==line.rstrip(b' \t'),f'trailing whitespace: {path.name}:{line_number}'
    print('ISA-06 D8-P5: BOUNDED TERMINAL DISPATCH; NO CERTIFIED ROM[3000] OR FINAL STOP PATH')
    print('TERMINAL-CHECK PASS words=5 gates=5 rom3000_fixtures=3 isolated_stops=2 '
          'P4_BLOB=PINNED P4_AUDIT_BLOB=PINNED targets=UNEXECUTED signed_zero=POLICY cpu=UNCHANGED')
    if show:
        for row in gates:
            print(f"{row['scenario']} entry={row['entry_pc']} path={row['path']} "
                  f"next_pc={row['terminal_pc']} class={row['classification']} "
                  f"qualification={row['qualification']}")

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--show-gates',action='store_true')
    args=parser.parse_args()
    main(args.show_gates)
