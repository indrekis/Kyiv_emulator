#!/usr/bin/env python3
"""D12-A read-only source and package gate; NOT a hardware oracle.

Requires repo HEAD c67c1e5, clean tracked tree and exactly five D12-A
untracked files. No checkout, mutation, Git writes, or peripheral execution.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
import subprocess
import sys

BASE='c67c1e5b4840b36202d94894f3eb59de8a879b81'
PINS={
 'src/main.cpp':'80de2590770966cc80cb812d5cc6e3c0afa6e8ea',
 'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
 'tests/isa/isa07_d9a_io24_branch_probe.cpp':'260f0bdfc6ad90af7e600c294e40d53ae641d57f',
 'tests/isa/isa07_d9b_io25_sequential_probe.cpp':'9fabacc0b0767d9cb594b79824f62a29b8b19171',
}
NEW=(
 'docs/ISA_07_D12A_IO24_HOST_CHARACTERIZATION.md',
 'docs/ISA_07_D12A_IO24_CODE_RISK_LEDGER.tsv',
 'tests/isa/isa07_d12a_io24_host_observation_probe.cpp',
 'tools/isa07_d12a_io24_host_sandbox.py',
 'tools/isa07_d12a_audit.py',
)
NEW_SHA256={
 'docs/ISA_07_D12A_IO24_HOST_CHARACTERIZATION.md':'07d9bc1aed1e3290fe9ae4c3bb380b31ba93de764bff817969b913cc8a116518',
 'docs/ISA_07_D12A_IO24_CODE_RISK_LEDGER.tsv':'cd85cdbd389f0645f96052274ee90a3f953fc86430d481f7f1b30dee2ebc57fc',
 'tests/isa/isa07_d12a_io24_host_observation_probe.cpp':'a614c78cab921b38cf3c0baf7a60437ee8850f561da6927ea20a47bc61d52ae6',
 'tools/isa07_d12a_io24_host_sandbox.py':'765d7d05dc8e641dc315b1c016b42c2d03e57cfc78e329d935dd583a2b724f23',
}

def git(*args):
    return subprocess.check_output(['git', *args],text=True,stderr=subprocess.PIPE).strip()

def require(ok,why):
    if not ok:raise RuntimeError(why)

def normalized(path):
    raw=Path(path).read_bytes()
    require(b'\r' not in raw.replace(b'\r\n',b''),'bare CR in '+path)
    return raw.replace(b'\r\n',b'\n')

def audit():
    require(git('rev-parse','--show-prefix')=='','run from repo root')
    require(git('rev-parse','HEAD')==BASE,'unexpected HEAD (requires c67c1e5)')
    require(not git('diff','--name-only'),'unexpected tracked working changes')
    require(not git('diff','--cached','--name-only'),'unexpected staged changes')
    for p,sha in PINS.items():
        require(git('rev-parse','HEAD:'+p)==sha,'Git source blob pin mismatch '+p)
    require(len(PINS)==4 and len(NEW)==5,'scope changed')
    for p in NEW:
        require(Path(p).is_file(),'D12-A file missing '+p)
        require(not git('ls-files','--',p),'D12-A file already tracked or staged '+p)
        b=normalized(p)
        require(bool(b),'empty D12-A file '+p)
        if p in NEW_SHA256:
            require(hashlib.sha256(b).hexdigest()==NEW_SHA256[p],
                    'content drift '+p)
    doc=normalized(NEW[0]).decode('utf-8')
    for t in ('c67c1e5','GY62','printed p. 15','SOURCE_STRICT','CODE_OBS',
              'HOST_POLICY','STATIC_ONLY','20 current-code observations',
              'NO-CPU-EDIT','D12-B','02000'):
        require(t.casefold() in doc.casefold(),'documentation qualification absent '+t)
    ledger=normalized(NEW[1]).decode('utf-8')
    rows=ledger.splitlines()
    require(len(rows)==17 and len({r.split('\t')[0] for r in rows})==len(rows),
            'risk ledger count or unique IDs drift')
    for marker in ('D12A-S01','D12A-B02','D12A-B03','D12A-B11','D12A-B12','D12A-D01'):
        require(marker in ledger,'risk ledger missing '+marker)
    probe=normalized(NEW[2]).decode('utf-8')
    for t in ('m.execute_opcode()', 'm.kmem.read_memory(a)',
              'D12A-OBS','02000','HARDWARE_ORACLE=0',
              'm.drum_num_read','m.drum_zone_read'):
        require(t in probe,'probe contract absent '+t)
    runner=normalized(NEW[3]).decode('utf-8')
    names=re.findall(r"^\s+Case\('([^']+)'",runner,re.M)
    require(len(names)==20 and len(set(names))==20,'expected 20 distinct modes')
    require('REVERSED_INTERVAL=STATIC_ONLY' in runner,
            'unsafe reversed interval qualification missing')
    require('TemporaryDirectory' in runner and 'subprocess.run' in runner,
            'isolation of real CPU absent')
    require("b'\\r\\n'" in normalized(NEW[4]).decode('utf-8'),
            'auditor must normalize CRLF')
    print('D12A-AUDIT PASS BASELINE=c67c1e5 PINS=4/4 NEW_FILES=5/5 '
          'CONTENT_SHA=4/4 CPU_MUTATION=0 W1_UNCHANGED=1 '
          'RISK_LEDGER=1 CASE_MATRIX=20/20 EOL_PORTABLE=1 '
          'REVERSED_INTERVAL=STATIC_ONLY HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')

if __name__=='__main__':
    try:audit()
    except (OSError,RuntimeError,UnicodeError,subprocess.CalledProcessError) as e:
        print('D12A-AUDIT FAIL',e,file=sys.stderr)
        raise SystemExit(1)
