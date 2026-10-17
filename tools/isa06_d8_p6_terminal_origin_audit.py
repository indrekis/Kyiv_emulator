#!/usr/bin/env python3
"""P6 GY62-vs-DPS64 source correction and natural terminal reachability guard."""
import argparse
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT/'docs/ISA_06_D8_P6_TERMINAL_PROVENANCE_AND_REACHABILITY.md'
LEDGER = ROOT/'docs/ISA_06_D8_P6_ORIGIN_LEDGER.tsv'
MANIFEST = ROOT/'docs/ISA_06_D8_P6_SOURCE_MANIFEST.tsv'
PROBE = ROOT/'tests/isa/isa06_d8_p6_natural_terminal_reach_probe.cpp'
P4 = ROOT/'tests/isa/isa06_d8_p4_multi_pattern_probe.cpp'
P5_AUDIT = ROOT/'tools/isa06_d8_p5_terminal_dispatch_audit.py'
P5_DOC = ROOT/'docs/ISA_06_D8_P5_TERMINAL_DISPATCH_QUALIFICATION.md'
P5_MANIFEST = ROOT/'docs/ISA_06_D8_P5_SOURCE_MANIFEST.tsv'
ROM = ROOT/'mem/ROM.txt'
BLOBS = {
    'mem/ROM.txt':'bb6224e130c59564a8ccc4b224c55e41e50784a3',
    'tests/isa/isa06_d8_p4_multi_pattern_probe.cpp':'915715f1c74854cc555b0a7aa114d5c975b176dc',
    'tests/isa/isa06_d8_p5_terminal_dispatch_probe.cpp':'4606e86f4344cf0e1f38b06a98a6bc390233b1eb',
    'tools/isa06_d8_p5_terminal_dispatch_audit.py':'7179b7d49e1bc92d186218dac6a0a31f5162740b',
}
PDF_SHA = 'a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'
WRONG_SCAN_SHA = '81027de0e4e942d0bdf7aad40cfe3501355c251a541814ea0f0a94ad818105b7'
ROM_FIXTURES = {0o3012:1, 0o3026:1<<40, 0o3042:1<<39}


