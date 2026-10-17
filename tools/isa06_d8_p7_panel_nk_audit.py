#!/usr/bin/env python3
"""ISA-06 D8-P7 source-based panel NK and documented fourth-test entry audit."""
import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/ISA_06_D8_P7_PANEL_CONTROL_AND_ENTRY.md'
EV=ROOT/'docs/ISA_06_D8_P7_SOURCE_EVIDENCE.tsv'
NK=ROOT/'docs/ISA_06_D8_P7_NK_ADDRESS_CONTRACT.tsv'
MAN=ROOT/'docs/ISA_06_D8_P7_SOURCE_MANIFEST.tsv'
CPP=ROOT/'tests/isa/isa06_d8_p7_documented_entry_probe.cpp'
P6_AUDIT=ROOT/'tools/isa06_d8_p6_terminal_origin_audit.py'
ROM=ROOT/'mem/ROM.txt'
PRE_P7_REF='6fe5999'
ORIGINAL_P6_BLOB='9959afbb99c41dc44e38b05e6cd05144c56f3d33'
ORIGINAL_P6_CPP_BLOB='3c17f28f9e45e082f0d5ab162c119e5cc039ecbc'
ORIGINAL_ROM_BLOB='bb6224e130c59564a8ccc4b224c55e41e50784a3'
ORIGINAL_P5_AUDITOR_BLOB='7179b7d49e1bc92d186218dac6a0a31f5162740b'
POST_P6_P5_AUDITOR_BLOB='0b6ddcc5afe930bf3575999ef54a33faa65475e4'
PDF_SHA='a3bf9871dfe05609a7c6ea33e6677c1fd508b6ae57443f152e27ad2be8c21eea'

def git_blob(path, ref='HEAD'):
    return subprocess.check_output(['git','rev-parse',ref+':'+path],cwd=ROOT,text=True).strip()

