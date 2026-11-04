#!/usr/bin/env python3
"""Portable offline audit and opt-in native replay of the B15 Euler example.

Offline inspection revalidates saved native evidence; it is NOT a new CPU run.
Native mode compiles and executes the unchanged production CPU with the saved
H115-B15 C++ harness and the historical printed FP ROM + private errata.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
PROV = HERE/'PROVENANCE.json'
PASS = 'PASS_FP_EULER_NATIVE_RECONSTRUCTED_NOT_HISTORICAL'
HOLD = 'HOLD_FP_EULER_EXAMPLE'

class AuditError(RuntimeError):
    pass

def require(cond, message):
    if not cond:
        raise AuditError(message)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_table(data: bytes) -> list[dict[str,str]]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig')), delimiter='\t'))

def report(result: dict) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode()

def encode_fp(q: Fraction) -> str:
    """Independent rational encoder: 33-bit mantissa, biased 7-bit order."""
    q=Fraction(q)
    if not q:
        return '00000000000000'
    negative=q<0
    q=abs(q)
    order=0
    while q>=1:
        q/=2
        order+=1
    while q<Fraction(1,2):
        q*=2
        order-=1
    require(-64<order<63, 'FP_ORDER_OUT_OF_RANGE')
    mant=q*(1<<40)
    require(mant.denominator==1, 'FP_VALUE_NOT_EXACTLY_REPRESENTABLE')
    word=int(mant)|(order+64)|(int(negative)<<40)
    require(word < (1<<41), 'FP_TOO_WIDE')
    return f'{word:014o}'

def calculate_steps() -> list[dict]:
    y=Fraction(1); t=Fraction(0); h=Fraction(1,4); threshold=Fraction(7,8)
    result=[]
    for i in range(1,5):
        old_y=y;old_t=t
        delta=h*y; y-=delta; t+=h; d=threshold-t
        result.append({'iteration':i,'y_before':str(old_y),'delta':str(delta),
          'y_after':str(y),'t_before':str(old_t),'t_after':str(t),
          'difference':str(d),'delta_word':encode_fp(delta),'y_word':encode_fp(y),
          't_word':encode_fp(t),'difference_word':encode_fp(d),
          'negative_exit':d<0})
    return result

def expected_checkpoints() -> list[dict[str,str]]:
    state={'y':encode_fp(Fraction(1)),'t':encode_fp(Fraction(0)),
           'delta':encode_fp(Fraction(0)),'d':encode_fp(Fraction(0))}
    cp=[{'pointer':'0230', **state}]
    for i, step in enumerate(calculate_steps()):
        state['delta']=step['delta_word']
        cp.append({'pointer':'0231',**state})
        state['y']=step['y_word']
        cp.append({'pointer':'0232',**state})
        state['t']=step['t_word']
        cp.append({'pointer':'0233',**state})
        state['d']=step['difference_word']
        cp.append({'pointer':'0234',**state})
        if i<3:
            cp.append({'pointer':'0235',**state})
            cp.append({'pointer':'0230',**state})
        else:
            cp.append({'pointer':'0236',**state})
    require(len(cp)==24,'INTERNAL_CHECKPOINT_PLAN')
    return cp

def parse_image(raw: bytes) -> dict[int,int]:
    lines=raw.decode('ascii').splitlines()
    require(lines and lines[0]=='KYIV41-OCT1', 'INVALID_K41_MAGIC')
    words={}
    for line in lines[1:]:
        require(re.fullmatch(r'[0-7]{4} [0-7]{14}',line) is not None, 'K41_SYNTAX')
        a,w=(int(x,8) for x in line.split())
        require(1<=a<0o2000 and a not in words and w<1<<41, 'K41_ADDRESS_OR_WORD')
        require(a>0o32,'FP_SCRATCH_OVERLAP')
        words[a]=w
    return words

def verify_zip(z: ZipFile) -> None:
    names=z.namelist()
    require(len(names)==len(set(names)), 'ZIP_DUPLICATE_MEMBERS')
    require(z.testzip() is None,'ZIP_CRC')
    for n in names:
        q=PurePosixPath(n)
        require(not q.is_absolute() and '..' not in q.parts and '\\' not in n,'ZIP_UNSAFE_PATH')
        require((z.getinfo(n).external_attr>>16)&0o170000 != 0o120000,'ZIP_SYMLINK')
    require('SHA256SUMS.txt' in names,'ZIP_NO_MANIFEST')
    checks={}
    for line in z.read('SHA256SUMS.txt').decode().splitlines():
        h, n=line.split('  ',1)
        require(n in names and n not in checks and sha(z.read(n))==h,'ZIP_SHA_MISMATCH:'+n)
        checks[n]=h
    require(set(names)==set(checks)|{'SHA256SUMS.txt'},'ZIP_UNCHECKED_MEMBER')

def verify_inputs() -> dict:
    p=json.loads(PROV.read_text(encoding='utf-8'))
    require(p['schema']=='KYIV_H115_B17_FP_EULER_EXAMPLE_V1','PROVENANCE_SCHEMA')
    items={'native.cpp':'native_cpp_sha256',
           'inputs/EULER_IMAGE.k41':'image_sha256',
           'inputs/INDEPENDENT_ORACLE.json':'oracle_sha256',
           'evidence/H115_B15_FP_EULER_ODE_EVIDENCE_V1.zip':'evidence_sha256'}
    for n,key in items.items():
        require(sha((HERE/n).read_bytes())==p[key], 'INPUT_SHA_DRIFT:'+n)
    raw=(HERE/'inputs/EULER_IMAGE.k41').read_bytes()
    words=parse_image(raw)
    def op(code,a,b,c): return (code<<36)|(a<<24)|(b<<12)|c
    expected={
      0o100:int(encode_fp(Fraction(1)),8),
      0o101:int(encode_fp(Fraction(1,4)),8),
      0o102:0,
      0o103:int(encode_fp(Fraction(7,8)),8),
      0o104:0,0o105:0,
      0o230:op(0o11,0o100,0o101,0o104),
      0o231:op(0o02,0o100,0o104,0o100),
      0o232:op(0o01,0o102,0o101,0o102),
      0o233:op(0o02,0o103,0o102,0o105),
      0o234:op(0o31,0o105,0o235,0o236),
      0o235:op(0o31,0,0o230,0o230),
      0o236:op(0o33,0,0,0)
    }
    require(words==expected,'IMAGE_WORD_DRIFT')
    oracle=json.loads((HERE/'inputs/INDEPENDENT_ORACLE.json').read_text(encoding='utf-8'))
    require(oracle['schema']=='KYIV_H115_B15_EULER_FRACTION_V1','ORACLE_SCHEMA')
    require(oracle['steps']==calculate_steps(),'ORACLE_FRACTION_DRIFT')
    require(oracle['final_y']=='81/256' and oracle['all_dyadic_exact'],'ORACLE_FINAL')
    native=(HERE/'native.cpp').read_text(encoding='utf-8')
    require(len(re.findall(r'cpu\.C_reg\s*=',native))==1 and 'cpu.C_reg=03300' in native,'UNEXPECTED_HOST_PC_ASSIGNMENT')
    require('cpu.kmem.write_rom(03574' not in native,'INVENTED_ROM_3574')
    require('HOLD_RAW_USER_INSTRUCTION_FETCH' in native,'MISSING_RAW_EXEC_GUARD')
    require('HOLD_SOURCE_DERIVED_TRAMPOLINE' in native,'MISSING_TRAMPOLINE_GUARD')
    require('cpu.kmem.write_rom(03455' in native and 'cpu.kmem.write_rom(03706' in native and
            'cpu.kmem.write_rom(03707' in native,'PRIVATE_ROM_PATCH_INCOMPLETE')
    return p

def check_evidence(files: dict[str,bytes], rc: int=0) -> dict:
    require(rc==0,'NATIVE_RETURN_CODE_'+str(rc))
    require('NATIVE_SESSIONS.tsv' in files and 'NATIVE_CHECKPOINTS.tsv' in files and
            'NATIVE_TRACE.tsv' in files,'NATIVE_REPORT_MISSING')
    ss=read_table(files['NATIVE_SESSIONS.tsv'])
    require(len(ss)==1, 'SESSION_CARDINALITY')
    s=ss[0]
    require(s['case']=='EULER_NEG_Y' and s['status']=='PASS_EULER_MACHINE_LOOP_NOT_HISTORICAL' and
        s['actual_cpu_run']=='1' and s['hardware_oracle']=='NO' and
        s['checkpoints']=='24' and s['arithmetic_ops']=='16' and
        s['iterations']=='4' and s['back_edge_count']=='3' and s['decisions']=='4' and
        s['end_pc']=='3305' and s['end_pointer']=='0236', 'SESSION_COVERAGE_DRIFT')
    checkpoints=read_table(files['NATIVE_CHECKPOINTS.tsv'])
    exp=expected_checkpoints()
    require(len(checkpoints)==len(exp),'CHECKPOINT_COUNT')
    for i,(r,e) in enumerate(zip(checkpoints,exp)):
        require(r['ordinal']==str(i) and r['pointer']==e['pointer'] and
                r['status']=='WORD_MATCH', 'CHECKPOINT_'+str(i)+'_STATUS_OR_POINTER')
        for key in ('y','t','delta','d'):
            require(r[key+'_expected']==e[key] and r[key+'_observed']==e[key],
                    'CHECKPOINT_'+str(i)+'_WORD_'+key)
    trace=read_table(files['NATIVE_TRACE.tsv'])
    require(int(s['steps'])==len(trace),'TRACE_LENGTH')
    require(not any(0o230<=int(r['pc_before'],8)<=0o236 for r in trace),'RAW_USER_EXECUTION')
    require(not any(int(r['pc_before'],8)==0o3574 for r in trace),'UNPRINTED_3574_EXECUTED')
    require(all(r['gate']=='CONTINUE' for r in trace),'UNEXPECTED_CPU_STOP')
    return {'status':PASS,'verification':'NATIVE_TRACE_AND_INDEPENDENT_RATIONAL_ORACLE',
        'steps':len(trace),'checkpoint_matches':len(checkpoints),'iterations':4,
        'fp_operations':16,'back_edges':3,'conditions':4,'final_y':'81/256',
        'hardware_oracle':False}

def saved_evidence() -> dict:
    p=verify_inputs()
    path=HERE/'evidence/H115_B15_FP_EULER_ODE_EVIDENCE_V1.zip'
    with ZipFile(path) as z:
        verify_zip(z)
        files={n:z.read(n) for n in z.namelist()}
    result=json.loads(files['RESULT.json'])
    require(result['status']==p['original_evidence_status'], 'B15_STATUS_DRIFT')
    require(result['native_steps']==619 and result['iterations']==4 and
      result['arithmetic_ops']==16 and result['final_y']=='81/256', 'B15_RESULT_DRIFT')
    return check_evidence(files)

def repo_preflight(root:Path) -> dict:
    p=verify_inputs()
    require((root/'src/main.cpp').is_file() and (root/'inc/kyiv.h').is_file(), 'NOT_KYIV_REPO')
    for name, expected in p['upstream_baseline_git_blob_sha1'].items():
        path=root/name
        require(path.is_file(),'REPO_SOURCE_MISSING:'+name)
        blob=subprocess.check_output(['git','hash-object',str(path)],cwd=root,text=True).strip()
        require(blob==expected,'REPO_SOURCE_DRIFT:'+name)
    for name,key in [('mem/ROM.txt','rom_sha256'),
      ('examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41','printed_fp_251_source_sha256')]:
        path=root/name
        require(path.is_file() and sha(path.read_bytes())==p[key],'REPO_ROM_DRIFT:'+name)
    return {'status':'PASS_REPO_SOURCE_PINS','source_pins':len(p['upstream_baseline_git_blob_sha1']),
            'fixed_rom_sha256':p['rom_sha256'],'historical_251_sha256':p['printed_fp_251_source_sha256']}

def native(root:Path,out:Path) -> int:
    require(out.parent.is_dir(),'OUT_PARENT_NOT_FOUND')
    require(not out.exists() and not out.with_suffix('.zip').exists(), 'OUT_ALREADY_EXISTS')
    out.mkdir()
    files={}
    status={'status':HOLD, 'reason':'NOT_STARTED'}
    rc=4
    try:
        files['SOURCE_CHECK.json']=report(repo_preflight(root))
        files['SAVED_EVIDENCE_CHECK.json']=report(saved_evidence())
        with tempfile.TemporaryDirectory(prefix='_fp_euler_native_',dir=root/'tempkyiv') as tmp:
            tmp=Path(tmp)
            exe=tmp/'fp_euler.exe'
            cmd=['g++','-std=c++17','-O0','-I',str(root/'inc'),
                 str(HERE/'native.cpp'),str(root/'src/main.cpp'),'-o',str(exe)]
            cp=subprocess.run(cmd,cwd=root,capture_output=True,timeout=180,check=False)
            files['COMPILER_STDOUT.txt']=cp.stdout
            files['COMPILER_STDERR.txt']=cp.stderr
            require(cp.returncode==0,'COMPILER_RETURN_CODE_'+str(cp.returncode))
            names=['NATIVE_TRACE.tsv','NATIVE_CHECKPOINTS.tsv','NATIVE_SESSIONS.tsv','NATIVE_EVENTS.tsv']
            paths=[tmp/n for n in names]
            cmd=[str(exe), str(root/'mem/ROM.txt'),
                 str(root/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'),
                 str(HERE/'inputs/EULER_IMAGE.k41'), *map(str,paths)]
            cp=subprocess.run(cmd,cwd=root,capture_output=True,timeout=240,check=False)
            files['NATIVE_STDOUT.txt']=cp.stdout
            files['NATIVE_STDERR.txt']=cp.stderr
            for n,path in zip(names,paths):
                if path.is_file():files[n]=path.read_bytes()
            status=check_evidence(files,cp.returncode)
            rc=0
    except Exception as ex:
        status={'status':HOLD,'reason':str(ex)}
    files['RESULT.json']=report(status)
    files['SHA256SUMS.txt']=b''.join(f'{sha(files[n])}  {n}\n'.encode() for n in sorted(files))
    for n,body in files.items(): (out/n).write_bytes(body)
    archive=out.with_suffix('.zip')
    with ZipFile(archive,'x',ZIP_DEFLATED,compresslevel=8) as z:
        for n,body in sorted(files.items()):z.writestr(n,body)
    with ZipFile(archive) as z:verify_zip(z)
    print('EULER_NATIVE_EVIDENCE='+str(archive))
    print('EULER_NATIVE_STATUS='+status['status'])
    if rc:print('EULER_HOLD_REASON='+str(status.get('reason')))
    return rc

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--offline',action='store_true',help='verify saved native B15 evidence; no CPU execution')
    group.add_argument('--selftest',action='store_true',help='verify image, independent oracle and negative controls')
    group.add_argument('--native',action='store_true',help='compile and run current pinned production CPU')
    ap.add_argument('--repo',type=Path,default=HERE.parents[1])
    ap.add_argument('--out',type=Path,help='new evidence directory for --native, within tempkyiv/')
    args=ap.parse_args()
    try:
        if args.selftest:
            p=verify_inputs()
            require(len(parse_image((HERE/'inputs/EULER_IMAGE.k41').read_bytes()))==13,'IMAGE_RECORD_COUNT')
            require(len(expected_checkpoints())==24,'CP_COUNT')
            require([s['y_after'] for s in calculate_steps()]==['3/4','9/16','27/64','81/256'],'EULER_MATH')
            try:
                parse_image((HERE/'inputs/EULER_IMAGE.k41').read_bytes().replace(b'KYIV41-OCT1',b'KYIV41-XCT1'))
            except AuditError: pass
            else: raise AuditError('NEGATIVE_MAGIC_ACCEPTED')
            print('FP_EULER_SELFTEST_PASS|SOURCE=1|IMAGE=13|ORACLE=4|CHECKPOINTS=24|NEGATIVE=1')
        elif args.offline:
            s=saved_evidence()
            print('FP_EULER_OFFLINE_EVIDENCE_PASS|NOT_NEW_CPU_RUN')
            print('iteration  t       y')
            print('0          0       1')
            for x in calculate_steps():
                print(f"{x['iteration']}          {x['t_after']:<7} {x['y_after']}")
            print('native_steps=',s['steps'],' check_points=',s['checkpoint_matches'])
        else:
            root=args.repo.resolve()
            require(args.out is not None,'NATIVE_REQUIRES_OUT')
            out=args.out.resolve()
            require(out.is_relative_to((root/'tempkyiv').resolve()),'OUT_NOT_WITHIN_TEMP_KYIV')
            return native(root,out)
        return 0
    except Exception as ex:
        print('FP_EULER_'+HOLD+'|'+str(ex),file=sys.stderr)
        return 4

if __name__=='__main__':
    sys.exit(main())