def text(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    assert b'\r' not in data, f'unsupported line endings: {path}'
    return data.decode('utf-8')


def git_blob(rel):
    return subprocess.check_output(['git','rev-parse','HEAD:'+rel],cwd=ROOT,text=True).strip()


def tsv(path):
    with path.open('r',encoding='utf-8',newline='') as inp:
        rows=list(csv.DictReader(inp,delimiter='\t'))
    assert rows and all(None not in row and None not in row.values() for row in rows),f'TSV drift: {path}'
    return rows


def hist_arrays(src):
    pattern=r'\{\s*(0[0-7]{3})\s*,\s*(0\'[0-7]{2}\'[0-7]{4}\'[0-7]{4}\'[0-7]{4}ULL)\s*\}'
    out={}
    for group in ('HIST','BRIDGE','TAIL'):
        m=re.search(r'constexpr HistoricalWord\s+'+group+r'\[\]\s*=\s*\{(.*?)\};',src,re.S)
        assert m,group
        hits=re.findall(pattern,m.group(1))
        assert len(hits)=={'HIST':27,'BRIDGE':6,'TAIL':6}[group],f'{group} count'
        for pc,word in hits:
            addr=int(pc,8)
            assert addr not in out, f'duplicate PC {pc}'
            out[addr]=word
    return out


def rom_census():
    # Byte-based so unrelated non-UTF8 legacy ROM lines and CRLF are harmless.
    found={}
    for raw in ROM.read_bytes().splitlines():
        m=re.fullmatch(rb'\s*(3[0-7]{3})\s+([0-7]{2})\s+([0-7]{4})\s+([0-7]{4})\s+([0-7]{4})\s*',raw)
        if m:
            address=int(m.group(1),8)
            assert address not in found, f'duplicate ROM address {address:o}'
            code=int(b''.join(m.group(i) for i in range(2,6)),8)
            found[address]=code
    assert 0o3000 not in found and 0o3001 not in found,'unknown ROM entry unexpectedly present'
    for address,expected in ROM_FIXTURES.items():
        assert found.get(address)==expected,f'repo ROM fixture drift at {address:o}'
    return found


def main(show):
    for rel,sha in BLOBS.items():
        assert git_blob(rel)==sha, f'baseline Git blob drift: {rel}'
    rows=tsv(MANIFEST)
    assert len(rows)==6
    got={r['source']:r for r in rows}
    assert got['GY62_1962_PDF']['sha256_or_git_blob']==PDF_SHA
    assert got['DPS64_1964_SCAN_NOT_GY62']['sha256_or_git_blob']==WRONG_SCAN_SHA
    for item,key in [('REPO_ROM','mem/ROM.txt'),('P4_CPP','tests/isa/isa06_d8_p4_multi_pattern_probe.cpp'),('P5_CPP','tests/isa/isa06_d8_p5_terminal_dispatch_probe.cpp'),('P5_AUDITOR_ORIGINAL','tools/isa06_d8_p5_terminal_dispatch_audit.py')]:
        assert got[item]['sha256_or_git_blob']==BLOBS[key]
    original=hist_arrays(text(P4))
    fresh=hist_arrays(text(PROBE))
    assert fresh==original and len(fresh)==39, 'P4 machine-word drift'
    assert fresh[0o164]=="0'31'3000'0022'0177ULL"
    assert fresh[0o165]=="0'33'0000'0001'0077ULL"
    assert fresh[0o166]=="0'33'0000'0003'0177ULL"
    p5=tsv(P5_MANIFEST)
    assert p5[0]['source']=='GY62_PRINTED_170_171'
    assert p5[0]['location']=='Vychislitelnaya-mashyna-Kiev_VHlushkov_EYushchenko_1962.pdf'
    assert p5[0]['sha256_or_git_blob']==PDF_SHA
    assert p5[0]['qualification']=='ORIGINAL_PDF_SHA256'
    src_p5=text(P5_AUDIT)
    assert 'GY62_PDF_SHA256' in src_p5 and PDF_SHA in src_p5
    assert 'SCAN_SHA256' not in src_p5 and WRONG_SCAN_SHA not in src_p5
    assert 'kiev0086.png' in text(P5_DOC) and 'incorrectly' in text(P5_DOC)
    census=rom_census()
    ledger=tsv(LEDGER)
    assert len(ledger)==12 and len({r['id'] for r in ledger})==12
    assert [r['status'] for r in ledger if r['id']=='TARGET_0177']==['OPEN']
    assert [r['status'] for r in ledger if r['id']=='P5_ATTRIBUTION_ERRATUM']==['CORRECTED']
    src=text(PROBE)
    assert 'if(pc==0164){' in src and 'break; // CRITICAL: 0164 IS NOT EXECUTED' in src
    assert 'MAX_STEPS=1350000' in src and 'ROM3000_NOT_INJECTED=1' in src
    assert 'cpu.kmem.write_rom(03000,' not in src and 'cpu.kmem.write_rom(03001,' not in src
    for phrase in ('POLICY','STRICT','OPEN','0022','0177','1962','1964','0164'):
        assert phrase in text(DOC),f'missing documented caveat {phrase}'
    for path in (DOC,LEDGER,MANIFEST,PROBE,P5_DOC,P5_MANIFEST,P5_AUDIT,Path(__file__)):
        for n,line in enumerate(path.read_bytes().replace(b'\r\n',b'\n').split(b'\n'),1):
            assert line==line.rstrip(b' \t'),f'trailing whitespace: {path.name}:{n}'
    print('ISA-06 D8-P6: GY62 SOURCE CORRECTED; REPO ROM ORIGINS QUALIFIED; NATURAL TERMINAL REACHABILITY IS POLICY')
    print('ORIGIN-CHECK PASS historical_words=39 ledger=12 sources=6 p5_erratum=CORRECTED '
          'P4_BLOB=PINNED P5_BLOB=PINNED ROM_BLOB=PINNED '
          'ROM3000=ABSENT ROM3001=ABSENT ROM_FIXTURES=3 terminal_0164=UNEXECUTED CPU=UNCHANGED')
    if show:
        for r in ledger:
            print(f"origin={r['id']} status={r['status']} boundary={r['boundary']}")

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--show-origins',action='store_true')
    args=parser.parse_args()
    main(args.show_origins)
