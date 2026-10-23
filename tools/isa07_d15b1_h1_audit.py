#!/usr/bin/env python3
"""D15/B1-H1 add-only auditor: canonical public example + observational native gate."""
import csv,hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='1b187d944d63ef0961e019e35de4a6374346e504'
IMAGE='examples/historical/gy1962/au1_logic.k41'
PROV='examples/historical/gy1962/au1_logic_provenance.tsv'
FILES=('docs/ISA_07_D15B1_H1_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H1_GY1962_AU1_LOGIC.md', 'examples/historical/gy1962/README.md', 'examples/historical/gy1962/au1_logic.k41', 'examples/historical/gy1962/au1_logic_provenance.tsv', 'tools/isa07_d15b1_h1_audit.py', 'tools/isa07_d15b1_h1_native.py')
DIGESTS={'docs/ISA_07_D15B1_H1_DECISION_LEDGER.tsv': '868b900f9f8d8a9e0db54cd1df0ba1cbbb935110b9998065c284da19fa94f914', 'docs/ISA_07_D15B1_H1_GY1962_AU1_LOGIC.md': '66d07b339e4aa64d39a8dfa5ad54e4d10969652ff31406d02c2c01fedf43702a', 'examples/historical/gy1962/README.md': 'faba0756f9a623abfd36d92fe47ce2dd3c30614015a6307515bdb4dab8195f91', 'examples/historical/gy1962/au1_logic.k41': '56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c', 'examples/historical/gy1962/au1_logic_provenance.tsv': '030ec0f76f20cffc7e30e53403a444ef2176630e51881964f9bb7e2d6c2f4f44', 'tools/isa07_d15b1_h1_native.py': '8654ad7aa283a4991546b2e91544bd8b5c77c2b13705ba7fd31546c947e5c195'}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def need(ok,label):
    if not ok:raise RuntimeError(label)
def verify_image(im,prov):
    rows=[line.strip().split() for line in im.decode('ascii').splitlines()
          if line.strip() and not line.startswith('#')]
    need(rows[0]==['KYIV41-OCT1'],'HEADER')
    records=rows[1:]
    need(len(records)==39 and all(len(x)==2 for x in records),'WORD_COUNT')
    need(all(len(a)==4 and len(w)==14 and set(a+w)<=set('01234567') for a,w in records),'OCTAL')
    addrs=[int(a,8) for a,_ in records]
    need(addrs==[0o2,0o3]+list(range(0o43,0o110)),'ADDRESS_SEQUENCE')
    m=dict(records)
    need(m['0073']=='17000200030347','XOR_SOURCE_0073')
    need(m['0074']=='16034700000076','COMPARE_SOURCE_0074')
    need(m['0075']=='33000000000000','STOP_SOURCE_0075')
    need(m['0102']=='16034730360107','SOURCE_BRANCH_0102')
    need(sum(v.startswith('33') for v in m.values())==12,'STOP_COUNT')
    source=list(csv.DictReader(prov.decode('utf8').splitlines(),delimiter='\t'))
    need(len(source)==39 and all(a==p['address'] and w==p['raw41']
          for (a,w),p in zip(records,source)),'PROVENANCE')
    need(all(p['verified']=='VISUAL_SINGLE_PASS' for p in source),'SECOND_PASS_UNSUPPORTED')
    return m

def selftest():
    a=(ROOT/IMAGE).read_bytes();b=(ROOT/PROV).read_bytes()
    verify_image(a,b)
    invalid=[(a.replace(b'0074 16034700000076',b'0074 16034730360076',1),b),
             (a.replace(b'0002 12525252525252',b'0002 12525252525258',1),b),
             (a,b.replace(b'VISUAL_SINGLE_PASS',b'INDEPENDENT_DOUBLE_PASS',1))]
    for x,y in invalid:
        try:verify_image(x,y)
        except (RuntimeError,UnicodeError):pass
        else:raise RuntimeError('MUTANT_ACCEPTED')
    print('D15B1H1-AUDIT-SELFTEST PASS MUTANTS_REJECTED=3/3 RECORDS=39/39')

def audit():
    need(git('rev-parse','HEAD').decode().strip()==BASE,'BASELINE')
    need(git('branch','--show-current').decode().strip()=='main','NOT_MAIN')
    need(not git('rev-parse','--show-prefix').strip(),'NOT_ROOT')
    need(not git('diff','--cached','--name-only').strip(),'STAGED')
    need(not git('diff','--name-only').strip(),'TRACKED_MUTATION')
    state=sorted(git('status','--porcelain=v1','--untracked-files=all').decode().splitlines())
    need(state==sorted('?? '+x for x in FILES),'SCOPE: '+repr(state))
    for rel,sha in DIGESTS.items():
        need(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha,'CONTENT_SHA_'+rel)
    verify_image((ROOT/IMAGE).read_bytes(),(ROOT/PROV).read_bytes())
    need(git('rev-parse','HEAD:mem/ROM.txt').decode().strip()=='b39868f9697c82fd3b9ba9b7448b8313293970c1','ROM_BLOB')
    need(hashlib.sha256((ROOT/IMAGE).read_bytes()).hexdigest()=='56951e9945720e3157474d7235b8932d0428ba6ed2044d82263eede24267b67c','IMAGE_PIN')
    print('D15B1H1-AUDIT PASS BASELINE=1b187d9 NEW=7/7 SOURCE_WORDS=39/39 CANONICAL_EXAMPLE=1 PROVENANCE=39/39 CPU_MUTATION=0 ROM_PIN=1 HISTORICAL_EXPECTATION_MATCH=0 ISA_ADJUDICATION=OPEN INDEPENDENT_SECOND_PASS=PENDING REAL_NATIVE_GATE=PENDING')
if __name__=='__main__':
    try:
        if sys.argv[1:]==['--self-test']:selftest()
        elif not sys.argv[1:]:audit()
        else:raise RuntimeError('USAGE')
    except Exception as e:print('D15B1H1-AUDIT FAIL',str(e),file=sys.stderr);sys.exit(1)
