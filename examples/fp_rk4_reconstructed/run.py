#!/usr/bin/env python3
"""Portable RK4 example: independently audit original native trace or replay on pinned production CPU.

The archived native proof is not a new native execution. Machine code and
native harness are the unmodified bytes accepted in H115-B16-R1.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
import oracle

HERE=Path(__file__).resolve().parent
PASS='PASS_FP_RK4_TWO_STEP_NATIVE_RECONSTRUCTED_NOT_HISTORICAL'
HOLD='HOLD_FP_RK4_EXAMPLE'
class AuditError(Exception):pass

def need(ok,msg):
    if not ok:raise AuditError(msg)
def sha(data):return hashlib.sha256(data).hexdigest()
def json_bytes(obj):return (json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode('utf-8')

def verify_evidence_zip(z):
    names=z.namelist()
    need(len(names)==len(set(names)),'ZIP_DUPLICATES')
    need(z.testzip() is None,'ZIP_CRC')
    need('SHA256SUMS.txt' in names,'ZIP_MANIFEST_MISSING')
    for name in names:
        q=PurePosixPath(name)
        need(not q.is_absolute() and '..' not in q.parts and '\\' not in name,'ZIP_UNSAFE_MEMBER')
        need((z.getinfo(name).external_attr>>16)&0o170000 != 0o120000,'ZIP_SYMLINK')
    checks={}
    for line in z.read('SHA256SUMS.txt').decode().splitlines():
        h,n=line.split('  ',1)
        need(n not in checks and n in names and sha(z.read(n))==h,'ZIP_MEMBER_SHA:'+n)
        checks[n]=h
    need(set(names)==set(checks)|{'SHA256SUMS.txt'},'ZIP_UNCHECKED_MEMBERS')
    return len(checks)

def verify_inputs():
    m=json.loads((HERE/'PROVENANCE.json').read_text(encoding='utf-8'))
    need(m['schema']=='KYIV_H115_B18_FP_RK4_RECONSTRUCTED_EXAMPLE_V1','PROVENANCE_SCHEMA')
    for filename,key in [
        ('native.cpp','original_native_sha256'),
        ('inputs/RK4_IMAGE.k41','image_sha256'),
        ('inputs/INDEPENDENT_ORACLE.json','independent_oracle_sha256'),
        ('oracle.py','oracle_source_sha256'),
        ('evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip','original_evidence_sha256'),
        ('reference/B16_HOLD_EVIDENCE_V1.zip','negative_B16_evidence_sha256'),
        ('reference/B15_PASS_EVIDENCE_V1.zip','prior_B15_evidence_sha256'),
    ]:
        need(sha((HERE/filename).read_bytes())==m[key],'SOURCE_SHA_DRIFT:'+filename)
    need(oracle.static()['status']=='PASS_B16_STATIC_NOT_NATIVE','ORACLE_STATIC_FAIL')
    return m

def audit_saved_evidence():
    m=verify_inputs()
    with ZipFile(HERE/'evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip') as z:
        n=verify_evidence_zip(z)
        files={name:z.read(name) for name in z.namelist()}
    result=json.loads(files['RESULT.json'])
    need(result['status']==m['original_evidence_status'],'NATIVE_RESULT_STATUS')
    actual=oracle.judge(files,0)
    need(actual['status']==m['original_evidence_status'],'NATIVE_REAUDIT_STATUS')
    for k,v in [('native_steps',1637),('iterations',2),('dispatcher_checkpoints',54),
                ('arithmetic_ops',50),('machine_back_edges',1),('conditional_decisions',2),
                ('first_y','1595/2048'),('final_y','2544025/4194304')]:
        need(actual[k]==v and result[k]==v,'NATIVE_RESULT_DRIFT:'+k)
    need(n==14,'NATIVE_EVIDENCE_FILE_COUNT')
    need(all(a==b for a,b in zip(oracle.math_iterations(),json.loads(
        (HERE/'inputs/INDEPENDENT_ORACLE.json').read_text())['iterations'])),'ORACLE_ITERATION_DRIFT')
    return {'status':PASS,'type':'REVALIDATED_SAVED_PRODUCTION_CPU_TRACE_NOT_NEW_CPU_EXECUTION',
        'native_steps':1637,'fp_arithmetic_operations':50,'dispatcher_checkpoints':54,
        'iterations':2,'first_y':'1595/2048','final_y':'2544025/4194304',
        'original_evidence_sha256':m['original_evidence_sha256'],'hardware_oracle':False}

def repo_preflight(root):
    m=verify_inputs()
    need((root/'src/main.cpp').is_file() and (root/'inc/kyiv.h').is_file(),'NOT_KYIV_REPO')
    for name,digest in m['upstream_baseline_git_blob_sha1'].items():
        path=root/name
        need(path.is_file(),'CPU_FILE_MISSING:'+name)
        cp=subprocess.run(['git','hash-object',str(path)],cwd=root,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,text=True,check=False)
        need(cp.returncode==0 and cp.stdout.strip()==digest,'CPU_SOURCE_DRIFT:'+name)
    for name,key in [('mem/ROM.txt','fixed_rom_sha256'),
        ('examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41','printed_fp_251_source_sha256')]:
        p=root/name
        need(p.is_file() and sha(p.read_bytes())==m[key],'ROM_SOURCE_DRIFT:'+name)
    return {'status':'PASS_PINNED_CPU_AND_HISTORICAL_ROM','source_files':len(m['upstream_baseline_git_blob_sha1'])}

def pack_evidence(out,files):
    need(not out.exists() and not out.with_suffix('.zip').exists(),'EVIDENCE_ALREADY_EXISTS')
    out.mkdir()
    files['SHA256SUMS.txt']=b''.join(f'{sha(files[name])}  {name}\n'.encode() for name in sorted(files))
    for n,data in files.items():(out/n).write_bytes(data)
    with ZipFile(out.with_suffix('.zip'),'x',ZIP_DEFLATED,compresslevel=8) as z:
        for n,data in sorted(files.items()):z.writestr(n,data)
    with ZipFile(out.with_suffix('.zip')) as z:verify_evidence_zip(z)
    print('FP_RK4_NATIVE_EVIDENCE='+str(out.with_suffix('.zip')),flush=True)

def replay(root,out):
    files={}
    result={'status':HOLD,'reason':'NOT_STARTED'}
    code=4
    try:
        files['SAVED_PROOF_AUDIT.json']=json_bytes(audit_saved_evidence())
        files['SOURCE_PREFLIGHT.json']=json_bytes(repo_preflight(root))
        with tempfile.TemporaryDirectory(prefix='_fp_rk4_',dir=root/'tempkyiv') as t:
            td=Path(t)
            exe=td/'fp_rk4.exe'
            command=['g++','-std=c++17','-O0','-I',str(root/'inc'),
                     str(HERE/'native.cpp'),str(root/'src/main.cpp'),'-o',str(exe)]
            cp=subprocess.run(command,cwd=root,capture_output=True,timeout=180,check=False)
            files['COMPILER_STDOUT.txt']=cp.stdout
            files['COMPILER_STDERR.txt']=cp.stderr
            need(cp.returncode==0,'COMPILER_RC_'+str(cp.returncode))
            names=['NATIVE_TRACE.tsv','NATIVE_CHECKPOINTS.tsv','NATIVE_SESSIONS.tsv','NATIVE_EVENTS.tsv']
            paths=[td/n for n in names]
            command=[str(exe),str(root/'mem/ROM.txt'),
                     str(root/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'),
                     str(HERE/'inputs/RK4_IMAGE.k41'),*(str(x) for x in paths)]
            cp=subprocess.run(command,cwd=root,capture_output=True,timeout=240,check=False)
            files['NATIVE_STDOUT.txt']=cp.stdout
            files['NATIVE_STDERR.txt']=cp.stderr
            for n,path in zip(names,paths):
                if path.is_file():files[n]=path.read_bytes()
            result=oracle.judge(files,cp.returncode)
            need(result['status']=='PASS_H115_B16_R1_BOUNDED_SUM_RK4_NOT_HISTORICAL',
                 'NATIVE_CPU_HOLD:'+result.get('reason','CHECKPOINT_OR_ROUTE'))
            code=0
            result={'status':PASS,'native_result':result,'new_native_run':True}
    except Exception as e:
        result={'status':HOLD,'reason':str(e),'new_native_run':False}
    files['RESULT.json']=json_bytes(result)
    pack_evidence(out,files)
    print('FP_RK4_NATIVE_STATUS='+result['status'],flush=True)
    return code

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group(required=True)
    modes.add_argument('--selftest',action='store_true')
    modes.add_argument('--offline',action='store_true')
    modes.add_argument('--native',action='store_true')
    ap.add_argument('--repo',type=Path,default=HERE.parents[1])
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    try:
        if args.selftest:
            verify_inputs()
            need(len(oracle.expected_image())==47,'IMAGE_SIZE')
            need(len(oracle.simulation()[0])==54,'CHECKPOINTS')
            need(oracle.judge({},4)['status']=='HOLD_H115_B16_R1','NEGATIVE_GATE')
            bad=(HERE/'inputs/RK4_IMAGE.k41').read_bytes().replace(b'KYIV41-OCT1',b'KYIV41-OCT2')
            try:oracle.parse_image(bad)
            except oracle.Hold:pass
            else:raise AuditError('BAD_MAGIC_ACCEPTED')
            print('FP_RK4_SELFTEST_PASS|IMAGE=47|STAGES=50|CHECKPOINTS=54|NEGATIVE_B16=1')
            return 0
        if args.offline:
            result=audit_saved_evidence()
            print('FP_RK4_OFFLINE_PASS|NOT_NEW_CPU_EXECUTION')
            print('step  t    y')
            print('0     0    1')
            for k in oracle.math_iterations():print(k['iteration'],k['t_after'],k['y_after'])
            print('NATIVE_STEPS=',result['native_steps'],' CHECKPOINTS=',result['dispatcher_checkpoints'])
            return 0
        root=args.repo.resolve()
        need(args.out is not None,'NATIVE_REQUIRES_OUT')
        out=args.out.resolve()
        need(out.is_relative_to((root/'tempkyiv').resolve()),'OUT_NOT_WITHIN_TEMP_KYIV')
        need((root/'tempkyiv').is_dir(),'TEMP_KYIV_MISSING')
        need(not out.exists() and not out.with_suffix('.zip').exists(),'OUT_ALREADY_EXISTS')
        return replay(root,out)
    except Exception as e:
        print(HOLD+'|'+str(e),file=sys.stderr)
        return 4

if __name__=='__main__':sys.exit(main())
