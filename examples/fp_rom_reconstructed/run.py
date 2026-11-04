#!/usr/bin/env python3
"""H115-B20: audit and natively replay a single, explicitly reconstructed Kyiv FP ROM.

The immutable source is a 251-word 1962 transcription.  The functional image
is a 257-word *modern reconstruction*, not a hardware/historical ROM oracle.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
SOURCE='examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'
FIXED='mem/ROM.txt'
FP_IMAGE=HERE/'inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41'
B19=HERE/'evidence/H115_B19_FP_SIGNED_OVERFLOW_NATIVE_EVIDENCE_V1.zip'
B19_PASS='PASS_H115_B19_SIGNED_OVERFLOW_PRIVATE_ROM_BOUNDED_NOT_HISTORICAL'
OFFLINE_PASS='PASS_H115_B20_FUNCTIONAL_ROM_STATIC_AND_EVIDENCE_NOT_NATIVE'
NATIVE_PASS='PASS_H115_B20_NATIVE_IMAGE_REPLAY_BYTE_IDENTICAL_NOT_HISTORICAL'
HOLD='HOLD_H115_B20_FUNCTIONAL_ROM'

class GateHold(RuntimeError):pass

def need(cond,code):
    if not cond:raise GateHold(code)

def sha(b):return hashlib.sha256(b).hexdigest()
def jsonbytes(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()

def strict_rom(blob):
    try:lines=blob.decode('ascii').splitlines()
    except UnicodeDecodeError:raise GateHold('NONASCII_ROM')
    need(lines and lines[0]=='KYIV41-OCT1','ROM_HEADER')
    from re import fullmatch
    d={}
    for line in lines[1:]:
        need(fullmatch(r'[0-7]{4} [0-7]{14}',line) is not None,'ROM_RECORD_FORMAT')
        a,v=int(line[:4],8),int(line[5:],8)
        need(0o3300<=a<0o4000 and v<(1<<41) and a not in d,'ROM_DUP_OR_RANGE')
        d[a]=v
    need(blob==('KYIV41-OCT1\n'+''.join(f'{a:04o} {w:014o}\n' for a,w in sorted(d.items()))).encode('ascii'),
         'ROM_NONCANONICAL_BYTES')
    return d

def archived(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=z.namelist()
        need(len(names)==len(set(names)),'ZIP_DUPLICATE')
        need(z.testzip() is None,'ZIP_CRC')
        for n in names:
            p=PurePosixPath(n)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in n and not (z.getinfo(n).external_attr>>16&0o170000==0o120000),
                 'ZIP_UNSAFE_MEMBER')
        need('SHA256SUMS.txt' in names,'ZIP_MANIFEST')
        index={}
        for line in z.read('SHA256SUMS.txt').decode('ascii').splitlines():
            d,n=line.split('  ',1)
            need(n in names and n not in index and sha(z.read(n))==d,'ZIP_MEMBER_SHA:'+n)
            index[n]=d
        need(set(index)==set(names)-{'SHA256SUMS.txt'},'ZIP_UNMANIFESTED_MEMBER')
        return {n:z.read(n) for n in names}

def audit(root):
    p=json.loads((HERE/'PROVENANCE.json').read_bytes())
    patches=json.loads((HERE/'PATCHES.json').read_bytes())
    need(p['schema']=='KYIV_H115_B20_FP_ROM_PROVENANCE_V1','PROVENANCE_SCHEMA')
    need(patches['schema']=='KYIV_H115_B20_FUNCTIONAL_FP_PATCHES_V1','PATCH_SCHEMA')
    source=(root/SOURCE).read_bytes(); fixed=(root/FIXED).read_bytes()
    need(sha(source)==p['source_image_sha256'],'PINNED_HISTORICAL_SOURCE_SHA')
    need(sha(fixed)==p['fixed_rom_sha256'],'PINNED_FIXED_ROM_SHA')
    old=strict_rom(source); new=strict_rom(FP_IMAGE.read_bytes())
    need(len(old)==251 and len(new)==257,'ROM_COUNTS')
    need(0o3574 not in old and 0o3574 not in new,'FORGED_3574')
    need(sha(FP_IMAGE.read_bytes())==p['functional_image_sha256'],'RECONSTRUCTED_ROM_SHA')
    need(p['patch_count']==12 and len(patches['patches'])==12,'PATCH_COUNT')
    diff={k for k in new if old.get(k)!=new[k]}
    need(len(diff)==12 and set(old).issubset(new),'ROM_MUTATION_SCOPE')
    touched=set()
    for entry in patches['patches']:
        a=int(entry['address_octal'],8)
        need(a not in touched and a in diff,'PATCH_EXTRA_OR_DUP')
        touched.add(a)
        ov=entry['original_word_octal']; nv=entry['functional_word_octal']
        need(new[a]==int(nv,8),'PATCH_VALUE_MISMATCH')
        if ov is None:
            need(a not in old and entry['classification']=='SYNTHETIC_UNPRINTED_WORD','PATCH_UNPRINTED_PROVENANCE')
        else:
            need(a in old and old[a]==int(ov,8) and entry['classification']=='REPLACEMENT_OF_PRINTED_WORD','PATCH_REPLACEMENT_PROVENANCE')
    need(len(new.keys()-old.keys())==6 and len({a for a in old if new[a]!=old[a]})==6,'PATCH_6_PLUS_6')
    e=B19.read_bytes()
    need(sha(e)==p['b19_evidence_sha256'],'B19_ARCHIVE_SHA')
    refs=archived(e)
    r=json.loads(refs['RESULT.json'])
    need(r['status']==B19_PASS and r['cpu_sessions']==52 and r['regression_cpu_runs']==51 and
         r['rk4_checkpoints']==42 and r['rk4_arithmetic_ops']==38 and r['regression_word_changes']==0,
         'B19_NOT_ACCEPTED')
    need(all(x['status']=='WORD_MATCH' for x in csv.DictReader(io.StringIO(refs['RK4/NATIVE_CHECKPOINTS.tsv'].decode()),delimiter='\t')),
         'B19_CHECKPOINT_MISMATCH')
    need(FP_IMAGE.name=='FP_FUNCTIONAL_1962_RECONSTRUCTED.k41','IMAGE_NAME')
    for path,key in [('reference/RK4_ORIGINAL_B16.k41','b16_original_rk4_image_sha256'),
                     ('native_rk4.cpp','native_rk4_image_loader_source_sha256'),
                     ('native_regression.cpp','native_regression_image_loader_source_sha256')]:
        need(sha((HERE/path).read_bytes())==p[key],'DEMO_SOURCE_SHA_DRIFT:'+path)
    # There is NO host PC override after initial boot, no per-address ROM patch.
    for name in ('native_rk4.cpp','native_regression.cpp'):
        src=(HERE/name).read_text(encoding='utf-8')
        need(src.count('cpu.C_reg=')==1,'RUNNER_PC_MUTATION:'+name)
        need(src.count('cpu.kmem.write_rom(')==1,'RUNNER_ROM_MUTATION:'+name)
        need('HOLD_FUNCTIONAL_ROM_ANCHOR_DRIFT' in src and ('HOLD_UNKNOWN' in src or 'UNKNOWN_ROM' in src or 'ROM_UNQUALIFIED' in src),
             'RUNNER_FAIL_CLOSED:'+name)
    return {'status':OFFLINE_PASS,'functional_rom_sha256':p['functional_image_sha256'],
            'historical_words':251,'functional_words':257,'replaced_source_words':6,'synthetic_unprinted_words':6,
            'b19_evidence_sha256':p['b19_evidence_sha256'],'b19_cpu_sessions':52,
            'historic_3574':'UNMATERIALIZED','physical_hardware_oracle':False}

def check_repo_cpu(root):
    p=json.loads((HERE/'PROVENANCE.json').read_bytes())
    for name,digest in p['upstream_cpu_git_blob'].items():
        q=subprocess.run(['git','hash-object',str(root/name)],cwd=root,capture_output=True,text=True)
        need(q.returncode==0 and q.stdout.strip()==digest,'CPU_GIT_BLOB_DRIFT:'+name)

def native(root,out):
    need(not out.exists() and not out.with_suffix('.zip').exists(),'NATIVE_OUTPUT_EXISTS')
    check_repo_cpu(root)
    base=audit(root)
    baseline=archived(B19.read_bytes())
    out.mkdir(parents=True)
    report={'status':HOLD,'reason':'NATIVE_NOT_STARTED','static':base}
    try:
        with tempfile.TemporaryDirectory(dir=root/'tempkyiv',prefix='_b20_native_') as tmp:
            d=Path(tmp)
            jobs=[('RK4','native_rk4.cpp',
                  [str(root/FIXED),str(FP_IMAGE),str(HERE/'reference/RK4_ORIGINAL_B16.k41')],
                  ['TRACE','CHECKPOINTS','SESSIONS','EVENTS']),
                  ('REGRESSION','native_regression.cpp',
                  [str(root/FIXED),str(FP_IMAGE)],['TRACE','RESULTS','INTERVENTIONS'])]
            for label,src,argv,outputs in jobs:
                exe=d/(label.lower()+'.exe')
                cp=subprocess.run(['g++','-std=c++17','-O0','-I',str(root/'inc'),str(HERE/src),str(root/'src/main.cpp'),'-o',str(exe)],
                                  cwd=root,capture_output=True,timeout=180)
                (out/(label+'_COMPILER_STDOUT.txt')).write_bytes(cp.stdout)
                (out/(label+'_COMPILER_STDERR.txt')).write_bytes(cp.stderr)
                need(cp.returncode==0,label+'_COMPILER_FAILED_'+str(cp.returncode))
                paths={x:out/(label+'_'+x+'.tsv') for x in outputs}
                cmd=[str(exe),*argv]
                if label=='RK4':cmd.extend(str(paths[x]) for x in outputs)
                else:cmd.extend([str(paths['TRACE']),str(paths['RESULTS']),'MACHINE_ROM_BRANCH',str(paths['INTERVENTIONS'])])
                cp=subprocess.run(cmd,cwd=root,capture_output=True,timeout=240)
                (out/(label+'_NATIVE_STDOUT.txt')).write_bytes(cp.stdout)
                (out/(label+'_NATIVE_STDERR.txt')).write_bytes(cp.stderr)
                need(cp.returncode==0,label+'_NATIVE_FAILED_'+str(cp.returncode))
                for kind,path in paths.items():
                    need(path.is_file(),label+'_MISSING_'+kind)
                    target=baseline[label+'/NATIVE_'+kind+'.tsv']
                    need(path.read_bytes()==target,'BYTE_DRIFT_'+label+'_'+kind)
            # Explicitly verify B19 outcomes, beyond raw file equality.
            rk=list(csv.DictReader((out/'RK4_CHECKPOINTS.tsv').open(),delimiter='\t'))
            reg=list(csv.DictReader((out/'REGRESSION_RESULTS.tsv').open(),delimiter='\t'))
            need(len(rk)==42 and all(x['status']=='WORD_MATCH' for x in rk),'RK4_ORACLE_HOLD')
            need(len(reg)==51 and sum('NUMERIC_EXACT' in x['status'] for x in reg)==39,'REGRESSION_ORACLE_HOLD')
            report={'status':NATIVE_PASS,'static':base,'cpu_sessions':52,
                'rk4_native_checkpoints':42,'rk4_numeric_operations':38,
                'regression_cases':51,'byte_identical_trace_and_results':7,
                'cpu_modified':False,'historical_rom_modified':False,'hardware_oracle':False}
    except Exception as exc:
        report={'status':HOLD,'reason':str(exc),'static':base}
    (out/'RESULT.json').write_bytes(jsonbytes(report))
    # Include ALL observed evidence files and hash every one.
    files={p.relative_to(out).as_posix():p.read_bytes() for p in sorted(out.iterdir()) if p.is_file()}
    files['SHA256SUMS.txt']=(''.join(sha(files[n])+'  '+n+'\n' for n in sorted(files))).encode('ascii')
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for name,blob in sorted(files.items()):z.writestr(name,blob)
    archived(out.with_suffix('.zip').read_bytes())
    print('B20_NATIVE_STATUS='+report['status'],flush=True)
    print('B20_NATIVE_EVIDENCE='+str(out.with_suffix('.zip')),flush=True)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    m=ap.add_mutually_exclusive_group(required=True)
    m.add_argument('--selftest',action='store_true')
    m.add_argument('--offline',action='store_true')
    m.add_argument('--native',action='store_true')
    ap.add_argument('--repo',type=Path)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    root=(a.repo or HERE.parents[1]).resolve()
    try:
        x=audit(root)
        if a.native:
            need(a.out is not None,'NATIVE_OUT_REQUIRED')
            report=native(root,(root/a.out).resolve())
            return 0 if report['status']==NATIVE_PASS else 4
        print(json.dumps(x,sort_keys=True,ensure_ascii=False))
        return 0
    except Exception as exc:
        print('H115_B20_HOLD|'+str(exc),file=sys.stderr)
        return 4
if __name__=='__main__':sys.exit(main())