def read(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    assert b'\r' not in data, f'unexpected line endings: {path}'
    return data.decode('utf-8')

def tsv(path):
    with path.open('r',encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    assert rows and all(None not in row and None not in row.values() for row in rows), f'TSV schema drift {path}'
    return rows

def rom_codes():
    values={}
    for raw in ROM.read_bytes().splitlines():
        m=re.fullmatch(rb'\s*(3[0-7]{3})\s+([0-7]{2})\s+([0-7]{4})\s+([0-7]{4})\s+([0-7]{4})\s*',raw)
        if m:
            address=int(m.group(1),8)
            assert address not in values
            values[address]=int(b''.join(m.group(i) for i in range(2,6)),8)
    return values

def check(show, source_pdf):
    assert git_blob('tools/isa06_d8_p6_terminal_origin_audit.py',PRE_P7_REF)==ORIGINAL_P6_BLOB, 'P6 auditor original drift'
    assert git_blob('tests/isa/isa06_d8_p6_natural_terminal_reach_probe.cpp',PRE_P7_REF)==ORIGINAL_P6_CPP_BLOB, 'P6 probe drift'
    assert git_blob('mem/ROM.txt')==ORIGINAL_ROM_BLOB, 'ROM drift'
    assert git_blob('tools/isa06_d8_p5_terminal_dispatch_audit.py','92f5352')==ORIGINAL_P5_AUDITOR_BLOB, 'pre-P6 P5 historical blob drift'
    assert git_blob('tools/isa06_d8_p5_terminal_dispatch_audit.py')==POST_P6_P5_AUDITOR_BLOB, 'post-P6 P5 blob drift'
    p6=read(P6_AUDIT)
    assert "P5_AUDIT_PRE_P6_REF = '92f5352'" in p6
    assert 'P5_AUDIT_POST_P6_BLOB' in p6 and POST_P6_P5_AUDITOR_BLOB in p6
    assert "git_blob('tools/isa06_d8_p5_terminal_dispatch_audit.py', P5_AUDIT_PRE_P6_REF)" in p6
    assert 'P5_ERRATUM_BLOB=PINNED' in p6

    rows=tsv(EV)
    assert len(rows)==24 and [r['id'] for r in rows]==[f'E{i:03d}' for i in range(1,25)]
    assert all(r['status'] in {'DOC','REPO_OBS','POLICY','CORRECTED'} for r in rows)
    pages={'8','120','121','122','161','170','171'}
    assert pages.issubset({r['printed_page'] for r in rows})
    lookup={r['id']:r for r in rows}
    assert lookup['E004']['subject']=='3000 sign positive' and lookup['E005']['subject']=='3000 sign negative'
    assert lookup['E009']['subject']=='RAM test IV' and '0117' in lookup['E009']['observation']
    assert lookup['E013']['subject']=='3000 3001 3002'
    assert lookup['E010']['subject']=='3001 sign negative'
    assert lookup['E019']['subject']=='0164'
    assert lookup['E020']['subject']=='0022'
    nk=tsv(NK)
    assert len(nk)==8 and [r['address'] for r in nk]==[f'{x:04o}' for x in range(0o3000,0o3010)]
    assert all(r['class']=='NK' and r['value_origin']=='OPERATOR' for r in nk)
    assert [r['panel_switch'] for r in nk[:3]]==['PANEL_SELECTOR_DOC']*3
    assert all(r['panel_switch']=='PANEL_SOURCE_NOT_SHOWN' for r in nk[3:])
    assert nk[0]['diagnostic_role']=='SIGN_CONTROLS_ALL_VS_SINGLE_RAM_TEST'
    assert nk[1]['diagnostic_role']=='SIGN_CONTROLS_TEST1_CUSTOM_CODE_FROM_3007'
    census=rom_codes()
    assert 0o3000 not in census and 0o3001 not in census
    assert census.get(0o3012)==1 and census.get(0o3026)==1<<40 and census.get(0o3042)==1<<39
    man=tsv(MAN)
    assert len(man)==6
    md={r['id']:r for r in man}
    expected={'GY62_PDF':PDF_SHA,'REPO_ROM':ORIGINAL_ROM_BLOB,'P6_AUDITOR_PRE_P7':ORIGINAL_P6_BLOB,
              'P5_AUDITOR_PRE_P6':ORIGINAL_P5_AUDITOR_BLOB,'P5_AUDITOR_POST_P6':POST_P6_P5_AUDITOR_BLOB,
              'P6_CPP':ORIGINAL_P6_CPP_BLOB}
    assert {k:r['sha_or_blob'] for k,r in md.items()}==expected
    if source_pdf:
        pdf=Path(source_pdf)
        assert hashlib.sha256(pdf.read_bytes()).hexdigest()==PDF_SHA,'optional source PDF changed'
    src=read(CPP)
    for code in ("0'01'0000'0000'0014ULL","0'01'3012'0000'0017ULL","0'01'0017'0000'0021ULL"):
        assert code in src,f'missing historical fourth RAM test entry word {code}'
    assert 'cpu.kmem.write_memory(0014, SIGN);' in src
    assert 'cpu.kmem.read_memory(0014)==0' in src
    assert 'cpu.C_reg==0122' in src
    assert 'STRICT=0/0' in src and 'POLICY=1/1' in src
    doc=read(DOC)
    for phrase in ('p. 8','p. 120','p. 121','p. 122','p. 161','p. 170',
                   '0117','3000','3001','3007','0177','POLICY','OPEN','H2 E022'):
        assert phrase in doc, f'missing evidence qualifier {phrase}'
    for item in (DOC,EV,NK,MAN,CPP,P6_AUDIT,Path(__file__)):
        for ln,line in enumerate(item.read_bytes().replace(b'\r\n',b'\n').split(b'\n'),1):
            assert line==line.rstrip(b' \t'), f'trailing whitespace: {item}:{ln}'
    print('ISA-06 D8-P7: NK3000 OPERATOR-CONTROLLED RAM TEST MODE; DOCUMENTED FOURTH ENTRY 0117; SIGNED-ZERO ORACLE OPEN')
    print('PANEL-CHECK PASS evidence=24 NK=8 panel_selected=3 entry_words=3 source_pages=7 '
          'P6_AUDITOR_PIN=REPAIRED_ROM_OPERATOR=DOC ROM3000_3001=ABSENT ROM3012_3026_3042=REPO_OBS '
          'CPU=UNCHANGED H2_E022=RETRACTED')
    if show:
        for r in rows:
            print('evidence='+r['id']+' page='+r['printed_page']+' status='+r['status']+' subject='+r['subject'].replace(' ','_'))

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--check',action='store_true')
    a.add_argument('--show-evidence',action='store_true')
    a.add_argument('--source-pdf',help='Optional exact GY62 PDF file to verify SHA256')
    ns=a.parse_args();check(ns.show_evidence, ns.source_pdf)
