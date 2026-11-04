#!/usr/bin/env python3
"""H115-B16-R1: fail-closed native 2-step RK4 on the reconstructed FP-ROM.

Only a user-side native C++ harness is compiled. Source ROM, fixed ROM and
production CPU source are immutable. Numerical oracle uses fractions.Fraction.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
HEAD_PREFIX = '74f4211'
PARENT_HEAD = '82bcacc0ad0e96abc23b98616b6390aa7715d3f6'
BRANCH = 'h114-fp-fast-track-romset'
OUT = 'H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip'
FIXED_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
SOURCE_SHA = 'ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba'
B15_PACKAGE_SHA = 'dd3893e946a2b03c3803332c85a91d2ab483e31beb65714a89ec223e17122c62'
B15_NATIVE_SHA = '53952441ae9e5dcb17e0f4be45fa1e9eca1aa635617b93e1e2754581f52ee100'
R1_NATIVE_SHA = 'e4cbf1410336d33bb7c0930d0c6f58253f60fff65eccf7434461676b6cc938eb'
B16_EVIDENCE_SHA = 'ec353fdf388c7a9fac4cf060ab3b9d378b8f743dfebb6fdd044429580e76adff'
B15_EVIDENCE_SHA = 'd2e4b797de6821b46cb8ec12022348508628a117db77c58d05682b976d752bca'

class Hold(Exception): pass

def need(ok, reason):
    if not ok:
        raise Hold(reason)

def sha(b): return hashlib.sha256(b).hexdigest()
def J(d): return (json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True, encoding='utf-8').rstrip('\r\n')
def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig')), delimiter='\t'))

def fp(q):
    # Independent fraction encoding; never use floating-point or C++ CPU arithmetic.
    q=F(q)
    if not q:return 0
    negative=q<0; q=abs(q); p=0
    while q>=1:q/=2;p+=1
    while q<F(1,2):q*=2;p-=1
    need(-64<p<63,'ORACLE_EXPONENT_RANGE')
    mant=q*(1<<40)
    need(mant.denominator==1,'ORACLE_INEXACT_STAGE:'+str(q))
    return int(mant)|int(p+64)|(int(negative)<<40)

def decode_fp(w):
    if not w:return F(0)
    neg=-1 if w & (1<<40) else 1
    mant=(w&((1<<40)-1))>>7
    exponent=(w&127)-64
    need((mant & (1<<32))!=0,'UNNORMALIZED_INPUT')
    return F(neg*mant,1<<33)*(F(2)**exponent)

def pack(op,a,b,c):
    need(0<=op<0o40 and all(0<=v<0o10000 for v in (a,b,c)),'PACK_RANGE')
    return (op<<36)|(a<<24)|(b<<12)|c

STATES=['y','t','k1','a','k2','b','k3','c','k4','sum','scaled','d']
ADDRS={
 'y':0o100,'t':0o101,'k1':0o120,'a':0o121,'k2':0o122,'b':0o123,
 'k3':0o124,'c':0o125,'k4':0o126,'sum':0o127,'scaled':0o130,'d':0o131,
}
CONSTANTS={0o102:F(1,4),0o103:F(1,8),0o104:F(2),0o105:F(6),0o106:F(0),0o107:F(3,8)}
STATES=['y','t','k1','a','k2','b','k3','c','k4','sum','scaled','d']
ADDRS={'y':0o100,'t':0o101,'k1':0o120,'a':0o121,'k2':0o122,'b':0o123,
 'k3':0o124,'c':0o125,'k4':0o126,'sum':0o127,'scaled':0o130,'d':0o131}
CONSTANTS={0o102:F(1,4),0o103:F(1,8),0o104:F(2),0o105:F(6),0o106:F(0),0o107:F(3,8),0o110:F(1)}
PROGRAM=[
 (0o02,0o106,0o100,0o120), # k1=-y
 (0o11,0o120,0o103,0o121), # a=k1*h/2
 (0o01,0o100,0o121,0o121), # a=y+a
 (0o02,0o106,0o121,0o122), # k2=-a
 (0o11,0o122,0o103,0o123), # b=k2*h/2
 (0o01,0o100,0o123,0o123), # b=y+b
 (0o02,0o106,0o123,0o124), # k3=-b
 (0o11,0o124,0o102,0o125), # c=k3*h
 (0o01,0o100,0o125,0o125), # c=y+c
 (0o02,0o106,0o125,0o126), # k4=-c
 (0o01,0o110,0o106,0o127), # sum=1 (compensation)
 (0o11,0o120,0o103,0o130), # scaled=k1/8
 (0o01,0o127,0o130,0o127), # sum+=k1/8
 (0o11,0o122,0o102,0o130), # scaled=k2/4
 (0o01,0o127,0o130,0o127), # sum+=k2/4
 (0o11,0o124,0o102,0o130), # scaled=k3/4
 (0o01,0o127,0o130,0o127), # sum+=k3/4
 (0o11,0o126,0o103,0o130), # scaled=k4/8
 (0o01,0o127,0o130,0o127), # sum+=k4/8
 (0o02,0o127,0o110,0o127), # sum-=1 (remove compensation)
 (0o12,0o127,0o105,0o130), # scaled=sum/6
 (0o11,0o130,0o104,0o130), # scaled=2*scaled
 (0o01,0o100,0o130,0o100), # y+=scaled
 (0o01,0o101,0o102,0o101), # t+=h
 (0o02,0o107,0o101,0o131), # d=threshold-t
]

PROGRAM_LABELS=['k1=-y', 'a=k1*h/2', 'a=y+a', 'k2=-a', 'b=k2*h/2', 'b=y+b', 'k3=-b', 'c=k3*h', 'c=y+c', 'k4=-c', 'sum=1 (compensation)', 'scaled=k1/8', 'sum+=k1/8', 'scaled=k2/4', 'sum+=k2/4', 'scaled=k3/4', 'sum+=k3/4', 'scaled=k4/8', 'sum+=k4/8', 'sum-=1 (remove compensation)', 'scaled=sum/6', 'scaled=2*scaled', 'y+=scaled', 't+=h', 'd=threshold-t']


def expected_image():
    a={0o100:fp(F(1)),0o101:0}
    a.update({address:fp(value) for address,value in CONSTANTS.items()})
    a.update({address:0 for key,address in ADDRS.items() if key not in ('y','t')})
    a.update({0o240+i:pack(*quad) for i,quad in enumerate(PROGRAM)})
    a[0o271]=pack(0o31,0o131,0o272,0o273)
    a[0o272]=pack(0o31,0,0o240,0o240)
    a[0o273]=pack(0o33,0,0,0)
    need(len(a)==47 and len(PROGRAM)==25,'IMAGE_COUNT')
    return a

def parse_image(data):
    lines=data.decode().splitlines()
    need(lines and lines[0]=='KYIV41-OCT1','K41_MAGIC')
    r={}
    for line in lines[1:]:
        need(re.fullmatch(r'[0-7]{4} [0-7]{14}',line) is not None,'K41_SYNTAX')
        a,w=(int(x,8) for x in line.split())
        need(a not in r and 0<a<0o2000 and w<(1<<41),'K41_DUPLICATE_OR_RANGE')
        r[a]=w
    return r

def verify_zip(z):
    need(z.testzip() is None,'ZIP_CRC')
    names=z.namelist()
    need(len(names)==len(set(names)),'ZIP_DUPLICATE')
    need('SHA256SUMS.txt' in names,'ZIP_MANIFEST')
    entries=z.read('SHA256SUMS.txt').decode().splitlines()
    for line in entries:
        h,n=line.split('  ',1)
        need(n in names and sha(z.read(n))==h,'ZIP_SHA_DRIFT:'+n)
    return len(entries)

def math_iterations():
    # A second, higher-level oracle independent from the machine program:
    # the RK4 stability polynomial for f(y)=-y is 1-h+h^2/2-h^3/6+h^4/24.
    h=F(1,4); r=1-h+h*h/2-h**3/6+h**4/24
    need(r==F(1595,2048),'RK4_STABILITY_FACTOR')
    y=F(1);t=F(0);it=[]
    for i in range(1,3):
        k1=-y; k2=-(y+h*k1/2); k3=-(y+h*k2/2); k4=-(y+h*k3)
        s=k1+2*k2+2*k3+k4;dy=h*s/6
        after=y+dy;t+=h;d=F(3,8)-t
        need(after==y*r,'RK4_CLOSED_FORM_MISMATCH')
        it.append({'iteration':i,'y_before':str(y),'y_after':str(after),
            't_after':str(t),'k1':str(k1),'k2':str(k2),
            'k3':str(k3),'k4':str(k4),'weighted_sum':str(s),'scaled_sum':str(s/8),
            'increment':str(dy),'d':str(d),'exit':d<0})
        y=after
    need(it[-1]['y_after']=='2544025/4194304','RK4_FINAL_DRIFT')
    return it

def simulation():
    words=expected_image()
    ram={a:decode_fp(v) for a,v in words.items() if a<0o200 and a!=0}
    expected=[{'pointer':'0240','iteration':0,**{k:f'{fp(ram[ADDRS[k]]):014o}' for k in STATES}}]
    stages=[];iterations=[]
    for iteration in (1,2):
        initial_y=ram[0o100]
        for i in range(25):
            opcode,a,b,c=PROGRAM[i]
            aa=ram[a];bb=ram[b]
            need(opcode in (1,2,0o11,0o12),'UNEXPECTED_ARITHMETIC_OPCODE')
            if opcode==1:v=aa+bb
            elif opcode==2:v=aa-bb
            elif opcode==0o11:v=aa*bb
            else:need(bb!=0,'ORACLE_DIV_ZERO');v=aa/bb
            if opcode==1 and 0o252<=0o240+i<=0o262 and bb:
                need(aa>0 and bb<0,'UNSAFE_SAMESIGN_NEGATIVE_SUM')
            old=ram[c];ram[c]=v
            stages.append({'iteration':iteration,'command':f'{0o240+i:04o}',
              'operation':f'{opcode:02o}','meaning':PROGRAM_LABELS[i],
              'destination':f'{c:04o}', 'before_fraction':str(old),
              'lhs_fraction':str(aa),'rhs_fraction':str(bb),
              'result_fraction':str(v),'expected_word':f'{fp(v):014o}',
              'exactly_representable':True})
            expected.append({'pointer':f'{0o240+i+1:04o}','iteration':iteration,
               **{k:f'{fp(ram[ADDRS[k]]):014o}' for k in STATES}})
        weighted=ram[0o120]+2*ram[0o122]+2*ram[0o124]+ram[0o126]
        need(ram[0o127]==weighted/8,'WEIGHTED_SUM_IDENTITY')
        need(ram[0o130]==weighted/24,'INCREMENT_IDENTITY')
        need(ram[0o100]==initial_y+F(1,4)*weighted/6,'RK4_STEP_IDENTITY')
        iterations.append({'iteration':iteration,'y_before':str(initial_y),
          'y_after':str(ram[0o100]),'t_after':str(ram[0o101]),
          'k1':str(ram[0o120]),'k2':str(ram[0o122]),
          'k3':str(ram[0o124]),'k4':str(ram[0o126]),
          'weighted_sum':str(weighted),'scaled_sum':str(weighted/8),
          'increment':str(ram[0o130]),'d':str(ram[0o131]),'exit':ram[0o131]<0})
        dest='0273' if iteration==2 else '0272'
        expected.append({'pointer':dest,'iteration':iteration,
                         **{k:f'{fp(ram[ADDRS[k]]):014o}' for k in STATES}})
        if iteration==1:
            expected.append({'pointer':'0240','iteration':iteration,
                             **{k:f'{fp(ram[ADDRS[k]]):014o}' for k in STATES}})
    need(len(expected)==54 and len(stages)==50,'ORACLE_COUNTS')
    need(iterations==math_iterations(),'HIGH_LEVEL_ORACLE_DRIFT')
    return expected,stages


def static():
    need(parse_image((HERE/'inputs/RK4_IMAGE.k41').read_bytes())==expected_image(),'IMAGE_WORD_DRIFT')
    oracle=json.loads((HERE/'inputs/INDEPENDENT_ORACLE.json').read_text())
    need(oracle['schema']=='H115_B16_R1_RK4_BOUNDED_SUM_FRACTION_EXACT_V1','ORACLE_SCHEMA')
    marks,stages=simulation()
    need(oracle['checkpoints']==marks,'ORACLE_CHECKPOINT_DRIFT')
    need(len(oracle['arithmetic_stages'])==50,'ORACLE_STAGE_LENGTH')
    for actual,expected in zip(oracle['arithmetic_stages'],stages):
        for k in ('iteration','command','operation','destination','before_fraction',
                  'result_fraction','expected_word','exactly_representable','lhs_fraction','rhs_fraction'):
            need(actual[k]==expected[k],'ORACLE_STAGE_DRIFT:'+actual['command']+':'+k)
    need(oracle['iterations']==math_iterations(),'RK4_MATH_DRIFT')
    need(oracle['final_y']=='2544025/4194304','RK4_FINAL_ORACLE_DRIFT')
    native=(HERE/'native.cpp').read_bytes()
    source=native.decode()
    need(sha(native)==R1_NATIVE_SHA,'NATIVE_SOURCE_SHA_DRIFT')
    need(len(re.findall(r'cpu\.C_reg\s*=',source))==1 and 'cpu.C_reg=03300' in source,'HOST_PC_WRITES')
    need('cpu.kmem.set_panel_nk_word(03000,pack(0,0,0240,0))' in source,'NK_ENTRY_DRIFT')
    need('HOLD_RAW_USER_INSTRUCTION_FETCH' in source and 'HOLD_UNQUALIFIED_RAM_EXEC' in source,'RAW_RAM_GUARD_MISSING')
    need('HOLD_SOURCE_DERIVED_TRAMPOLINE' in source and 'HOLD_USER_SOURCE_MUTATION' in source,'SOURCE_PROVENANCE_GUARD_MISSING')
    need('cpu.kmem.write_rom(03574' not in source and 'cpu.kmem.write_memory(03574' not in source,'INVENTED_3574')
    need(source.count('cpu.kmem.write_rom(03455')==1 and source.count('cpu.kmem.write_rom(03706')==1,'PRIVATE_FP_PATCH_DRIFT')
    need(source.count('cpu.kmem.write_rom(')==8,'FP_PATCH_COUNT_DRIFT')
    # Previously observed native failure is preserved as a negative control.
    with ZipFile(HERE/'reference/B16_HOLD_EVIDENCE_V1.zip') as z:
        verify_zip(z)
        need(json.loads(z.read('RESULT.json'))['status']=='HOLD_H115_B16','PREVIOUS_B16_STATUS')
        original_image=parse_image(z.read('INPUT_RK4_IMAGE.k41'))
        candidate_image=expected_image()
        need(all(original_image[0o240+i]==candidate_image[0o240+i] for i in range(10)),
             'B16_FIRST_TEN_COMMANDS_DRIFT')
        need(original_image[0o252]!=candidate_image[0o252] and
             original_image[0o252]==pack(0o01,0o122,0o124,0o127) and
             candidate_image[0o252]==pack(0o01,0o110,0o106,0o127),
             'B16_OVERFLOW_PROBE_REPLACEMENT_DRIFT')
        cps=rows(z.read('NATIVE_CHECKPOINTS.tsv'))
        need(len(cps)==12 and cps[-1]['pointer']=='0253' and
             cps[-1]['status']=='WORD_MISMATCH' and
             cps[-1]['sum_expected']=='36100000000101' and
             cps[-1]['sum_observed']=='01700000000101','ORIGINAL_FAILURE_ANCHOR')
    with ZipFile(HERE/'reference/B15_PASS_EVIDENCE_V1.zip') as z:
        verify_zip(z)
        need(json.loads(z.read('RESULT.json'))['status']==
             'PASS_H115_B15_EULER_MACHINE_ODE_NOT_HISTORICAL','B15_PASS_ANCHOR')
    need(sha((HERE/'reference/B16_HOLD_EVIDENCE_V1.zip').read_bytes())==B16_EVIDENCE_SHA,'B16_ZIP_PIN')
    need(sha((HERE/'reference/B15_PASS_EVIDENCE_V1.zip').read_bytes())==B15_EVIDENCE_SHA,'B15_ZIP_PIN')
    return {'status':'PASS_B16_STATIC_NOT_NATIVE','previous_B15_status':'PASS',
        'source_sha256':SOURCE_SHA,'fixed_rom_sha256':FIXED_SHA,
        'input_records':47,'arithmetic_stages':50,'machine_iterations':2,
        'machine_decisions':2,'machine_back_edges':1,'dispatcher_checkpoints':54,
        'numerical_oracle':'INDEPENDENT_EXACT_RATIONAL_RECHECKED_TWICE',
        'final_y':oracle['final_y'],'production_cpu_changed':False,
        'historical_3574':'UNFILLED','historical_claim':'NONE',
        'native_execution':'NOT_YET_RUN'}

def judge(files,rc):
    if rc!=0 and 'NATIVE_SESSIONS.tsv' not in files:
        return {'status':'HOLD_H115_B16_R1','reason':f'NATIVE_RC_{rc}_NO_SESSIONS'}
    ss=rows(files['NATIVE_SESSIONS.tsv']) if 'NATIVE_SESSIONS.tsv' in files else []
    cc=rows(files['NATIVE_CHECKPOINTS.tsv']) if 'NATIVE_CHECKPOINTS.tsv' in files else []
    if len(ss)!=1 or ss[0]['case']!='RK4_NEG_Y':
        return {'status':'HOLD_H115_B16_R1','reason':'SESSION_CARDINALITY','sessions':ss}
    s=ss[0]
    marks,_=simulation()
    if len(cc)!=54:
        return {'status':'HOLD_H115_B16_R1','reason':'CHECKPOINT_CARDINALITY',
                'observed':len(cc),'expected':54,'session':s}
    mismatch=None
    for i,(r,e) in enumerate(zip(cc,marks)):
        if r['ordinal']!=str(i) or r['pointer']!=e['pointer'] or r['status']!='WORD_MATCH' or any(
            r[k+'_expected']!=e[k] or r[k+'_observed']!=e[k] for k in STATES):
            mismatch={'ordinal':i,'actual':r,'expected':e};break
    if mismatch:
        return {'status':'HOLD_H115_B16_R1','reason':'CHECKPOINT_DRIFT','first_mismatch':mismatch}
    if(rc!=0 or s['status']!='PASS_RK4_BOUNDED_SUM_MACHINE_NOT_HISTORICAL' or
       s['checkpoints']!='54' or s['arithmetic_ops']!='50' or
       s['iterations']!='2' or s['back_edge_count']!='1' or s['decisions']!='2' or
       s['end_pc']!='3305' or s['end_pointer']!='0273' or
       s['actual_cpu_run']!='1' or s['hardware_oracle']!='NO'):
        return {'status':'HOLD_H115_B16_R1','reason':'NATIVE_SESSION_DRIFT','native_rc':rc,'session':s}
    tt=rows(files['NATIVE_TRACE.tsv'])
    need(len(tt)==int(s['steps']),'NATIVE_TRACE_LENGTH')
    need(all(r['gate']=='CONTINUE' for r in tt),'UNEXPECTED_CPU_STOP')
    need(not any(0o240<=int(r['pc_before'],8)<=0o273 for r in tt),'RAW_USER_INSTRUCTION_FETCH')
    need(not any(int(r['pc_before'],8)==0o3574 for r in tt),'UNPRINTED_3574')
    return {'status':'PASS_H115_B16_R1_BOUNDED_SUM_RK4_NOT_HISTORICAL',
        'program':'classical RK4 f(y)=-y','step':'1/4',
        'iterations':2,'cpu_sessions':1,'native_steps':len(tt),'arithmetic_ops':50,
        'conditional_decisions':2,'machine_back_edges':1,'dispatcher_checkpoints':54,
        'first_y':'1595/2048','final_y':'2544025/4194304','final_t':'1/2',
        'historical_status':'SYNTHETIC_PRIVATE_FP_ROM','hardware_oracle':'NO',
        'historical_3574':'UNFILLED','stop_policy':'BEFORE_USER_STOP_SENTINEL'}
